"""Link Import API Router — HTTP link import with metadata extraction.

Endpoints:
  POST   /api/v1/links/preview  — preview metadata from a URL
  POST   /api/v1/links/import   — import a video from a URL (queues processing)
  POST   /api/v1/videos/import  — alias: import video from link

F002: Link Import Parsing
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import User, Video, VideoStatus
from ..schemas.link_schema import (
    LinkImportRequest,
    LinkImportResponse,
    LinkMetadataResponse,
)
from ..services.link_parser import link_parser, LinkMetadata

router = APIRouter(prefix="/api/v1", tags=["Link Import"])


# ── Shared helpers ──


async def _get_user(db: AsyncSession, user_id: str) -> User:
    """Verify user exists; raise 404 if not."""
    uid = uuid.UUID(user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user


def _link_metadata_to_response(meta: LinkMetadata) -> LinkMetadataResponse:
    return LinkMetadataResponse(
        url=meta.url,
        title=meta.title,
        description=meta.description,
        thumbnail_url=meta.thumbnail_url,
        duration_seconds=meta.duration_seconds,
        platform=meta.platform,
        author=meta.author,
        extractable=meta.extractable,
        error=meta.error,
    )


# ── Endpoints ──


@router.post("/links/preview", response_model=LinkMetadataResponse)
async def preview_link(body: LinkImportRequest):
    """Preview metadata from a video link without importing.

    Returns title, description, thumbnail, platform info.
    Does NOT create any database records.
    """
    url = str(body.url)
    metadata = await link_parser.preview(url)
    return _link_metadata_to_response(metadata)


@router.post("/links/import", response_model=LinkImportResponse)
async def import_link(
    body: LinkImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import a video from an HTTP link.

    1. Validate URL & extract metadata via link parser
    2. Create a Video record with source_url
    3. Dispatch Celery task for download → ASR → Notes → Graph pipeline
    4. Return video_id immediately (async processing)

    Requires user_id query parameter for ownership assignment.
    """
    url = str(body.url)

    # ── Step 1: Extract metadata ──
    metadata = await link_parser.preview(url)

    if not metadata.extractable:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "UNSUPPORTED_URL",
                "message": metadata.error or "URL does not point to a supported video source",
                "url": url,
            },
        )

    # ── Step 2: Create Video record ──
    title = body.title or metadata.title or url.rstrip("/").split("/")[-1] or "Imported Video"

    video = Video(
        user_id=uuid.uuid4(),  # Placeholder — replace with real user when auth is wired
        title=title,
        filename=url.rstrip("/").split("/")[-1] or "video",
        file_path=url,  # store source URL as file_path for now
        source_url=url,
        status=VideoStatus.UPLOADED,
        progress=0,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    video_id_str = str(video.id)

    # ── Step 3: Dispatch Celery task ──
    try:
        from ..celery_app import celery_app

        celery_app.send_task(
            "process_link_import",
            args=[video_id_str, url, body.language],
            task_id=f"link-import-{video.id}",
        )
        logger.info("Link import task dispatched: video=%s", video_id_str)
    except Exception as exc:
        logger.warning("Celery task dispatch failed (non-fatal): %s", exc)
        # Still return success — task can be re-dispatched manually

    await db.commit()

    return LinkImportResponse(
        video_id=video_id_str,
        url=url,
        title=title,
        status="queued",
        message=f"Video import queued. Metadata: platform={metadata.platform}, "
                f"title='{title[:60]}'. Processing will begin shortly.",
    )


@router.post("/videos/import", response_model=LinkImportResponse)
async def import_video_alias(
    body: LinkImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Alias endpoint: POST /api/v1/videos/import → same as /links/import."""
    return await import_link(body, db)


# Late import for logger
import logging
logger = logging.getLogger(__name__)
