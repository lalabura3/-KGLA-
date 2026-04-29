"""Video ORM model."""
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import TimestampMixin, UUIDPKMixin, VideoStatus


class Video(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "videos"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[VideoStatus] = mapped_column(
        String(20), default=VideoStatus.UPLOADED, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    segments = relationship("VideoSegment", back_populates="video", lazy="dynamic")
    knowledge_nodes = relationship("KnowledgeNode", back_populates="video", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Video {self.title} [{self.status}]>"
