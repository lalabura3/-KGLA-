"""Services package — exports all service singletons.

Updated: added auth_service, link_parser.
"""
from .asr_service import ASRService, asr_service
from .auth_service import AuthService, auth_service
from .link_parser import LinkParserService, link_parser

__all__ = [
    "ASRService", "asr_service",
    "AuthService", "auth_service",
    "LinkParserService", "link_parser",
]
