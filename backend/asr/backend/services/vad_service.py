"""Voice Activity Detection (VAD) service — split audio into speech segments.

Uses Silero VAD (via silero-vad) or fallback energy-based detection.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Data types ──


@dataclass
class VADSegment:
    start: float  # seconds
    end: float  # seconds
    confidence: float = 1.0


@dataclass
class VADResult:
    segments: list[VADSegment] = field(default_factory=list)
    total_duration: float = 0.0
    speech_duration: float = 0.0

    @property
    def speech_ratio(self) -> float:
        return self.speech_duration / max(self.total_duration, 0.001)


# ── VAD Service ──


class VADService:
    """Detects speech regions in audio for ASR preprocessing.

    Strategy:
      1. Try Silero VAD (lightweight PyTorch model) — best accuracy.
      2. Fallback: energy-based threshold (numpy).
    """

    def __init__(self, method: str = "auto"):
        self.method = method
        self._silero_model = None

    def detect(self, audio_path: Path, sample_rate: int = 16000) -> VADResult:
        """Run VAD on a WAV file, return speech segment boundaries."""
        try:
            return self._silero_detect(audio_path, sample_rate)
        except ImportError:
            logger.info("Silero VAD not available, falling back to energy-based VAD")
            return self._energy_based_detect(audio_path, sample_rate)
        except Exception as exc:
            logger.warning("Silero VAD failed (%s), falling back to energy-based", exc)
            return self._energy_based_detect(audio_path, sample_rate)

    def _silero_detect(self, audio_path: Path, sample_rate: int) -> VADResult:
        """Silero VAD: Returns speech segments with timestamps."""
        try:
            from silero_vad import (
                VADIterator,
                read_audio,
            )
        except ImportError:
            raise

        audio = read_audio(str(audio_path), sampling_rate=sample_rate)
        audio_np = audio.numpy()

        vad = VADIterator(sample_rate=sample_rate)
        segments: list[VADSegment] = []
        window_samples = 512  # 32ms at 16kHz
        is_speech = False
        speech_start = 0.0

        for i in range(0, len(audio_np) - window_samples, window_samples):
            chunk = audio_np[i : i + window_samples]
            result = vad(chunk)
            if result is not None:
                for speech_chunk in result:
                    if not is_speech:
                        is_speech = True
                        speech_start = i / sample_rate
                    # Keep accumulating
                if is_speech and not result:
                    is_speech = False
                    segments.append(
                        VADSegment(start=speech_start, end=i / sample_rate)
                    )

        # Close trailing speech segment
        if is_speech:
            segments.append(
                VADSegment(start=speech_start, end=len(audio_np) / sample_rate)
            )

        vad.reset_states()

        total_duration = len(audio_np) / sample_rate
        speech_duration = sum(s.end - s.start for s in segments)

        return VADResult(
            segments=segments,
            total_duration=total_duration,
            speech_duration=speech_duration,
        )

    def _energy_based_detect(self, audio_path: Path, sample_rate: int) -> VADResult:
        """Fallback: energy-threshold VAD using numpy + scipy (if available)."""
        try:
            from scipy.io import wavfile

            sr, audio = wavfile.read(str(audio_path))
        except ImportError:
            # Raw numpy fallback: read PCM with subprocess
            audio = self._read_raw_pcm(audio_path, sample_rate)
            sr = sample_rate

        if audio.ndim > 1:
            audio = audio.mean(axis=1)  # stereo → mono
        audio = audio.astype(np.float32)

        # Normalize
        if np.abs(audio).max() > 0:
            audio /= np.abs(audio).max()

        # Energy envelope
        frame_len = int(sr * 0.025)  # 25ms
        hop_len = int(sr * 0.010)  # 10ms
        energy = np.array(
            [
                np.sqrt(np.mean(audio[i : i + frame_len] ** 2))
                for i in range(0, len(audio) - frame_len, hop_len)
            ]
        )

        # Adaptive threshold: 20% of max energy
        threshold = np.max(energy) * 0.20
        is_speech = energy > threshold

        segments = self._merge_intervals(is_speech, hop_len / sr)
        total_duration = len(audio) / sr
        speech_duration = sum(s.end - s.start for s in segments)

        return VADResult(
            segments=segments,
            total_duration=total_duration,
            speech_duration=speech_duration,
        )

    @staticmethod
    def _merge_intervals(
        is_speech: np.ndarray, frame_dur: float, min_silence_gap: float = 0.3
    ) -> list[VADSegment]:
        """Merge contiguous speech frames, bridging short silence gaps."""
        segments: list[VADSegment] = []
        in_speech = False
        silence_frames = 0
        max_silence_frames = int(min_silence_gap / frame_dur)
        speech_start = 0

        for i, speech in enumerate(is_speech):
            if speech:
                if not in_speech and silence_frames <= max_silence_frames and segments:
                    # Bridge short silence — extend previous segment
                    segments[-1].end = (i + 1) * frame_dur
                    silence_frames = 0
                elif not in_speech:
                    speech_start = i * frame_dur
                    in_speech = True
                silence_frames = 0
            else:
                if in_speech:
                    silence_frames += 1
                    if silence_frames > max_silence_frames:
                        segments.append(
                            VADSegment(
                                start=speech_start,
                                end=(i - silence_frames + 1) * frame_dur,
                            )
                        )
                        in_speech = False
                        silence_frames = 0

        if in_speech:
            segments.append(
                VADSegment(
                    start=speech_start,
                    end=len(is_speech) * frame_dur,
                )
            )

        return segments

    @staticmethod
    def _read_raw_pcm(audio_path: Path, sample_rate: int) -> np.ndarray:
        """Read raw PCM from WAV using FFmpeg."""
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                "-",
            ],
            capture_output=True,
            check=True,
        )
        return np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)


# Singleton
vad_service = VADService()
