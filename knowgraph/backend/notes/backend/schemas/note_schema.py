"""Structured JSON Schema definitions for AI-generated notes.

Defines the expected output format from the LLM.
"""
from __future__ import annotations

from typing import Literal

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
                "topic": {"type": "string", "description": "Main topic domain (e.g., 'machine-learning', 'physics')"},
                "difficulty": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced", "expert"],
                    "description": "Content difficulty level",
                },
                "estimated_reading_time_minutes": {"type": "integer"},
                "requires_prerequisites": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Prerequisite knowledge topics",
                },
                "is_technical": {"type": "boolean", "description": "Whether content contains technical jargon"},
                "has_code": {"type": "boolean", "description": "Whether the video discusses/contains code"},
                "language": {
                    "type": "string",
                    "enum": ["zh", "en", "mixed"],
                    "description": "Primary language",
                },
                "speaker_count": {"type": "integer", "minimum": 1},
            },
        },
    },
}

# ── Pydantic models for type-safe deserialization ──


class EvidenceItem:
    quote: str
    segment_index: int


class Section:
    heading: str
    content: str
    start_time: float
    end_time: float
    key_points: list[str] = []
    source_segment_indices: list[int] = []
    evidence: list[EvidenceItem] = []


class NoteMetadata:
    topic: str = ""
    difficulty: str = "intermediate"
    estimated_reading_time_minutes: int = 5
    requires_prerequisites: list[str] = []
    is_technical: bool = False
    has_code: bool = False
    language: str = "zh"
    speaker_count: int = 1


class NoteOutput:
    title: str = ""
    summary: str = ""
    sections: list[Section] = []
    keywords: list[str] = []
    metadata: NoteMetadata
