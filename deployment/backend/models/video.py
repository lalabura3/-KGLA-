"""Video and VideoSegment models."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ASR_DONE = "asr_done"
    NOTES_DONE = "notes_done"
    GRAPH_DONE = "graph_done"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(256), default="未命名视频")
    filename = Column(String(256), nullable=False)
    file_path = Column(Text, nullable=False)
    duration = Column(Float, default=0.0)  # seconds
    status = Column(SAEnum(VideoStatus), default=VideoStatus.UPLOADED)
    source_url = Column(Text, nullable=True)  # original URL if imported from link
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, default=0)  # Processing progress 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="videos")
    segments = relationship("VideoSegment", back_populates="video", cascade="all, delete-orphan")
    knowledge_nodes = relationship("KnowledgeNode", back_populates="video", cascade="all, delete-orphan")


class VideoSegment(Base):
    __tablename__ = "video_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)  # seconds
    end_time = Column(Float, nullable=False)
    title = Column(String(256), default="")
    content = Column(Text, default="")  # ASR text for this segment
    summary = Column(Text, default="")  # AI summary
    keyframe_path = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)  # JSON string of embedding vector
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    video = relationship("Video", back_populates="segments")
