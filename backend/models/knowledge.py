"""Knowledge graph ORM models — nodes and typed relations.

Extracted by the LLM from ASR transcripts + AI-generated notes.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import MasteryLevel, NodeType, RelationType, TimestampMixin, UUIDPKMixin


class KnowledgeNode(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "knowledge_nodes"

    video_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(256), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    node_type: Mapped[NodeType] = mapped_column(
        String(20), default=NodeType.CONCEPT, nullable=False,
    )
    segment_index: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    importance: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False,
    )
    mastery: Mapped[MasteryLevel] = mapped_column(
        String(20), default=MasteryLevel.UNKNOWN, nullable=False,
    )

    # ── Relationships ──
    video = relationship("Video", back_populates="knowledge_nodes")
    outgoing_relations = relationship(
        "Relation",
        foreign_keys="Relation.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_relations = relationship(
        "Relation",
        foreign_keys="Relation.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeNode {self.name} [{self.node_type}]>"


class Relation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "relations"

    source_node_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[RelationType] = mapped_column(
        String(20), default=RelationType.RELATES_TO, nullable=False,
    )
    strength: Mapped[float] = mapped_column(
        Float, default=0.5, nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ──
    source_node = relationship(
        "KnowledgeNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_relations",
    )
    target_node = relationship(
        "KnowledgeNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_relations",
    )

    def __repr__(self) -> str:
        return f"<Relation {self.source_node.name} --[{self.relation_type}]--> {self.target_node.name}>"
