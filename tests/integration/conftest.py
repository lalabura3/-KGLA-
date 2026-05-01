"""Shared fixtures for integration tests."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ── Mock data ──


@pytest.fixture
def sample_video_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def sample_audio_path(tmp_path: Path) -> Path:
    """Simulate extracted audio file path."""
    path = tmp_path / "audio_test.wav"
    path.write_bytes(b"\x00" * 1024)  # 1KB fake WAV
    return path


@pytest.fixture
def sample_video_metadata() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": "深度学习入门",
        "filename": "deep_learning_intro.mp4",
        "file_path": "/uploads/deep_learning_intro.mp4",
        "file_size": 104857600,  # 100 MB
        "duration": 1800.0,  # 30 mins
        "format": "mp4",
        "status": "completed",
        "progress": 100,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_asr_segments() -> list[dict]:
    """Simulated ASR output segments for a 30-min deep learning lecture."""
    return [
        {
            "segment_index": 0,
            "start": 0.0,
            "end": 5.2,
            "text": "今天我们来讲一下深度学习的基础概念",
            "confidence": 0.95,
            "words": ["今天", "我们", "来", "讲", "一下", "深度", "学习", "的", "基础", "概念"],
        },
        {
            "segment_index": 1,
            "start": 5.2,
            "end": 12.8,
            "text": "深度学习是机器学习的一个分支它使用多层神经网络来学习数据的表示",
            "confidence": 0.93,
            "words": ["深度", "学习", "是", "机器", "学习", "的", "一个", "分支", "它", "使用", "多层", "神经", "网络", "来", "学习", "数据", "的", "表示"],
        },
        {
            "segment_index": 2,
            "start": 12.8,
            "end": 20.5,
            "text": "与传统机器学习不同深度学习不需要手动特征工程",
            "confidence": 0.91,
            "words": ["与", "传统", "机器", "学习", "不同", "深度", "学习", "不", "需要", "手动", "特征", "工程"],
        },
        {
            "segment_index": 3,
            "start": 20.5,
            "end": 30.0,
            "text": "它通过卷积神经网络和循环神经网络等架构自动从原始数据中提取特征",
            "confidence": 0.88,
            "words": ["它", "通过", "卷积", "神经", "网络", "和", "循环", "神经", "网络", "等", "架构", "自动", "从", "原始", "数据", "中", "提取", "特征"],
        },
        {
            "segment_index": 4,
            "start": 30.0,
            "end": 38.2,
            "text": "CNN在图像识别领域表现出色而RNN适合处理序列数据如文本和语音",
            "confidence": 0.90,
            "words": ["CNN", "在", "图像", "识别", "领域", "表现", "出色", "而", "RNN", "适合", "处理", "序列", "数据", "如", "文本", "和", "语音"],
        },
        {
            "segment_index": 5,
            "start": 38.2,
            "end": 45.0,
            "text": "transformer架构近年来取得了突破性进展成为NLP领域的主流方法",
            "confidence": 0.87,
            "words": ["transformer", "架构", "近年", "来", "取得", "了", "突破性", "进展", "成为", "NLP", "领域", "的", "主流", "方法"],
        },
        {
            "segment_index": 6,
            "start": 45.0,
            "end": 52.0,
            "text": "GPU的并行计算能力大大加速了深度学习的训练过程",
            "confidence": 0.94,
            "words": ["GPU", "的", "并行", "计算", "能力", "大大", "加速", "了", "深度", "学习", "的", "训练", "过程"],
        },
        {
            "segment_index": 7,
            "start": 52.0,
            "end": 60.0,
            "text": "今天我们讲的内容包括神经网络的基本原理反向传播算法和梯度下降优化",
            "confidence": 0.92,
            "words": ["今天", "我们", "讲", "的", "内容", "包括", "神经", "网络", "的", "基本", "原理", "反向", "传播", "算法", "和", "梯度", "下降", "优化"],
        },
        {
            "segment_index": 8,
            "start": 180.0,
            "end": 188.5,
            "text": "反向传播算法是训练神经网络的核心它通过链式法则计算梯度",
            "confidence": 0.91,
            "words": ["反向", "传播", "算法", "是", "训练", "神经", "网络", "的", "核心", "它", "通过", "链式", "法则", "计算", "梯度"],
        },
        {
            "segment_index": 9,
            "start": 188.5,
            "end": 195.0,
            "text": "梯度下降算法通过不断调整权重来最小化损失函数",
            "confidence": 0.93,
            "words": ["梯度", "下降", "算法", "通过", "不断", "调整", "权重", "来", "最小化", "损失", "函数"],
        },
    ]


@pytest.fixture
def sample_vad_result():
    """Simulated VAD result."""
    from dataclasses import dataclass

    @dataclass
    class MockVADSegment:
        start: float
        end: float
        speech: bool

    @dataclass
    class MockVADResult:
        segments: list
        total_duration: float
        speech_duration: float
        speech_ratio: float

    return MockVADResult(
        segments=[
            MockVADSegment(start=0.0, end=5.5, speech=True),
            MockVADSegment(start=5.2, end=13.0, speech=True),
            MockVADSegment(start=12.8, end=21.0, speech=True),
            MockVADSegment(start=20.5, end=31.0, speech=True),
            MockVADSegment(start=30.0, end=39.0, speech=True),
            MockVADSegment(start=38.0, end=46.0, speech=True),
            MockVADSegment(start=45.0, end=53.0, speech=True),
            MockVADSegment(start=52.0, end=61.0, speech=True),
            MockVADSegment(start=179.0, end=190.0, speech=True),
            MockVADSegment(start=188.0, end=196.0, speech=True),
        ],
        total_duration=196.0,
        speech_duration=180.0,
        speech_ratio=0.918,
    )


@pytest.fixture
def sample_transcript_segments() -> list[dict]:
    """Transcript segments for note generation (minimal set)."""
    return [
        {"segment_index": 0, "start": 0.0, "end": 5.2, "text": "今天我们来讲一下深度学习的基础概念", "speaker_id": None},
        {"segment_index": 1, "start": 5.2, "end": 12.8, "text": "深度学习是机器学习的一个分支它使用多层神经网络来学习数据的表示", "speaker_id": None},
        {"segment_index": 2, "start": 12.8, "end": 20.5, "text": "与传统机器学习不同深度学习不需要手动特征工程", "speaker_id": None},
    ]


@pytest.fixture
def sample_note_sections() -> list[dict]:
    """Sample note sections for graph extraction."""
    return [
        {
            "section_index": 0,
            "heading": "深度学习基础概念",
            "content": "深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。与传统的机器学习方法不同，深度学习不需要手动特征工程，而是通过网络层自动提取特征。",
            "key_points": [
                "深度学习是机器学习的子领域",
                "使用多层神经网络进行学习",
                "无需手动特征工程"
            ],
        },
        {
            "section_index": 1,
            "heading": "核心网络架构",
            "content": "卷积神经网络（CNN）在图像识别领域表现优异，通过卷积层自动提取空间特征。循环神经网络（RNN）擅长处理序列数据，如文本和时间序列。Transformer架构通过自注意力机制在NLP领域取得了突破性进展。",
            "key_points": [
                "CNN适用于图像识别",
                "RNN擅长处理序列数据",
                "Transformer是NLP领域的主流架构"
            ],
        },
        {
            "section_index": 2,
            "heading": "训练算法与优化",
            "content": "反向传播算法通过链式法则计算梯度，是训练神经网络的核心算法。梯度下降通过不断调整网络权重来最小化损失函数。GPU的并行计算能力大大加速了这一训练过程。",
            "key_points": [
                "反向传播是训练核心",
                "梯度下降用于权重优化",
                "GPU加速训练过程"
            ],
        },
    ]


@pytest.fixture
def sample_llm_service_url() -> str:
    return "http://test-llm:8002"


# ── Mock LLM response helpers ──


@pytest.fixture
def mock_metadata_llm_response() -> dict:
    """Simulated Stage 1 LLM response for metadata extraction."""
    return {
        "title": "深度学习入门：神经网络基础",
        "summary": "本文介绍了深度学习的基本概念，包括神经网络架构、CNN和RNN等核心模型，以及反向传播和梯度下降等训练算法。内容覆盖了从基础概念到核心网络架构的系统性介绍。",
        "keywords": ["深度学习", "神经网络", "CNN", "RNN", "Transformer", "反向传播", "梯度下降", "特征工程", "GPU", "NLP"],
        "metadata": {
            "topic": "深度学习",
            "difficulty": "intermediate",
            "is_technical": True,
            "has_code": False,
            "language": "zh",
            "speaker_count": 1,
        },
    }


@pytest.fixture
def mock_sections_llm_response() -> list:
    """Simulated Stage 2 LLM response for section generation."""
    return [
        {
            "heading": "深度学习基础概念",
            "content": "深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。",
            "start_time": 0.0,
            "end_time": 20.5,
            "key_points": [
                "深度学习是机器学习的子领域",
                "无需手动特征工程",
            ],
            "source_segment_indices": [0, 1, 2],
            "evidence": [
                {"quote": "深度学习是机器学习的一个分支", "segment_index": 1},
                {"quote": "不需要手动特征工程", "segment_index": 2},
            ],
        },
        {
            "heading": "核心网络架构",
            "content": "CNN在图像识别领域表现出色，RNN适合处理序列数据，Transformer通过自注意力机制在NLP领域取得突破。",
            "start_time": 20.5,
            "end_time": 45.0,
            "key_points": [
                "CNN适用于图像识别",
                "RNN擅长序列数据",
                "Transformer是NLP主流架构",
            ],
            "source_segment_indices": [3, 4, 5],
            "evidence": [
                {"quote": "CNN在图像识别领域表现出色", "segment_index": 4},
                {"quote": "RNN适合处理序列数据", "segment_index": 4},
                {"quote": "Transformer架构近年来取得了突破性进展", "segment_index": 5},
            ],
        },
        {
            "heading": "训练算法与优化",
            "content": "反向传播算法通过链式法则计算梯度，梯度下降通过调整权重来最小化损失函数。",
            "start_time": 45.0,
            "end_time": 195.0,
            "key_points": [
                "反向传播是训练核心",
                "梯度下降用于权重优化",
            ],
            "source_segment_indices": [7, 8, 9],
            "evidence": [
                {"quote": "反向传播算法是训练神经网络的核心", "segment_index": 8},
                {"quote": "梯度下降算法通过不断调整权重来最小化损失函数", "segment_index": 9},
            ],
        },
    ]


@pytest.fixture
def mock_polish_llm_response() -> dict:
    """Simulated Stage 3 LLM response for polish."""
    return {
        "title": "深度学习入门：神经网络基础",
        "summary": "本文介绍了深度学习的基本概念，包括神经网络架构、CNN和RNN等核心模型，以及反向传播和梯度下降等训练算法。",
        "keywords": ["深度学习", "神经网络", "CNN", "RNN", "Transformer", "反向传播", "梯度下降"],
        "sections": [
            {
                "heading": "深度学习基础概念",
                "content": "深度学习是机器学习的一个分支，使用多层神经网络自动学习数据的表示。",
                "key_points": ["深度学习是机器学习的子领域", "无需手动特征工程"],
                "hallucination_flags": [],
            },
            {
                "heading": "核心网络架构",
                "content": "CNN在图像识别领域表现出色，RNN适合处理序列数据，Transformer在NLP领域取得突破。",
                "key_points": ["CNN适用于图像识别", "RNN擅长序列数据", "Transformer是NLP主流架构"],
                "hallucination_flags": [],
            },
            {
                "heading": "训练算法与优化",
                "content": "反向传播算法通过链式法则计算梯度，梯度下降通过调整权重来最小化损失函数。",
                "key_points": ["反向传播是训练核心", "梯度下降用于权重优化"],
                "hallucination_flags": [],
            },
        ],
    }


@pytest.fixture
def mock_nodes_llm_response() -> dict:
    """Simulated Stage 1 LLM response for node extraction."""
    return {
        "nodes": [
            {
                "name": "深度学习",
                "description": "机器学习的一个分支，使用多层神经网络学习数据表示",
                "node_type": "CONCEPT",
                "importance": 0.95,
                "segment_indices": [0, 1],
            },
            {
                "name": "神经网络",
                "description": "由多层神经元组成的计算模型，是深度学习的核心架构",
                "node_type": "TECHNOLOGY",
                "importance": 0.90,
                "segment_indices": [1, 7],
            },
            {
                "name": "CNN",
                "description": "卷积神经网络，在图像识别领域表现优异",
                "node_type": "TECHNOLOGY",
                "importance": 0.80,
                "segment_indices": [4],
            },
            {
                "name": "RNN",
                "description": "循环神经网络，适合处理序列数据如文本和语音",
                "node_type": "TECHNOLOGY",
                "importance": 0.78,
                "segment_indices": [4],
            },
            {
                "name": "Transformer",
                "description": "基于自注意力机制的神经网络架构，NLP领域的主流方法",
                "node_type": "TECHNOLOGY",
                "importance": 0.85,
                "segment_indices": [5],
            },
            {
                "name": "反向传播",
                "description": "训练神经网络的核心算法，通过链式法则计算梯度",
                "node_type": "METHODOLOGY",
                "importance": 0.85,
                "segment_indices": [8],
            },
            {
                "name": "梯度下降",
                "description": "通过不断调整权重来最小化损失函数的优化算法",
                "node_type": "METHODOLOGY",
                "importance": 0.82,
                "segment_indices": [9],
            },
            {
                "name": "GPU",
                "description": "图形处理器，其并行计算能力加速深度学习训练",
                "node_type": "TECHNOLOGY",
                "importance": 0.70,
                "segment_indices": [6],
            },
        ]
    }


@pytest.fixture
def mock_relations_llm_response() -> dict:
    """Simulated Stage 2 LLM response for relation extraction."""
    return {
        "relations": [
            {
                "source": "深度学习",
                "target": "神经网络",
                "relation_type": "IS_A",
                "strength": 0.9,
                "description": "深度学习是神经网络的一种应用范式",
            },
            {
                "source": "深度学习",
                "target": "CNN",
                "relation_type": "RELATES_TO",
                "strength": 0.7,
                "description": "CNN是深度学习中用于图像处理的重要架构",
            },
            {
                "source": "深度学习",
                "target": "RNN",
                "relation_type": "RELATES_TO",
                "strength": 0.7,
                "description": "RNN是深度学习中用于序列数据的架构",
            },
            {
                "source": "深度学习",
                "target": "反向传播",
                "relation_type": "USES",
                "strength": 0.85,
                "description": "深度学习使用反向传播算法进行训练",
            },
            {
                "source": "反向传播",
                "target": "梯度下降",
                "relation_type": "RELATES_TO",
                "strength": 0.8,
                "description": "反向传播计算梯度，梯度下降使用梯度更新权重",
            },
            {
                "source": "CNN",
                "target": "Transformer",
                "relation_type": "CONTRASTS_WITH",
                "strength": 0.5,
                "description": "CNN使用卷积操作，Transformer使用自注意力机制",
            },
            {
                "source": "深度学习",
                "target": "GPU",
                "relation_type": "USES",
                "strength": 0.75,
                "description": "深度学习利用GPU的并行计算加速训练",
            },
        ]
    }
