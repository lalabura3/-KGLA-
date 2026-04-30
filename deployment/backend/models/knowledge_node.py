"""Knowledge node model."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class MasteryLevel(str, enum.Enum):
    NOT_LEARNED = "not_learned"
    LEARNING = "learning"
    MASTERED = "mastered"


class NodeType(str, enum.Enum):
    CONCEPT = "concept"
    TERM = "term"
    FORMULA = "formula"
    PERSON = "person"
    EVENT = "event"
    METHOD = "method"
    EXAMPLE = "example"


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, default="")
    node_type = Column(SAEnum(NodeType), default=NodeType.CONCEPT)
    timestamp = Column(Float, default=0.0)  # video timestamp
    segment_index = Column(Integer, default=0)  # which segment this belongs to
    importance = Column(Float, default=0.5)  # 0.0 - 1.0
    mastery = Column(SAEnum(MasteryLevel), default=MasteryLevel.NOT_LEARNED)
    embedding = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    video = relationship("Video", back_populates="knowledge_nodes")
    outgoing_relations = relationship(
        "Relation",
        foreign_keys="Relation.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    incoming_relations = relationship(
        "Relation",
        foreign_keys="Relation.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )
