"""ASR API router — segment preview, manual correction, and progress endpoints.

Endpoints:
  POST   /api/v1/videos/{id}/asr/transcribe   — kick off ASR
  GET    /api/v1/videos/{id}/asr/segments     — list segments with preview
  PATCH  /api/v1/videos/{id}/asr/segments/{s} — manually correct a segment
  GET    /api/v1/videos/{id}/asr/status       — pipeline progress
  WS     /ws/video/{id}/asr                    — WebSocket progress push
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Video, VideoSegment, VideoStatus

router = APIRouter(prefix="/api/v1/videos", tags=["ASR"])


# ── Pydantic schemas ──


class TranscribeRequest(BaseModel):
    language: str = Field(default="zh", description="Language code (zh, en, etc.)")


class TranscribeResponse(BaseModel):
    video_id: str
    status: str
    message: str


class SegmentOut(BaseModel):
    id: str
    segment_index: int
    start_time: float
    end_time: float
    text: str
    confidence: float
    words: list[str] = []
    speaker_id: str | None = None
    is_manually_edited: bool = False

    class Config:
        from_attributes = True


class SegmentPreview(BaseModel):
    """Preview data for a segment, including context."""

    segment: SegmentOut
    prev_text: str | None = None  # Previous segment text for context
    next_text: str | None = None  # Next segment text for context


class SegmentCorrectionRequest(BaseModel):
    text: str | None = None
    start_time: float | None = None
    end_time: float | None = None


class SegmentCorrectionResponse(BaseModel):
    id: str
    segment_index: int
    text: str
    is_manually_edited: bool
    original_text: str | None = None


class ASRStatusResponse(BaseModel):
    video_id: str
    status: str
    progress: int
    segment_count: int = 0
    duration: float | None = None
    error: str | None = None


# ── Endpoints ──


@router.post("/{video_id}/asr/transcribe", response_model=TranscribeResponse)
async def start_transcription(
    video_id: str,
    body: TranscribeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Kick off ASR transcription for a video via Celery."""
    vid = uuid.UUID(video_id)
    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    if video.status == VideoStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="ASR already in progress")

    # Reset segments if re-transcribing
    if video.status == VideoStatus.COMPLETED:
        from sqlalchemy import delete

        await db.execute(delete(VideoSegment).where(VideoSegment.video_id == vid))

    video.status = VideoStatus.PROCESSING
    video.progress = 0
    await db.commit()

    # Dispatch Celery task
    from ..celery_app import celery_app

    celery_app.send_task(
        "process_video_asr",
        args=[str(vid), video.file_path, body.language],
        task_id=f"asr-{vid}",  # Idempotent
    )

    return TranscribeResponse(
        video_id=video_id,
        status="processing",
        message="ASR transcription started",
    )


@router.get("/{video_id}/asr/status", response_model=ASRStatusResponse)
async def get_asr_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get ASR pipeline progress."""
    vid = uuid.UUID(video_id)
    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Count existing segments
    seg_result = await db.execute(
        select(VideoSegment).where(VideoSegment.video_id == vid)
    )
    segments = seg_result.scalars().all()

    return ASRStatusResponse(
        video_id=video_id,
        status=video.status.value,
        progress=video.progress,
        segment_count=len(segments),
        duration=video.duration,
        error=video.error_message,
    )


@router.get("/{video_id}/asr/segments", response_model=list[SegmentPreview])
async def list_segments(
    video_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List ASR segments with surrounding context for preview."""
    vid = uuid.UUID(video_id)
    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Fetch segments ordered by index
    seg_result = await db.execute(
        select(VideoSegment)
        .where(VideoSegment.video_id == vid)
        .order_by(VideoSegment.segment_index)
        .offset(offset)
        .limit(limit)
    )
    segments = seg_result.scalars().all()

    previews = []
    for i, seg in enumerate(segments):
        prev_text = segments[i - 1].text if i > 0 else None
        # For next text, check inline (not perfect for pagination but acceptable)
        next_seg = None
        if i + 1 < len(segments):
            next_seg = segments[i + 1]
        # If at edge of page, query one more
        elif i + 1 == len(segments):
            extra = await db.execute(
                select(VideoSegment)
                .where(
                    VideoSegment.video_id == vid,
                    VideoSegment.segment_index > seg.segment_index,
                )
                .order_by(VideoSegment.segment_index)
                .limit(1)
            )
            next_seg = extra.scalar_one_or_none()

        previews.append(
            SegmentPreview(
                segment=SegmentOut(
                    id=str(seg.id),
                    segment_index=seg.segment_index,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    text=seg.text,
                    confidence=seg.confidence,
                    words=seg.words or [],
                    speaker_id=seg.speaker_id,
                    is_manually_edited=seg.is_manually_edited,
                ),
                prev_text=prev_text,
                next_text=next_seg.text if next_seg else None,
            )
        )

    return previews


@router.patch(
    "/{video_id}/asr/segments/{segment_id}",
    response_model=SegmentCorrectionResponse,
)
async def correct_segment(
    video_id: str,
    segment_id: str,
    correction: SegmentCorrectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually correct an ASR segment (text, timing)."""
    vid = uuid.UUID(video_id)
    sid = uuid.UUID(segment_id)

    result = await db.execute(
        select(VideoSegment).where(
            VideoSegment.id == sid,
            VideoSegment.video_id == vid,
        )
    )
    segment = result.scalar_one_or_none()

    if not segment:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    if correction.text is not None:
        if not segment.is_manually_edited:
            segment.original_text = segment.text  # Preserve original
            segment.is_manually_edited = True
        segment.text = correction.text

    if correction.start_time is not None:
        segment.start_time = correction.start_time
        segment.is_manually_edited = True

    if correction.end_time is not None:
        segment.end_time = correction.end_time
        segment.is_manually_edited = True

    await db.commit()
    await db.refresh(segment)

    return SegmentCorrectionResponse(
        id=str(segment.id),
        segment_index=segment.segment_index,
        text=segment.text,
        is_manually_edited=segment.is_manually_edited,
        original_text=segment.original_text,
    )


# ── WebSocket progress endpoint ──


@router.websocket("/ws/video/{video_id}/asr")
async def asr_progress_ws(websocket: WebSocket, video_id: str):
    """WebSocket endpoint for real-time ASR progress updates.

    Subscribes to Redis pub/sub channel `video:{video_id}:progress`.
    """
    await websocket.accept()

    vid = uuid.UUID(video_id)
    import redis.asyncio as aioredis

    from ..config import get_settings

    settings = get_settings()

    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"video:{vid}:progress")

        # Send initial state
        async with async_session_factory() as db:
            from sqlalchemy import select

            from ..database import async_session_factory

            result = await db.execute(select(Video).where(Video.id == vid))
            video = result.scalar_one_or_none()
            if video:
                await websocket.send_json(
                    {
                        "event": "status",
                        "status": video.status.value,
                        "progress": video.progress,
                    }
                )

        # Stream progress events
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json({"event": "progress", **data})

                if data.get("stage") == "complete":
                    await websocket.send_json(
                        {"event": "complete", "progress": 100}
                    )
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"event": "error", "error": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await pubsub.unsubscribe(f"video:{vid}:progress")
            await r.close()
        except Exception:
            pass
