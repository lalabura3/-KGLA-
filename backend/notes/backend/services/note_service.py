"""AI Note Generation Service — 3-stage pipeline for structured study notes.

Pipeline:
  1. metadata  → Generate title, summary, keywords, metadata via LLM
  2. sections  → Break transcript into structured, timestamp-anchored sections
  3. polish    → Hallucination self-check, language polish, dedup

Integrates with the LLM provider service and the ASR pipeline output (segments).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

from ..prompts.note_prompts import (
    METADATA_PROMPT,
    NOTE_OUTPUT_SCHEMA,  # shared schema from schemas/note_schema.py
    POLISH_PROMPT,
    SECTIONS_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


# ── Data types ──


@dataclass
class NoteEvidence:
    """Verbatim quote from transcript with source segment index."""
    quote: str
    segment_index: int


@dataclass
class NoteSection:
    """One structured note section anchored to a video timestamp range."""
    heading: str
    content: str
    start_time: float
    end_time: float
    key_points: list[str] = field(default_factory=list)
    source_segment_indices: list[int] = field(default_factory=list)
    evidence: list[NoteEvidence] = field(default_factory=list)
    hallucination_flags: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class NoteMetadata:
    """Video metadata extracted by LLM."""
    topic: str = ""
    difficulty: str = "intermediate"
    estimated_reading_time_minutes: int = 5
    requires_prerequisites: list[str] = field(default_factory=list)
    is_technical: bool = False
    has_code: bool = False
    language: str = "zh"
    speaker_count: int = 1


@dataclass
class NoteOutput:
    """Complete structured note output."""
    title: str = ""
    summary: str = ""
    sections: list[NoteSection] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    metadata: NoteMetadata = field(default_factory=NoteMetadata)
    raw_full_text: str = ""


@dataclass
class NoteGenerationResult:
    """Final result of note generation for a video."""
    video_id: uuid.UUID
    status: str  # "completed" | "failed"
    note: Optional[NoteOutput] = None
    error: Optional[str] = None
    stages_completed: int = 0
    elapsed_ms: float = 0.0


# ── Note Service ──


class NoteService:
    """Core note generation service: metadata → sections → polish."""

    def __init__(
        self,
        llm_url: str = "http://llm:8002",
        timeout: int = 120,
        max_retries: int = 2,
    ):
        self.llm_url = llm_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    # ── Stage 1: Metadata extraction ──

    async def extract_metadata(
        self,
        full_transcript: str,
    ) -> tuple[str, str, list[str], NoteMetadata]:
        """Generate title, summary, keywords, and metadata from full transcript."""
        prompt = METADATA_PROMPT.format(transcript=full_transcript[:16000])

        response_text = await self._call_llm(
            system=SYSTEM_PROMPT,
            user=prompt,
            temperature=0.3,
        )

        data = self._parse_json_safe(response_text)

        title = data.get("title", "Untitled")
        summary = data.get("summary", "")
        keywords = data.get("keywords", [])

        meta_raw = data.get("metadata", {})
        metadata = NoteMetadata(
            topic=meta_raw.get("topic", ""),
            difficulty=meta_raw.get("difficulty", "intermediate"),
            is_technical=meta_raw.get("is_technical", False),
            has_code=meta_raw.get("has_code", False),
            language=meta_raw.get("language", "zh"),
            speaker_count=meta_raw.get("speaker_count", 1),
        )

        logger.info(
            "Stage 1 (metadata) complete: title='%s', %d keywords, topic=%s",
            title, len(keywords), metadata.topic,
        )
        return title, summary, keywords, metadata

    # ── Stage 2: Section generation ──

    async def generate_sections(
        self,
        transcript_segments: list[dict],
        title: str,
        topic: str,
    ) -> list[NoteSection]:
        """Generate timestamp-anchored sections from transcript segments.

        Args:
            transcript_segments: List of dicts with keys:
                segment_index, start, end, text, speaker_id
            title: Video title from stage 1
            topic: Topic domain from stage 1
        """
        # Build timestamped transcript text
        transcript_text = self._build_timestamped_transcript(transcript_segments)

        prompt = SECTIONS_PROMPT.format(
            title=title,
            topic=topic,
            transcript_with_timestamps=transcript_text,
        )

        response_text = await self._call_llm(
            system=SYSTEM_PROMPT,
            user=prompt,
            temperature=0.4,
        )

        raw_sections = self._parse_json_safe(response_text)

        sections: list[NoteSection] = []
        for i, sec in enumerate(raw_sections):
            evidence = [
                NoteEvidence(quote=ev["quote"], segment_index=ev["segment_index"])
                for ev in sec.get("evidence", [])
            ]

            sections.append(
                NoteSection(
                    heading=sec.get("heading", f"Section {i + 1}"),
                    content=sec.get("content", ""),
                    start_time=float(sec.get("start_time", 0)),
                    end_time=float(sec.get("end_time", 0)),
                    key_points=sec.get("key_points", []),
                    source_segment_indices=sec.get("source_segment_indices", []),
                    evidence=evidence,
                )
            )

        logger.info("Stage 2 (sections) complete: %d sections", len(sections))
        return sections

    # ── Stage 3: Polish & hallucination check ──

    async def polish(
        self,
        note: NoteOutput,
        transcript_snippet: str,
    ) -> NoteOutput:
        """Polish language, check for hallucinations, dedup content."""
        notes_json = self._note_to_json(note)

        prompt = POLISH_PROMPT.format(
            transcript_snippet=transcript_snippet[:8000],
            notes_json=json.dumps(notes_json, ensure_ascii=False, indent=2),
        )

        response_text = await self._call_llm(
            system=SYSTEM_PROMPT,
            user=prompt,
            temperature=0.2,
        )

        polished = self._parse_json_safe(response_text)

        # Merge polished data back
        if polished.get("title"):
            note.title = polished["title"]
        if polished.get("summary"):
            note.summary = polished["summary"]
        if polished.get("keywords"):
            note.keywords = polished["keywords"]

        # Update sections with polish results, track hallucination flags
        polished_sections = polished.get("sections", [])
        for i, ps in enumerate(polished_sections):
            if i < len(note.sections):
                ns = note.sections[i]
                ns.heading = ps.get("heading", ns.heading)
                ns.content = ps.get("content", ns.content)
                ns.key_points = ps.get("key_points", ns.key_points)
                flags = ps.get("hallucination_flags", [])
                ns.hallucination_flags = flags
                if flags:
                    ns.confidence = max(0.0, 1.0 - 0.2 * len(flags))
                    logger.warning(
                        "Section #%d hallucination flags: %s (confidence=%.2f)",
                        i, flags, ns.confidence,
                    )

        # Compute overall hallucination score
        all_flags = [f for s in note.sections for f in s.hallucination_flags]
        hallucination_score = min(len(all_flags) * 0.1, 1.0) if note.sections else 0.0

        logger.info(
            "Stage 3 (polish) complete: %d section flags, overall_hallucination=%.2f",
            len(all_flags), hallucination_score,
        )
        return note

    # ── Full pipeline ──

    async def generate(
        self,
        video_id: uuid.UUID,
        transcript_segments: list[dict],
        progress_callback: Optional[callable] = None,
    ) -> NoteGenerationResult:
        """Run the full note generation pipeline.

        Args:
            video_id: UUID of the video.
            transcript_segments: ASR output segments as dicts with keys:
                segment_index, start, end, text, speaker_id
            progress_callback: async callable(stage: str, progress: int).

        Returns:
            NoteGenerationResult with structured note or error.
        """
        import time

        start = time.monotonic()

        try:
            if not transcript_segments:
                return NoteGenerationResult(
                    video_id=video_id,
                    status="failed",
                    error="No transcript segments provided",
                )

            # Build full transcript text (for metadata stage)
            full_transcript = "\n".join(
                f"[{seg['segment_index']}] ({seg['start']:.1f}s-{seg['end']:.1f}s) {seg.get('text', '')}"
                for seg in transcript_segments
            )

            if progress_callback:
                await progress_callback("metadata", 10)

            # Stage 1: Metadata
            title, summary, keywords, metadata = await self.extract_metadata(full_transcript)

            if progress_callback:
                await progress_callback("sections", 30)

            # Stage 2: Sections
            sections = await self.generate_sections(
                transcript_segments=transcript_segments,
                title=title,
                topic=metadata.topic,
            )

            if progress_callback:
                await progress_callback("polish", 70)

            # Build intermediate NoteOutput
            note = NoteOutput(
                title=title,
                summary=summary,
                sections=sections,
                keywords=keywords,
                metadata=metadata,
                raw_full_text=full_transcript,
            )

            # Stage 3: Polish
            transcript_snippet = full_transcript[:8000]
            note = await self.polish(note, transcript_snippet)

            # Compute full_text
            note.raw_full_text = self._compose_full_text(note)

            if progress_callback:
                await progress_callback("complete", 100)

            elapsed = (time.monotonic() - start) * 1000

            logger.info(
                "Note generation complete: video=%s, sections=%d, elapsed=%.0fms",
                video_id, len(note.sections), elapsed,
            )

            return NoteGenerationResult(
                video_id=video_id,
                status="completed",
                note=note,
                stages_completed=3,
                elapsed_ms=elapsed,
            )

        except Exception as exc:
            logger.exception("Note generation failed for video %s: %s", video_id, exc)
            elapsed = (time.monotonic() - start) * 1000
            return NoteGenerationResult(
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

        last_error: Optional[str] = None

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
                # Strip markdown code fences if present
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

        # Unreachable
        raise RuntimeError(f"LLM call failed: {last_error}")

    # ── Parsing helpers ──

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences (```json ... ```)."""
        text = text.strip()
        if text.startswith("```"):
            # Remove opening fence line
            text = re.sub(r"^```\w*\s*\n?", "", text)
            # Remove closing fence
            text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    @staticmethod
    def _parse_json_safe(text: str) -> dict | list:
        """Parse JSON safely, handling common LLM output issues."""
        text = NoteService._strip_fences(text)

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object/array with regex
        json_match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse LLM JSON output: %s", text[:500])
        return {} if text.strip().startswith("{") else []

    @staticmethod
    def _build_timestamped_transcript(segments: list[dict]) -> str:
        """Build a readable timestamped transcript for the LLM prompt."""
        lines = []
        for seg in segments:
            speaker = ""
            if seg.get("speaker_id"):
                speaker = f"[Speaker {seg['speaker_id']}] "
            lines.append(
                f"[Seg {seg['segment_index']}] "
                f"({seg['start']:.1f}s → {seg['end']:.1f}s) "
                f"{speaker}{seg.get('text', '')}"
            )
        return "\n".join(lines)

    @staticmethod
    def _note_to_json(note: NoteOutput) -> dict:
        """Serialize NoteOutput to dict for LLM polish stage."""
        return {
            "title": note.title,
            "summary": note.summary,
            "keywords": note.keywords,
            "metadata": {
                "topic": note.metadata.topic,
                "difficulty": note.metadata.difficulty,
                "is_technical": note.metadata.is_technical,
                "has_code": note.metadata.has_code,
                "language": note.metadata.language,
                "speaker_count": note.metadata.speaker_count,
            },
            "sections": [
                {
                    "heading": s.heading,
                    "content": s.content,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "key_points": s.key_points,
                    "source_segment_indices": s.source_segment_indices,
                    "evidence": [
                        {"quote": e.quote, "segment_index": e.segment_index}
                        for e in s.evidence
                    ],
                }
                for s in note.sections
            ],
        }

    @staticmethod
    def _compose_full_text(note: NoteOutput) -> str:
        """Compose the full readable note text from structured sections."""
        lines = [
            f"# {note.title}",
            "",
            f"## 摘要",
            note.summary,
            "",
            f"**关键词**: {', '.join(note.keywords)}",
            "",
        ]

        for i, section in enumerate(note.sections, 1):
            lines.append(f"## {section.heading}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.key_points:
                lines.append("**要点**:")
                for kp in section.key_points:
                    lines.append(f"- {kp}")
                lines.append("")

        return "\n".join(lines)


# Singleton
note_service = NoteService()
