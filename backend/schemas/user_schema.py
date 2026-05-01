"""Pydantic schemas for User."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Request body for creating a user."""
    username: str = Field(..., min_length=3, max_length=64, examples=["charlie"])
    email: EmailStr = Field(..., examples=["charlie@studyai.dev"])
    password: str = Field(..., min_length=8, max_length=128, examples=["s3cret!!"])


class UserUpdate(BaseModel):
    """Request body for partial user update."""
    username: str | None = Field(None, min_length=3, max_length=64)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    avatar_url: str | None = Field(None, max_length=512)


class UserRead(BaseModel):
    """Public user representation (never includes password)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "charlie",
                "email": "charlie@studyai.dev",
                "avatar_url": None,
                "created_at": "2026-05-01T00:00:00+08:00",
                "updated_at": "2026-05-01T00:00:00+08:00",
            }
        }
