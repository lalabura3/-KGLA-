"""Pydantic schemas for API request/response."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ─── Video Schemas ───

class VideoCreate(BaseModel):
    title: Optional[str] = "未命名视频"
    source_url: Optional[str] = None


class VideoResponse(BaseModel):
    id: int
    user_id: int
    title: str
    filename: str
    duration: float
    status: str
    source_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoStatusResponse(BaseModel):
    id: int
    status: str
    progress: float = 0.0  # 0-100
    current_stage: str = ""
    error_message: Optional[str] = None


class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int


# ─── Segment Schemas ───

class SegmentResponse(BaseModel):
    id: int
    video_id: int
    segment_index: int
    start_time: float
    end_time: float
    title: str
    content: str
    summary: str
    keyframe_path: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Note Schemas ───

class NoteResponse(BaseModel):
    video_id: int
    video_title: str
    segments: List[SegmentResponse]
    total_segments: int


class NoteUpdateRequest(BaseModel):
    segment_id: int
    content: str


# ─── Knowledge Graph Schemas ───

class NodeResponse(BaseModel):
    id: int
    video_id: int
    name: str
    description: str
    node_type: str
    timestamp: float
    segment_index: int
    importance: float
    mastery: str

    class Config:
        from_attributes = True


class RelationResponse(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    relation_type: str
    strength: float
    description: str

    class Config:
        from_attributes = True


class GraphResponse(BaseModel):
    video_id: int
    nodes: List[NodeResponse]
    relations: List[RelationResponse]


class MasteryUpdateRequest(BaseModel):
    node_id: int
    mastery: str = Field(pattern=r"^(not_learned|learning|mastered)$")


# ─── QA Schema ───

class QARequest(BaseModel):
    video_id: int
    question: str


class QAResponse(BaseModel):
    answer: str
    related_segments: List[dict] = []


# ─── User Schema ───

class UserCreate(BaseModel):
    username: str
    display_name: Optional[str] = ""


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    created_at: datetime

    class Config:
        from_attributes = True
