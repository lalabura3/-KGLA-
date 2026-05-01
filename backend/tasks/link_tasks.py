"""Celery task for link import processing pipeline.

Link import flow:
  1. Download video from URL (if direct file link) / queue download
  2. Extract audio (FFmpeg)
  3. Run VAD
  4. Transcribe via Whisper
  5. Persist ASR segments to DB
  6. Chain → generate notes → extract graph

F002: Link Import Parsing — async processing task
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

import aiohttp
import redis.asyncio as aioredis

from backend.config import get_settings
from backend.database import async_session_factory
from backend.models import Video, VideoSegment, VideoStatus
from backend.services.asr_service import asr_service

logger = logging.getLogger(__name__)

settings = get_settings()


async def _update_progress(video_id: uuid.UUID, stage: str, progress: int) -> None:
    """Push progress updates via Redis pub/sub."""
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(
            f"video:{video_id}:link_import_progress",
            json.dumps({"stage": stage, "progress": progress}),
        )
        await r.close()
    except Exception:
        pass


async def _download_video(url: str, dest_dir: Path) -> Path:
    """Download video from URL to a local temporary file.

    Returns the path to the downloaded file.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename from URL
    filename = url.rstrip("/").split("/")[-1]
    if not filename or "." not in filename[-10:]:
        filename = f"imported_{uuid.uuid4().hex[:8]}.mp4"

    dest_path = dest_dir / filename

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=3600),  # 1h for large files
            headers={"User-Agent": "StudyAI/0.1"},
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"Download failed: HTTP {resp.status} from {url}"
                )

            total = 0
            with open(dest_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):  # 1MB chunks
                    f.write(chunk)
                    total += len(chunk)

            logger.info(
                "Downloaded: %s → %s (%d bytes)", url, dest_path.name, total
            )

    return dest_path


async def process_link_import(
    video_id_str: str,
    url: str,
    language: str = "zh",
) -> dict:
    """Async link import pipeline.

    Args:
        video_id_str: UUID of the Video record.
        url: Source URL of the video.
        language: Language code for ASR.

    Returns:
        {"status": "completed"|"failed", "segments_count": int, "error": str|None}
    """
    video_id = uuid.UUID(video_id_str)

    async def on_progress(stage: str, progress: int):
        await _update_progress(video_id, stage, progress)

    tmp_dir = Path(tempfile.gettempdir()) / "studyai_imports" / video_id_str
    video_path: Path | None = None

    try:
        # Step 1: Update status
        async with async_session_factory() as db:
            from sqlalchemy import select

            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return {"status": "failed", "error": f"Video {video_id} not found"}

            video.status = VideoStatus.PROCESSING
            video.progress = 5
            await db.commit()

        await on_progress("downloading", 10)

        # Step 2: Download video from URL
        video_path = await _download_video(url, tmp_dir)

        # Update video record with real file_path
        async with async_session_factory() as db:
            video = (await db.execute(select(Video).where(Video.id == video_id))).scalar_one()
            video.file_path = str(video_path)
            video.filename = video_path.name
            video.progress = 20
            await db.commit()

        await on_progress("extracting", 30)

        # Step 3: Run ASR pipeline
        asr_result = await asr_service.process(
            video_path=video_path,
            video_id=video_id,
            language=language,
            run_vad=True,
            progress_callback=on_progress,
        )

        await on_progress("persisting", 90)

        # Step 4: Persist ASR segments to DB
        async with async_session_factory() as db:
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

            # Update video record
            video = (await db.execute(select(Video).where(Video.id == video_id))).scalar_one()
            video.status = VideoStatus.COMPLETED
            video.progress = 100
            video.duration = asr_result.duration

            await db.commit()

        await on_progress("complete", 100)

        logger.info(
            "Link import pipeline complete: video=%s, segments=%d, duration=%.1fs",
            video_id, len(asr_result.segments), asr_result.duration,
        )

        return {
            "status": "completed",
            "segments_count": len(asr_result.segments),
            "duration": asr_result.duration,
            "error": None,
        }

    except Exception as exc:
        logger.exception("Link import failed for video %s: %s", video_id, exc)

        # Update video status to FAILED
        try:
            async with async_session_factory() as db:
                video = (await db.execute(select(Video).where(Video.id == video_id))).scalar_one()
                video.status = VideoStatus.FAILED
                video.error_message = str(exc)[:1000]
                await db.commit()
        except Exception:
            pass

        return {"status": "failed", "error": str(exc)}

    finally:
        # Cleanup temp files
        if video_path and video_path.exists():
            try:
                video_path.unlink()
            except OSError:
                pass


# ── Celery task wrapper (sync → async bridge) ──


def process_link_import_task(video_id: str, url: str, language: str = "zh") -> dict:
    """Celery task entry point — runs the async link import pipeline."""
    return asyncio.run(process_link_import(video_id, url, language))
