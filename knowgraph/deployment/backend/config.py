"""Application configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/learnflow.db"

    # File storage
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 500

    # AI Services URLs
    whisper_url: str = "http://localhost:8001"
    llm_url: str = "http://localhost:8002"

    # LLM Mode: "api" or "local"
    llm_mode: str = "api"
    llm_api_key: str = ""
    llm_api_base: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # Video processing
    keyframe_interval: int = 10  # seconds between keyframes
    supported_video_formats: list = [".mp4", ".flv", ".avi", ".mov", ".mkv", ".webm"]

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


settings = Settings()
