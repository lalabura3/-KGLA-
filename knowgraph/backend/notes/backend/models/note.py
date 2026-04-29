"""Note & NoteSection ORM models — AI-generated structured notes tied to video segments."""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import TimestampMixin, UUIDPKMixin


class Note(Base, UUIDPKMixin, TimestampMixin):
    """Top-level note for a video — one per processed video."""

    __tablename__ = "notes"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    hallucination_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="zh", nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sections = relationship(
        "NoteSection", back_populates="note",
        order_by="NoteSection.section_index",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Note video={self.video_id} title='{self.title[:40]}...'>"


class NoteSection(Base, UUIDPKMixin, TimestampMixin):
    """Individual note section tied to a video timestamp anchor."""

    __tablename__ = "note_sections"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    segment_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    key_points: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    hallucination_flags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    note = relationship("Note", back_populates="sections")

    def __repr__(self) -> str:
        return f"<NoteSection #{self.section_index} [{self.start_time:.1f}s] {self.heading}>"
