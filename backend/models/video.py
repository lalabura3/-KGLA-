"""Video ORM model — top-level resource representing an uploaded video.

Each video feeds through the ASR → Notes → Graph pipeline.
Status tracks lifecycle; progress is 0-100%.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import TimestampMixin, UUIDPKMixin, VideoStatus


class Video(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "videos"

    user_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False,
    )
    filename: Mapped[str] = mapped_column(
        String(512), nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1024), nullable=False,
    )
    duration: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True,
    )
    status: Mapped[VideoStatus] = mapped_column(
        String(20), default=VideoStatus.UPLOADED,
        nullable=False, index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    progress: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
    )

    # ── Relationships ──
    user = relationship("User", back_populates="videos")
    segments = relationship(
        "VideoSegment", back_populates="video",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    knowledge_nodes = relationship(
        "KnowledgeNode", back_populates="video",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notes = relationship(
        "Note", back_populates="video",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Video {self.title} [{self.status}]>"
