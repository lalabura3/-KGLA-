"""ASR Pipeline service — orchestrates audio extraction, Whisper transcription, and VAD.

Workflow:
  1. extract_audio  → FFmpeg: video → mono 16kHz WAV
  2. run_vad        → Silero VAD: detect speech regions
  3. transcribe     → Whisper HTTP: audio → segments[]
  4. post_process   → Term dictionary injection + VAD alignment
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp

from ..utils.term_dictionary import TermDictionary, default_terms
from .vad_service import VADResult, VADSegment, vad_service

logger = logging.getLogger(__name__)


# ── Data types ──


@dataclass
class ASRSegment:
    """Single transcribed segment with metadata."""

    index: int
    start: float  # seconds
    end: float  # seconds
    text: str
    confidence: float = 0.0
    words: list[str] = field(default_factory=list)
    speaker_id: Optional[str] = None


@dataclass
class ASRResult:
    """Full ASR result for a video."""

    video_id: uuid.UUID
    segments: list[ASRSegment] = field(default_factory=list)
    language: str = "zh"
    duration: float = 0.0
    vad_result: Optional[VADResult] = None


# ── ASR Service ──


class ASRService:
    """Core ASR service: extract audio, transcribe via Whisper, post-process."""

    def __init__(
        self,
        whisper_url: str = "http://whisper:8001",
        term_dict: Optional[TermDictionary] = None,
    ):
        self.whisper_url = whisper_url.rstrip("/")
        self.term_dict = term_dict or default_terms

    # ── Step 1: Audio extraction ──

    async def extract_audio(
        self,
        video_path: Path,
        output_dir: Optional[Path] = None,
        sample_rate: int = 16000,
    ) -> Path:
        """Extract mono 16kHz WAV audio from video using FFmpeg.

        Returns Path to the extracted WAV file.
        """
        output_dir = output_dir or Path(tempfile.gettempdir()) / "studyai_audio"
        output_dir.mkdir(parents=True, exist_ok=True)

        video_id = video_path.stem
        audio_path = output_dir / f"{video_id}.wav"

        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # no video
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", "1",  # mono
            "-y",  # overwrite
            str(audio_path),
        ]

        logger.info("Extracting audio: %s → %s", video_path.name, audio_path.name)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(f"FFmpeg audio extraction failed: {error_msg}")

        # Parse duration from FFmpeg stderr
        duration = self._parse_duration(stderr.decode("utf-8", errors="replace"))
        logger.info(
            "Audio extracted: %s (%.1fs, %d bytes)",
            audio_path.name,
            duration,
            audio_path.stat().st_size,
        )

        return audio_path

    # ── Step 2: VAD ──

    async def run_vad(self, audio_path: Path, sample_rate: int = 16000) -> VADResult:
        """Run voice activity detection on extracted audio."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, vad_service.detect, audio_path, sample_rate)
        logger.info(
            "VAD complete: %d speech segments (%.1fs / %.1fs, ratio=%.2f)",
            len(result.segments),
            result.speech_duration,
            result.total_duration,
            result.speech_ratio,
        )
        return result

    # ── Step 3: Whisper transcription ──

    async def transcribe(
        self,
        audio_path: Path,
        language: str = "zh",
        vad_segments: Optional[list[VADSegment]] = None,
        initial_prompt: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> list[ASRSegment]:
        """Send audio to Whisper service for transcription.

        Uses faster-whisper large-v3 via CTranslate2 backend.
        """
        if not initial_prompt:
            initial_prompt = self.term_dict.build_prompt()

        # Build hotwords from term dictionary
        hotwords = self.term_dict.get_hotwords("")  # all terms

        payload = {
            "language": language,
            "initial_prompt": initial_prompt,
            "hotwords": hotwords,
            "vad_filter": True,
            "word_timestamps": True,
        }

        # If VAD segments provided, pass them to Whisper for guided decoding
        if vad_segments:
            payload["vad_segments"] = [
                {"start": s.start, "end": s.end} for s in vad_segments
            ]

        transcribe_url = f"{self.whisper_url}/transcribe"

        async with aiohttp.ClientSession() as session:
            # Step A: Upload audio
            with open(audio_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("audio", f, filename=audio_path.name)
                form.add_field("params", json.dumps(payload))

                async with session.post(
                    transcribe_url, data=form, timeout=aiohttp.ClientTimeout(total=600)
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(
                            f"Whisper transcription failed (HTTP {resp.status}): {text[:500]}"
                        )
                    result = await resp.json()

        segments = []
        for i, seg in enumerate(result.get("segments", [])):
            segments.append(
                ASRSegment(
                    index=i,
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                    confidence=seg.get("confidence", 0.0),
                    words=seg.get("words", []),
                )
            )

        logger.info("Whisper transcription complete: %d segments", len(segments))
        return segments

    # ── Step 4: Post-processing ──

    def post_process(
        self, segments: list[ASRSegment], vad_result: Optional[VADResult] = None
    ) -> list[ASRSegment]:
        """Post-process segments: term injection, VAD alignment, confidence smoothing."""
        # Convert to dict for term dictionary injection
        segment_dicts = [
            {
                "text": s.text,
                "start": s.start,
                "end": s.end,
                "confidence": s.confidence,
            }
            for s in segments
        ]
        corrected = self.term_dict.inject_into_segments(segment_dicts)

        # Rebuild ASRSegment list
        for i, (orig, corr) in enumerate(zip(segments, corrected)):
            orig.text = corr["text"]
            if corr["text"] != orig.text:
                logger.debug("Term corrected: '%s' → '%s'", orig.text, corr["text"])

        # Align with VAD boundaries (trim silence edges)
        if vad_result and vad_result.segments:
            segments = self._align_with_vad(segments, vad_result.segments)

        return segments

    @staticmethod
    def _align_with_vad(
        segments: list[ASRSegment], vad_segments: list[VADSegment]
    ) -> list[ASRSegment]:
        """Adjust segment boundaries to match VAD-detected speech regions."""
        aligned: list[ASRSegment] = []
        vad_idx = 0

        for seg in segments:
            # Find the VAD segment that contains this ASR segment's midpoint
            seg_mid = (seg.start + seg.end) / 2
            while vad_idx < len(vad_segments) - 1 and vad_segments[vad_idx].end < seg_mid:
                vad_idx += 1

            if vad_idx < len(vad_segments):
                vad = vad_segments[vad_idx]
                # Clamp to VAD boundary (with 100ms padding)
                padding = 0.1
                seg.start = max(seg.start, vad.start - padding)
                seg.end = min(seg.end, vad.end + padding)

            aligned.append(seg)

        return aligned

    # ── Full pipeline ──

    async def process(
        self,
        video_path: Path,
        video_id: uuid.UUID,
        language: str = "zh",
        run_vad: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> ASRResult:
        """Run the full ASR pipeline: extract → VAD → transcribe → post-process."""
        result = ASRResult(video_id=video_id, language=language)

        if progress_callback:
            await progress_callback("extracting", 0)

        # Step 1: Extract audio
        audio_path = await self.extract_audio(video_path)
        result.duration = self._get_audio_duration(audio_path)

        if progress_callback:
            await progress_callback("vad", 20)

        # Step 2: VAD
        vad_result = None
        if run_vad:
            vad_result = await self.run_vad(audio_path)
            result.vad_result = vad_result

        if progress_callback:
            await progress_callback("transcribing", 30)

        # Step 3: Transcribe
        initial_prompt = self.term_dict.build_prompt()
        segments = await self.transcribe(
            audio_path,
            language=language,
            vad_segments=vad_result.segments if vad_result else None,
            initial_prompt=initial_prompt,
            progress_callback=progress_callback,
        )

        if progress_callback:
            await progress_callback("post_processing", 85)

        # Step 4: Post-process
        segments = self.post_process(segments, vad_result)
        result.segments = segments

        if progress_callback:
            await progress_callback("complete", 100)

        # Cleanup
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            pass

        logger.info(
            "ASR pipeline complete: video=%s, segments=%d, duration=%.1fs",
            video_id,
            len(segments),
            result.duration,
        )
        return result

    # ── Helpers ──

    @staticmethod
    def _parse_duration(ffmpeg_stderr: str) -> float:
        """Parse duration from FFmpeg stderr output."""
        import re

        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", ffmpeg_stderr)
        if match:
            h, m, s, cs = match.groups()
            return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100
        return 0.0

    @staticmethod
    def _get_audio_duration(audio_path: Path) -> float:
        """Get audio duration via FFprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0


# Singleton
asr_service = ASRService()
