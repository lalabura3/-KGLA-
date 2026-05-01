"""Middleware package — exports all middleware classes and setup utilities.

Updated: added AuthMiddleware for JWT authentication.
"""
from .auth import AuthMiddleware
from .cors import setup_cors
from .error_handler import GlobalErrorHandlerMiddleware
from .request_id import RequestIDMiddleware

__all__ = [
    "AuthMiddleware",
    "GlobalErrorHandlerMiddleware",
    "RequestIDMiddleware",
    "setup_cors",
]
