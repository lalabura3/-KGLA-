"""Auth API Router — user registration, login, profile management.

Endpoints:
  POST   /api/v1/auth/register      — create a new user account
  POST   /api/v1/auth/login         — authenticate and receive JWT
  GET    /api/v1/auth/me            — get current user profile
  PATCH  /api/v1/auth/me            — update current user profile
  POST   /api/v1/auth/refresh       — refresh access token

Auth headers: Authorization: Bearer <token>
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..dependencies import get_current_user
from ..database import get_db
from ..models import User
from ..schemas.user_schema import UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

logger = logging.getLogger(__name__)


# ── Pydantic schemas ──


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["charlie"])
    email: EmailStr = Field(..., examples=["charlie@studyai.dev"])
    password: str = Field(..., min_length=8, max_length=128, examples=["s3cret!!"])
    avatar_url: str | None = Field(None, max_length=512)


class RegisterResponse(BaseModel):
    id: str
    username: str
    email: str
    message: str = "Registration successful"


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["charlie"])
    password: str = Field(..., examples=["s3cret!!"])


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=3, max_length=64)
    email: EmailStr | None = None
    avatar_url: str | None = Field(None, max_length=512)


class MessageResponse(BaseModel):
    message: str


# ── Endpoints ──


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account.

    Username and email must be unique.
    Password is hashed with bcrypt before storage.
    """
    from ..services.auth_service import auth_service

    try:
        user = await auth_service.register(
            db=db,
            username=body.username,
            email=body.email,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await db.commit()

    return RegisterResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username and password, receive a JWT access token.

    Token format: "Bearer <jwt>"
    Token expiry: configured by APP_ACCESS_TOKEN_EXPIRE_MINUTES (default 1440 = 24h).
    """
    from ..services.auth_service import auth_service

    try:
        result = await auth_service.login(
            db=db,
            username=body.username,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    return LoginResponse(**result)


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's profile.

    Requires: Authorization: Bearer <token>
    """
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile.

    Requires: Authorization: Bearer <token>
    """
    if body.username is not None:
        # Check uniqueness
        from sqlalchemy import select

        existing = await db.execute(
            select(User)
            .where(User.username == body.username)
            .where(User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Username '{body.username}' is already taken",
            )
        current_user.username = body.username

    if body.email is not None:
        current_user.email = body.email
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url

    await db.commit()
    await db.refresh(current_user)

    return UserRead.model_validate(current_user)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """Refresh the access token — issue a new one with fresh expiry.

    Requires: Authorization: Bearer <token> (still-valid token)
    """
    from ..services.auth_service import create_access_token

    token = create_access_token(current_user.id, current_user.username)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
        },
    )
