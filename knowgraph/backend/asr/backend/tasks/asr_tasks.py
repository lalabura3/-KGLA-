"""Celery tasks for the ASR pipeline.

Orchestrates the full audio transcription pipeline asynchronously.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

import redis.asyncio as aioredis

from backend.services.asr_service import asr_service
from backend.database import async_session_factory, get_settings
from backend.models import Video, VideoSegment, VideoStatus

logger = logging.getLogger(__name__)

settings = get_settings()

# This module is imported by Celery worker; the Celery app instance
# is expected to be configured at backend/celery_app.py


async def _update_progress(video_id: uuid.UUID, stage: str, progress: int) -> None:
    """Push progress update via Redis pub/sub for WebSocket consumers."""
    import json as _json

    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(
            f"video:{video_id}:progress",
            _json.dumps({"stage": stage, "progress": progress}),
        )
        await r.close()
    except Exception:
        pass  # Non-critical


async def _update_video_progress(video_id: uuid.UUID, progress: int) -> None:
    """Write progress to DB so polling endpoint works."""
    async with async_session_factory() as db:
        from sqlalchemy import select

        result = await db.execute(select(Video).where(Video.id == video_id))
        video = result.scalar_one_or_none()
        if video:
            video.progress = progress
            await db.commit()


async def process_video_asr(
    video_id_str: str,
    video_path_str: str,
    language: str = "zh",
) -> dict:
    """ASR pipeline entry point (async).

    Args:
        video_id_str: UUID of the Video record.
        video_path_str: Filesystem path to the uploaded video file.
        language: Language code (zh, en, etc.).

    Returns:
        {"status": "completed"|"failed", "segments": int, "error": str|None}
    """
    video_id = uuid.UUID(video_id_str)
    video_path = Path(video_path_str)

    async def on_progress(stage: str, progress: int):
        await _update_progress(video_id, stage, progress)
        await _update_video_progress(video_id, progress)

    try:
        # Update status → PROCESSING
        async with async_session_factory() as db:
            from sqlalchemy import select

            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return {"status": "failed", "error": f"Video {video_id} not found"}

            video.status = VideoStatus.PROCESSING
            video.progress = 0
            await db.commit()

        # Run ASR pipeline
        asr_result = await asr_service.process(
            video_path=video_path,
            video_id=video_id,
            language=language,
            run_vad=True,
            progress_callback=on_progress,
        )

        # Persist segments
        async with async_session_factory() as db:
            # Delete old segments if re-processing
            from sqlalchemy import delete, select

            await db.execute(
                delete(VideoSegment).where(VideoSegment.video_id == video_id)
            )

            for seg in asr_result.segments:
                db_segment = VideoSegment(
                    video_id=video_id,
                    segment_index=seg.index,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text,
                    confidence=seg.confidence,
                    words=seg.words,
                    speaker_id=seg.speaker_id,
                )
                db.add(db_segment)

            # Update video
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if video:
                video.status = VideoStatus.COMPLETED
                video.duration = asr_result.duration
                video.progress = 100

            await db.commit()

        await on_progress("complete", 100)

        logger.info(
            "ASR completed: video=%s, %d segments, %.1fs",
            video_id,
            len(asr_result.segments),
            asr_result.duration,
        )

        return {
            "status": "completed",
            "segments": len(asr_result.segments),
            "duration": asr_result.duration,
            "error": None,
        }

    except Exception as exc:
        logger.exception("ASR pipeline failed for video %s: %s", video_id, exc)

        # Mark as FAILED
        try:
            async with async_session_factory() as db:
                from sqlalchemy import select

                result = await db.execute(select(Video).where(Video.id == video_id))
                video = result.scalar_one_or_none()
                if video:
                    video.status = VideoStatus.FAILED
                    video.error_message = str(exc)
                    await db.commit()
        except Exception as db_exc:
            logger.error("Failed to update video status: %s", db_exc)

        return {"status": "failed", "segments": 0, "error": str(exc)}


# ── Celery task wrapper (sync → async bridge) ──
# This is the function that Celery will call.
# It wraps the async pipeline in an event loop.


def process_video_asr_task(video_id: str, video_path: str, language: str = "zh") -> dict:
    """Celery task entry point — runs the async ASR pipeline."""
    return asyncio.run(process_video_asr(video_id, video_path, language))
