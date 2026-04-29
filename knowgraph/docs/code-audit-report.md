# 「学知图谱」代码审计与 PRD 合规验证报告

**审计人：** Frank (技术评审员)  
**日期：** 2026-04-29  
**任务：** p-mojhffoinvpwa9-task-4  
**代码库：** `/root/.openclaw/workspace/projects/ai-learning-agent/`  
**代码总量：** ~35 文件，~2800 行

---

## 总体评分

| 维度 | 评分 | 等级 |
|------|------|------|
| PRD 合规度 | 7.5/10 | 🟡 良好（核心链路已实现，有缺口） |
| 架构一致性 | 6.5/10 | 🟡 需改进（存在耦合与职责重叠） |
| 命名规范 | 8/10 | 🟢 良好 |
| 错误处理 | 4/10 | 🔴 不足（多处裸奔） |
| 安全与隐私 | 5/10 | 🟡 需加强 |
| 代码可复用度 | 6/10 | 🟡 中等 |
| **综合** | **6.2/10** | **🟡 可投产 MVP，但需补齐关键缺口** |

---

## 1. PRD 技术合规验证

### 1.1 核心链路实现情况

| PRD 要求 | 代码实现 | 状态 | 说明 |
|----------|---------|------|------|
| 视频上传 (FR-01) | `routers/videos.py:upload_video` | ✅ | 支持 500MB 限制 |
| 视频链接导入 (FR-02) | `routers/videos.py:import_from_link` | ⚠️ | 占位实现，未做实际链接解析 |
| 格式校验 | `routers/videos.py` L24-26 | ✅ | .mp4/.flv/.avi/.mov/.mkv/.webm |
| ASR 处理 (FR-03) | `services/asr_service.py` + `ai-services/whisper_service.py` | ✅ | Whisper large-v3 + VAD |
| 语义分段 (FR-04) | 由 Whisper VAD 完成 | ⚠️ | 未调用 LLM 做语义断点，依赖 Whisper 原生分段 |
| 关键帧提取 (FR-05) | `services/video_processor.py:extract_keyframes` | ✅ | FFmpeg fps=1/10 |
| 图文笔记 (FR-06) | `services/note_generator.py` | ✅ | LLM 生成 |
| 时间戳跳转 (FR-07) | 前端 `learn/[videoId].js:handleSeek` | ✅ | |
| 知识点提取 (FR-08) | `services/graph_builder.py:extract_knowledge_nodes` | ✅ | |
| 关系推断 (FR-09) | `services/graph_builder.py:infer_relations` | ✅ | |
| 图谱交互 (FR-10) | `components/KnowledgeGraph.js` | ✅ | vis-network |
| 笔记编辑 (FR-11) | `routers/notes.py:update_segment` | ✅ | |
| AI 问答 (FR-12) | `routers/qa.py` | ✅ | RAG 实现（简单关键词匹配） |
| 掌握度标记 (FR-13) | `routers/graph.py:update_mastery` | ✅ | |
| 学习仪表盘 (FR-14) | `pages/index.js` 上部分统计 | ⚠️ | 功能偏浅，非独立仪表盘 |

### 1.2 PRD 缺口清单

| # | PRD 要求 | 缺失情况 | 严重度 |
|---|---------|---------|--------|
| 1 | **导出功能 (Markdown/PDF)** | 完全未实现 | 🔴 高 |
| 2 | **VAD 分段预览与手动修正** | 未实现，无法纠正前端 ASR 分段偏差 | 🔴 高 |
| 3 | **视频播放器集成** | 仅有占位 UI，无实际播放功能 | 🔴 高 |
| 4 | **关键帧插入笔记** | `extract_keyframes` 实现了但未关联到笔记展示 | 🟡 中 |
| 5 | **语义分段 (LLM)** | 当前完全依赖 Whisper VAD 分段，未用 LLM 做话题划分 | 🟡 中 |
| 6 | **用户认证系统** | 所有 API 硬编码 `user_id=1`，无登录体系 | 🟡 中 |
| 7 | **文件加密存储** | PRD 要求 AES-256，代码未实现 | 🟡 中 |
| 8 | **图谱节点聚类/分组** | PRD 要求章节聚类 → 群组折叠，未实现 | 🟡 中 |
| 9 | **跨视频知识图谱** | 明确标注 Phase 2，合理 | 🟢 低 |

---

## 2. 架构一致性分析

### 2.1 架构分层评估

```
当前架构:
[Frontend/Next.js] ──HTTP── [Backend/FastAPI] ──HTTP── [ai-services]
                                  │
                                  ├── models/    (SQLAlchemy)  ✅ 清晰
                                  ├── routers/   (API 端点)     ✅ 清晰
                                  ├── services/  (业务逻辑)     ⚠️ 部分耦合
                                  ├── schemas/   (Pydantic)     ✅ 清晰
                                  └── config.py                 ✅ 清晰
```

### 2.2 架构问题

#### ❌ 问题 1: LLM 服务双实例重复

```
backend/services/llm_service.py  ← 一个 LLM 客户端
ai-services/llm_service.py       ← 另一个 LLM 服务（含本地推理）
```

**问题：** 两个 `llm_service.py` 都实现了 `chat()` 方法和 `LLM_MODE` 判断。backend 版本调用 `ai-services` 的 `/v1/chat/completions`，而 ai-services 版本要么代理到 DeepSeek API，要么本地推理。**backend 版本中 `_call_api` 直接发请求到 `self.api_base`（DeepSeek），绕过了 ai-services 代理层**——这意味着 backend 的 `llm_mode=api` 时完全不使用 ai-services，破坏了"所有 AI 推理统一走 ai-services"的架构意图。

**影响：** 架构不一致，存在两套 LLM 调用路径，调试和维护困难。

#### ❌ 问题 2: `process_video_pipeline` 耦合在 router 中

```python
# routers/videos.py L115-207
async def process_video_pipeline(video_id: int, video_path: str):
    """Full processing pipeline: ASR → Notes → Knowledge Graph."""
    from database import async_session  # <-- router 内直接操作 DB
    from models.knowledge_node import KnowledgeNode, NodeType
    from models.relation import Relation, RelationType
```

**问题：** 整个视频处理管线（180+ 行）写在 router 文件里，not in services/。它直接操作数据库、直接 import model、直接创建记录。违反了"router 只做路由分发，services 做业务逻辑"的原则。

**影响：** 代码不可测试、不可复用。如果后续要支持 CLI 触发处理或批量处理，这段逻辑完全无法独立调用。

#### ❌ 问题 3: `asr_service.py` 中 import 位置错误

```python
# services/asr_service.py
class ASRService:
    ...
    def _mock_transcribe(self, audio_path: str) -> dict:
        import os  # <-- 函数内 import
        ...

import os  # noqa: E402 (fix import order)  # <-- 文件末尾补 import
```

**问题：** `transcribe()` 方法中用了 `os.path.basename()` 但 `os` 在函数内的 `_mock_transcribe` 才 import，顶部并没有 import。实际上 `transcribe()` 方法中直接使用了 `os`（第 L35 行），但 `os` 的 import 在文件末尾 `# noqa: E402`。这是一个明显的 import 顺序问题。

**影响：** 代码可读性差，且违反了 PEP8 规范。

#### ⚠️ 问题 4: Schemas 与 Models 混淆

```python
# schemas/models.py  ← 命名歧义
# 实际上是 Pydantic schemas，不是 DB models
```

**问题：** 文件名 `schemas/models.py` 与 `models/` 目录混淆。建议改为 `schemas/dto.py` 或 `schemas/responses.py`。

#### ⚠️ 问题 5: 前端数据流混乱

`learn/[videoId].js` 中：
```javascript
async function loadData() {
  const [v, n, g] = await Promise.all([
    getVideo(videoId),
    getNotes(videoId).catch(() => null),
    import('../../lib/api').then((m) => m.getGraph(videoId)).catch(() => null),
    //  ^^^^^^^^^ 动态 import，而非直接引用已导入的函数
  ]);
```

**问题：** 使用 `import('../../lib/api').then(...)` 动态 import，而 `getGraph` 已经在文件顶部通过 `../lib/api` 导入的其他函数中被一起导入了。这是多余的异步操作。

---

## 3. 命名规范检查

### 3.1 Python 命名

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 文件名 | ✅ | snake_case，规范 |
| 类名 | ✅ | PascalCase（Video, KnowledgeNode, LLMService） |
| 函数名 | ✅ | snake_case |
| 变量名 | ✅ | snake_case |
| 常量 | ✅ | UPPER_SNAKE（SYSTEM_PROMPTS） |
| Enum | ✅ | 使用 str enum |

### 3.2 JavaScript 命名

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 组件文件名 | ✅ | PascalCase（KnowledgeGraph.js, VideoUpload.js） |
| 函数名 | ✅ | camelCase |
| API 函数 | ✅ | 语义清晰 |

### 3.3 命名问题

| # | 文件 | 问题 |
|---|------|------|
| 1 | `backend/` 目录 | `__init__.py` 为空，但目录内有实际的 main.py、config.py 等模块。建议要么将其改为真正的 Package（在 `__init__.py` 中暴露接口），要么移除 `__init__.py`。 |
| 2 | `routers/qa.py` | tags `["qa"]` 但 prefix 是 `/api`，与其他 router 的 `/api/xxx` 不统一 |
| 3 | `schemas/models.py` | 文件名具有误导性 |
| 4 | `services/llm_service.py` | 与 `ai-services/llm_service.py` 同名不同功能，容易混淆 |

---

## 4. 错误处理完整性

### 🔴 严重问题

#### 4.1 `process_video_pipeline` 仅 catch 顶层异常，无分段恢复

```python
# routers/videos.py L197-207
except Exception as e:
    try:
        video.status = VideoStatus.FAILED
        video.error_message = str(e)
        await db.commit()
    except Exception:
        pass  # <-- 静默吞掉所有异常！
    raise
```

**问题：**
- 每个步骤失败后整个 Pipeline 中断，没有断点续传机制
- 内部的 `except Exception: pass` 是完全不可接受的——如果 commit 失败，video 状态停留在 Processing 无法恢复
- 没有对 ASR 失败、LLM 调用失败、关键帧提取失败做区分处理

#### 4.2 `llm_service.py` 异常吞 JSON 响应

```python
# backend/services/llm_service.py L76-82
except Exception as e:
    return json.dumps({
        "title": "示例标题",
        "summary": f"这是开发模式的模拟响应。API调用失败: {str(e)}。请配置正确的LLM_API_KEY。",
        ...
    })
```

**问题：** LLM 调用失败后返回模拟数据！调用方（`note_generator`、`graph_builder`）会收到格式正确的假数据而无感知，导致错误的笔记和图谱被存入数据库。

#### 4.3 `asr_service.py` 连接失败返回 mock 数据

```python
# backend/services/asr_service.py L39-42
except httpx.RequestError as e:
    return self._mock_transcribe(audio_path)  # <-- 返回假转录！
```

**问题：** Whisper 服务不可用时，不会抛出异常中断流程，而是返回 `"这是模拟语音识别结果"`。用户会看到虚假笔记，且无法发现。

#### 4.4 `note_generator.py` 和 `graph_builder.py` 的 fallback

```python
# services/note_generator.py L21-28
except (json.JSONDecodeError, KeyError, IndexError):
    return {
        "title": f"片段 {start_time:.0f}s",
        "summary": segment_text[:100],  # <-- 原文截断当摘要
        "keywords": [{"name": "知识点", ...}]  # <-- 占位数据
    }
```

**问题：** LLM 返回格式异常时，生成无意义的占位数据。应该向上传播错误，标记该 segment 需要重试。

### 📊 错误处理评分

| 文件 | 异常处理 | 评分 | 说明 |
|------|---------|------|------|
| routers/videos.py | 有但不足 | 5/10 | 仅顶层 try/except，无分段恢复 |
| routers/notes.py | 基本 | 6/10 | 404 和 400 处理完整 |
| routers/graph.py | 基本 | 6/10 | |
| routers/qa.py | 不足 | 4/10 | RAG 上下文构建无异常处理 |
| services/llm_service.py | **危险** | 2/10 | 异常时返回 mock 数据 |
| services/asr_service.py | **危险** | 2/10 | 异常时返回 mock 数据 |
| services/note_generator.py | 不足 | 3/10 | fallback 产生无意义数据 |
| services/graph_builder.py | 不足 | 3/10 | fallback 返回空列表 |
| services/video_processor.py | 基本 | 6/10 | FFmpeg 命令异常有抛出 |
| ai-services/whisper_service.py | 基本 | 6/10 | 有 try/except 返回 500 |
| ai-services/llm_service.py | 良好 | 7/10 | 分层处理，返回清晰错误 |

---

## 5. 架构红线验证

### 红线 #1: LLM Provider 必须抽象接口化

**判定：❌ 未满足**

```python
# backend/services/llm_service.py
class LLMService:
    async def chat(self, messages: list, temperature: float = 0.3) -> str:
        if self.mode == "api":
            return await self._call_api(messages, temperature)
        else:
            return await self._call_local(messages, temperature)
```

虽然存在 `LLMService` 类封装了 `api` 和 `local` 两种模式，但：

1. **API 模式直接请求 DeepSeek，绕过了 ai-services** — 架构上应该是 backend → ai-services（统一代理）→ DeepSeek/本地，但当前 backend 的 API 模式走 `self.api_base`（直接 DeepSeek）
2. **切换 provider 需要改环境变量**，而非通过接口注入 — 没有 `LLMProvider` 抽象基类
3. **测试困难** — 无法 mock LLMService，因为它内部直接 `self.client = httpx.AsyncClient()`

```python
# 建议的重构方向:
class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list, **kwargs) -> str: ...

class DeepSeekProvider(LLMProvider): ...
class QwenLocalProvider(LLMProvider): ...

# Factory
def get_llm_provider() -> LLMProvider:
    if settings.llm_mode == "api":
        return DeepSeekProvider(...)
    return QwenLocalProvider(...)
```

### 红线 #2: API 必须版本化

**判定：⚠️ 部分满足**

```python
# main.py
app = FastAPI(title="学知图谱 API", version="0.1.0")
```

- ✅ 有 version 字段
- ✅ 路由有 `/api/` 前缀
- ❌ 无 `/api/v1/` 版本路径
- ❌ 前后端未协商 API 版本

**影响：** 未来 API breaking change 时无法平滑过渡。

### 红线 #3: 所有异步任务必须有状态追踪

**判定：⚠️ 大部分满足，有缺口**

```python
# models/video.py
class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ASR_DONE = "asr_done"
    NOTES_DONE = "notes_done"
    GRAPH_DONE = "graph_done"
    COMPLETED = "completed"
    FAILED = "failed"
```

✅ 状态枚举完整  
✅ 前端有轮询机制（3秒间隔）  
❌ 无 WebSocket 实时推送（PRD 提到需要）  
❌ 失败后无重试机制  
❌ `progress` 值是硬编码的（30%, 50%, 70%, 90%），非动态计算  

### 红线 #4: ASR 输出必须保存原始结果

**判定：❌ 未满足**

```python
# routers/videos.py process_video_pipeline:
transcription = await asr_service.transcribe(audio_path)
# 直接使用 transcription，没有持久化原始 ASR 结果
```

Whisper 返回的完整转录（含每个 segment 的 start/end/text）仅在内存中使用后就丢弃了。后续修正、重跑、调优都需要原始数据。

---

## 6. 安全与隐私检查

| 检查项 | 状态 | 说明 |
|--------|------|------|
| CORS | ⚠️ | `allow_origins=["*"]` — 生产环境必须限制 |
| 用户认证 | ❌ | 硬编码 `user_id=1`，无认证体系 |
| 数据隔离 | ❌ | 无用户隔离，任何人可访问任何视频 |
| 文件上传校验 | ✅ | 文件扩展名白名单 |
| 文件大小限制 | ⚠️ | 配置有 `max_upload_size_mb=500` 但未在 API 层强制执行 |
| SQL 注入 | ✅ | 使用 SQLAlchemy ORM，参数化查询 |
| API Key 保护 | ✅ | 通过 `.env` 加载 |
| 输入校验 | ⚠️ | Pydantic 有基础校验，但 QA 接口无长度限制 |
| 速率限制 | ❌ | 未实现 |
| 文件加密 | ❌ | PRD 要求 AES-256，未实现 |

---

## 7. 代码可复用度评估

### 7.1 可复用组件

| 组件 | 可复用度 | 说明 |
|------|---------|------|
| `KnowledgeGraph.js` | 🟢 高 | 封装完整，支持动态 import，可独立使用 |
| `VideoUpload.js` | 🟢 高 | 支持上传+链接两种模式，拖拽/点击 |
| `notes_generator.py` | 🟡 中 | segment 级分析可复用，但耦合到 SYSTEM_PROMPTS |
| `graph_builder.py` | 🟡 中 | 依赖 llm_service 全局单例 |
| `video_processor.py` | 🟢 高 | FFmpeg 工具函数，纯函数，无副作用 |
| `asr_service.py` | 🟡 中 | mock fallback 影响可复用度 |
| `routers/videos.py` (pipeline) | 🔴 低 | 耦合在 router 内，不可独立调用 |
| `routers/qa.py` | 🔴 低 | RAG 检索方式简陋（关键词匹配），难以复用 |

### 7.2 重构优先级建议

| 优先级 | 文件 | 重构动作 |
|--------|------|---------|
| **P0** | `services/llm_service.py` | 剔除 mock fallback，异常应向上传播 |
| **P0** | `services/asr_service.py` | 剔除 mock fallback |
| **P0** | `routers/videos.py` | pipeline 迁移到 `services/video_pipeline.py` |
| **P1** | `services/llm_service.py` | 引入 `LLMProvider` 抽象基类 |
| **P1** | `schemas/models.py` | 重命名为 `schemas/dto.py` |
| **P1** | `routers/qa.py` | RAG 检索升级为向量检索 |
| **P2** | 全局 | API 路径加 `/v1/` 前缀 |
| **P2** | `config.py` | `max_upload_size_mb` 在 API 层强制校验 |

---

## 8. 数据库 Schema 评估

### 8.1 PRD 数据模型对应

| PRD 实体 | SQLAlchemy Model | 匹配度 | 问题 |
|----------|-----------------|--------|------|
| Video | ✅ `Video` | 90% | PRD 有 `notes` 字段，DB 用 Segment 表替代 |
| VideoSegment | ✅ `VideoSegment` | 85% | PRD 中 Segment 含 `keyframes[]`，DB 仅单 `keyframe_path` |
| KnowledgeNode | ✅ `KnowledgeNode` | 95% | |
| Relation | ✅ `Relation` | 95% | |
| User | ✅ `User` | 60% | PRD 有 `name`/`email`，DB 有 `username`/`email`/`display_name`，缺少密码字段（认证未实现） |
| Notes | ❌ | 0% | PRD 中笔记是独立实体，代码中嵌入 Segment 处理 |

### 8.2 Schema 问题

1. **Video.user_id 外键关联到 users 表** — 但 users 表无密码字段，无认证
2. **VideoSegment.embedding 存为 Text（JSON string）** — 不适合向量检索，后续 RAG 升级时需迁移
3. **缺少 `notes` 表** — PRD 中笔记是独立实体，当前与 Segment 强耦合
4. **KnowledgeNode.name 无索引** — 图谱搜索靠 `contains()` LIKE 查询，中等规模下会变慢

---

## 9. 测试覆盖

**当前代码库：0 测试文件。**

| 模块 | 测试 | 严重度 |
|------|------|--------|
| 所有模块 | ❌ 0 | 🔴 极高 |

**建议：**
- `services/video_processor.py` → 单元测试优先（纯函数，最易测）
- `schemas/models.py` → Pydantic 校验测试
- `services/graph_builder.py` → 集成测试（mock LLM 返回）
- `routers/*` → 用 FastAPI TestClient 写集成测试

---

## 10. 问题汇总与修复清单

### 🔴 Critical（阻塞投产）

| # | 问题 | 文件 | 修复时间 |
|---|------|------|---------|
| C1 | LLM 失败返回 mock 数据，导致虚假笔记入库 | `services/llm_service.py` L76-82 | 15min |
| C2 | ASR 失败返回 mock 转录 | `services/asr_service.py` L39-42 | 15min |
| C3 | Pipeline 内层 `except: pass` 静默丢异常 | `routers/videos.py` L203-204 | 10min |
| C4 | 无视频播放器集成（核心交互缺失） | `learn/[videoId].js` | 2-3天 |
| C5 | 无用户认证，`user_id=1` 硬编码 | 全局 | 2-3天 |

### 🟡 Major（影响质量）

| # | 问题 | 文件 |
|---|------|------|
| M1 | Pipeline 耦合在 router，不可复用 | `routers/videos.py` |
| M2 | LLM Provider 未抽象接口化（违反红线） | `services/llm_service.py` |
| M3 | API 无版本路径 `/api/v1/` | `main.py` |
| M4 | ASR 原始结果未持久化 | `routers/videos.py` |
| M5 | 错误处理无分段恢复/重试 | `routers/videos.py` |
| M6 | CORS `allow_origins=["*"]` | `main.py` |
| M7 | 前端动态 import 冗余 | `learn/[videoId].js` |
| M8 | 文件上传大小限制未在 API 层强制 | `routers/videos.py` |
| M9 | `schemas/models.py` 命名歧义 | `schemas/` |
| M10 | `asr_service.py` import 顺序错误 | `services/asr_service.py` |

### 🟢 Minor（建议改进）

| # | 问题 |
|---|------|
| m1 | KnowledgeNode.name 无索引 |
| m2 | 缺少 WebSocket 进度推送 |
| m3 | VideoSegment.embedding 存储方式不适用向量检索 |
| m4 | 缺少暗色/亮色主题切换 |
| m5 | 缺少无障碍设计（a11y） |
| m6 | 0 测试覆盖 |

---

## 11. 代码可复用度总评

| 维度 | 评估 |
|------|------|
| **可直接复用** | `video_processor.py`、`KnowledgeGraph.js`、`VideoUpload.js`、`schemas/models.py` |
| **需小幅修改后复用** | `asr_service.py`（删除 mock）、`note_generator.py`（解耦 prompt）、`graph_builder.py`（依赖注入） |
| **需重构后复用** | `routers/videos.py` pipeline 部分、`llm_service.py`（抽象接口） |
| **不建议复用** | `routers/qa.py`（RAG 太简陋，建议重写） |

**总体可复用度：60%** — 核心算法服务层设计良好，但 mock fallback 和耦合问题降低了可信度。

---

## 12. 给开发团队的行动建议

### 本周必须完成（Before MVP 继续开发）

1. **修复 C1-C3** — 移除所有 mock fallback，异常正确向上传播（2小时内可完成）
2. **集成视频播放器** — 选择 video.js 或 Plyr 等现成方案（而非从零开发）
3. **实现最小认证** — JWT + bcrypt，先做单用户模式（2-3天）
4. **Pipeline 迁移至 services/** — 解耦 router 与业务逻辑

### 本月建议

5. **LLM Provider 接口抽象** — 为 DeepSeek → Qwen 切换做准备
6. **API /v1/ 版本化** — 一次性加前缀，低风险
7. **补充 ASR 原始结果持久化** — 修改 pipeline 的一个步骤
8. **写 5-10 个核心测试** — 覆盖 video_processor + schemas

---

*Frank | 技术评审员 | 2026-04-29*
