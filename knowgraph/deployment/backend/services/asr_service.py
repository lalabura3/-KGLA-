"""ASR Service — communicates with Whisper API service."""
import httpx
from typing import Optional
from config import settings


class ASRService:
    def __init__(self):
        self.base_url = settings.whisper_url
        self.client = httpx.AsyncClient(timeout=3600.0)  # Long timeout for transcription

    async def transcribe(self, audio_path: str, language: str = "zh") -> dict:
        """Transcribe audio file using Whisper service.
        Returns dict with: segments [{start, end, text}, ...], full_text
        """
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
                params = {"language": language, "response_format": "verbose_json"}
                resp = await self.client.post(
                    f"{self.base_url}/transcribe",
                    files=files,
                    params=params
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.RequestError as e:
            # Fallback: return mock data for development without GPU
            return self._mock_transcribe(audio_path)

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _mock_transcribe(self, audio_path: str) -> dict:
        """Mock transcription for development without GPU service running."""
        import os
        filename = os.path.basename(audio_path)
        return {
            "full_text": f"这是来自文件 {filename} 的模拟语音识别结果。请在部署 Whisper 服务后获得真实转录。",
            "segments": [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "text": f"这是来自文件 {filename} 的模拟语音识别结果。"
                },
                {
                    "start": 10.0,
                    "end": 20.0,
                    "text": "请在部署 Whisper 服务后获得真实转录。"
                }
            ],
            "language": "zh",
            "mock": True
        }


import os  # noqa: E402 (fix import order)

asr_service = ASRService()
