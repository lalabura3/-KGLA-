"""Knowledge Graph API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.video import Video, VideoStatus
from models.knowledge_node import KnowledgeNode, MasteryLevel
from models.relation import Relation
from schemas.models import (
    GraphResponse, NodeResponse, RelationResponse,
    MasteryUpdateRequest
)
from services.graph_builder import build_video_graph

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/{video_id}", response_model=GraphResponse)
async def get_video_graph(video_id: int, db: AsyncSession = Depends(get_db)):
    """Get knowledge graph for a video."""
    # Check video exists and is processed
    video_query = select(Video).where(Video.id == video_id)
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")

    if video.status not in (VideoStatus.GRAPH_DONE, VideoStatus.COMPLETED):
        # Return empty graph if still processing
        if video.status in (VideoStatus.UPLOADED, VideoStatus.PROCESSING):
            return GraphResponse(video_id=video_id, nodes=[], relations=[])

    # Get nodes
    nodes_query = select(KnowledgeNode).where(
        KnowledgeNode.video_id == video_id
    ).order_by(KnowledgeNode.timestamp)
    nodes_result = await db.execute(nodes_query)
    nodes = nodes_result.scalars().all()

    # Get relations
    node_ids = [n.id for n in nodes]
    if node_ids:
        relations_query = select(Relation).where(
            Relation.source_node_id.in_(node_ids),
        )
        relations_result = await db.execute(relations_query)
        relations = relations_result.scalars().all()
    else:
        relations = []

    return GraphResponse(
        video_id=video_id,
        nodes=[NodeResponse(
            id=n.id, video_id=n.video_id,
            name=n.name, description=n.description,
            node_type=n.node_type.value if hasattr(n.node_type, 'value') else str(n.node_type),
            timestamp=n.timestamp,
            segment_index=n.segment_index,
            importance=n.importance,
            mastery=n.mastery.value if hasattr(n.mastery, 'value') else str(n.mastery)
        ) for n in nodes],
        relations=[RelationResponse(
            id=r.id, source_node_id=r.source_node_id,
            target_node_id=r.target_node_id,
            relation_type=r.relation_type.value if hasattr(r.relation_type, 'value') else str(r.relation_type),
            strength=r.strength, description=r.description
        ) for r in relations]
    )


@router.put("/mastery")
async def update_mastery(
    request: MasteryUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update mastery level of a knowledge node."""
    query = select(KnowledgeNode).where(KnowledgeNode.id == request.node_id)
    result = await db.execute(query)
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(404, "知识点未找到")

    node.mastery = MasteryLevel(request.mastery)
    await db.commit()
    return {"message": "掌握度已更新", "node_id": node.id, "mastery": node.mastery.value}


@router.get("/search/{video_id}")
async def search_nodes(
    video_id: int,
    query_str: str = "",
    db: AsyncSession = Depends(get_db)
):
    """Search knowledge nodes in a video's graph."""
    nodes_query = select(KnowledgeNode).where(
        KnowledgeNode.video_id == video_id,
        KnowledgeNode.name.contains(query_str) if query_str else True
    )
    result = await db.execute(nodes_query)
    nodes = result.scalars().all()

    return [
        {
            "id": n.id,
            "name": n.name,
            "node_type": n.node_type.value if hasattr(n.node_type, 'value') else str(n.node_type),
            "mastery": n.mastery.value if hasattr(n.mastery, 'value') else str(n.mastery),
            "importance": n.importance
        }
        for n in nodes
    ]
