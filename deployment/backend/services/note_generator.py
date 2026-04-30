"""Note generation service — uses LLM to create structured notes from ASR output."""
import json
from typing import List
from services.llm_service import llm_service, SYSTEM_PROMPTS


async def generate_segment_analysis(segment_text: str, start_time: float) -> dict:
    """Analyze a single video segment and extract knowledge points."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS["segment"]},
        {"role": "user", "content": f"视频片段（时间轴 {start_time:.1f}秒）：\n{segment_text}"}
    ]
    response = await llm_service.chat(messages)
    try:
        result = llm_service._parse_json_from_response(response)
        return result
    except (json.JSONDecodeError, KeyError, IndexError):
        # Fallback structured response
        return {
            "title": f"片段 {start_time:.0f}s",
            "summary": segment_text[:100],
            "keywords": [
                {"name": "知识点", "description": segment_text[:50], "type": "concept"}
            ]
        }


async def generate_full_note(video_title: str, transcript: str) -> str:
    """Generate a complete structured note for the entire video."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPTS["note_generation"].format(
            video_title=video_title
        )},
        {"role": "user", "content": transcript}
    ]
    response = await llm_service.chat(messages, temperature=0.3)
    return response
