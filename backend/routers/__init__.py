"""Routers package — exports all API routers.

Updated: added auth_router, link_import_router, video_router.
"""
from .auth import router as auth_router
from .health import router as health_router
from .link_import import router as link_import_router
from .videos import router as video_router

__all__ = [
    "auth_router",
    "health_router",
    "link_import_router",
    "video_router",
]
