# T17: AI 笔记生成 (AI Note Generation)

## 概述

基于 ASR 转写结果，通过 LLM 三阶段流水线生成结构化学习笔记：
1. **Metadata** — 生成标题、摘要、关键词、元数据
2. **Sections** — 按时间段拆分章节，时间戳锚定 + 原文证据引用
3. **Polish** — 幻觉自检、语言润色、内容去重

## 目录结构

```
t17-ai-notes/
├── README.md
└── backend/
    ├── models/
    │   └── note.py              # Note & NoteSection ORM 模型
    ├── schemas/
    │   └── note_schema.py       # LLM 输出 JSON Schema 定义
    ├── prompts/
    │   └── note_prompts.py      # 三阶段 Prompt 模板
    ├── services/
    │   └── note_service.py      # 核心笔记生成服务
    ├── tasks/
    │   └── note_tasks.py        # Celery 异步任务
    └── routers/
        └── notes.py             # FastAPI 路由
```

## 数据模型

### Note（笔记主表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| video_id | UUID → videos.id | 关联视频（唯一） |
| title | String(512) | 笔记标题 |
| summary | Text | 100-200 字摘要 |
| full_text | Text | 完整笔记文本 |
| keywords | JSONB | 10-20 个关键词 |
| metadata | JSONB | 主题/难度/语言等元数据 |
| hallucination_score | Float | 幻觉评分 (0-1) |
| language | String(10) | 主要语言 |
| word_count | Integer | 总字数 |

### NoteSection（笔记章节）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| note_id | UUID → notes.id | 关联笔记 |
| section_index | Integer | 章节序号 |
| heading | String(256) | 章节标题 |
| content | Text | 章节内容（连贯段落） |
| start_time | Float | 起始时间戳（秒） |
| end_time | Float | 结束时间戳（秒） |
| segment_ids | JSONB | 源 segment 编号 |
| key_points | JSONB | 关键要点 |
| source_text | Text | 原文参考（截断） |
| hallucination_flags | JSONB | 幻觉标记 |
| confidence | Float | 置信度 (0-1) |

## 三阶段流水线

### Stage 1: Metadata 提取
- **输入**: 完整转写文本（最多 16000 字符）
- **输出**: title, summary, keywords, metadata (topic/difficulty/language/speaker_count)
- **温度**: 0.3

### Stage 2: 章节拆分
- **输入**: 带时间戳的转写文本 + 标题/主题
- **输出**: 按主题逻辑拆分的章节列表
- **约束**: 每章节至少 2 条 evidence（原文引用），时间戳精确匹配 segment 边界
- **温度**: 0.4

### Stage 3: 润色与幻觉自检
- **输入**: 生成的笔记 JSON + 原文摘要
- **输出**: 修正后的笔记，标记 hallucination_flags
- **检查项**: 内容忠实度、时间戳正确性、evidence 准确性、章节合理性、语言质量
- **温度**: 0.2

## 幻觉预防机制

1. **Evidence 强制**：每个章节必须附带 2+ 条原文引用
2. **三阶段自检**：Polish 阶段逐条核对 evidence 是否存在于原文
3. **Hallucination Score**：`score = min(flags_count × 0.1, 1.0)`
4. **Section Confidence**：有幻觉标记的章节自动降低置信度

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/videos/{id}/notes/generate` | 启动笔记生成 |
| GET | `/api/v1/videos/{id}/notes` | 获取完整笔记（含章节） |
| GET | `/api/v1/videos/{id}/notes/sections` | 分页列出章节 |
| PATCH | `/api/v1/videos/{id}/notes/sections/{sid}` | 手动编辑章节 |
| GET | `/api/v1/videos/{id}/notes/status` | 查询生成状态 |
| DELETE | `/api/v1/videos/{id}/notes` | 删除笔记（重新生成） |
| WS | `/ws/video/{id}/notes` | WebSocket 进度推送 |

## Celery 任务

任务名：`generate_notes`

```python
# 在 celery_app.py 中注册
celery_app.task(name="generate_notes", bind=True, max_retries=2)(
    lambda self, video_id: (
        __import__("backend.tasks.note_tasks", fromlist=["generate_notes_task"])
        .generate_notes_task(video_id)
    )
)
```

## 集成点

- **上游**: T16 ASR Pipeline → `VideoSegment` 表
- **下游**: T18 知识图谱 → 笔记文本作为图谱构建输入
- **LLM**: 通过 `http://llm:8002/v1/chat/completions` 调用
- **Redis**: 进度推送 `video:{id}:note_progress`
