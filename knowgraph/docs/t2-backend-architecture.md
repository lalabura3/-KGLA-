# T2：后端框架与数据库设计 — 技术方案

> 作者：Charlie（后端工程师）  
> 日期：2026-04-29  
> 状态：待 T1（Ella 基础设施）就绪后启动

---

## 1. 目标

在现有代码基础上，修复 3 个 Critical 问题并完成 MVP 级后端基础设施，支撑 T6/T7/T8 开发。

---

## 2. 待修复的 Critical 问题

### 2.1 异步处理架构对齐 → Celery

**现状**：`backend/routers/videos.py` 用 `BackgroundTasks.add_task()` 同步执行 Pipeline。

**方案**：

```python
# videos.py — 改动点
from celery_app import celery_app  # 已存在

@router.post("/upload", ...)
async def upload_video(...):
    # ... 保存文件、创建 DB 记录 ...
    await db.commit()
    await db.refresh(db_video)

    # ✅ 改为发送 Celery task
    celery_app.send_task(
        "process_video",
        args=[str(db_video.id), str(save_path), "zh"],
        task_id=f"video-{db_video.id}"  # 幂等去重
    )
    # ❌ 删除 background_tasks.add_task(...)
```

**附**：`celery_app.py` 的 task 骨架已存在，只需实现具体逻辑（复用已有 services）。

---

### 2.2 事务一致性

**现状**：Pipeline 中多次 `commit()`，中间失败数据残留。

**方案**：每个阶段写入前先检查前置条件，改为阶段幂等写入 + 统一错误处理：

```python
async def process_video_pipeline(video_id: str, video_path: str):
    """幂等 Pipeline：每个阶段可独立重试"""
    async with async_session() as db:
        try:
            video = await _get_video(db, video_id)
            
            # Stage 1: ASR (幂等：检查 segments 是否已存在)
            if not await _has_segments(db, video_id):
                await _run_asr_stage(db, video, video_path)
            
            # Stage 2: Notes (幂等：检查 notes 是否已生成)
            if not await _has_notes(db, video_id):
                await _run_notes_stage(db, video, segments)
            
            # Stage 3: Graph (幂等：检查 graph 是否已构建)
            if not await _has_graph(db, video_id):
                await _run_graph_stage(db, video, segments)
            
            video.status = VideoStatus.COMPLETED
            await db.commit()
            
        except Exception as e:
            logger.error(f"Pipeline failed for video {video_id}: {e}")
            try:
                video.status = VideoStatus.FAILED
                video.error_message = str(e)
                await db.commit()
            except Exception:
                await db.rollback()
```

---

### 2.3 数据库迁移 → Alembic

**方案**：

```bash
# 初始化 Alembic（一次性）
pip install alembic
alembic init backend/migrations

# 配置 alembic.ini 指向异步 PostgreSQL
# env.py 中设置 target_metadata = Base.metadata
```

**迁移流程**：
1. 自动生成：`alembic revision --autogenerate -m "init"`
2. 应用：`alembic upgrade head`
3. 回滚：`alembic downgrade -1`

**集成**：在 `docker-compose.yml` 的 backend 启动命令中加入 `alembic upgrade head && uvicorn ...`

---

## 3. 服务架构设计

### 3.1 整体分层

```
┌─────────────────────────────────────────────────┐
│                  Nginx (80)                      │
├────────┬────────┬────────┬────────┬─────────────┤
│Next.js │FastAPI │Celery  │Whisper │ LLM Service │
│ :3000  │ :8000  │ Worker │ :8001  │ :8002       │
└────────┴────────┴────────┴────────┴─────────────┘
          │                  │
    ┌─────┴─────┐      ┌────┴────┐
    │ PostgreSQL │      │  Redis   │
    │ :5432      │      │  :6379   │
    └───────────┘      └─────────┘
```

### 3.2 Celery Pipeline 任务拆解

```
Task: process_video (Celery)
  │
  ├─ Sub-task 1: extract_audio (FFmpeg)
  │     → output: /uploads/audio/{video_id}.wav
  │
  ├─ Sub-task 2: transcribe (→ Whisper HTTP)
  │     → output: segments[] in DB
  │
  ├─ Sub-task 3: analyze_segments (→ LLM HTTP)
  │     → output: titles, summaries, keywords in DB
  │
  ├─ Sub-task 4: build_graph (→ LLM HTTP)
  │     → output: knowledge_nodes + relations in DB
  │
  └─ Sub-task 5: cleanup (rm audio.wav)
```

**进度回调**：每个子任务完成时通过 Redis 更新进度，API 通过 `GET /api/videos/{id}/status` 读取。

### 3.3 WebSocket 进度推送（P1）

```
GET /ws/video/{video_id}
  → SSE 或 WebSocket
  → 从 Redis pub/sub 订阅进度事件
  → 前端实时渲染进度条
```

（P1 实现，MVP 用轮询即可）

---

## 4. 数据库设计

### 4.1 ERD

```
┌──────────┐       ┌──────────────┐       ┌──────────────────┐
│  users   │       │   videos     │       │ knowledge_nodes  │
├──────────┤       ├──────────────┤       ├──────────────────┤
│ id (PK)  │──┐    │ id (PK)      │──┐    │ id (PK)          │
│ username │  │    │ user_id (FK) │◄─┘    │ video_id (FK)    │──┐
│ email    │  │    │ title        │  │    │ name             │  │
│ ...      │  └───►│ filename     │  │    │ description      │  │
└──────────┘       │ file_path    │  │    │ node_type (enum) │  │
                   │ duration     │  │    │ timestamp        │  │
                   │ status(enum) │  │    │ segment_index    │  │
                   │ source_url   │  │    │ importance       │  │
                   │ error_msg    │  │    │ mastery (enum)   │  │
                   │ created_at   │  │    │ embedding        │  │
                   │ updated_at   │  │    └──────────────────┘  │
                   └──────────────┘                             │
                          │                                     │
                          │ (1:N)                               │
                   ┌──────▼───────┐         ┌──────────────────┐│
                   │video_segments│         │    relations     ││
                   ├──────────────┤         ├──────────────────┤│
                   │ id (PK)      │         │ id (PK)          │◄┘
                   │ video_id(FK) │         │ source_node_id(FK)
                   │ segment_idx  │         │ target_node_id(FK)
                   │ start_time   │         │ relation_type(enum)
                   │ end_time     │         │ strength         │
                   │ title        │         │ description      │
                   │ content      │         └──────────────────┘
                   │ summary      │
                   │ keyframe_path│
                   │ embedding    │
                   └──────────────┘
```

### 4.2 索引策略

```sql
-- Videos: 按用户 + 状态查询
CREATE INDEX idx_videos_user_status ON videos(user_id, status);
CREATE INDEX idx_videos_created ON videos(created_at DESC);

-- Segments: 按视频 + 时间轴查询
CREATE INDEX idx_segments_video_time ON video_segments(video_id, start_time);

-- Knowledge Nodes: 按视频 + 类型查询
CREATE INDEX idx_nodes_video ON knowledge_nodes(video_id);
CREATE INDEX idx_nodes_type ON knowledge_nodes(video_id, node_type);

-- Relations: 按源/目标节点查询 (图谱遍历核心)
CREATE INDEX idx_relations_source ON relations(source_node_id);
CREATE INDEX idx_relations_target ON relations(target_node_id);
CREATE INDEX idx_relations_type ON relations(relation_type);

-- Users: 唯一性约束已通过 unique=True 定义
CREATE INDEX idx_users_username ON users(username);
```

### 4.3 图谱遍历查询优化

```python
# graph.py — 焦点模式：查找 n-hop 邻居
from sqlalchemy import text

async def get_focus_subgraph(db, node_id: int, hops: int = 1):
    """递归获取 n-hop 邻居子图"""
    # 方案1：应用层递归（小图 OK）
    # 方案2：PostgreSQL RECURSIVE CTE（大图推荐）
    query = text("""
        WITH RECURSIVE subgraph AS (
            SELECT source_node_id AS node_id FROM relations 
            WHERE target_node_id = :start
            UNION
            SELECT target_node_id FROM relations 
            WHERE source_node_id = :start
            UNION
            SELECT r.source_node_id FROM relations r
            JOIN subgraph s ON r.target_node_id = s.node_id
            WHERE s.node_id NOT IN (SELECT node_id FROM subgraph WHERE ...)
        )
        SELECT * FROM knowledge_nodes WHERE id IN (SELECT node_id FROM subgraph)
    """)
```

---

## 5. API 规范扩展

### 5.1 新增 Endpoints

| Method | Path | Description | Priority |
|--------|------|-------------|----------|
| GET | `/api/v1/health` | 健康检查（已有） | P0 |
| POST | `/api/v1/videos/upload` | 上传视频 | P0 |
| GET | `/api/v1/videos/{id}/status` | 处理进度 | P0 |
| GET | `/api/v1/videos/{id}` | 视频详情 | P0 |
| GET | `/api/v1/notes/{video_id}` | AI 笔记 | P0 |
| GET | `/api/v1/graph/{video_id}` | 知识图谱数据 | P0 |
| GET | `/api/v1/graph/{video_id}/focus/{node_id}` | 焦点子图 | P1 |
| GET | `/api/v1/graph/{video_id}/path?from=&to=` | 路径模式 | P1 |
| GET | `/api/v1/graph/{video_id}/search?q=` | 图谱搜索 | P1 |
| PUT | `/api/v1/graph/mastery` | 更新掌握度 | P1 |
| POST | `/api/v1/qa` | AI 问答 | P1 |
| WS | `/ws/video/{id}` | 实时进度 | P1 |

### 5.2 统一错误响应

```json
{
  "error": {
    "code": "VIDEO_NOT_FOUND",
    "message": "视频未找到",
    "detail": "video_id=999 does not exist"
  }
}
```

### 5.3 全局异常处理中间件

```python
# 新增 backend/middleware/error_handler.py
from fastapi import Request
from fastapi.responses import JSONResponse

async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}
    )
```

---

## 6. 配置管理增强

```python
# config.py 新增项
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # API
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "structured"  # structured | plain
    
    # Security (MVP 占位)
    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
```

---

## 7. 日志标准化

```python
# 新增 backend/utils/logging.py
import structlog

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer() if settings.log_format == "plain"
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

logger = structlog.get_logger()
```

---

## 8. 开发计划

| Week | Task | Deliverable |
|------|------|------------|
| W1-D1 | Alembic 初始化，生成并应用首次 migration | schema.sql |
| W1-D2 | 修复 Celery 集成，实现幂等 Pipeline | celery tasks |
| W2-D1 | 索引策略 + 图谱遍历查询 | graph queries |
| W2-D2 | 统一错误处理 + 结构化日志 | middleware |
| W2-D3 | WebSocket 进度推送 | ws endpoint |
| W2-D4 | 配置管理增强 + API 版本化 | /api/v1 prefix |

**依赖**：T1 完成（PostgreSQL + Redis + Docker GPU 环境）

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Celery worker OOM（大视频） | worker_prefetch_multiplier=1, task_time_limit=1800 |
| 图谱 N+1 查询 | eager loading (`selectinload`), 批量查询 |
| PostgreSQL CTE 递归性能 | 设置 `max_recursion_depth`, fallback 应用层递归 |
| Alembic 与已有表冲突 | 首次迁移用 `--autogenerate` + 手动 review |

---

*待 T1 就绪后执行，届时根据 Ella 的实际环境配置微调。*
