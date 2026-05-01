"""Health check router — liveness and readiness probes."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_liveness():
    """Liveness probe: always returns 200 if the process is alive."""
    return {"status": "ok", "service": "studyai-backend"}


@router.get("/health/ready")
async def health_readiness():
    """Readiness probe: checks if the app can serve traffic.

    Verifies database connectivity.
    """
    from ..config import settings
    from ..database import engine

    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(
                # lightweight query
                __import__("sqlalchemy").text("SELECT 1")
            )
            db_ok = True
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return {
        "status": "ready" if db_ok else "not_ready",
        "checks": {
            "database": "ok" if db_ok else "unavailable",
        },
    }
