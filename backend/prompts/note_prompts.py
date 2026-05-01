"""Prompt templates for AI note generation.

策略：3 阶段流水线
  1. title_summary — 生成标题、摘要、关键词、元数据
  2. sections — 按时间段生成结构化章节
  3. polish — 润色、去重、幻觉自检
"""
from __future__ import annotations

from .note_schema import NOTE_OUTPUT_SCHEMA

# ── System prompt (shared across stages) ──

SYSTEM_PROMPT = """你是 StudyAI 的智能笔记生成助手。你的任务是将视频转写文本转化为结构化学习笔记。

核心原则：
1. **忠实原文**：所有观点必须能从转写文本中找到支撑，不得凭空编造。
2. **时间锚定**：每个章节必须绑定到具体的时间戳区间。
3. **证据驱动**：每条关键观点必须附带原文引用（evidence），无引用即视为幻觉。
4. **结构化输出**：严格遵循 JSON Schema 输出格式。
5. **学术风格**：使用清晰、客观的语言，避免冗余和口语化表达。

输出语言：与原文相同。如果原文是中文，用中文输出；英文则用英文。
"""

# ── Stage 1: Title, summary, keywords, metadata ──

METADATA_PROMPT = """分析以下视频转写内容，提取元信息并以 JSON 格式输出。

## 要求
1. title：精炼标题（10-20 字），概括视频核心内容
2. summary：100-200 字摘要，涵盖主要论点
3. keywords：10-20 个关键术语
4. metadata.topic：主题领域
5. metadata.difficulty：内容难度（beginner/intermediate/advanced/expert）
6. metadata.is_technical：是否包含技术术语/代码
7. metadata.has_code：是否包含代码讨论
8. metadata.language：主要语言（zh/en/mixed）
9. metadata.speaker_count：说话人数

## 转写文本
{transcript}

## 输出格式
请严格按以下 JSON Schema 输出（不要包含 markdown 代码块标记）：
{{
  "title": "...",
  "summary": "...",
  "keywords": ["...", "..."],
  "metadata": {{
    "topic": "...",
    "difficulty": "...",
    "is_technical": true/false,
    "has_code": true/false,
    "language": "...",
    "speaker_count": 1
  }}
}}
"""

# ── Stage 2: Structured sections with timestamp anchors ──

SECTIONS_PROMPT = """将以下视频转写文本拆分为结构化的学习笔记章节。

## 上下文
- 视频标题：{title}
- 视频主题：{topic}

## 要求
1. 按主题逻辑拆分章节（非机械按时间等分）
2. 每个章节必须绑定 start_time 和 end_time（秒），必须精确来自转写文本中已有的时间戳
3. 每个章节的 heading 为内容小结（10-20 字）
4. content 为 2-5 句连贯总结，保持学术风格
5. key_points 为 2-5 条要点
6. **每章节至少包含 2 条 evidence（原文引用）**，标记对应的 segment_index
7. source_segment_indices 列出该章节覆盖的 segment 编号

## 转写文本（含时间戳和segment编号）
{transcript_with_timestamps}

## 输出格式
严格按以下 JSON 格式输出章节列表（不要包含 markdown 代码块标记）：
[
  {{
    "heading": "深度学习基础概念",
    "content": "本节介绍了深度学习的核心定义...",
    "start_time": 0.0,
    "end_time": 120.5,
    "key_points": ["深度学习是机器学习的分支", "核心算法是反向传播"],
    "source_segment_indices": [0, 1, 2, 3, 4],
    "evidence": [
      {{"quote": "深度学习是机器学习的一个重要分支", "segment_index": 0}},
      {{"quote": "反向传播是训练神经网络的核心算法", "segment_index": 2}}
    ]
  }}
]
"""

# ── Stage 3: Polish & self-consistency check ──

POLISH_PROMPT = """审核并润色以下 AI 生成的笔记，修正任何问题。

## 原始转写文本（参考）
{transcript_snippet}

## 生成的笔记
{notes_json}

## 检查清单
1. 内容是否忠实于原文？（标记任何偏离原文的陈述）
2. 时间戳是否正确？（章节时间必须在转写文本时间范围内）
3. evidence 引用是否准确？（逐条核对引用内容是否真的在原文中出现）
4. 章节划分是否合理？（不应重复、不应遗漏重要内容）
5. 语言是否清晰、学术化？

## 输出格式
返回修正后的完整 JSON，格式与输入相同。如果无需修改，直接返回原 JSON。

## 重要
- 如果发现幻觉（即笔记中包含原文不存在的信息），请修正或删除该内容
- 在每条修改的章节中添加 hallucination_flags 字段，标记发现的问题
"""

# ── Convenience: compose all stages into a single-shot prompt ──

SINGLE_SHOT_PROMPT = """You are an expert educational note-taker. Given a video transcript with timestamps, produce a structured study note.

{system_prompt}

## Video Transcript (with timestamps and segment indices)
{transcript_with_timestamps}

## Instructions
Analyze the transcript and produce a comprehensive, well-structured study note. Follow these rules strictly:
1. Each section MUST quote evidence from the transcript — no fabrication.
2. Timestamps must match the transcript exactly — do not invent times.
3. Use academic, objective language.
4. Output MUST be valid JSON matching the schema below.

## Output JSON Schema
{schema}

IMPORTANT: Output raw JSON only (no markdown fences)."""
