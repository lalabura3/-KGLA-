"""Pydantic schemas for Video."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models import VideoStatus


class VideoCreate(BaseModel):
    """Request body for uploading/registering a video.

    File is uploaded via multipart form; this is the metadata payload.
    """
    title: str = Field(..., min_length=1, max_length=512, examples=["Lecture 3: Backpropagation"])
    source_url: str | None = Field(None, max_length=2048, examples=["https://youtube.com/watch?v=..."])
    language: str = Field("zh", pattern=r"^(zh|en|mixed)$")


class VideoStatusUpdate(BaseModel):
    """Partial update — mainly for status/progress changes."""
    status: VideoStatus | None = None
    progress: int | None = Field(None, ge=0, le=100)
    title: str | None = Field(None, max_length=512)
    error_message: str | None = None


class VideoRead(BaseModel):
    """Video public representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    filename: str
    file_path: str
    duration: float | None = None
    source_url: str | None = None
    status: VideoStatus
    error_message: str | None = None
    progress: int = 0
    created_at: datetime
    updated_at: datetime


class VideoListResponse(BaseModel):
    """Paginated video list."""
    items: list[VideoRead]
    total: int
    page: int = 1
    page_size: int = 20
