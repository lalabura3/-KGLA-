"""
Async database engine & session factory.
Uses asyncpg driver for PostgreSQL.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Import all models so they are registered on Base.metadata ──
# (Alembic autogenerate and create_all depend on this import)
from . import models  # noqa: E402, F401


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency: yields an async DB session with auto-commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_no_commit() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency: yields a session without auto-commit (for read-only)."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
