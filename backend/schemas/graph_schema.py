"""Pydantic schemas for Knowledge Graph + LLM output JSON Schema.

Dual role:
  1. API serialization (KnowledgeNodeRead, RelationRead, GraphResponse)
  2. LLM structured output contract (NODE_EXTRACTION_SCHEMA, RELATION_EXTRACTION_SCHEMA)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models import MasteryLevel, NodeType, RelationType


# ═══════════════════════════════════════════════════════════════
# API Schemas
# ═══════════════════════════════════════════════════════════════

class KnowledgeNodeCreate(BaseModel):
    """Knowledge node payload from Celery worker."""
    name: str = Field(..., max_length=256)
    description: str | None = Field(None, max_length=2000)
    node_type: NodeType = NodeType.CONCEPT
    segment_index: int | None = None
    importance: float = Field(0.5, ge=0.0, le=1.0)
    mastery: MasteryLevel = MasteryLevel.UNKNOWN


class KnowledgeNodeRead(BaseModel):
    """Knowledge node public representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    name: str
    description: str | None = None
    node_type: NodeType
    segment_index: int | None = None
    importance: float = 0.5
    mastery: MasteryLevel = MasteryLevel.UNKNOWN
    created_at: datetime
    updated_at: datetime


class RelationCreate(BaseModel):
    """Relation payload from Celery worker."""
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relation_type: RelationType = RelationType.RELATES_TO
    strength: float = Field(0.5, ge=0.0, le=1.0)
    description: str | None = Field(None, max_length=500)


class RelationRead(BaseModel):
    """Relation public representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    relation_type: RelationType
    strength: float = 0.5
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class GraphResponse(BaseModel):
    """Full knowledge graph for a video."""
    nodes: list[KnowledgeNodeRead]
    relations: list[RelationRead]
    video_id: uuid.UUID
    node_count: int
    relation_count: int


# ═══════════════════════════════════════════════════════════════
# LLM Output Schema (JSON Schema contract)
# ═══════════════════════════════════════════════════════════════

NODE_EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "required": ["nodes"],
    "properties": {
        "nodes": {
            "type": "array",
            "description": "Extracted knowledge nodes from the note",
            "minItems": 5,
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["name", "description", "node_type", "importance", "segment_indices"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Knowledge node name using original terminology from the note",
                        "maxLength": 256,
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of this concept (20-100 characters)",
                        "maxLength": 500,
                    },
                    "node_type": {
                        "type": "string",
                        "enum": [
                            "CONCEPT", "PERSON", "TECHNOLOGY",
                            "METHODOLOGY", "EXAMPLE", "RELATION", "PREREQUISITE",
                        ],
                        "description": "Type of knowledge node",
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score 0.0-1.0 based on coverage depth in the note",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "segment_indices": {
                        "type": "array",
                        "description": "List of section indices this node is associated with",
                        "minItems": 1,
                        "items": {"type": "integer"},
                    },
                },
            },
        },
    },
}

RELATION_EXTRACTION_SCHEMA: dict = {
    "type": "object",
    "required": ["relations"],
    "properties": {
        "relations": {
            "type": "array",
            "description": "Semantic relations between extracted knowledge nodes",
            "minItems": 3,
            "maxItems": 50,
            "items": {
                "type": "object",
                "required": ["source", "target", "relation_type", "strength", "description"],
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source knowledge node name (must exist in extracted nodes list)",
                        "maxLength": 256,
                    },
                    "target": {
                        "type": "string",
                        "description": "Target knowledge node name (must exist in extracted nodes list)",
                        "maxLength": 256,
                    },
                    "relation_type": {
                        "type": "string",
                        "enum": [
                            "PREREQUISITE_OF",
                            "IS_A",
                            "PART_OF",
                            "RELATES_TO",
                            "CONTRASTS_WITH",
                            "LEADS_TO",
                            "EXAMPLE_OF",
                            "USES",
                            "APPLIES_TO",
                        ],
                        "description": "Type of semantic relation",
                    },
                    "strength": {
                        "type": "number",
                        "description": "Relation strength 0.0-1.0",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of how these nodes relate in the note context",
                        "maxLength": 300,
                    },
                },
            },
        },
    },
}
