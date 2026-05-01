"""ORM models — full export with shared enums & mixins.

Coverage: User, Video, VideoSegment, Note, NoteSection, KnowledgeNode, Relation.

Merged from T14 (User), T16 (Video/VideoSegment/KnowledgeNode/Relation), T17 (Note/NoteSection).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


# ═══════════════════════════════════════════════════════════════
# Mixins
# ═══════════════════════════════════════════════════════════════

class TimestampMixin:
    """Automatically managed created_at / updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPKMixin:
    """UUID v4 primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════

class VideoStatus(str, enum.Enum):
    """Lifecycle status for video processing pipeline."""
    UPLOADED   = "uploaded"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class NodeType(str, enum.Enum):
    """Knowledge node category."""
    CONCEPT = "concept"
    FACT    = "fact"
    PERSON  = "person"
    TERM    = "term"
    EVENT   = "event"


class MasteryLevel(str, enum.Enum):
    """User mastery of a knowledge node."""
    UNKNOWN      = "unknown"
    BEGINNER     = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED     = "advanced"
    EXPERT       = "expert"


class RelationType(str, enum.Enum):
    """Semantic relation between knowledge nodes."""
    RELATES_TO   = "relates_to"
    PREREQUISITE = "prerequisite"
    CONTAINS     = "contains"
    CAUSES       = "causes"
    EXAMPLE_OF   = "example_of"
    COMPARES_WITH = "compares_with"


# ═══════════════════════════════════════════════════════════════
# Model imports — MUST be imported for Alembic autogenerate
# ═══════════════════════════════════════════════════════════════

from .user import User                          # noqa: E402, F401
from .video import Video                        # noqa: E402, F401
from .video_segment import VideoSegment         # noqa: E402, F401
from .knowledge import KnowledgeNode, Relation   # noqa: E402, F401
from .note import Note, NoteSection             # noqa: E402, F401


__all__ = [
    # Mixins
    "TimestampMixin",
    "UUIDPKMixin",
    # Enums
    "VideoStatus",
    "NodeType",
    "MasteryLevel",
    "RelationType",
    # Models
    "User",
    "Video",
    "VideoSegment",
    "KnowledgeNode",
    "Relation",
    "Note",
    "NoteSection",
]
