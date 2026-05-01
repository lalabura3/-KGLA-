"""Authentication Middleware — JWT verification via Starlette middleware.

Applied to all /api/v1/* routes when APP_AUTH_ENABLED is true.
Skips health endpoints, auth endpoints, and OPTIONS requests.

This is a GLOBAL middleware — individual endpoints can use
get_current_user dependency for fine-grained auth instead.
"""
from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings

logger = logging.getLogger(__name__)

# ── Paths excluded from auth middleware ──

AUTH_WHITELIST = {
    "/api/v1/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/favicon.ico",
}

AUTH_WHITELIST_PREFIXES = (
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware.

    When APP_AUTH_ENABLED=true, validates every request against the
    Authorization header.  Whitelisted paths and OPTIONS requests are
    skipped.

    On failure returns 401 with structured error body.

    NOTE: This middleware is optional.  The get_current_user FastAPI
    dependency provides the same protection per-endpoint.  Use this
    middleware for blanket protection; use the dependency for
    selective protection.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # ── Skip if auth is disabled globally ──
        if not settings.auth_enabled:
            return await call_next(request)

        # ── Skip OPTIONS (CORS preflight) ──
        if request.method == "OPTIONS":
            return await call_next(request)

        # ── Skip whitelisted paths ──
        path = request.url.path.rstrip("/")

        if path in AUTH_WHITELIST:
            return await call_next(request)

        for prefix in AUTH_WHITELIST_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # ── Verify token ──
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return _unauthorized("MISSING_TOKEN", "Authorization header is required")

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _unauthorized(
                "INVALID_HEADER",
                "Authorization header must be 'Bearer <token>'",
            )

        try:
            from ..services.auth_service import decode_access_token

            payload = decode_access_token(token)
            # Inject user info into request state for downstream handlers
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")

        except Exception as exc:
            return _unauthorized("INVALID_TOKEN", str(exc))

        return await call_next(request)


def _unauthorized(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )
