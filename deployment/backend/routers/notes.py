"""Notes and segments API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.video import Video, VideoSegment, VideoStatus
from schemas.models import NoteResponse, SegmentResponse, NoteUpdateRequest

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("/{video_id}", response_model=NoteResponse)
async def get_notes(video_id: int, db: AsyncSession = Depends(get_db)):
    """Get AI-generated notes for a video."""
    # Get video
    video_query = select(Video).where(Video.id == video_id)
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")

    if video.status in (VideoStatus.UPLOADED, VideoStatus.PROCESSING):
        raise HTTPException(400, "视频正在处理中，请稍后再查看笔记")

    # Get segments
    seg_query = select(VideoSegment).where(
        VideoSegment.video_id == video_id
    ).order_by(VideoSegment.segment_index)
    seg_result = await db.execute(seg_query)
    segments = seg_result.scalars().all()

    return NoteResponse(
        video_id=video.id,
        video_title=video.title,
        segments=[
            SegmentResponse(
                id=s.id, video_id=s.video_id,
                segment_index=s.segment_index,
                start_time=s.start_time, end_time=s.end_time,
                title=s.title, content=s.content,
                summary=s.summary, keyframe_path=s.keyframe_path
            ) for s in segments
        ],
        total_segments=len(segments)
    )


@router.put("/{video_id}/segment/{segment_id}")
async def update_segment(
    video_id: int,
    segment_id: int,
    request: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Edit a note segment (user manual edit)."""
    query = select(VideoSegment).where(
        VideoSegment.id == segment_id,
        VideoSegment.video_id == video_id
    )
    result = await db.execute(query)
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(404, "笔记片段未找到")

    segment.content = request.content
    await db.commit()
    return {"message": "笔记已更新"}
