"""QA and user endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.video import Video, VideoSegment, VideoStatus
from schemas.models import QARequest, QAResponse
from services.llm_service import llm_service, SYSTEM_PROMPTS

router = APIRouter(prefix="/api", tags=["qa"])


@router.post("/qa", response_model=QAResponse)
async def ask_question(request: QARequest, db: AsyncSession = Depends(get_db)):
    """Ask a question about video content (RAG-style)."""
    # Get video
    video_query = select(Video).where(Video.id == request.video_id)
    video_result = await db.execute(video_query)
    video = video_result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")

    # Get segments as context
    seg_query = select(VideoSegment).where(
        VideoSegment.video_id == request.video_id
    ).order_by(VideoSegment.segment_index)
    seg_result = await db.execute(seg_query)
    segments = seg_result.scalars().all()

    if not segments:
        raise HTTPException(400, "视频尚未完成处理，请稍后再试")

    # Build transcript context
    transcript_parts = []
    for s in segments:
        timestamp_min = int(s.start_time // 60)
        timestamp_sec = int(s.start_time % 60)
        transcript_parts.append(
            f"[{timestamp_min:02d}:{timestamp_sec:02d}] {s.content}"
        )
    transcript = "\n".join(transcript_parts)

    # Query LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS["qa"].format(transcript=transcript)},
        {"role": "user", "content": request.question}
    ]
    answer = await llm_service.chat(messages, temperature=0.5)

    # Find related segments (simple keyword matching)
    related = []
    question_lower = request.question.lower()
    for s in segments:
        if any(kw in s.content.lower() for kw in question_lower.split()):
            related.append({
                "segment_index": s.segment_index,
                "start_time": s.start_time,
                "title": s.title,
                "text": s.summary or s.content[:100]
            })

    return QAResponse(answer=answer, related_segments=related[:5])
