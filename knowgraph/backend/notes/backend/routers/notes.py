"""Notes API router — note generation, retrieval, and editing.

Endpoints:
  POST   /api/v1/videos/{id}/notes/generate  — kick off note generation
  GET    /api/v1/videos/{id}/notes            — get generated note
  GET    /api/v1/videos/{id}/notes/sections   — list note sections
  PATCH  /api/v1/videos/{id}/notes/sections/{sid} — edit a section
  GET    /api/v1/videos/{id}/notes/status     — note generation progress
  DELETE /api/v1/videos/{id}/notes            — delete and re-generate
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Note, NoteSection

router = APIRouter(prefix="/api/v1/videos", tags=["Notes"])


# ── Pydantic schemas ──


class GenerateNotesRequest(BaseModel):
    """Request to trigger note generation."""
    force: bool = Field(default=False, description="Force re-generation even if notes exist")


class GenerateNotesResponse(BaseModel):
    video_id: str
    status: str
    message: str


class NoteSectionOut(BaseModel):
    id: str
    section_index: int
    heading: str
    content: str
    start_time: float
    end_time: float | None = None
    key_points: list[str] = []
    hallucination_flags: list[str] = []
    confidence: float = 1.0

    class Config:
        from_attributes = True


class NoteOut(BaseModel):
    id: str
    video_id: str
    title: str
    summary: str
    keywords: list[str] = []
    metadata_: dict | None = Field(None, alias="metadata")
    hallucination_score: float = 0.0
    language: str = "zh"
    word_count: int = 0
    sections: list[NoteSectionOut] = []

    class Config:
        from_attributes = True


class NoteStatusResponse(BaseModel):
    video_id: str
    has_notes: bool
    note_id: str | None = None
    section_count: int = 0
    hallucination_score: float = 0.0
    word_count: int = 0
    generated_at: str | None = None


class SectionUpdateRequest(BaseModel):
    heading: str | None = None
    content: str | None = None
    key_points: list[str] | None = None


class SectionUpdateResponse(BaseModel):
    id: str
    section_index: int
    heading: str
    content: str
    updated: bool = True


# ── Endpoints ──


@router.post("/{video_id}/notes/generate", response_model=GenerateNotesResponse)
async def start_note_generation(
    video_id: str,
    body: GenerateNotesRequest = GenerateNotesRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Kick off AI note generation via Celery."""
    vid = uuid.UUID(video_id)

    # Check video exists
    from ..models import Video

    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Check if notes already exist
    existing = await db.execute(select(Note).where(Note.video_id == vid))
    existing_note = existing.scalar_one_or_none()

    if existing_note and not body.force:
        raise HTTPException(
            status_code=409,
            detail=f"Notes already exist for video {video_id}. Use force=true to re-generate.",
        )

    # Dispatch Celery task
    from ..celery_app import celery_app

    celery_app.send_task(
        "generate_notes",
        args=[str(vid)],
        task_id=f"note-{vid}",  # Idempotent
    )

    return GenerateNotesResponse(
        video_id=video_id,
        status="processing",
        message="Note generation started",
    )


@router.get("/{video_id}/notes", response_model=NoteOut)
async def get_notes(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the generated note for a video, including all sections."""
    vid = uuid.UUID(video_id)

    result = await db.execute(
        select(Note).where(Note.video_id == vid)
    )
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail=f"No notes found for video {video_id}")

    # Eager-load sections
    sections_result = await db.execute(
        select(NoteSection)
        .where(NoteSection.note_id == note.id)
        .order_by(NoteSection.section_index)
    )
    sections = sections_result.scalars().all()

    return NoteOut(
        id=str(note.id),
        video_id=str(note.video_id),
        title=note.title,
        summary=note.summary,
        keywords=note.keywords or [],
        metadata=note.metadata_,
        hallucination_score=note.hallucination_score,
        language=note.language,
        word_count=note.word_count,
        sections=[
            NoteSectionOut(
                id=str(s.id),
                section_index=s.section_index,
                heading=s.heading,
                content=s.content,
                start_time=s.start_time,
                end_time=s.end_time,
                key_points=s.key_points or [],
                hallucination_flags=s.hallucination_flags or [],
                confidence=s.confidence,
            )
            for s in sections
        ],
    )


@router.get("/{video_id}/notes/sections", response_model=list[NoteSectionOut])
async def list_note_sections(
    video_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List note sections with pagination."""
    vid = uuid.UUID(video_id)

    # Find the note for this video
    note_result = await db.execute(select(Note).where(Note.video_id == vid))
    note = note_result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail=f"No notes found for video {video_id}")

    sections_result = await db.execute(
        select(NoteSection)
        .where(NoteSection.note_id == note.id)
        .order_by(NoteSection.section_index)
        .offset(offset)
        .limit(limit)
    )
    sections = sections_result.scalars().all()

    return [
        NoteSectionOut(
            id=str(s.id),
            section_index=s.section_index,
            heading=s.heading,
            content=s.content,
            start_time=s.start_time,
            end_time=s.end_time,
            key_points=s.key_points or [],
            hallucination_flags=s.hallucination_flags or [],
            confidence=s.confidence,
        )
        for s in sections
    ]


@router.patch(
    "/{video_id}/notes/sections/{section_id}",
    response_model=SectionUpdateResponse,
)
async def update_note_section(
    video_id: str,
    section_id: str,
    update: SectionUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually edit a note section (heading, content, key_points)."""
    vid = uuid.UUID(video_id)
    sid = uuid.UUID(section_id)

    # Verify note exists for this video
    note_result = await db.execute(select(Note).where(Note.video_id == vid))
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail=f"No notes found for video {video_id}")

    # Fetch the section
    section_result = await db.execute(
        select(NoteSection).where(
            NoteSection.id == sid,
            NoteSection.note_id == note.id,
        )
    )
    section = section_result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    if update.heading is not None:
        section.heading = update.heading
    if update.content is not None:
        section.content = update.content
    if update.key_points is not None:
        section.key_points = update.key_points

    await db.commit()
    await db.refresh(section)

    return SectionUpdateResponse(
        id=str(section.id),
        section_index=section.section_index,
        heading=section.heading,
        content=section.content,
    )


@router.get("/{video_id}/notes/status", response_model=NoteStatusResponse)
async def get_note_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get note generation status and metadata."""
    vid = uuid.UUID(video_id)

    result = await db.execute(select(Note).where(Note.video_id == vid))
    note = result.scalar_one_or_none()

    if not note:
        return NoteStatusResponse(
            video_id=video_id,
            has_notes=False,
        )

    # Count sections
    sections_result = await db.execute(
        select(NoteSection).where(NoteSection.note_id == note.id)
    )
    sections = sections_result.scalars().all()

    return NoteStatusResponse(
        video_id=video_id,
        has_notes=True,
        note_id=str(note.id),
        section_count=len(sections),
        hallucination_score=note.hallucination_score,
        word_count=note.word_count,
        generated_at=note.created_at.isoformat() if note.created_at else None,
    )


@router.delete("/{video_id}/notes", status_code=204)
async def delete_notes(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete generated notes for a video (for re-generation)."""
    vid = uuid.UUID(video_id)

    result = await db.execute(select(Note).where(Note.video_id == vid))
    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail=f"No notes found for video {video_id}")

    # Cascade delete sections via ORM relationship
    await db.delete(note)
    await db.commit()


# ── WebSocket progress endpoint ──


@router.websocket("/ws/video/{video_id}/notes")
async def note_progress_ws(websocket: WebSocket, video_id: str):
    """WebSocket endpoint for real-time note generation progress.

    Subscribes to Redis pub/sub channel `video:{video_id}:note_progress`.
    """
    await websocket.accept()

    vid = uuid.UUID(video_id)

    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"video:{vid}:note_progress")

        # Send initial check
        from ..database import async_session_factory
        from sqlalchemy import select

        async with async_session_factory() as db:
            result = await db.execute(select(Note).where(Note.video_id == vid))
            note = result.scalar_one_or_none()
            if note:
                await websocket.send_json(
                    {
                        "event": "status",
                        "has_notes": True,
                        "note_id": str(note.id),
                    }
                )
            else:
                await websocket.send_json(
                    {"event": "status", "has_notes": False}
                )

        import redis.asyncio as aioredis

        from ..config import get_settings

        settings = get_settings()

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
            await pubsub.unsubscribe(f"video:{vid}:note_progress")
            await r.close()
        except Exception:
            pass
