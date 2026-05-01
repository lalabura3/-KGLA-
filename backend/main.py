"""Updated main.py — integrates F002, ASR persistence, and auth.

Diff from T25 main.py:
  1. Register link_import_router (F002)
  2. Register video_router (upload + ASR persistence)
  3. Register auth_router (JWT registration/login)
  4. Add AuthMiddleware (conditional on APP_AUTH_ENABLED)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .middleware import (
    AuthMiddleware,
    GlobalErrorHandlerMiddleware,
    RequestIDMiddleware,
    setup_cors,
)
from .routers import (
    auth_router,
    health_router,
    link_import_router,
    video_router,
)
from .utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info(
        "Starting %s [%s]",
        settings.app_name,
        settings.app_env,
        debug=settings.debug,
        host=settings.host,
        port=settings.port,
    )
    logger.info("API prefix: %s", settings.api_prefix)
    logger.info("Database: %s", _mask_dsn(settings.database_url))
    logger.info("Redis: %s", _mask_dsn(settings.redis_url))
    logger.info("Auth enabled: %s", settings.auth_enabled)

    from .database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
            logger.info("Database connection verified")
    except Exception as exc:
        logger.warning("Database not reachable at startup: %s", exc)

    yield

    logger.info("Shutting down %s", settings.app_name)
    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # ── Middleware stack (order matters: last added = first executed) ──
    setup_cors(app)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(GlobalErrorHandlerMiddleware)

    # Auth middleware (conditional — controlled by APP_AUTH_ENABLED)
    if settings.auth_enabled:
        app.add_middleware(AuthMiddleware)
        logger.info("Auth middleware enabled — JWT required for /api/v1/*")

    # ── Routers ──
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(auth_router)          # Auth routes are self-prefixed: /api/v1/auth
    app.include_router(link_import_router)   # Link import routes: /api/v1/links/*
    app.include_router(video_router)         # Video routes: /api/v1/videos/*

    # ── Note & Graph routers (from T17/T18 — uncomment when integrated)
    # app.include_router(note_router)
    # app.include_router(graph_router)

    # ── Exception handlers ──
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found",
                    "detail": str(exc.detail),
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(405)
    async def method_not_allowed_handler(request, exc):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=405,
            content={
                "error": {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": str(exc.detail),
                    "request_id": request_id,
                }
            },
        )

    return app


def _mask_dsn(dsn: str) -> str:
    import re
    return re.sub(r":([^@]+)@", ":****@", dsn)


app = create_app()
