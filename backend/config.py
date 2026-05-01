"""
Configuration management via pydantic-settings.
All env vars prefixed with APP_ or sourced from .env.

Loads in order: defaults → .env file → environment variables.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "StudyAI Backend"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # ── API ──
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Database (PostgreSQL async) ──
    database_url: str = (
        "postgresql+asyncpg://studyai:studyai@postgres:5432/studyai"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # ── Database sync URL (for Alembic) ──
    database_sync_url: str = (
        "postgresql://studyai:studyai@postgres:5432/studyai"
    )

    # ── Redis ──
    redis_url: str = "redis://redis:6379/0"
    redis_result_backend: str = "redis://redis:6379/1"

    # ── Celery ──
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    celery_task_time_limit: int = 1800  # 30 min
    celery_worker_prefetch_multiplier: int = 1

    # ── Whisper Service ──
    whisper_service_url: str = "http://whisper:8001"

    # ── LLM Provider ──
    llm_provider: Literal["deepseek", "qwen-local", "auto"] = "auto"
    llm_timeout: int = 120
    llm_max_retries: int = 2

    # DeepSeek (cloud)
    llm_deepseek_api_key: str = ""
    llm_deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_deepseek_model: str = "deepseek-chat"

    # Qwen (local Ollama/vLLM)
    llm_qwen_base_url: str = "http://ollama:11434/v1"
    llm_qwen_model: str = "qwen2.5:14b"

    # ── Uploads ──
    upload_dir: Path = Path("/uploads")
    max_upload_size_mb: int = 2048

    # ── CORS ──
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True

    # ── Logging ──
    log_level: str = "INFO"
    log_format: Literal["structured", "plain"] = "structured"

    # ── Security (MVP) ──
    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ── Celery Task Routing ──
    celery_task_routes: dict = {
        "process_video_asr": {"queue": "asr"},
        "process_video_notes": {"queue": "notes"},
        "process_video_graph": {"queue": "graph"},
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()


# Convenience alias
settings = get_settings()
