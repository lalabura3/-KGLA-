"""Knowledge Graph Service — 2-stage extraction from AI-generated notes.

Pipeline:
  1. nodes   → Extract knowledge nodes from note (title, summary, keywords, sections)
  2. edges   → Infer semantic relations between extracted nodes

Integrates with T17 Note output and T16 knowledge_node / relation DB models.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field

import aiohttp

from ..prompts.graph_prompts import (
    SYSTEM_PROMPT,
    NODE_EXTRACTION_PROMPT,
    RELATION_EXTRACTION_PROMPT,
    build_sections_text,
)

logger = logging.getLogger(__name__)


# ── Data types ──


@dataclass
class KnowledgeNodeData:
    """One extracted knowledge node."""
    name: str
    description: str
    node_type: str  # CONCEPT, PERSON, TECHNOLOGY, METHODOLOGY, EXAMPLE, RELATION, PREREQUISITE
    importance: float = 0.5
    segment_indices: list[int] = field(default_factory=list)


@dataclass
class RelationData:
    """One semantic relation between two nodes."""
    source: str
    target: str
    relation_type: str
    strength: float = 0.5
    description: str = ""


@dataclass
class GraphExtractionResult:
    """Final result of graph extraction for a video."""
    video_id: uuid.UUID
    status: str  # "completed" | "failed"
    nodes: list[KnowledgeNodeData] = field(default_factory=list)
    relations: list[RelationData] = field(default_factory=list)
    error: str | None = None
    stages_completed: int = 0
    elapsed_ms: float = 0.0


# ── Graph Service ──


class GraphService:
    """Knowledge graph extraction service: nodes → relations."""

    def __init__(
        self,
        llm_url: str = "http://llm:8002",
        timeout: int = 90,
        max_retries: int = 2,
    ):
        self.llm_url = llm_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    # ── Stage 1: Node extraction ──

    async def extract_nodes(
        self,
        title: str,
        summary: str,
        keywords: list[str],
        sections: list[dict],
    ) -> list[KnowledgeNodeData]:
        """Extract knowledge nodes from a generated note.

        Args:
            title: Note title.
            summary: Note summary.
            keywords: List of keywords from the note.
            sections: List of section dicts with keys:
                section_index, heading, content, key_points.

        Returns:
            List of extracted KnowledgeNodeData.
        """
        sections_text, section_index_map = build_sections_text(sections)

        prompt = NODE_EXTRACTION_PROMPT.format(
            title=title,
            summary=summary,
            keywords=json.dumps(keywords, ensure_ascii=False),
            sections_text=sections_text,
            section_index_map=section_index_map,
        )

        response_text = await self._call_llm(
            system=SYSTEM_PROMPT,
            user=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        data = self._parse_json_safe(response_text)
        raw_nodes = data.get("nodes", [])

        nodes = []
        for n in raw_nodes:
            nodes.append(
                KnowledgeNodeData(
                    name=n.get("name", "").strip(),
                    description=n.get("description", "").strip(),
                    node_type=n.get("node_type", "CONCEPT"),
                    importance=float(n.get("importance", 0.5)),
                    segment_indices=n.get("segment_indices", []),
                )
            )

        # Deduplicate by name (case-insensitive merge)
        nodes = self._dedup_nodes(nodes)

        logger.info(
            "Stage 1 (node extraction) complete: %d nodes extracted",
            len(nodes),
        )
        return nodes

    # ── Stage 2: Relation extraction ──

    async def extract_relations(
        self,
        title: str,
        note_full_text: str,
        nodes: list[KnowledgeNodeData],
    ) -> list[RelationData]:
        """Infer semantic relations between extracted nodes.

        Args:
            title: Note title.
            note_full_text: Full note text for context.
            nodes: Previously extracted node list.

        Returns:
            List of RelationData.
        """
        nodes_json = [
            {
                "name": n.name,
                "description": n.description,
                "node_type": n.node_type,
                "importance": n.importance,
            }
            for n in nodes
        ]

        # Use first 12000 chars of full text for context
        full_text_snippet = note_full_text[:12000]

        prompt = RELATION_EXTRACTION_PROMPT.format(
            title=title,
            nodes_json=json.dumps(nodes_json, ensure_ascii=False, indent=2),
            full_text_snippet=full_text_snippet,
        )

        response_text = await self._call_llm(
            system=SYSTEM_PROMPT,
            user=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        data = self._parse_json_safe(response_text)
        raw_relations = data.get("relations", [])

        node_names = {n.name.lower() for n in nodes}

        relations = []
        for r in raw_relations:
            source = r.get("source", "").strip()
            target = r.get("target", "").strip()

            # Skip if source or target not in extracted nodes
            if source.lower() not in node_names or target.lower() not in node_names:
                logger.warning(
                    "Skipping relation '%s → %s': node not in extracted set",
                    source, target,
                )
                continue

            relations.append(
                RelationData(
                    source=source,
                    target=target,
                    relation_type=r.get("relation_type", "RELATES_TO"),
                    strength=float(r.get("strength", 0.5)),
                    description=r.get("description", "").strip(),
                )
            )

        # Remove duplicates (same source-target-type)
        relations = self._dedup_relations(relations)

        logger.info(
            "Stage 2 (relation extraction) complete: %d relations extracted",
            len(relations),
        )
        return relations

    # ── Full pipeline ──

    async def extract(
        self,
        video_id: uuid.UUID,
        title: str,
        summary: str,
        keywords: list[str],
        sections: list[dict],
        full_text: str,
        progress_callback: callable | None = None,
    ) -> GraphExtractionResult:
        """Run the full graph extraction pipeline.

        Args:
            video_id: UUID of the video.
            title: Note title.
            summary: Note summary.
            keywords: Note keywords.
            sections: Note sections (section_index, heading, content, key_points).
            full_text: Full note text.
            progress_callback: async callable(stage: str, progress: int).

        Returns:
            GraphExtractionResult with nodes and relations.
        """
        import time

        start = time.monotonic()

        try:
            if not sections:
                return GraphExtractionResult(
                    video_id=video_id,
                    status="failed",
                    error="No note sections provided for graph extraction",
                )

            if progress_callback:
                await progress_callback("nodes", 10)

            # Stage 1: Nodes
            nodes = await self.extract_nodes(title, summary, keywords, sections)

            if not nodes:
                logger.warning("No nodes extracted for video %s", video_id)
                return GraphExtractionResult(
                    video_id=video_id,
                    status="failed",
                    error="No knowledge nodes could be extracted",
                )

            if progress_callback:
                await progress_callback("edges", 60)

            # Stage 2: Relations
            relations = await self.extract_relations(title, full_text, nodes)

            if progress_callback:
                await progress_callback("complete", 100)

            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Graph extraction complete: video=%s, nodes=%d, relations=%d, elapsed=%.0fms",
                video_id, len(nodes), len(relations), elapsed,
            )

            return GraphExtractionResult(
                video_id=video_id,
                status="completed",
                nodes=nodes,
                relations=relations,
                stages_completed=2,
                elapsed_ms=elapsed,
            )

        except Exception as exc:
            logger.exception("Graph extraction failed for video %s: %s", video_id, exc)
            elapsed = (time.monotonic() - start) * 1000
            return GraphExtractionResult(
                video_id=video_id,
                status="failed",
                error=str(exc),
                elapsed_ms=elapsed,
            )

    # ── LLM helpers ──

    async def _call_llm(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Call the LLM service with retry logic."""
        payload = {
            "model": "default",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.llm_url}/v1/chat/completions",
                        json=payload,
                        timeout=self.timeout,
                    ) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            raise RuntimeError(
                                f"LLM API error (HTTP {resp.status}): {text[:500]}"
                            )
                        result = await resp.json()

                content = result["choices"][0]["message"]["content"]
                content = self._strip_fences(content)
                return content

            except Exception as exc:
                last_error = str(exc)
                if attempt < self.max_retries:
                    wait_s = 2 ** attempt
                    logger.warning(
                        "LLM call attempt %d/%d failed: %s. Retrying in %ds...",
                        attempt + 1, self.max_retries + 1, last_error, wait_s,
                    )
                    await asyncio.sleep(wait_s)
                else:
                    raise RuntimeError(
                        f"LLM call failed after {self.max_retries + 1} attempts: {last_error}"
                    )

        raise RuntimeError(f"LLM call failed: {last_error}")

    # ── Parsing & dedup helpers ──

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    @staticmethod
    def _parse_json_safe(text: str) -> dict | list:
        """Parse JSON safely, handling common LLM output issues."""
        text = GraphService._strip_fences(text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse LLM JSON output: %s", text[:500])
        return {} if text.strip().startswith("{") else []

    @staticmethod
    def _dedup_nodes(nodes: list[KnowledgeNodeData]) -> list[KnowledgeNodeData]:
        """Deduplicate nodes by name (case-insensitive), merging metadata."""
        seen: dict[str, KnowledgeNodeData] = {}
        for node in nodes:
            key = node.name.lower().strip()
            if key in seen:
                existing = seen[key]
                # Keep longer description
                if len(node.description) > len(existing.description):
                    existing.description = node.description
                # Higher importance wins
                existing.importance = max(existing.importance, node.importance)
                # Merge segment indices
                existing.segment_indices = list(
                    set(existing.segment_indices + node.segment_indices)
                )
            else:
                seen[key] = node
        return list(seen.values())

    @staticmethod
    def _dedup_relations(relations: list[RelationData]) -> list[RelationData]:
        """Remove duplicate relations (same source-target-type-direction)."""
        seen: set[tuple[str, str, str]] = set()
        deduped: list[RelationData] = []
        for rel in relations:
            key = (rel.source.lower(), rel.target.lower(), rel.relation_type)
            # Also check reversed direction for undirected relation types
            key_rev = (rel.target.lower(), rel.source.lower(), rel.relation_type)
            if key not in seen and key_rev not in seen:
                seen.add(key)
                deduped.append(rel)
        return deduped


# Singleton
graph_service = GraphService()
