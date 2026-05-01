"""LLM Provider factory + exports.

Selects the active provider at module-load time based on
`settings.llm_provider`.  Hot-swap: change the env var, restart.

Supported providers:
    - "deepseek"  → DeepSeekProvider (cloud)
    - "qwen-local" → QwenLocalProvider (Ollama/vLLM)
    - "auto"       → Try deepseek first, fallback to qwen-local
"""
from __future__ import annotations

import logging
from functools import lru_cache

from .base import LLMProvider
from .deepseek import DeepSeekProvider
from .qwen_local import QwenLocalProvider

logger = logging.getLogger(__name__)


def _build_llm_provider() -> LLMProvider:
    """Build and return the active LLM provider based on config."""
    from backend.config import settings

    provider_type = settings.llm_provider.lower().strip()

    if provider_type == "deepseek":
        return DeepSeekProvider(
            api_key=settings.llm_deepseek_api_key,
            base_url=settings.llm_deepseek_base_url,
            model=settings.llm_deepseek_model,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )

    if provider_type == "qwen-local":
        # For local deployment: no API key needed
        return QwenLocalProvider(
            base_url=settings.llm_qwen_base_url,
            model=settings.llm_qwen_model,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )

    if provider_type == "auto":
        # Try DeepSeek first, fallback to Qwen-local
        logger.info("LLM provider 'auto': trying DeepSeek…")
        if settings.llm_deepseek_api_key:
            logger.info("DeepSeek API key found, using DeepSeek provider.")
            return _build_llm_provider()  # re-enter as "deepseek"
        logger.info("No DeepSeek key, falling back to Qwen-local.")
        return QwenLocalProvider(
            base_url=settings.llm_qwen_base_url,
            model=settings.llm_qwen_model,
            timeout=settings.llm_timeout,
            max_retries=settings.llm_max_retries,
        )

    raise ValueError(
        f"Unknown LLM provider type: {provider_type!r}. "
        f"Supported: deepseek, qwen-local, auto"
    )


@lru_cache()
def get_llm_provider() -> LLMProvider:
    """Return the cached singleton LLM provider.

    Hot-swap: change APP_LLM_PROVIDER env var and restart the process.
    """
    provider = _build_llm_provider()
    logger.info(
        "LLM provider selected: %s (structured_output=%s)",
        provider.provider_name,
        provider.supports_structured_output,
    )
    return provider


# Convenience alias — evaluated at first import
llm_provider: LLMProvider | None = None


def _lazy_init():
    """Lazy-init the module-level singleton so import order doesn't matter."""
    global llm_provider
    if llm_provider is None:
        llm_provider = get_llm_provider()
    return llm_provider


__all__ = [
    "LLMProvider",
    "DeepSeekProvider",
    "QwenLocalProvider",
    "get_llm_provider",
    "llm_provider",
]
