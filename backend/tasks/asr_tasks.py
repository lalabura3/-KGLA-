"""Celery task for ASR pipeline — full flow with segment persistence.

ASR Pipeline:
  1. Load video record from DB
  2. Extract audio via FFmpeg
  3. Run Voice Activity Detection (Silero VAD)
  4. Transcribe via Whisper HTTP service
  5. Post-process (term dictionary + VAD alignment)
  6. Persist ALL segments to video_segments table
  7. Update video status & progress via Redis pub/sub

Supports idempotent re-run: skip if video already has segments.

F002-ASR: ASR Raw Result Persistence
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path

import redis.asyncio as aioredis

from backend.config import get_settings
from backend.database import async_session_factory
from backend.models import Video, VideoSegment, VideoStatus
from backend.services.asr_service import asr_service, ASRResult

logger = logging.getLogger(__name__)

settings = get_settings()


async def _update_progress(video_id: uuid.UUID, stage: str, progress: int) -> None:
    """Push progress updates via Redis pub/sub."""
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(
            f"video:{video_id}:asr_progress",
            json.dumps({"stage": stage, "progress": progress}),
        )
        await r.close()
    except Exception:
        pass


async def _persist_segments(
    db,
    video_id: uuid.UUID,
    asr_result: ASRResult,
) -> int:
    """Persist ASR segments to video_segments table.

    Returns count of segments persisted.
    """
    from sqlalchemy import delete, select

    # Idempotency: remove existing segments before re-insert
    existing = await db.execute(
        select(VideoSegment).where(VideoSegment.video_id == video_id)
    )
    for old_seg in existing.scalars().all():
        await db.delete(old_seg)
    await db.flush()

    # Bulk insert all segments
    count = 0
    for seg in asr_result.segments:
        db_segment = VideoSegment(
            video_id=video_id,
            segment_index=seg.index,
            start_time=seg.start,
            end_time=seg.end,
            text=seg.text,
            confidence=seg.confidence,
            words=seg.words if seg.words else None,
            speaker_id=seg.speaker_id,
        )
        db.add(db_segment)
        count += 1

    # Batch-flush for performance
    await db.flush()

    logger.info(
        "Persisted %d segments for video=%s",
        count, video_id,
    )
    return count


async def process_video_asr(
    video_id_str: str,
    language: str = "zh",
    force: bool = False,
) -> dict:
    """Run the full ASR pipeline and persist segments.

    Args:
        video_id_str: UUID of the Video record.
        language: Language code (zh, en, etc.)
        force: If True, re-run even if segments already exist.

    Returns:
        {
            "status": "completed"|"failed",
            "segments_count": int,
            "duration": float,
            "error": str | None
        }
    """
    video_id = uuid.UUID(video_id_str)

    async def on_progress(stage: str, progress: int):
        await _update_progress(video_id, stage, progress)

    try:
        from sqlalchemy import select

        # ── Load video ──
        async with async_session_factory() as db:
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return {"status": "failed", "error": f"Video {video_id} not found"}

            # Idempotency check
            if not force:
                existing = await db.execute(
                    select(VideoSegment)
                    .where(VideoSegment.video_id == video_id)
                    .limit(1)
                )
                if existing.first() is not None:
                    logger.info(
                        "ASR already complete for video=%s, skipping", video_id
                    )
                    # Count existing
                    count_result = await db.execute(
                        select(VideoSegment).where(
                            VideoSegment.video_id == video_id
                        )
                    )
                    count = len(count_result.scalars().all())
                    return {
                        "status": "completed",
                        "segments_count": count,
                        "duration": video.duration,
                        "error": None,
                        "idempotent": True,
                    }

            video_path = Path(video.file_path)
            if not video_path.exists():
                return {
                    "status": "failed",
                    "error": f"Video file not found: {video.file_path}",
                }

            # Update status to PROCESSING
            video.status = VideoStatus.PROCESSING
            video.progress = 0
            await db.commit()

        await on_progress("extracting", 10)

        # ── Run ASR pipeline ──
        asr_result = await asr_service.process(
            video_path=video_path,
            video_id=video_id,
            language=language,
            run_vad=True,
            progress_callback=on_progress,
        )

        await on_progress("persisting", 90)

        # ── Persist segments to DB ──
        async with async_session_factory() as db:
            segments_count = await _persist_segments(db, video_id, asr_result)

            # Update video record
            video = (
                await db.execute(select(Video).where(Video.id == video_id))
            ).scalar_one()
            video.status = VideoStatus.COMPLETED
            video.progress = 100
            video.duration = asr_result.duration

            await db.commit()

        await on_progress("complete", 100)

        logger.info(
            "ASR pipeline complete: video=%s, segments=%d, duration=%.1fs",
            video_id, segments_count, asr_result.duration,
        )

        return {
            "status": "completed",
            "segments_count": segments_count,
            "duration": asr_result.duration,
            "error": None,
        }

    except Exception as exc:
        logger.exception("ASR pipeline failed for video %s: %s", video_id, exc)

        # Update video status to FAILED
        try:
            async with async_session_factory() as db:
                video = (
                    await db.execute(select(Video).where(Video.id == video_id))
                ).scalar_one()
                video.status = VideoStatus.FAILED
                video.error_message = str(exc)[:1000]
                await db.commit()
        except Exception:
            pass

        return {"status": "failed", "error": str(exc)}


# ── Celery task wrapper (sync → async bridge) ──


def process_video_asr_task(
    video_id: str, language: str = "zh", force: bool = False
) -> dict:
    """Celery task entry point — runs the async ASR pipeline.

    Task ID format: asr-{video_id}
    Queue: asr
    """
    return asyncio.run(process_video_asr(video_id, language, force))
