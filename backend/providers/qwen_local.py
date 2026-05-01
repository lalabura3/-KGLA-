"""Qwen Local Provider — Ollama / vLLM local deployment.

For offline / air-gapped deployment with Qwen 2.5 via Ollama.

Configuration via settings:
    APP_LLM_QWEN_BASE_URL=http://ollama:11434/v1
    APP_LLM_QWEN_MODEL=qwen2.5:14b
"""
from __future__ import annotations

import json as _json
import logging
import re
from typing import AsyncGenerator

import httpx

from .base import LLMProvider

logger = logging.getLogger(__name__)


class QwenLocalProvider(LLMProvider):
    """Qwen local deployment via Ollama / vLLM OpenAI-compatible endpoint.

    Ollama usage:
        ollama pull qwen2.5:14b
        ollama serve
    """

    def __init__(
        self,
        *,
        base_url: str = "http://ollama:11434/v1",
        model: str = "qwen2.5:14b",
        timeout: float = 120.0,
        max_retries: int = 2,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = httpx.Timeout(timeout, connect=10.0)
        self._max_retries = max_retries

    # ── LLMProvider interface ──

    @property
    def provider_name(self) -> str:
        return "qwen-local"

    @property
    def supports_structured_output(self) -> bool:
        # Ollama's OpenAI endpoint supports response_format json_object
        return True

    async def chat_completion(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        return await self._request("/chat/completions", payload)

    async def chat_completion_stream(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue

    # ── Internal ──

    async def _request(self, path: str, payload: dict) -> str:
        """Send POST to local LLM endpoint with retry logic."""
        last_error: str | None = None

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        f"{self._base_url}{path}",
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if resp.status_code != 200:
                        text = await resp.aread()
                        raise RuntimeError(
                            f"Qwen local error (HTTP {resp.status_code}): {text[:500]}"
                        )
                    data = resp.json()

                content = data["choices"][0]["message"]["content"]
                return self._strip_fences(content)

            except Exception as exc:
                last_error = str(exc)
                if attempt < self._max_retries:
                    import asyncio

                    wait = 2 ** attempt
                    logger.warning(
                        "Qwen-local attempt %d/%d failed: %s. Retry in %ds…",
                        attempt + 1, self._max_retries + 1, last_error, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(
                        f"Qwen-local failed after {self._max_retries + 1} attempts: {last_error}"
                    )

        raise RuntimeError(f"Qwen-local unreachable: {last_error}")

    @staticmethod
    def _strip_fences(text: str) -> str:
        """Remove markdown code fences."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()
