"""
Alembic migration environment.

Auto-discovers all models via backend.models.Base.metadata.
Uses the synchronous database URL from backend.config.settings.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path as _Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Ensure the backend package is on sys.path ──
BACKEND_ROOT = _Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

# ── Alembic Config ──
config = context.config

# Override sqlalchemy.url from application settings
from backend.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.database_sync_url)

# ── Logging ──
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Metadata for autogenerate ──
# Import all models so Base.metadata is fully populated
from backend.database import Base  # noqa: E402
import backend.models  # noqa: E402, F401  — triggers __init__.py imports

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting).

    Calls context.execute() with the string output of
    context.configure(url=url, ...).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB).

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
