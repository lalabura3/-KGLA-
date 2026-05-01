"""Authentication Service — JWT token generation, bcrypt hashing, credential validation.

Flow:
  register → hash password (bcrypt) → store User
  login    → verify password → issue access_token (JWT)
  verify   → decode JWT → return current_user

Configuration: controlled by APP_AUTH_ENABLED env var.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import User

logger = logging.getLogger(__name__)

# ── Password hashing ──

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT ──


def create_access_token(
    user_id: uuid.UUID,
    username: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Payload includes:
      - sub: user_id (string)
      - username: human-readable
      - iat: issued-at timestamp
      - exp: expiration timestamp
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Returns the token payload dict.

    Raises:
        JWTError: if token is invalid, expired, or malformed.
    """
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


# ── Auth Service ──


class AuthService:
    """Authentication service: register, login, verify."""

    @staticmethod
    async def register(
        db: AsyncSession,
        username: str,
        email: str,
        password: str,
    ) -> User:
        """Register a new user.

        Args:
            db: Async DB session.
            username: Desired username (unique).
            email: Email address (unique).
            password: Plaintext password (≥8 chars).

        Returns:
            Created User ORM instance.

        Raises:
            ValueError: if username or email already taken.
        """
        # Check uniqueness
        existing_username = await db.execute(
            select(User).where(User.username == username)
        )
        if existing_username.scalar_one_or_none():
            raise ValueError(f"Username '{username}' is already taken")

        existing_email = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalar_one_or_none():
            raise ValueError(f"Email '{email}' is already registered")

        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        logger.info("User registered: id=%s, username=%s", user.id, username)
        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        username: str,
        password: str,
    ) -> dict:
        """Authenticate a user and return a JWT access token.

        Args:
            db: Async DB session.
            username: Username.
            password: Plaintext password.

        Returns:
            {
                "access_token": str,
                "token_type": "bearer",
                "user": { "id": str, "username": str, "email": str }
            }

        Raises:
            ValueError: invalid credentials.
        """
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid username or password")

        token = create_access_token(user.id, user.username)

        logger.info("User logged in: id=%s, username=%s", user.id, username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
            },
        }

    @staticmethod
    async def get_current_user(
        db: AsyncSession,
        token: str,
    ) -> User:
        """Validate JWT token and return the authenticated User.

        Args:
            db: Async DB session.
            token: JWT access token string.

        Returns:
            User ORM instance.

        Raises:
            ValueError: invalid or expired token.
        """
        try:
            payload = decode_access_token(token)
            user_id_str: str = payload.get("sub")
            if not user_id_str:
                raise ValueError("Token payload missing 'sub' claim")

            user_id = uuid.UUID(user_id_str)
        except (JWTError, ValueError) as exc:
            raise ValueError(f"Invalid token: {exc}")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id_str} not found")

        return user


# Singleton
auth_service = AuthService()
