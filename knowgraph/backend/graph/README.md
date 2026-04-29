# T18: 知识图谱构建 (Knowledge Graph Construction)

## 概述

基于 T17 AI 笔记生成的输出，通过 LLM 两阶段流水线从结构化笔记中提取知识点及其语义关系，构建视频知识图谱。

### 处理流程

```
T16 ASR Pipeline                    T17 AI Notes                    T18 Knowledge Graph
  ┌──────────────┐                  ┌──────────────┐                ┌──────────────────┐
  │ VideoSegment │  segments[]      │    Note      │  title,sum,    │ KnowledgeNode[]  │
  │ (segments)   │ ─────────────►   │   Sections   │  keywords,     │ Relation[]       │
  └──────────────┘                  │              │  sections      │                  │
                                    └──────────────┘ ────────────►  └──────────────────┘
                                        ↑                                 ↑
                                    LLM Stage 1-3                  LLM Stage: Nodes→Edges
```

## 目录结构

```
t18-knowledge-graph/
├── README.md
└── backend/
    ├── schemas/
    │   └── graph_schema.py       # LLM 输出 JSON Schema 定义
    ├── prompts/
    │   └── graph_prompts.py      # 两阶段 Prompt 模板
    ├── services/
    │   └── graph_service.py      # 核心图谱提取服务
    ├── tasks/
    │   └── graph_tasks.py        # Celery 异步任务
    └── routers/
        └── graph.py             # FastAPI 路由
```

## 数据模型

复用 T16 中定义的 `KnowledgeNode` 和 `Relation` ORM 模型。

### KnowledgeNode（知识点节点）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| video_id | UUID → videos.id | 关联视频 |
| name | String(256) | 知识点名称 |
| description | Text | 简要描述 |
| node_type | Enum | CONCEPT/PERSON/TECHNOLOGY/METHODOLOGY/EXAMPLE/RELATION/PREREQUISITE |
| segment_index | Integer | 关联的章节索引 |
| importance | Float | 重要性评分 (0-1) |
| mastery | Enum | 掌握程度（由用户更新） |

### Relation（节点间关系）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| source_node_id | UUID → knowledge_nodes.id | 源节点 |
| target_node_id | UUID → knowledge_nodes.id | 目标节点 |
| relation_type | Enum | PREREQUISITE_OF/IS_A/PART_OF/RELATES_TO/CONTRASTS_WITH/LEADS_TO/EXAMPLE_OF/USES/APPLIES_TO |
| strength | Float | 关系强度 (0-1) |
| description | Text | 关系描述 |

## 两阶段流水线

### Stage 1: Node Extraction（节点提取）
- **输入**: 笔记标题、摘要、关键词、章节内容
- **输出**: 5-20 个知识点节点
- **温度**: 0.3
- **去重**: 同名节点自动合并（保留较长描述 + 更高重要性 + 合并章节索引）

### Stage 2: Relation Extraction（关系提取）
- **输入**: Stage 1 输出的节点列表 + 笔记全文（前 12000 字符）
- **输出**: 3-50 条语义关系
- **温度**: 0.3
- **校验**: 自动过滤 source/target 不在已提取节点列表中的关系

## 幂等性保证

1. **任务幂等**: Celery task_id 使用 `graph-{video_id}`，同一视频不会重复执行
2. **DB 幂等**: 执行前检查 `knowledge_nodes` 表是否已有该视频的记录，有则跳过
3. **重试**: 单任务最多重试 2 次，指数退避

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/videos/{id}/graph/extract` | 启动图谱提取（需先有笔记） |
| GET | `/api/v1/videos/{id}/graph` | 获取完整图谱（节点+关系） |
| GET | `/api/v1/videos/{id}/graph/nodes` | 分页列出节点（支持类型过滤） |
| GET | `/api/v1/videos/{id}/graph/focus/{node_id}` | n-hop 焦点子图 |
| GET | `/api/v1/videos/{id}/graph/search?q=` | 搜索节点名称/描述 |
| GET | `/api/v1/videos/{id}/graph/status` | 查询提取状态 |
| PUT | `/api/v1/graph/mastery` | 更新掌握度 |
| DELETE | `/api/v1/videos/{id}/graph` | 删除图谱（重新提取） |
| WS | `/ws/video/{id}/graph` | WebSocket 进度推送 |

## Celery 任务

任务名：`extract_graph`

```python
# 在 celery_app.py 中注册
celery_app.task(name="extract_graph", bind=True, max_retries=2)(
    lambda self, video_id: (
        __import__("backend.tasks.graph_tasks", fromlist=["extract_graph_task"])
        .extract_graph_task(video_id)
    )
)
```

## 图谱遍历查询

### 焦点模式 (Focus Subgraph)
使用 PostgreSQL `RECURSIVE CTE` 实现 n-hop 邻居遍历：
```sql
WITH RECURSIVE subgraph AS (
    SELECT id FROM knowledge_nodes WHERE id = :start_id
    UNION
    SELECT r.target_node_id FROM relations r
    JOIN subgraph s ON r.source_node_id = s.id
    WHERE (SELECT COUNT(*) FROM subgraph) < :max_nodes
    UNION
    SELECT r.source_node_id FROM relations r
    JOIN subgraph s ON r.target_node_id = s.id
    WHERE (SELECT COUNT(*) FROM subgraph) < :max_nodes
)
SELECT * FROM knowledge_nodes WHERE id IN (SELECT id FROM subgraph);
```

### 搜索模式
使用 `ILIKE` 实现大小写不敏感的模糊搜索，按重要性降序排列。

## 集成点

- **上游**: T17 AI 笔记生成 → `Note` + `NoteSection` 表（必须先完成笔记生成）
- **下游**: 前端可视化（期望 D3.js / vis.js 等）或 QA 问答系统
- **LLM**: 通过 `http://llm:8002/v1/chat/completions` 调用
- **Redis**: 进度推送 `video:{id}:graph_progress`
