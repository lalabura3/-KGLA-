"""Global error handler middleware.

Converts all unhandled exceptions into a uniform JSON error response.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from ..utils.logging import get_logger

logger = get_logger(__name__)


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches all unhandled exceptions and returns a uniform error shape."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.exception(
                "Unhandled error",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "detail": str(exc) if request.app.debug else None,
                        "request_id": request_id,
                    }
                },
            )
