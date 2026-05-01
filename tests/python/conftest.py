"""
Pytest configuration and shared fixtures for 学知图谱 backend tests.
"""
import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


# ──────────────────────────────────────────────
# Environment & Paths
# ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).resolve().parents[4]


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Directory for test fixtures (sample videos, transcripts, etc.)."""
    d = project_root / "tests" / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ──────────────────────────────────────────────
# Async helpers
# ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ──────────────────────────────────────────────
# Mock / fake factories
# ──────────────────────────────────────────────
@pytest.fixture
def mock_whisper_result():
    """Return a realistic Whisper ASR result with segments."""
    return {
        "text": "人工智能的核心在于让机器具备学习能力。深度学习通过多层神经网络实现特征提取。",
        "segments": [
            {
                "id": 0,
                "seek": 0,
                "start": 0.0,
                "end": 5.2,
                "text": "人工智能的核心在于让机器具备学习能力。",
                "tokens": [],
                "temperature": 1.0,
            },
            {
                "id": 1,
                "seek": 0,
                "start": 5.5,
                "end": 12.0,
                "text": "深度学习通过多层神经网络实现特征提取。",
                "tokens": [],
                "temperature": 1.0,
            },
        ],
        "language": "zh",
    }


@pytest.fixture
def mock_llm_notes_result():
    """Return a realistic LLM-generated note."""
    return {
        "title": "人工智能与深度学习基础",
        "summary": "本章介绍了人工智能的核心目标是让机器具备学习能力，"
                   "深度学习通过多层神经网络结构实现自动化特征提取。",
        "key_concepts": [
            {"name": "人工智能", "description": "使机器具备学习与推理能力的技术总称"},
            {"name": "深度学习", "description": "基于多层神经网络的特征学习方法"},
            {"name": "特征提取", "description": "从原始数据中自动学习有效表示"},
        ],
        "relations": [
            {"source": "人工智能", "target": "深度学习", "relation": "核心技术"},
            {"source": "深度学习", "target": "特征提取", "relation": "实现方式"},
        ],
        "timestamps": [
            {"start": 0.0, "end": 5.2, "concept": "人工智能"},
            {"start": 5.5, "end": 12.0, "concept": "深度学习"},
        ],
    }


@pytest.fixture
def mock_video_metadata():
    """Return realistic video metadata."""
    return {
        "id": "test-video-001",
        "filename": "ai_intro.mp4",
        "duration_seconds": 45 * 60,  # 45 min
        "resolution": "1920x1080",
        "codec": "h264",
        "file_size_mb": 2048,
        "language": "zh",
    }


@pytest.fixture
def mock_graph_data():
    """Return realistic knowledge graph data."""
    return {
        "nodes": [
            {"id": "n1", "label": "人工智能", "group": "core_concept", "weight": 10},
            {"id": "n2", "label": "深度学习", "group": "method", "weight": 8},
            {"id": "n3", "label": "特征提取", "group": "technique", "weight": 5},
            {"id": "n4", "label": "神经网络", "group": "architecture", "weight": 7},
        ],
        "edges": [
            {"from": "n1", "to": "n2", "label": "核心技术", "weight": 5},
            {"from": "n2", "to": "n3", "label": "实现方式", "weight": 3},
            {"from": "n2", "to": "n4", "label": "基于", "weight": 4},
            {"from": "n1", "to": "n4", "label": "使用", "weight": 2},
        ],
    }
