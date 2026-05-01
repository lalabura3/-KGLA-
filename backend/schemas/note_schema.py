"""Pydantic schemas for Note & NoteSection + LLM output JSON Schema.

This file serves two roles:
  1. API serialization (NoteCreate, NoteRead, etc.)
  2. LLM structured output contract (NOTE_OUTPUT_SCHEMA)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
# API Schemas
# ═══════════════════════════════════════════════════════════════

class NoteSectionCreate(BaseModel):
    """Individual note section (supplied by celery worker)."""
    section_index: int = Field(..., ge=0)
    heading: str = Field(..., max_length=256)
    content: str
    start_time: float = Field(..., ge=0)
    end_time: float | None = Field(None, ge=0)
    segment_ids: list[str] | None = None
    key_points: list[str] | None = None
    source_text: str | None = None
    hallucination_flags: list[str] | None = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class NoteCreate(BaseModel):
    """Request body for creating a note (celery worker → API)."""
    video_id: uuid.UUID
    title: str = Field(..., max_length=512)
    summary: str
    full_text: str
    keywords: list[str] | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    hallucination_score: float = Field(0.0, ge=0.0, le=1.0)
    language: str = Field("zh", max_length=10)
    word_count: int = Field(0, ge=0)
    sections: list[NoteSectionCreate] = []


class NoteSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    section_index: int
    heading: str
    content: str
    start_time: float
    end_time: float | None = None
    segment_ids: list[str] | None = None
    key_points: list[str] | None = None
    source_text: str | None = None
    hallucination_flags: list[str] | None = None
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    video_id: uuid.UUID
    title: str
    summary: str
    keywords: list[str] | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    hallucination_score: float = 0.0
    language: str = "zh"
    word_count: int = 0
    created_at: datetime
    updated_at: datetime


class NoteDetailResponse(NoteRead):
    """Note with all sections included."""
    sections: list[NoteSectionRead] = []


# ═══════════════════════════════════════════════════════════════
# LLM Output Schema (JSON Schema contract)
# ═══════════════════════════════════════════════════════════════

NOTE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["title", "summary", "sections", "keywords", "metadata"],
    "properties": {
        "title": {
            "type": "string",
            "description": "Video-derived title summarizing the content",
            "maxLength": 200,
        },
        "summary": {
            "type": "string",
            "description": "100-200 word summary of the entire video",
            "maxLength": 1000,
        },
        "sections": {
            "type": "array",
            "description": "Chronological sections, each anchored to a time range",
            "minItems": 1,
            "maxItems": 50,
            "items": {
                "type": "object",
                "required": ["heading", "content", "start_time", "end_time"],
                "properties": {
                    "heading": {
                        "type": "string",
                        "description": "Section title",
                        "maxLength": 150,
                    },
                    "content": {
                        "type": "string",
                        "description": "Section body — a coherent paragraph summarizing this time segment",
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Start timestamp in seconds (must match a segment boundary)",
                        "minimum": 0,
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End timestamp in seconds (must match a segment boundary)",
                        "minimum": 0,
                    },
                    "key_points": {
                        "type": "array",
                        "description": "Bullet-point key takeaways from this section",
                        "items": {"type": "string"},
                        "maxItems": 10,
                    },
                    "source_segment_indices": {
                        "type": "array",
                        "description": "Indices of segment_ids that source this section",
                        "items": {"type": "integer"},
                    },
                    "evidence": {
                        "type": "array",
                        "description": "Short verbatim quotes from the transcript that support the key points — required for hallucination prevention",
                        "items": {
                            "type": "object",
                            "required": ["quote", "segment_index"],
                            "properties": {
                                "quote": {"type": "string", "maxLength": 300},
                                "segment_index": {"type": "integer"},
                            },
                        },
                    },
                },
            },
        },
        "keywords": {
            "type": "array",
            "description": "10-20 key terms/concepts extracted from the video",
            "items": {"type": "string"},
            "minItems": 5,
        },
        "metadata": {
            "type": "object",
            "description": "Video metadata extracted by LLM",
            "properties": {
                "topic": {"type": "string", "description": "Main topic domain"},
                "difficulty": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced", "expert"],
                },
                "estimated_reading_time_minutes": {"type": "integer"},
                "requires_prerequisites": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "is_technical": {"type": "boolean"},
                "has_code": {"type": "boolean"},
                "language": {
                    "type": "string",
                    "enum": ["zh", "en", "mixed"],
                },
                "speaker_count": {"type": "integer", "minimum": 1},
            },
        },
    },
}
