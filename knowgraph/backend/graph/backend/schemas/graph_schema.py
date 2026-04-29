"""Structured JSON Schema definitions for knowledge graph extraction.

Defines the expected LLM output format for:
  1. Node extraction (Stage 1)
  2. Relation extraction (Stage 2)
"""
from __future__ import annotations

# ── Stage 1 Schema: Knowledge Nodes ──

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
                        "enum": ["CONCEPT", "PERSON", "TECHNOLOGY", "METHODOLOGY", "EXAMPLE", "RELATION", "PREREQUISITE"],
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

# ── Stage 2 Schema: Relations ──

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
