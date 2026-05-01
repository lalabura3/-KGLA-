"""Structured logging setup using structlog + standard logging."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from ..config import settings

# Shared processors for all loggers
_shared_processors: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]

# Renderer: structured (JSON) or plain (console)
if settings.log_format == "structured":
    _renderer = structlog.processors.JSONRenderer()
else:
    _renderer = structlog.dev.ConsoleRenderer(colors=True)


def setup_logging() -> None:
    """Configure structlog for the application.

    Must be called once at application startup.
    """
    structlog.configure(
        processors=_shared_processors + [_renderer],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also configure the root stdlib logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(message)s" if settings.log_format == "structured"
            else "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
        )
    )
    # Remove any existing handlers to avoid double-logging
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").handlers = []


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger."""
    return structlog.get_logger(name)
