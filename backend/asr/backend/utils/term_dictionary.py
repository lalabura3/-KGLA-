"""Domain-specific term dictionary for ASR injection (专业术语词典注入).

Provides targeted vocabulary hints to Whisper for domain terms (CS, math, ML, etc.).
Terms are loaded from a built-in list + an optional external file.
"""
from __future__ import annotations

from typing import Optional

# ── Built-in terms (CS/ML/math domain) ──
_BUILTIN_TERMS: dict[str, str] = {
    # Programming
    "API": "A-P-I",
    "SDK": "S-D-K",
    "JSON": "J-S-O-N",
    "REST": "Rest",
    "GraphQL": "Graph-Q-L",
    "CRUD": "C-R-U-D",
    # ML / AI
    "ReLU": "relu",
    "Softmax": "softmax",
    "TensorFlow": "tensorflow",
    "PyTorch": "PyTorch",
    "CUDA": "C-U-D-A",
    "CTranslate2": "C-Translate-2",
    "faster-whisper": "faster whisper",
    "LoRA": "LoRA",
    "Backpropagation": "back propagation",
    # Math
    "eigenvalue": "eigen value",
    "SVD": "S-V-D",
    "PCA": "P-C-A",
    "ReLU": "relu",
    "Softmax": "softmax",
    # OS / Networking
    "Linux": "Linux",
    "TCP/IP": "T-C-P-I-P",
    "HTTP": "H-T-T-P",
    "HTTPS": "H-T-T-P-S",
    "SSH": "S-S-H",
    "DNS": "D-N-S",
    "Docker": "Docker",
    "Kubernetes": "Kubernetes",
    # Chinese-specific terms
    "深度学习": "深度学习",
    "神经网络": "神经网络",
    "卷积": "卷积",
    "反向传播": "反向传播",
    "自然语言处理": "自然语言处理",
    "计算机视觉": "计算机视觉",
    "强化学习": "强化学习",
    "微调": "微调",
    "向量数据库": "向量数据库",
}


class TermDictionary:
    """Manages domain-specific terms for ASR enhancement."""

    def __init__(self, extra_terms: Optional[dict[str, str]] = None):
        self._terms: dict[str, str] = dict(_BUILTIN_TERMS)
        if extra_terms:
            self._terms.update(extra_terms)

    def load_from_file(self, path: str) -> None:
        """Load extra terms from a JSON file: {"term": "pronunciation_hint"}."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            extra = json.load(f)
        self._terms.update(extra)

    @property
    def all_terms(self) -> dict[str, str]:
        return dict(self._terms)

    def get_hotwords(self, text: str) -> list[str]:
        """Return terms found in the given text, for Whisper `hotwords` param."""
        found: list[str] = []
        for term in self._terms:
            if term.lower() in text.lower():
                found.append(term)
        return found

    def build_prompt(self, max_terms: int = 50) -> str:
        """Build a prompt string of top-priority terms for Whisper initial_prompt."""
        # Sort by term length desc (longer = more specific = higher priority)
        sorted_terms = sorted(self._terms.keys(), key=len, reverse=True)[:max_terms]
        return "Domain terms: " + ", ".join(sorted_terms)

    def inject_into_segments(self, segments: list[dict]) -> list[dict]:
        """Post-process segments: correct known term mis-transcriptions."""
        for seg in segments:
            text = seg.get("text", "")
            for term, hint in self._terms.items():
                # Simple fuzzy: if the hint is in text but the canonical term isn't
                if hint.lower() in text.lower() and term.lower() not in text.lower():
                    text = text.replace(hint, term)
            seg["text"] = text
        return segments


# Global singleton
default_terms = TermDictionary()
