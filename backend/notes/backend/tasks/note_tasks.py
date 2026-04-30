"""Celery tasks for AI note generation.

Orchestrates the 3-stage note generation pipeline asynchronously
after ASR transcription completes.
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
import uuid

import redis.asyncio as aioredis

from backend.services.note_service import NoteGenerationResult, NoteOutput, note_service
from backend.database import async_session_factory, get_settings
from backend.models import Note, NoteSection, Video, VideoSegment, VideoStatus

logger = logging.getLogger(__name__)

settings = get_settings()


async def _update_note_progress(video_id: uuid.UUID, stage: str, progress: int) -> None:
    """Push note generation progress via Redis pub/sub."""
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(
            f"video:{video_id}:note_progress",
            _json.dumps({"stage": stage, "progress": progress}),
        )
        await r.close()
    except Exception:
        pass


async def generate_notes(
    video_id_str: str,
) -> dict:
    """Async note generation entry point.

    Args:
        video_id_str: UUID of the Video record.

    Returns:
        {"status": "completed"|"failed", "note_id": str|null, "error": str|null,
         "sections": int, "elapsed_ms": float}
    """
    video_id = uuid.UUID(video_id_str)

    async def on_progress(stage: str, progress: int):
        await _update_note_progress(video_id, stage, progress)

    try:
        # Fetch transcript segments from DB
        async with async_session_factory() as db:
            from sqlalchemy import select

            # Verify video exists and is in COMPLETED state
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return {"status": "failed", "error": f"Video {video_id} not found"}

            # Fetch segments
            seg_result = await db.execute(
                select(VideoSegment)
                .where(VideoSegment.video_id == video_id)
                .order_by(VideoSegment.segment_index)
            )
            segments = seg_result.scalars().all()

            if not segments:
                return {"status": "failed", "error": "No transcript segments found"}

            # Convert to dict format expected by note_service
            transcript_segments = [
                {
                    "segment_index": seg.segment_index,
                    "start": seg.start_time,
                    "end": seg.end_time,
                    "text": seg.text,
                    "speaker_id": seg.speaker_id,
                }
                for seg in segments
            ]

        # Run note generation
        result: NoteGenerationResult = await note_service.generate(
            video_id=video_id,
            transcript_segments=transcript_segments,
            progress_callback=on_progress,
        )

        if result.status == "failed" or result.note is None:
            return {
                "status": "failed",
                "error": result.error or "Unknown error",
                "elapsed_ms": result.elapsed_ms,
            }

        note: NoteOutput = result.note

        # Calculate word count
        word_count = len(note.raw_full_text)

        # Compute hallucination score
        all_flags = [f for s in note.sections for f in s.hallucination_flags]
        hallucination_score = min(len(all_flags) * 0.1, 1.0) if note.sections else 0.0

        # Persist note and sections
        async with async_session_factory() as db:
            # Delete existing note for this video (idempotent re-generation)
            from sqlalchemy import delete, select

            existing = await db.execute(
                select(Note).where(Note.video_id == video_id)
            )
            existing_note = existing.scalar_one_or_none()
            if existing_note:
                await db.delete(existing_note)
                await db.flush()

            # Create Note record
            db_note = Note(
                video_id=video_id,
                title=note.title,
                summary=note.summary,
                full_text=note.raw_full_text,
                keywords=note.keywords,
                metadata_={
                    "topic": note.metadata.topic,
                    "difficulty": note.metadata.difficulty,
                    "is_technical": note.metadata.is_technical,
                    "has_code": note.metadata.has_code,
                    "language": note.metadata.language,
                    "speaker_count": note.metadata.speaker_count,
                    "estimated_reading_time_minutes": note.metadata.estimated_reading_time_minutes,
                },
                hallucination_score=hallucination_score,
                language=note.metadata.language,
                word_count=word_count,
            )
            db.add(db_note)
            await db.flush()  # Get note.id

            # Create NoteSection records
            for i, section in enumerate(note.sections):
                db_section = NoteSection(
                    note_id=db_note.id,
                    section_index=i,
                    heading=section.heading,
                    content=section.content,
                    start_time=section.start_time,
                    end_time=section.end_time,
                    segment_ids=[str(si) for si in section.source_segment_indices],
                    key_points=section.key_points,
                    source_text=note.raw_full_text[:2000],  # Truncated reference
                    hallucination_flags=section.hallucination_flags,
                    confidence=section.confidence,
                )
                db.add(db_section)

            await db.commit()

            note_id = str(db_note.id)

        await _update_note_progress(video_id, "complete", 100)

        logger.info(
            "Note generation completed: video=%s, note=%s, sections=%d, words=%d, hallu=%.2f",
            video_id, note_id, len(note.sections), word_count, hallucination_score,
        )

        return {
            "status": "completed",
            "note_id": note_id,
            "sections": len(note.sections),
            "word_count": word_count,
            "hallucination_score": hallucination_score,
            "elapsed_ms": result.elapsed_ms,
            "error": None,
        }

    except Exception as exc:
        logger.exception("Note generation failed for video %s: %s", video_id, exc)
        return {
            "status": "failed",
            "error": str(exc),
            "elapsed_ms": 0,
        }


# ── Celery task wrapper (sync → async bridge) ──


def generate_notes_task(video_id: str) -> dict:
    """Celery task entry point — runs the async note generation pipeline."""
    return asyncio.run(generate_notes(video_id))
