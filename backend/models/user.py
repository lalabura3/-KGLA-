"""User ORM model.

One user can own many videos.  Auth is MVP-optional; hashed_password
column is included so the schema is ready for JWT when enabled.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from . import TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
    )

    # ── Relationships ──
    videos = relationship(
        "Video", back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"
