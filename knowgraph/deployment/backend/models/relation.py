"""Relation model for knowledge graph edges."""
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class RelationType(str, enum.Enum):
    PREREQUISITE = "prerequisite"  # A is prerequisite for B
    CONTAINS = "contains"          # A contains B (B is sub-topic of A)
    SIMILAR = "similar"            # A is similar to B
    CONTRAST = "contrast"          # A contrasts with B
    CAUSAL = "causal"              # A causes B
    SEQUENCE = "sequence"          # A comes after B in learning order
    REFERENCE = "reference"        # A references B
    RELATED = "related"            # General relation


class Relation(Base):
    __tablename__ = "relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    relation_type = Column(SAEnum(RelationType), nullable=False)
    strength = Column(Float, default=0.5)  # 0.0 - 1.0, how strong the relation is
    description = Column(String(512), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    source_node = relationship(
        "KnowledgeNode",
        foreign_keys=[source_node_id],
        back_populates="outgoing_relations"
    )
    target_node = relationship(
        "KnowledgeNode",
        foreign_keys=[target_node_id],
        back_populates="incoming_relations"
    )
