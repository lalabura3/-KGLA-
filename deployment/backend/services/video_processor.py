"""Video processing service — FFmpeg keyframe extraction, format handling."""
import os
import asyncio
import subprocess
from pathlib import Path
from config import settings


async def extract_audio(video_path: str, output_path: str) -> str:
    """Extract audio from video for ASR processing.
    Returns path to extracted audio file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # PCM 16-bit
        "-ar", "16000",           # 16kHz sample rate (Whisper optimal)
        "-ac", "1",               # mono
        "-y",                     # overwrite
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {stderr.decode()}")
    return output_path


async def extract_keyframes(video_path: str, output_dir: str, interval: int = None) -> list:
    """Extract keyframes at regular intervals.
    Returns list of keyframe file paths.
    """
    if interval is None:
        interval = settings.keyframe_interval

    os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps=1/{interval},scale=640:-1",
        "-q:v", "5",
        "-y",
        output_pattern
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    # Collect generated keyframes
    frames = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.startswith("frame_") and f.endswith(".jpg")
    ])
    return frames


async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return float(stdout.decode().strip())


def find_closest_keyframe(keyframes: list, timestamp: float, interval: int = 10) -> str:
    """Find the keyframe closest to given timestamp."""
    target_frame = round(timestamp / interval)
    # Keyframes are named frame_0001.jpg, frame_0002.jpg, etc.
    target_filename = f"frame_{target_frame:04d}.jpg"
    for kf in keyframes:
        if target_filename in kf:
            return kf
    # Fallback: return first available keyframe
    return keyframes[0] if keyframes else ""
