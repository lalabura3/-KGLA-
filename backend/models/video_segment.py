"""VideoSegment ORM model — sentence-level ASR transcription segments.

Each row represents one transcribed speech segment with VAD timestamps
and word-level detail (optional).  Supports manual editing workflow.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import TimestampMixin, UUIDPKMixin


class VideoSegment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "video_segments"

    video_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    start_time: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    end_time: Mapped[float] = mapped_column(
        Float, nullable=False,
    )
    text: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    words: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True,
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
    )
    is_manually_edited: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    original_text: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ──
    video = relationship("Video", back_populates="segments")

    def __repr__(self) -> str:
        return (
            f"<VideoSegment #{self.segment_index}"
            f" [{self.start_time:.1f}s–{self.end_time:.1f}s]>"
        )
