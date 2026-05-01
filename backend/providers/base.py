"""LLM Provider — abstract base class.

All LLM providers must implement this interface. The factory
(providers/__init__.py) selects the active provider at startup
based on `settings.llm_provider`.

Hot-swap: change APP_LLM_PROVIDER env var + restart.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class LLMProvider(ABC):
    """Abstract interface for LLM backends.

    Implementations:
        - DeepSeekProvider  (cloud API, OpenAI-compatible)
        - QwenLocalProvider (Ollama / vLLM, local deployment)
    """

    @abstractmethod
    async def chat_completion(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request and return the text response.

        Args:
            system: System prompt.
            user: User prompt / message content.
            temperature: Sampling temperature (0.0–1.0).
            max_tokens: Maximum tokens in the response.
            json_mode: If True, request JSON-only output (provider-dependent).

        Returns:
            Text content of the first choice.
        """
        ...

    @abstractmethod
    async def chat_completion_stream(
        self,
        *,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion — yields text chunks as they arrive."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g. 'deepseek', 'qwen-local')."""
        ...

    @property
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Whether this provider natively supports structured JSON output."""
        ...
