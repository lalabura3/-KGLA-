"""Link Parser Service — HTTP link recognition & metadata extraction.

Supported platforms (MVP): generic HTTP video, YouTube, Bilibili.
Extensible via extractor registry.

F002: Link Import Parsing
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


# ── Data types ──


@dataclass
class LinkMetadata:
    """Extracted metadata from a video link."""
    url: str
    title: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    platform: str | None = None
    author: str | None = None
    extractable: bool = False
    error: str | None = None
    raw: dict = field(default_factory=dict)


# ── Extractor interface ──


class BaseExtractor:
    """Abstract base for platform-specific metadata extractors."""

    name: str = "base"

    def can_handle(self, url: str) -> bool:
        """Return True if this extractor can handle the given URL."""
        return False

    async def extract(self, url: str, session: aiohttp.ClientSession) -> LinkMetadata:
        """Extract metadata from the URL. Override in subclasses."""
        raise NotImplementedError


# ── Generic HTTP Extractor ──


class GenericExtractor(BaseExtractor):
    """Generic extractor — works for any HTTP link (OpenGraph / HTML meta tags).

    Used as fallback when no platform-specific extractor matches.
    """

    name = "generic"

    def can_handle(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    async def extract(self, url: str, session: aiohttp.ClientSession) -> LinkMetadata:
        """Fetch the page and parse OpenGraph / meta tags."""
        metadata = LinkMetadata(url=url, platform="generic")

        # Simple regex for video-file extensions in URL
        video_extensions = (".mp4", ".webm", ".mkv", ".avi", ".mov")
        if any(url.lower().endswith(ext) for ext in video_extensions):
            # Direct video file URL
            filename = url.rstrip("/").rsplit("/", 1)[-1]
            metadata.title = filename
            metadata.extractable = True
            metadata.platform = "direct"
            return metadata

        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; StudyAI/0.1; +https://studyai.dev)"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                },
                allow_redirects=True,
                max_redirects=5,
            ) as resp:
                if resp.status >= 400:
                    metadata.error = f"HTTP {resp.status}: {resp.reason}"
                    return metadata

                html = await resp.text()

            # Parse OpenGraph & Twitter Card meta tags
            og_title = self._parse_meta(html, "og:title")
            og_desc = self._parse_meta(html, "og:description")
            og_image = self._parse_meta(html, "og:image")
            og_type = self._parse_meta(html, "og:type")
            twitter_title = self._parse_meta(html, "twitter:title")
            twitter_desc = self._parse_meta(html, "twitter:description")
            twitter_image = self._parse_meta(html, "twitter:image")

            # Determine video platform from og:type or URL hint
            if og_type and "video" in og_type.lower():
                metadata.platform = og_type
            elif "youtube.com" in url or "youtu.be" in url:
                metadata.platform = "youtube"
            elif "bilibili.com" in url:
                metadata.platform = "bilibili"
            elif "vimeo.com" in url:
                metadata.platform = "vimeo"

            # Extract title
            metadata.title = (
                og_title
                or twitter_title
                or self._parse_title_tag(html)
                or self._parse_meta(html, "title")
            )

            metadata.description = og_desc or twitter_desc
            metadata.thumbnail_url = og_image or twitter_image

            # Check for <video> tag or video source
            has_video = bool(
                re.search(r"<(?:video|source)[^>]+(?:src|type=[\"']video)", html, re.I)
            )
            has_youtube_player = bool(
                re.search(r"(?:youtube\.com/embed/|youtube\.com/player)", html)
            )

            if has_video or has_youtube_player:
                metadata.extractable = True

        except asyncio.TimeoutError:
            metadata.error = "Request timed out"
        except aiohttp.ClientError as exc:
            metadata.error = f"HTTP client error: {exc}"
        except Exception as exc:
            metadata.error = f"Unexpected error: {exc}"

        return metadata

    @staticmethod
    def _parse_meta(html: str, property_name: str) -> str | None:
        """Parse a single meta tag value (og:*, twitter:*, etc.)."""
        patterns = [
            rf'<meta\s+[^>]*property\s*=\s*["\']{re.escape(property_name)}["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
            rf'<meta\s+[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*property\s*=\s*["\']{re.escape(property_name)}["\']',
            rf'<meta\s+[^>]*name\s*=\s*["\']{re.escape(property_name)}["\'][^>]*content\s*=\s*["\']([^"\']+)["\']',
            rf'<meta\s+[^>]*content\s*=\s*["\']([^"\']+)["\'][^>]*name\s*=\s*["\']{re.escape(property_name)}["\']',
        ]
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _parse_title_tag(html: str) -> str | None:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        return m.group(1).strip() if m else None


# ── YouTube Extractor (via oEmbed + page scrape) ──


class YouTubeExtractor(BaseExtractor):
    """Extract metadata from YouTube links via oEmbed + opengraph."""

    name = "youtube"

    YOUTUBE_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([\w-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([\w-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([\w-]+)",
        r"(?:https?://)?youtu\.be/([\w-]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]+)",
    ]

    def can_handle(self, url: str) -> bool:
        for pattern in self.YOUTUBE_PATTERNS:
            if re.search(pattern, url, re.I):
                return True
        return False

    def _extract_video_id(self, url: str) -> str | None:
        for pattern in self.YOUTUBE_PATTERNS:
            m = re.search(pattern, url, re.I)
            if m:
                return m.group(1)
        return None

    async def extract(self, url: str, session: aiohttp.ClientSession) -> LinkMetadata:
        """Extract YouTube metadata via oEmbed endpoint."""
        video_id = self._extract_video_id(url)
        metadata = LinkMetadata(url=url, platform="youtube", extractable=True)

        # Use oEmbed endpoint (no API key required)
        oembed_url = (
            f"https://www.youtube.com/oembed"
            f"?url=https://www.youtube.com/watch?v={video_id}"
            f"&format=json"
        )

        try:
            async with session.get(
                oembed_url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    metadata.title = data.get("title", metadata.title)
                    metadata.author = data.get("author_name", metadata.author)
                    metadata.thumbnail_url = data.get("thumbnail_url")

            # Also try to scrape the watch page for description
            if video_id:
                watch_url = f"https://www.youtube.com/watch?v={video_id}"
                try:
                    async with session.get(
                        watch_url,
                        timeout=aiohttp.ClientTimeout(total=15),
                        headers={
                            "User-Agent": "Mozilla/5.0 (compatible; StudyAI/0.1)",
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                    ) as page_resp:
                        if page_resp.status == 200:
                            html = await page_resp.text()
                            # Extract description from og:description
                            desc = GenericExtractor._parse_meta(html, "og:description")
                            if desc:
                                metadata.description = desc

                            # Try to extract duration from ISO 8601 format in meta
                            duration_match = re.search(
                                r'<meta\s+itemprop="duration"\s+content="PT(\d+)M(\d+)S"',
                                html,
                            )
                            if duration_match:
                                minutes = int(duration_match.group(1))
                                seconds = int(duration_match.group(2))
                                metadata.duration_seconds = minutes * 60 + seconds
                except Exception:
                    pass  # Non-critical: page scrape is best-effort

        except Exception as exc:
            metadata.error = f"YouTube metadata fetch failed: {exc}"
            # Still extractable even if metadata fetch fails partially
            metadata.extractable = True

        return metadata


# ── Bilibili Extractor ──


class BilibiliExtractor(BaseExtractor):
    """Extract metadata from Bilibili links via oEmbed or page scrape."""

    name = "bilibili"

    BILI_PATTERNS = [
        r"(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[\w]+)",
        r"(?:https?://)?(?:www\.)?bilibili\.com/video/av(\d+)",
    ]

    def can_handle(self, url: str) -> bool:
        for pattern in self.BILI_PATTERNS:
            if re.search(pattern, url, re.I):
                return True
        return "bilibili.com" in url

    async def extract(self, url: str, session: aiohttp.ClientSession) -> LinkMetadata:
        """Extract Bilibili metadata."""
        metadata = LinkMetadata(url=url, platform="bilibili", extractable=True)

        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; StudyAI/0.1)",
                    "Accept": "text/html,application/xhtml+xml",
                },
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    metadata.error = f"Bilibili page returned {resp.status}"
                    metadata.extractable = False
                    return metadata

                html = await resp.text()

            # Parse OpenGraph / meta tags
            og_title = GenericExtractor._parse_meta(html, "og:title")
            og_desc = GenericExtractor._parse_meta(html, "og:description")
            og_image = GenericExtractor._parse_meta(html, "og:image")

            metadata.title = og_title
            metadata.description = og_desc
            metadata.thumbnail_url = og_image

            # Try to find video data in page scripts
            video_data_match = re.search(
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*\(function',
                html,
                re.DOTALL,
            )
            if video_data_match:
                try:
                    import json

                    data = json.loads(video_data_match.group(1))
                    video_info = data.get("videoData", {})
                    if video_info:
                        metadata.title = video_info.get("title", metadata.title)
                        metadata.description = video_info.get("desc", metadata.description)
                        metadata.duration_seconds = video_info.get("duration")
                        owner = video_info.get("owner", {})
                        metadata.author = owner.get("name", metadata.author)
                        metadata.raw = video_info
                except (json.JSONDecodeError, KeyError):
                    pass

        except Exception as exc:
            metadata.error = f"Bilibili metadata fetch failed: {exc}"
            metadata.extractable = True  # Still extractable via other methods

        return metadata


# ── Link Parser Service ──


class LinkParserService:
    """Central service: recognizes links and extracts metadata.

    Extractor registry — add new platforms by registering extractors.
    Order: platform-specific (YouTube, Bilibili) → fallback to GenericExtractor.
    """

    def __init__(self):
        self._extractors: list[BaseExtractor] = [
            YouTubeExtractor(),
            BilibiliExtractor(),
            GenericExtractor(),  # Always last as fallback
        ]

    def register(self, extractor: BaseExtractor) -> None:
        """Register a custom extractor (inserted before generic fallback)."""
        self._extractors.insert(-1, extractor)

    def is_valid_url(self, url: str) -> bool:
        """Check if a string is a valid HTTP(S) URL."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def find_extractor(self, url: str) -> BaseExtractor:
        """Find the first extractor that can handle this URL."""
        for ext in self._extractors:
            if ext.can_handle(url):
                return ext
        raise ValueError(f"No extractor found for URL: {url}")

    async def preview(self, url: str) -> LinkMetadata:
        """Extract metadata for preview (before import)."""
        if not self.is_valid_url(url):
            return LinkMetadata(
                url=url, extractable=False, error="Invalid URL format"
            )

        extractor = self.find_extractor(url)
        async with aiohttp.ClientSession() as session:
            return await extractor.extract(url, session)

    async def import_video(self, url: str, user_id: str) -> LinkMetadata:
        """Extract metadata and validate extractability for import."""
        metadata = await self.preview(url)

        if not metadata.extractable:
            if not metadata.error:
                metadata.error = (
                    "URL is not recognized as a video source or cannot be extracted"
                )
        return metadata


# Singleton
link_parser = LinkParserService()
