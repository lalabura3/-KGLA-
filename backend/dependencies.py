"""FastAPI Dependencies — reusable dependency injection helpers.

Provides:
  - get_current_user: FastAPI dependency that extracts & validates JWT from
    the Authorization header, returns User model.
  - get_optional_user: Same but returns None if no token (for optional auth).

Usage:
    @router.get("/me")
    async def me(current_user: User = Depends(get_current_user)):
        ...
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import User

logger = logging.getLogger(__name__)

# ── Security scheme ──

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Dependencies ──


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: extract JWT, validate, return current User.

    If APP_AUTH_ENABLED is False, returns a placeholder anonymous user.
    This allows incremental auth rollout — no breaking change to existing endpoints.

    Raises:
        HTTPException 401: if token is missing, invalid, or expired.
    """
    # ── Auth disabled (MVP mode) ──
    if not settings.auth_enabled:
        # Return a placeholder anonymous user
        from uuid import uuid4

        result = await db.execute(
            __import__("sqlalchemy").select(User).where(User.username == "anonymous")
        )
        anon = result.scalar_one_or_none()
        if not anon:
            # Create anonymous user if not exists
            from ..services.auth_service import hash_password

            anon = User(
                id=uuid4(),
                username="anonymous",
                email="anonymous@studyai.local",
                hashed_password=hash_password("anonymous"),
            )
            db.add(anon)
            await db.flush()
            await db.refresh(anon)

        return anon

    # ── Auth enabled: validate token ──
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_TOKEN",
                "message": "Authorization header is required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    from ..services.auth_service import AuthService

    try:
        user = await AuthService.get_current_user(db, token)
        return user
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_TOKEN",
                "message": str(exc),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """FastAPI dependency: returns User if valid token, None otherwise.

    Use for endpoints that work both with and without authentication.
    """
    if not credentials:
        return None

    token = credentials.credentials

    from ..services.auth_service import AuthService

    try:
        user = await AuthService.get_current_user(db, token)
        return user
    except ValueError:
        return None
