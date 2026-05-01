"""Video API Router — upload, ASR trigger, segment retrieval.

Endpoints:
  POST   /api/v1/videos/upload              — upload a video file
  POST   /api/v1/videos/{id}/asr            — trigger ASR processing
  GET    /api/v1/videos/{id}/segments       — get ASR segments (paginated)
  GET    /api/v1/videos/{id}/segments/raw   — raw ASR result (all segments, no pagination)
  GET    /api/v1/videos/{id}/progress       — processing progress
  DELETE /api/v1/videos/{id}                — delete video + all data
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import Video, VideoSegment, VideoStatus
from ..schemas.asr_schema import VideoSegmentRead, VideoSegmentListResponse

router = APIRouter(prefix="/api/v1", tags=["Videos"])

logger = logging.getLogger(__name__)


# ── Pydantic schemas ──


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str
    title: str
    file_size_bytes: int
    status: str = "uploaded"


class ASRTriggerResponse(BaseModel):
    video_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    video_id: str
    status: str
    progress: int
    duration: float | None = None
    error_message: str | None = None


class RawSegmentResponse(BaseModel):
    """Single raw ASR segment with full word detail."""
    index: int
    start: float
    end: float
    text: str
    confidence: float = 0.0
    words: list[str] | None = None
    speaker_id: str | None = None


class RawASRResponse(BaseModel):
    """Full raw ASR result for a video."""
    video_id: str
    language: str = "zh"
    duration: float = 0.0
    segments: list[RawSegmentResponse] = []
    total: int = 0


# ── Endpoints ──


@router.post("/videos/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    user_id: str = Form(default=""),  # Optional until auth is wired
    db: AsyncSession = Depends(get_db),
):
    """Upload a video file.

    Saves to settings.upload_dir, creates a Video DB record,
    returns video_id for subsequent ASR trigger.
    """
    # Validate file type
    ALLOWED_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv"}
    original_name = file.filename or "video.mp4"
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save file
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_id = uuid.uuid4()
    safe_filename = f"{video_id}{ext}"
    file_path = upload_dir / safe_filename

    file_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
            file_size += len(chunk)

    # Create video record
    display_title = title or original_name.rsplit(".", 1)[0]

    video = Video(
        id=video_id,
        user_id=uuid.UUID(user_id) if user_id else uuid.uuid4(),
        title=display_title,
        filename=original_name,
        file_path=str(file_path),
        status=VideoStatus.UPLOADED,
        progress=0,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    logger.info(
        "Video uploaded: id=%s, filename=%s, size=%d",
        video_id, original_name, file_size,
    )

    return VideoUploadResponse(
        video_id=str(video_id),
        filename=original_name,
        title=display_title,
        file_size_bytes=file_size,
        status="uploaded",
    )


@router.post("/videos/{video_id}/asr", response_model=ASRTriggerResponse)
async def trigger_asr(
    video_id: str,
    language: str = Query(default="zh"),
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Trigger ASR processing for an uploaded video.

    Dispatches a Celery task that runs the full pipeline:
    extract audio → VAD → Whisper transcription → persist segments.
    """
    vid = uuid.UUID(video_id)

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    if not Path(video.file_path).exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found on disk: {video.file_path}",
        )

    # Check idempotency
    existing = await db.execute(
        select(VideoSegment).where(VideoSegment.video_id == vid).limit(1)
    )
    if existing.first() is not None and not force:
        raise HTTPException(
            status_code=409,
            detail=f"ASR segments already exist for video {video_id}. "
                   f"Use force=true to re-process.",
        )

    # Dispatch Celery task
    from ..celery_app import celery_app

    celery_app.send_task(
        "process_video_asr",
        args=[video_id, language, force],
        task_id=f"asr-{vid}",
    )

    return ASRTriggerResponse(
        video_id=video_id,
        status="processing",
        message="ASR pipeline dispatched",
    )


@router.get("/videos/{video_id}/segments", response_model=VideoSegmentListResponse)
async def get_segments(
    video_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated ASR segments for a video."""
    vid = uuid.UUID(video_id)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(VideoSegment).where(
            VideoSegment.video_id == vid
        )
    )
    total = count_result.scalar() or 0

    # Fetch segments
    result = await db.execute(
        select(VideoSegment)
        .where(VideoSegment.video_id == vid)
        .order_by(VideoSegment.segment_index)
        .offset(offset)
        .limit(limit)
    )
    segments = result.scalars().all()

    return VideoSegmentListResponse(
        items=[
            VideoSegmentRead(
                id=s.id,
                video_id=s.video_id,
                segment_index=s.segment_index,
                start_time=s.start_time,
                end_time=s.end_time,
                text=s.text,
                confidence=s.confidence,
                words=s.words,
                speaker_id=s.speaker_id,
                is_manually_edited=s.is_manually_edited,
                original_text=s.original_text,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in segments
        ],
        total=total,
        video_id=vid,
    )


@router.get("/videos/{video_id}/segments/raw", response_model=RawASRResponse)
async def get_raw_segments(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get complete raw ASR result — all segments with full detail.

    No pagination. Used for downstream processing (notes, graph) and debugging.
    """
    vid = uuid.UUID(video_id)

    # Get video
    video_result = await db.execute(select(Video).where(Video.id == vid))
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Get all segments
    result = await db.execute(
        select(VideoSegment)
        .where(VideoSegment.video_id == vid)
        .order_by(VideoSegment.segment_index)
    )
    segments = result.scalars().all()

    return RawASRResponse(
        video_id=video_id,
        duration=video.duration or 0.0,
        segments=[
            RawSegmentResponse(
                index=s.segment_index,
                start=s.start_time,
                end=s.end_time,
                text=s.text,
                confidence=s.confidence,
                words=s.words,
                speaker_id=s.speaker_id,
            )
            for s in segments
        ],
        total=len(segments),
    )


@router.get("/videos/{video_id}/progress", response_model=ProgressResponse)
async def get_progress(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get processing progress for a video."""
    vid = uuid.UUID(video_id)

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    return ProgressResponse(
        video_id=video_id,
        status=video.status.value,
        progress=video.progress,
        duration=video.duration,
        error_message=video.error_message,
    )


@router.delete("/videos/{video_id}", status_code=204)
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a video and all associated data (segments, notes, graph, file)."""
    vid = uuid.UUID(video_id)

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Delete file from disk
    try:
        file_path = Path(video.file_path)
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass

    # Cascade delete via ORM
    await db.delete(video)
    await db.commit()


# ── WebSocket progress endpoint ──


@router.websocket("/ws/video/{video_id}/asr")
async def asr_progress_ws(websocket: WebSocket, video_id: str):
    """WebSocket endpoint for real-time ASR processing progress.

    Subscribes to Redis pub/sub channel `video:{video_id}:asr_progress`.
    """
    await websocket.accept()

    vid = uuid.UUID(video_id)

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"video:{vid}:asr_progress")

        # Send initial status
        async with async_session_factory() as db:
            result = await db.execute(select(Video).where(Video.id == vid))
            video = result.scalar_one_or_none()
            if video:
                await websocket.send_json({
                    "event": "status",
                    "video_id": video_id,
                    "status": video.status.value,
                    "progress": video.progress,
                })

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
            await pubsub.unsubscribe(f"video:{vid}:asr_progress")
            await r.close()
        except Exception:
            pass
