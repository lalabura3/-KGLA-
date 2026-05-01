"""Pydantic schemas for request/response serialization.

Coverage: User, Video, VideoSegment, Note/NoteSection, KnowledgeNode/Relation.
All schemas use Pydantic v2 with `model_config = ConfigDict(from_attributes=True)`.
"""
from __future__ import annotations

from .user_schema import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from .video_schema import (
    VideoCreate,
    VideoRead,
    VideoStatusUpdate,
    VideoListResponse,
)
from .asr_schema import (
    VideoSegmentRead,
    VideoSegmentListResponse,
)
from .note_schema import (
    NoteCreate,
    NoteRead,
    NoteSectionCreate,
    NoteSectionRead,
    NoteDetailResponse,
    NOTE_OUTPUT_SCHEMA,
)
from .graph_schema import (
    KnowledgeNodeCreate,
    KnowledgeNodeRead,
    RelationCreate,
    RelationRead,
    GraphResponse,
    NODE_EXTRACTION_SCHEMA,
    RELATION_EXTRACTION_SCHEMA,
)

__all__ = [
    # User
    "UserCreate",
    "UserRead",
    "UserUpdate",
    # Video
    "VideoCreate",
    "VideoRead",
    "VideoStatusUpdate",
    "VideoListResponse",
    # ASR Segments
    "VideoSegmentRead",
    "VideoSegmentListResponse",
    # Notes
    "NoteCreate",
    "NoteRead",
    "NoteSectionCreate",
    "NoteSectionRead",
    "NoteDetailResponse",
    "NOTE_OUTPUT_SCHEMA",
    # Knowledge Graph
    "KnowledgeNodeCreate",
    "KnowledgeNodeRead",
    "RelationCreate",
    "RelationRead",
    "GraphResponse",
    "NODE_EXTRACTION_SCHEMA",
    "RELATION_EXTRACTION_SCHEMA",
]
