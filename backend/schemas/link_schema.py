"""Pydantic schemas for link import & metadata extraction."""
from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class LinkImportRequest(BaseModel):
    """Request to import a video from an HTTP link."""
    url: HttpUrl = Field(
        ...,
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )
    title: str | None = Field(
        None,
        max_length=512,
        description="Optional: override the auto-extracted title",
    )
    language: str = Field(
        "zh",
        description="Expected spoken language for ASR",
    )
    tags: list[str] = Field(default_factory=list, max_length=20)


class LinkImportResponse(BaseModel):
    """Response after link import is queued."""
    video_id: str
    url: str
    title: str | None = None
    status: str = "queued"
    message: str


class LinkMetadataResponse(BaseModel):
    """Preview: extracted metadata before import."""
    url: str
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    platform: str | None = None
    author: str | None = None
    extractable: bool = False
    error: str | None = None
