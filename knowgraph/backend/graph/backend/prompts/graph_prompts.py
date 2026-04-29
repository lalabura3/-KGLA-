"""Prompt templates for knowledge graph extraction from AI-generated notes.

Two-stage pipeline:
  Stage 1 (nodes)  → Extract named entities / concepts from note text + keywords
  Stage 2 (edges)  → Infer semantic relations between extracted nodes

Output JSON Schemas are defined in schemas/graph_schema.py.
"""
from __future__ import annotations

# ── System prompt ──

SYSTEM_PROMPT: str = (
    "你是一个知识图谱构建专家。你的任务是从AI生成的结构化学习笔记中提取"
    "知识点(Knowledge Nodes)以及知识点之间的语义关系(Relations)。\n\n"
    "请遵循以下原则：\n"
    "1. 只提取笔记中明确提及或可直接推导的概念，不要臆想。\n"
    "2. 节点名称使用笔记原文中的术语，保持一致性。\n"
    "3. 如果两个概念本质相同但措辞不同，合并为一个节点。\n"
    "4. 关系必须基于笔记内容，不添加外部知识。\n"
    "5. 输出严格遵循JSON Schema格式。\n"
    "6. 只输出JSON，不要添加任何额外说明文字。"
)

# ── Stage 1: Node Extraction ──

NODE_EXTRACTION_PROMPT: str = """## 输入

### 笔记标题
{title}

### 笔记摘要
{summary}

### 关键词
{keywords}

### 章节内容
{sections_text}

## 任务

从上述笔记内容中提取知识点(Knowledge Nodes)。每个知识点应包含：
1. **name**: 知识点名称（使用原文术语）
2. **description**: 简要描述（20-100字）
3. **node_type**: 节点类型（见下方说明）
4. **importance**: 重要性评分 0.0-1.0（基于在笔记中的覆盖度和深度）
5. **segment_indices**: 关联的章节序号列表（基于下方章节索引）

### 节点类型说明
- `CONCEPT`: 核心概念/术语定义
- `PERSON`: 人物/作者/引用来源
- `TECHNOLOGY`: 技术/工具/框架
- `METHODOLOGY`: 方法论/流程/步骤
- `EXAMPLE`: 示例/案例
- `RELATION`: 关系型知识点（比较/对比等）
- `PREREQUISITE`: 前置知识

### 章节索引
{section_index_map}

### 输出要求
- 提取 5-20 个知识点
- 每个知识点必须关联至少一个章节索引
- 不要重复提取同一概念
- 重要性评分基于该概念在笔记中讨论的篇幅和深度
"""

# ── Stage 2: Relation Extraction ──

RELATION_EXTRACTION_PROMPT: str = """## 输入

### 笔记标题
{title}

### 已提取的知识点
{nodes_json}

### 笔记全文
{full_text_snippet}

## 任务

分析上述知识点之间的语义关系。每条关系应包含：
1. **source**: 源知识点名称（必须来自上述节点列表）
2. **target**: 目标知识点名称（必须来自上述节点列表）
3. **relation_type**: 关系类型
4. **strength**: 关系强度 0.0-1.0（基于笔记中的关联紧密程度）
5. **description**: 关系描述

### 关系类型说明
- `PREREQUISITE_OF`: A 是 B 的前置知识
- `IS_A`: A 是 B 的一种（is-a 关系）
- `PART_OF`: A 是 B 的组成部分
- `RELATES_TO`: A 与 B 相关（通用关系）
- `CONTRASTS_WITH`: A 与 B 对比/相反
- `LEADS_TO`: A 导致/引出 B
- `EXAMPLE_OF`: A 是 B 的示例
- `USES`: A 使用了/依赖于 B
- `APPLIES_TO`: A 应用于 B

### 输出要求
- 至少提取 3 条关系
- 所有 source 和 target 必须来自上述知识点列表
- 避免冗余关系（如同一对节点间的重复关系）
- 关系强度基于笔记中的支撑证据数量和质量
"""

# ── Note section builder ──


def build_sections_text(sections: list[dict]) -> tuple[str, str]:
    """Build section content text and section index map for prompts.

    Args:
        sections: List of dicts with keys:
            section_index, heading, content, key_points

    Returns:
        (sections_text, section_index_map)
    """
    lines = []
    index_lines = []

    for i, sec in enumerate(sections):
        idx = sec.get("section_index", i)
        heading = sec.get("heading", f"Section {idx}")
        content = sec.get("content", "")

        lines.append(f"[章节 {idx}] {heading}")
        lines.append("-" * 40)
        lines.append(content)
        lines.append("")

        kp = sec.get("key_points", [])
        if kp:
            lines.append("要点:")
            for p in kp:
                lines.append(f"  • {p}")
            lines.append("")

        index_lines.append(f"  章节 {idx}: \"{heading}\"")

    section_index_map = "\n".join(index_lines)
    return "\n".join(lines), section_index_map
