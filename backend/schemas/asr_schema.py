"""Pydantic schemas for VideoSegment (ASR transcription)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoSegmentRead(BaseModel):
    """Single ASR segment."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    segment_index: int
    start_time: float
    end_time: float
    text: str
    confidence: float = 0.0
    words: list[str] | None = None
    speaker_id: str | None = None
    is_manually_edited: bool = False
    original_text: str | None = None
    created_at: datetime
    updated_at: datetime


class VideoSegmentListResponse(BaseModel):
    """Paginated segment list."""
    items: list[VideoSegmentRead]
    total: int
    video_id: uuid.UUID
