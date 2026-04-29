"""Celery tasks for knowledge graph extraction.

Orchestrates the 2-stage graph extraction pipeline after
AI note generation completes.

Chain: T16 ASR → T17 Notes → T18 Graph
"""
from __future__ import annotations

import asyncio
import json as _json
import logging
import uuid

import redis.asyncio as aioredis

from backend.database import async_session_factory, get_settings
from backend.models import (
    KnowledgeNode,
    MasteryLevel,
    NodeType,
    Note,
    NoteSection,
    Relation,
    RelationType,
    Video,
)
from backend.services.graph_service import GraphService, graph_service

logger = logging.getLogger(__name__)

settings = get_settings()


async def _update_graph_progress(video_id: uuid.UUID, stage: str, progress: int) -> None:
    """Push graph extraction progress via Redis pub/sub."""
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.publish(
            f"video:{video_id}:graph_progress",
            _json.dumps({"stage": stage, "progress": progress}),
        )
        await r.close()
    except Exception:
        pass


async def extract_graph(
    video_id_str: str,
) -> dict:
    """Async graph extraction entry point.

    Args:
        video_id_str: UUID of the Video record.

    Returns:
        {
            "status": "completed"|"failed",
            "node_count": int,
            "relation_count": int,
            "error": str | None,
            "elapsed_ms": float
        }
    """
    video_id = uuid.UUID(video_id_str)

    async def on_progress(stage: str, progress: int):
        await _update_graph_progress(video_id, stage, progress)

    try:
        # Fetch note data from DB
        async with async_session_factory() as db:
            from sqlalchemy import select

            # Verify video exists
            result = await db.execute(select(Video).where(Video.id == video_id))
            video = result.scalar_one_or_none()
            if not video:
                return {"status": "failed", "error": f"Video {video_id} not found"}

            # Fetch the generated note
            note_result = await db.execute(
                select(Note).where(Note.video_id == video_id)
            )
            note = note_result.scalar_one_or_none()
            if not note:
                return {
                    "status": "failed",
                    "error": f"Note not found for video {video_id}. Run note generation first.",
                }

            # Fetch note sections
            sections_result = await db.execute(
                select(NoteSection)
                .where(NoteSection.note_id == note.id)
                .order_by(NoteSection.section_index)
            )
            db_sections = sections_result.scalars().all()

            if not db_sections:
                return {
                    "status": "failed",
                    "error": f"No sections found for note {note.id}",
                }

            # Check if graph already exists (idempotency)
            existing_nodes = await db.execute(
                select(KnowledgeNode).where(
                    KnowledgeNode.video_id == video_id
                ).limit(1)
            )
            if existing_nodes.first() is not None:
                logger.info(
                    "Graph already exists for video %s, skipping extraction",
                    video_id,
                )
                # Count existing
                node_count_result = await db.execute(
                    select(KnowledgeNode).where(
                        KnowledgeNode.video_id == video_id
                    )
                )
                existing_all = node_count_result.scalars().all()
                relation_count = 0
                for en in existing_all:
                    rel_result = await db.execute(
                        select(Relation).where(
                            Relation.source_node_id == en.id
                        )
                    )
                    relation_count += len(rel_result.scalars().all())
                return {
                    "status": "completed",
                    "node_count": len(existing_all),
                    "relation_count": relation_count,
                    "error": None,
                    "elapsed_ms": 0,
                    "idempotent": True,
                }

            # Convert DB sections to dict format for service
            sections = [
                {
                    "section_index": s.section_index,
                    "heading": s.heading,
                    "content": s.content,
                    "key_points": s.key_points or [],
                }
                for s in db_sections
            ]

            # Convert DB note fields
            keywords = note.keywords or []
            full_text = note.full_text or ""

        # Run graph extraction
        result = await graph_service.extract(
            video_id=video_id,
            title=note.title,
            summary=note.summary,
            keywords=keywords,
            sections=sections,
            full_text=full_text,
            progress_callback=on_progress,
        )

        if result.status == "failed":
            return {
                "status": "failed",
                "error": result.error or "Unknown error",
                "elapsed_ms": result.elapsed_ms,
            }

        # Persist nodes and relations
        async with async_session_factory() as db:
            # Create a name→DB-id mapping
            node_id_map: dict[str, uuid.UUID] = {}

            for nd in result.nodes:
                db_node = KnowledgeNode(
                    video_id=video_id,
                    name=nd.name,
                    description=nd.description,
                    node_type=NodeType(nd.node_type),
                    importance=nd.importance,
                    segment_index=nd.segment_indices[0] if nd.segment_indices else None,
                    mastery=MasteryLevel.UNKNOWN,
                )
                db.add(db_node)
                await db.flush()  # Get db_node.id
                node_id_map[nd.name.lower()] = db_node.id

            # Create relations
            for rel in result.relations:
                source_id = node_id_map.get(rel.source.lower())
                target_id = node_id_map.get(rel.target.lower())

                if source_id is None or target_id is None:
                    logger.warning(
                        "Cannot create relation '%s' → '%s': node ID not found",
                        rel.source, rel.target,
                    )
                    continue

                db_relation = Relation(
                    source_node_id=source_id,
                    target_node_id=target_id,
                    relation_type=RelationType(rel.relation_type),
                    strength=rel.strength,
                    description=rel.description,
                )
                db.add(db_relation)

            # Update video progress
            video.status = "COMPLETED"
            video.progress = 100

            await db.commit()

        await _update_graph_progress(video_id, "complete", 100)

        logger.info(
            "Graph extraction persisted: video=%s, nodes=%d, relations=%d, elapsed=%.0fms",
            video_id, len(result.nodes), len(result.relations), result.elapsed_ms,
        )

        return {
            "status": "completed",
            "node_count": len(result.nodes),
            "relation_count": len(result.relations),
            "error": None,
            "elapsed_ms": result.elapsed_ms,
        }

    except Exception as exc:
        logger.exception("Graph extraction failed for video %s: %s", video_id, exc)
        return {
            "status": "failed",
            "error": str(exc),
            "elapsed_ms": 0,
        }


# ── Celery task wrapper (sync → async bridge) ──


def extract_graph_task(video_id: str) -> dict:
    """Celery task entry point — runs the async graph extraction pipeline."""
    return asyncio.run(extract_graph(video_id))
