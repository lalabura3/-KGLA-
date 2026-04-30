"""Video upload and management endpoints."""
import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime

from database import get_db
from config import settings
from models.video import Video, VideoSegment, VideoStatus
from schemas.models import VideoResponse, VideoListResponse, VideoStatusResponse
from services.video_processor import extract_audio, extract_keyframes, get_video_duration
from services.asr_service import asr_service
from services.note_generator import generate_segment_analysis, generate_full_note
from services.graph_builder import build_video_graph

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    user_id: int = Form(1),  # Default user for MVP
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """Upload a video file and start processing."""
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.supported_video_formats:
        raise HTTPException(400, f"不支持的文件格式: {ext}。支持: {', '.join(settings.supported_video_formats)}")

    # Save file
    upload_dir = Path(settings.upload_dir) / "raw"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())[:8]
    save_path = upload_dir / f"{file_id}_{file.filename}"

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Create DB record
    db_video = Video(
        user_id=user_id,
        title=title or file.filename,
        filename=file.filename,
        file_path=str(save_path),
        status=VideoStatus.UPLOADED
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    # Start processing in background
    if background_tasks:
        background_tasks.add_task(process_video_pipeline, db_video.id, str(save_path))

    return VideoResponse(
        id=db_video.id,
        user_id=db_video.user_id,
        title=db_video.title,
        filename=db_video.filename,
        duration=db_video.duration,
        status=db_video.status.value,
        source_url=db_video.source_url,
        error_message=db_video.error_message,
        created_at=db_video.created_at,
        updated_at=db_video.updated_at
    )


@router.post("/link", response_model=VideoResponse)
async def import_from_link(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    user_id: int = Form(1),
    db: AsyncSession = Depends(get_db)
):
    """Import video from URL (placeholder — actual download depends on platform)."""
    # For MVP: create record with URL, user handles downloading
    db_video = Video(
        user_id=user_id,
        title=title or f"链接视频 {url[:30]}",
        filename=f"link_{uuid.uuid4().hex[:8]}.mp4",
        file_path="",  # No local file yet
        source_url=url,
        status=VideoStatus.UPLOADED
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    return VideoResponse(
        id=db_video.id,
        user_id=db_video.user_id,
        title=db_video.title,
        filename=db_video.filename,
        duration=db_video.duration,
        status=db_video.status.value,
        source_url=db_video.source_url,
        created_at=db_video.created_at,
        updated_at=db_video.updated_at
    )


@router.get("/", response_model=VideoListResponse)
async def list_videos(
    user_id: int = 1,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List all videos for a user."""
    query = select(Video).where(Video.user_id == user_id).order_by(Video.created_at.desc())
    result = await db.execute(query.offset(skip).limit(limit))
    videos = result.scalars().all()

    count_query = select(Video).where(Video.user_id == user_id)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return VideoListResponse(
        videos=[VideoResponse(
            id=v.id, user_id=v.user_id, title=v.title,
            filename=v.filename, duration=v.duration,
            status=v.status.value, source_url=v.source_url,
            error_message=v.error_message,
            created_at=v.created_at, updated_at=v.updated_at
        ) for v in videos],
        total=total
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Get video details."""
    query = select(Video).where(Video.id == video_id)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")
    return VideoResponse(
        id=video.id, user_id=video.user_id, title=video.title,
        filename=video.filename, duration=video.duration,
        status=video.status.value, source_url=video.source_url,
        error_message=video.error_message,
        created_at=video.created_at, updated_at=video.updated_at
    )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: int, db: AsyncSession = Depends(get_db)):
    """Get processing status of a video."""
    query = select(Video).where(Video.id == video_id)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")

    # Calculate progress based on status
    progress_map = {
        VideoStatus.UPLOADED: (0, "等待处理"),
        VideoStatus.PROCESSING: (30, "正在处理视频..."),
        VideoStatus.ASR_DONE: (50, "语音识别完成"),
        VideoStatus.NOTES_DONE: (70, "笔记生成完成"),
        VideoStatus.GRAPH_DONE: (90, "知识图谱生成中"),
        VideoStatus.COMPLETED: (100, "处理完成"),
        VideoStatus.FAILED: (0, f"处理失败: {video.error_message or '未知错误'}"),
    }
    progress, stage = progress_map.get(video.status, (0, "未知状态"))

    return VideoStatusResponse(
        id=video.id,
        status=video.status.value,
        progress=progress,
        current_stage=stage,
        error_message=video.error_message
    )


@router.delete("/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a video and its associated data."""
    query = select(Video).where(Video.id == video_id)
    result = await db.execute(query)
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "视频未找到")

    # Delete file
    if video.file_path and os.path.exists(video.file_path):
        os.remove(video.file_path)

    await db.delete(video)
    await db.commit()
    return {"message": "视频已删除", "id": video_id}


# ─── Background Processing Pipeline ───

async def process_video_pipeline(video_id: int, video_path: str):
    """Full processing pipeline: ASR → Notes → Knowledge Graph."""
    from database import async_session

    async with async_session() as db:
        try:
            query = select(Video).where(Video.id == video_id)
            result = await db.execute(query)
            video = result.scalar_one()

            video.status = VideoStatus.PROCESSING
            video.progress = 5
            await db.commit()

            # Step 1: Get duration + extract audio (0-20%)
            duration = await get_video_duration(video_path)
            video.duration = duration
            video.progress = 10
            await db.commit()

            audio_dir = Path(settings.upload_dir) / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = str(audio_dir / f"audio_{video_id}.wav")
            await extract_audio(video_path, audio_path)
            video.progress = 20
            await db.commit()

            # Step 2: Transcribe audio (20-40%)
            transcription = await asr_service.transcribe(audio_path)
            video.status = VideoStatus.ASR_DONE
            video.progress = 40
            await db.commit()

            # Step 3: Extract keyframes (40-45%)
            keyframe_dir = Path(settings.upload_dir) / "keyframes" / str(video_id)
            keyframes = await extract_keyframes(video_path, str(keyframe_dir))
            video.progress = 45
            await db.commit()

            # Step 4: Process segments with LLM (45-70%)
            segments_data = []
            total_segs = len(transcription.get("segments", []))
            for i, seg in enumerate(transcription.get("segments", [])):
                start = seg.get("start", i * 10)
                end = seg.get("end", (i + 1) * 10)
                text = seg.get("text", "")

                analysis = await generate_segment_analysis(text, start)

                db_segment = VideoSegment(
                    video_id=video.id,
                    segment_index=i,
                    start_time=start,
                    end_time=end,
                    title=analysis.get("title", f"片段 {i+1}"),
                    content=text,
                    summary=analysis.get("summary", ""),
                )
                db.add(db_segment)

                segments_data.append({
                    "segment_index": i,
                    "start_time": start,
                    "end_time": end,
                    "title": analysis.get("title", f"片段 {i+1}"),
                    "summary": analysis.get("summary", ""),
                    "keywords": analysis.get("keywords", []),
                    "content": text,
                })

                if total_segs > 0:
                    video.progress = 45 + int(25 * (i + 1) / total_segs)
                    await db.commit()

            await db.commit()
            video.status = VideoStatus.NOTES_DONE
            video.progress = 70
            await db.commit()

            # Step 5: Build knowledge graph (70-95%)
            from models.knowledge_node import KnowledgeNode, NodeType
            from models.relation import Relation, RelationType

            video.progress = 75
            await db.commit()

            graph_data = await build_video_graph(segments_data)

            video.progress = 85
            await db.commit()

            node_map = {}
            for idx, nd in enumerate(graph_data.get("nodes", [])):
                db_node = KnowledgeNode(
                    video_id=video.id,
                    name=nd["name"],
                    description=nd.get("description", ""),
                    node_type=nd.get("node_type", "concept"),
                    timestamp=nd.get("timestamp", 0),
                    segment_index=nd.get("segment_index", 0),
                    importance=nd.get("importance", 0.5),
                )
                db.add(db_node)
                await db.flush()
                node_map[idx] = db_node.id

            for rel in graph_data.get("relations", []):
                src_idx = rel.get("source_node_index")
                tgt_idx = rel.get("target_node_index")
                if src_idx is not None and tgt_idx is not None:
                    db_rel = Relation(
                        source_node_id=node_map[src_idx],
                        target_node_id=node_map[tgt_idx],
                        relation_type=rel.get("relation_type", "related"),
                        strength=rel.get("strength", 0.5),
                        description=rel.get("description", ""),
                    )
                    db.add(db_rel)

            await db.commit()
            video.status = VideoStatus.GRAPH_DONE
            video.progress = 95
            await db.commit()

            # Step 6: Done!
            video.status = VideoStatus.COMPLETED
            video.progress = 100
            await db.commit()

        except Exception as e:
            try:
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                await db.commit()
            except Exception:
                pass
            raise
