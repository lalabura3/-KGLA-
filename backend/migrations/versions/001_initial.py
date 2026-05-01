"""Initial schema — all 7 tables

Revision ID: 001_initial
Revises:
Create Date: 2026-05-01

Creates tables:
  - users                    (PK UUID, username/email unique)
  - videos                   (FK→users, status indexed)
  - video_segments           (FK→videos, segment_index)
  - knowledge_nodes          (FK→videos, name + node_type)
  - relations                (FKs→knowledge_nodes × 2, self-referential)
  - notes                    (FK→videos, unique per video)
  - note_sections            (FK→notes, section_index)

All tables use UUID v4 primary keys and timestamp tracking.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Shared column factories ──


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    ]


# ─────────────────────────────────────────────────────────────
# Upgrade
# ─────────────────────────────────────────────────────────────


def upgrade() -> None:
    # ── 1. users ──
    op.create_table(
        "users",
        _id_column(),
        sa.Column("username", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        *_timestamps(),
    )

    # ── 2. videos ──
    op.create_table(
        "videos",
        _id_column(),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="uploaded",
            index=True,
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        *_timestamps(),
    )

    # ── 3. video_segments ──
    op.create_table(
        "video_segments",
        _id_column(),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("segment_index", sa.Integer, nullable=False),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("words", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("speaker_id", sa.String(36), nullable=True),
        sa.Column(
            "is_manually_edited",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("original_text", sa.Text, nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_video_segments_video_segment",
        "video_segments",
        ["video_id", "segment_index"],
    )

    # ── 4. knowledge_nodes ──
    op.create_table(
        "knowledge_nodes",
        _id_column(),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("node_type", sa.String(20), nullable=False, server_default="concept"),
        sa.Column("segment_index", sa.Integer, nullable=True),
        sa.Column("importance", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("mastery", sa.String(20), nullable=False, server_default="unknown"),
        *_timestamps(),
    )
    op.create_index(
        "ix_knowledge_nodes_video_name",
        "knowledge_nodes",
        ["video_id", "name"],
    )

    # ── 5. relations ──
    op.create_table(
        "relations",
        _id_column(),
        sa.Column(
            "source_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "relation_type",
            sa.String(20),
            nullable=False,
            server_default="relates_to",
        ),
        sa.Column("strength", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("description", sa.Text, nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_relations_pair",
        "relations",
        ["source_node_id", "target_node_id"],
    )

    # ── 6. notes ──
    op.create_table(
        "notes",
        _id_column(),
        sa.Column(
            "video_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("full_text", sa.Text, nullable=False),
        sa.Column("keywords", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "hallucination_score",
            sa.Float,
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("language", sa.String(10), nullable=False, server_default="zh"),
        sa.Column("word_count", sa.Integer, nullable=False, server_default="0"),
        *_timestamps(),
    )

    # ── 7. note_sections ──
    op.create_table(
        "note_sections",
        _id_column(),
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("section_index", sa.Integer, nullable=False),
        sa.Column("heading", sa.String(256), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=True),
        sa.Column("segment_ids", postgresql.JSONB, nullable=True),
        sa.Column("key_points", postgresql.JSONB, nullable=True),
        sa.Column("source_text", sa.Text, nullable=True),
        sa.Column("hallucination_flags", postgresql.JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        *_timestamps(),
    )
    op.create_index(
        "ix_note_sections_note_index",
        "note_sections",
        ["note_id", "section_index"],
    )


# ─────────────────────────────────────────────────────────────
# Downgrade
# ─────────────────────────────────────────────────────────────


def downgrade() -> None:
    op.drop_table("note_sections")
    op.drop_table("notes")
    op.drop_table("relations")
    op.drop_table("knowledge_nodes")
    op.drop_table("video_segments")
    op.drop_table("videos")
    op.drop_table("users")
