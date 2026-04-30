"""Knowledge Graph API router — graph extraction, retrieval, and query.

Endpoints:
  POST   /api/v1/videos/{id}/graph/extract   — kick off graph extraction
  GET    /api/v1/videos/{id}/graph            — get full graph (nodes + edges)
  GET    /api/v1/videos/{id}/graph/nodes      — paginated node list
  GET    /api/v1/videos/{id}/graph/focus/{node_id} — n-hop focus subgraph
  GET    /api/v1/videos/{id}/graph/search?q=  — search nodes by name/description
  GET    /api/v1/videos/{id}/graph/status     — extraction progress
  PUT    /api/v1/graph/mastery                — update node mastery level
  DELETE /api/v1/videos/{id}/graph            — delete graph (re-extract)
  WS     /ws/video/{id}/graph                 — WebSocket progress

Depends on upstream T17 Note generation.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db, get_settings
from ..models import KnowledgeNode, NodeType, MasteryLevel, Relation, RelationType, Video
from ..schemas.graph_schema import NODE_EXTRACTION_SCHEMA, RELATION_EXTRACTION_SCHEMA

router = APIRouter(prefix="/api/v1", tags=["Knowledge Graph"])


# ── Pydantic schemas ──


class ExtractGraphRequest(BaseModel):
    """Request to trigger graph extraction."""
    force: bool = Field(default=False, description="Force re-extraction even if graph exists")


class ExtractGraphResponse(BaseModel):
    video_id: str
    status: str
    message: str


class NodeOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    node_type: str = "CONCEPT"
    importance: float = 0.5
    mastery: str = "unknown"
    segment_index: int | None = None

    class Config:
        from_attributes = True


class RelationOut(BaseModel):
    id: str
    source: str
    target: str
    source_id: str
    target_id: str
    relation_type: str
    strength: float = 0.5
    description: str | None = None

    class Config:
        from_attributes = True


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    relations: list[RelationOut]


class GraphStatusResponse(BaseModel):
    video_id: str
    has_graph: bool
    node_count: int = 0
    relation_count: int = 0
    extracted_at: str | None = None


class UpdateMasteryRequest(BaseModel):
    node_id: str
    mastery: str = Field(..., description="Mastery level: unknown|novice|beginner|intermediate|advanced|expert")


class UpdateMasteryResponse(BaseModel):
    id: str
    name: str
    mastery: str
    updated: bool = True


# ── Constants ──

NODE_TYPE_MAP = {
    "CONCEPT": NodeType.CONCEPT,
    "PERSON": NodeType.PERSON,
    "TECHNOLOGY": NodeType.TECHNOLOGY,
    "METHODOLOGY": NodeType.METHODOLOGY,
    "EXAMPLE": NodeType.EXAMPLE,
    "RELATION": NodeType.RELATION,
    "PREREQUISITE": NodeType.PREREQUISITE,
}

MASTERY_MAP = {
    "unknown": MasteryLevel.UNKNOWN,
    "novice": MasteryLevel.NOVICE,
    "beginner": MasteryLevel.BEGINNER,
    "intermediate": MasteryLevel.INTERMEDIATE,
    "advanced": MasteryLevel.ADVANCED,
    "expert": MasteryLevel.EXPERT,
}


# ── Endpoints ──


@router.post("/videos/{video_id}/graph/extract", response_model=ExtractGraphResponse)
async def start_graph_extraction(
    video_id: str,
    body: ExtractGraphRequest = ExtractGraphRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Kick off knowledge graph extraction via Celery.

    Requires that AI notes (T17) have already been generated for this video.
    """
    vid = uuid.UUID(video_id)

    # Verify video exists
    result = await db.execute(select(Video).where(Video.id == vid))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

    # Verify notes exist (precondition for graph extraction)
    from ..models import Note

    note_result = await db.execute(select(Note).where(Note.video_id == vid))
    note = note_result.scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=412,
            detail="Notes must be generated before graph extraction. "
                   f"POST /api/v1/videos/{video_id}/notes/generate first.",
        )

    # Check existing graph
    existing = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.video_id == vid).limit(1)
    )
    if existing.first() and not body.force:
        raise HTTPException(
            status_code=409,
            detail=f"Graph already exists for video {video_id}. Use force=true to re-extract.",
        )

    # Dispatch Celery task
    from ..celery_app import celery_app

    celery_app.send_task(
        "extract_graph",
        args=[str(vid)],
        task_id=f"graph-{vid}",  # Idempotent
    )

    return ExtractGraphResponse(
        video_id=video_id,
        status="processing",
        message="Knowledge graph extraction started",
    )


@router.get("/videos/{video_id}/graph", response_model=GraphOut)
async def get_graph(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the full knowledge graph for a video (nodes + edges)."""
    vid = uuid.UUID(video_id)

    nodes_result = await db.execute(
        select(KnowledgeNode)
        .where(KnowledgeNode.video_id == vid)
        .order_by(KnowledgeNode.importance.desc())
    )
    nodes = nodes_result.scalars().all()

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for video {video_id}",
        )

    # Build node_id → name lookup
    node_map = {str(n.id): n.name for n in nodes}

    # Fetch all relations for these nodes
    node_ids = [n.id for n in nodes]
    relations_result = await db.execute(
        select(Relation)
        .where(
            Relation.source_node_id.in_(node_ids) |  # type: ignore[union-attr]
            Relation.target_node_id.in_(node_ids)     # type: ignore[union-attr]
        )
    )
    relations = relations_result.scalars().all()

    return GraphOut(
        nodes=[
            NodeOut(
                id=str(n.id),
                name=n.name,
                description=n.description,
                node_type=str(n.node_type.value) if hasattr(n.node_type, 'value') else str(n.node_type),
                importance=n.importance,
                mastery=str(n.mastery.value) if hasattr(n.mastery, 'value') else str(n.mastery),
                segment_index=n.segment_index,
            )
            for n in nodes
        ],
        relations=[
            RelationOut(
                id=str(r.id),
                source=node_map.get(str(r.source_node_id), str(r.source_node_id)),
                target=node_map.get(str(r.target_node_id), str(r.target_node_id)),
                source_id=str(r.source_node_id),
                target_id=str(r.target_node_id),
                relation_type=str(r.relation_type.value) if hasattr(r.relation_type, 'value') else str(r.relation_type),
                strength=r.strength,
                description=r.description,
            )
            for r in relations
        ],
    )


@router.get("/videos/{video_id}/graph/nodes", response_model=list[NodeOut])
async def list_graph_nodes(
    video_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    node_type: str | None = Query(default=None, description="Filter by node type"),
    db: AsyncSession = Depends(get_db),
):
    """List knowledge nodes with pagination and optional type filter."""
    vid = uuid.UUID(video_id)

    query = select(KnowledgeNode).where(KnowledgeNode.video_id == vid)

    if node_type:
        nt = NODE_TYPE_MAP.get(node_type.upper())
        if nt:
            query = query.where(KnowledgeNode.node_type == nt)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid node type: {node_type}")

    query = query.order_by(KnowledgeNode.importance.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    nodes = result.scalars().all()

    return [
        NodeOut(
            id=str(n.id),
            name=n.name,
            description=n.description,
            node_type=str(n.node_type.value) if hasattr(n.node_type, 'value') else str(n.node_type),
            importance=n.importance,
            mastery=str(n.mastery.value) if hasattr(n.mastery, 'value') else str(n.mastery),
            segment_index=n.segment_index,
        )
        for n in nodes
    ]


@router.get("/videos/{video_id}/graph/focus/{node_id}", response_model=GraphOut)
async def get_focus_subgraph(
    video_id: str,
    node_id: str,
    hops: int = Query(default=1, ge=1, le=3, description="N-hop neighbors to include"),
    db: AsyncSession = Depends(get_db),
):
    """Get a focus subgraph: a node and its n-hop neighbors."""
    vid = uuid.UUID(video_id)
    nid = uuid.UUID(node_id)

    # Verify the node exists and belongs to this video
    node_result = await db.execute(
        select(KnowledgeNode).where(
            KnowledgeNode.id == nid,
            KnowledgeNode.video_id == vid,
        )
    )
    target_node = node_result.scalar_one_or_none()
    if not target_node:
        raise HTTPException(
            status_code=404,
            detail=f"Node {node_id} not found for video {video_id}",
        )

    # Use recursive CTE for n-hop neighbor traversal
    query = text("""
        WITH RECURSIVE subgraph AS (
            -- Base: the focus node
            SELECT id FROM knowledge_nodes WHERE id = :start_id
            UNION
            -- Neighbors via outgoing relations
            SELECT r.target_node_id FROM relations r
            JOIN subgraph s ON r.source_node_id = s.id
            -- Simple cycle prevention via depth limit
            WHERE (SELECT COUNT(*) FROM subgraph) < :max_nodes
            UNION
            -- Neighbors via incoming relations
            SELECT r.source_node_id FROM relations r
            JOIN subgraph s ON r.target_node_id = s.id
            WHERE (SELECT COUNT(*) FROM subgraph) < :max_nodes
        )
        SELECT * FROM knowledge_nodes
        WHERE video_id = :video_id AND id IN (SELECT id FROM subgraph)
        ORDER BY importance DESC
    """)

    # Estimate max nodes: 1 + degree * (hops) reasonable upper bound
    max_nodes = 1 + 10 * hops  # Assume average degree ~10

    nodes_result = await db.execute(
        query,
        {"start_id": nid, "video_id": vid, "max_nodes": max_nodes},
    )
    nodes = nodes_result.fetchall()

    if not nodes:
        return GraphOut(nodes=[], relations=[])

    node_ids = [row[0] for row in nodes]
    node_map = {row[0]: row[1] for row in nodes}

    # Fetch relations within this subgraph
    relations_result = await db.execute(
        select(Relation).where(
            Relation.source_node_id.in_(node_ids) &
            Relation.target_node_id.in_(node_ids)
        )
    )
    relations = relations_result.scalars().all()

    # Full node objects
    full_nodes_result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
    )
    full_nodes = full_nodes_result.scalars().all()

    return GraphOut(
        nodes=[
            NodeOut(
                id=str(n.id),
                name=n.name,
                description=n.description,
                node_type=str(n.node_type.value) if hasattr(n.node_type, 'value') else str(n.node_type),
                importance=n.importance,
                mastery=str(n.mastery.value) if hasattr(n.mastery, 'value') else str(n.mastery),
                segment_index=n.segment_index,
            )
            for n in full_nodes
        ],
        relations=[
            RelationOut(
                id=str(r.id),
                source=node_map.get(str(r.source_node_id), str(r.source_node_id)),
                target=node_map.get(str(r.target_node_id), str(r.target_node_id)),
                source_id=str(r.source_node_id),
                target_id=str(r.target_node_id),
                relation_type=str(r.relation_type.value) if hasattr(r.relation_type, 'value') else str(r.relation_type),
                strength=r.strength,
                description=r.description,
            )
            for r in relations
        ],
    )


@router.get("/videos/{video_id}/graph/search")
async def search_graph_nodes(
    video_id: str,
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    db: AsyncSession = Depends(get_db),
):
    """Search knowledge nodes by name or description (ILike)."""
    vid = uuid.UUID(video_id)

    query = select(KnowledgeNode).where(
        KnowledgeNode.video_id == vid,
    )

    # Use ILIKE for case-insensitive search
    from sqlalchemy import or_

    pattern = f"%{q}%"
    query = query.where(
        or_(
            KnowledgeNode.name.ilike(pattern),
            KnowledgeNode.description.ilike(pattern),
        )
    ).order_by(KnowledgeNode.importance.desc()).limit(50)

    result = await db.execute(query)
    nodes = result.scalars().all()

    return [
        NodeOut(
            id=str(n.id),
            name=n.name,
            description=n.description,
            node_type=str(n.node_type.value) if hasattr(n.node_type, 'value') else str(n.node_type),
            importance=n.importance,
            mastery=str(n.mastery.value) if hasattr(n.mastery, 'value') else str(n.mastery),
            segment_index=n.segment_index,
        )
        for n in nodes
    ]


@router.get("/videos/{video_id}/graph/status", response_model=GraphStatusResponse)
async def get_graph_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get graph extraction status and metadata."""
    vid = uuid.UUID(video_id)

    nodes_result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.video_id == vid)
    )
    nodes = nodes_result.scalars().all()

    # Count relations linked to this video's nodes
    relation_count = 0
    if nodes:
        node_ids = [n.id for n in nodes]
        relations_result = await db.execute(
            select(Relation).where(
                Relation.source_node_id.in_(node_ids) |
                Relation.target_node_id.in_(node_ids)
            )
        )
        relation_count = len(relations_result.scalars().all())

    created_at = nodes[0].created_at.isoformat() if nodes and hasattr(nodes[0], 'created_at') and nodes[0].created_at else None

    return GraphStatusResponse(
        video_id=video_id,
        has_graph=len(nodes) > 0,
        node_count=len(nodes),
        relation_count=relation_count,
        extracted_at=created_at,
    )


@router.put("/graph/mastery", response_model=UpdateMasteryResponse)
async def update_node_mastery(
    body: UpdateMasteryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update the mastery level of a knowledge node.

    Mastery levels: unknown → novice → beginner → intermediate → advanced → expert.
    This is a user-facing endpoint; mastery is initially UNKNOWN after extraction.
    """
    nid = uuid.UUID(body.node_id)
    mastery_key = body.mastery.lower()

    if mastery_key not in MASTERY_MAP:
        valid = ", ".join(MASTERY_MAP.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mastery level '{body.mastery}'. Valid: {valid}",
        )

    result = await db.execute(select(KnowledgeNode).where(KnowledgeNode.id == nid))
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {body.node_id} not found")

    node.mastery = MASTERY_MAP[mastery_key]
    await db.commit()
    await db.refresh(node)

    return UpdateMasteryResponse(
        id=str(node.id),
        name=node.name,
        mastery=str(node.mastery.value) if hasattr(node.mastery, 'value') else str(node.mastery),
    )


@router.delete("/videos/{video_id}/graph", status_code=204)
async def delete_graph(
    video_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete the knowledge graph for a video (for re-extraction).

    Cascade deletes all associated relations via FK constraints.
    """
    vid = uuid.UUID(video_id)

    # Delete all nodes (relations cascade via FK ondelete=CASCADE)
    nodes_result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.video_id == vid)
    )
    nodes = nodes_result.scalars().all()

    if not nodes:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for video {video_id}",
        )

    for node in nodes:
        await db.delete(node)

    await db.commit()


# ── WebSocket progress endpoint ──


@router.websocket("/ws/video/{video_id}/graph")
async def graph_progress_ws(websocket: WebSocket, video_id: str):
    """WebSocket endpoint for real-time graph extraction progress.

    Subscribes to Redis pub/sub channel `video:{video_id}:graph_progress`.
    """
    await websocket.accept()

    vid = uuid.UUID(video_id)

    import redis.asyncio as aioredis

    try:
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"video:{vid}:graph_progress")

        # Send initial status
        async with async_session_factory() as db:
            result = await db.execute(
                select(KnowledgeNode).where(KnowledgeNode.video_id == vid).limit(1)
            )
            has_graph = result.first() is not None
            await websocket.send_json(
                {"event": "status", "has_graph": has_graph}
            )

        # Stream progress events
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json({"event": "progress", **data})

                if data.get("stage") == "complete":
                    await websocket.send_json(
                        {"event": "complete", "progress": 100}
                    )
                    break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"event": "error", "error": str(exc)})
        except Exception:
            pass
    finally:
        try:
            await pubsub.unsubscribe(f"video:{vid}:graph_progress")
            await r.close()
        except Exception:
            pass
