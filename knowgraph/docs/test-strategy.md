# 学知图谱 — 测试策略文档

**版本:** 1.0.0  
**日期:** 2026-04-29  
**负责人:** Dave (QA 工程师)

---

## 1. 测试哲学

> "没有测试覆盖的代码就是遗留代码"

本项目的测试策略遵循以下原则：
- **左移测试 (Shift Left):** 测试活动尽早介入，需求评审阶段即开始设计验收标准
- **金字塔模型:** 大量单元测试 + 适量集成测试 + 少量 E2E 测试
- **自动化优先:** 所有回归测试必须自动化，手动测试仅用于探索性和可用性测试
- **缺陷即用例:** 每个 Bug 修复必须附带自动化回归测试用例

---

## 2. 测试金字塔

### 2.1 后端测试 (Python)

```
工具栈: pytest + pytest-cov + pytest-asyncio + httpx
覆盖目标: ≥ 70% 行覆盖
```

#### 单元测试清单

| 模块 | 测试文件 | 预计用例 | 覆盖重点 |
|------|---------|---------|---------|
| 音频提取 | `test_audio_extraction.py` | 8 | FFmpeg 调用、采样率、声道、错误处理 |
| ASR 转录 | `test_asr_pipeline.py` | 14 | Whisper 结果结构、语言检测、性能约束、VAD |
| LLM 笔记 | `test_llm_pipeline.py` | 18 | 输出格式、幻觉检测、JSON Schema、Provider 切换 |
| 知识图谱 | `test_knowledge_graph.py` | 14 | 图构建、查询、序列化、边界条件 |
| 视频上传 | `test_video_upload.py` | 12 | 格式校验、文件大小、分片上传、状态追踪 |
| API 路由 | `test_api_routes.py` | 10 | 状态码、请求校验、认证、错误响应 |
| 数据库 | `test_db_models.py` | 8 | CRUD、迁移、约束、事务 |

### 2.2 前端测试 (TypeScript)

```
工具栈: Jest + ts-jest + Testing Library + MSW
覆盖目标: ≥ 70% 分支覆盖
```

| 模块 | 测试文件 | 预计用例 | 覆盖重点 |
|------|---------|---------|---------|
| 视频上传组件 | `UploadPage.test.tsx` | 8 | 拖拽、进度、错误、文件类型 |
| AI 笔记组件 | `NotesPanel.test.tsx` | 6 | 渲染、概念点击、时间戳跳转 |
| 知识图谱组件 | `KnowledgeGraph.test.tsx` | 8 | 渲染、交互、性能 |
| 图谱搜索 | `GraphSearch.test.tsx` | 5 | 搜索、高亮、空结果 |
| 状态管理 | `useVideoStore.test.ts` | 6 | 状态转换、异步操作 |
| API 层 | `api.test.ts` | 5 | 请求拦截、错误处理、重试 |

### 2.3 E2E 测试

```
工具栈: Playwright
浏览器: Chromium + Firefox + WebKit
设备: Desktop + iPad (9.7") + iPad Pro (12.9")
```

| 场景 | 用例数 | 优先级 |
|------|--------|--------|
| 视频上传全流程 | 5 | P0 |
| AI 笔记查看与交互 | 3 | P0 |
| 知识图谱操作 | 5 | P0 |
| 响应式布局 | 3 | P0 |
| 错误处理 | 4 | P0 |
| 跨浏览器冒烟 | 1 | P0 |

### 2.4 专门的 ASR WER 基准测试

见 `tests/wer/WER_TEST_DESIGN.md`。独立于常规测试流水线，在模型升级或配置变更时运行。

---

## 3. 测试环境与数据

### 3.1 环境管理

| 环境 | 触发条件 | 测试类型 |
|------|---------|---------|
| **Dev** | 本地开发 / PR | 单元 + 集成 |
| **CI (PR)** | 每次 Push | 单元 + 集成 + E2E 冒烟 |
| **CI (Main)** | Merge 到 main | 单元 + 集成 + 完整 E2E |
| **Staging** | 预发布 | 全量 E2E + 性能测试 |

### 3.2 测试数据管理

- **视频测试集:** 5-10 个标准测试视频（各学科、时长、语速）
- **ASR 黄金集:** 20 个样本 + 人工校对参考文本
- **Mock 数据:** 使用 factory-boy / faker 生成，避免硬编码
- **数据库:** 每个测试会话使用独立的测试数据库（Docker 容器）

---

## 4. CI/CD 集成

### 4.1 流水线阶段

```
PR Open / Push
    │
    ├── Stage 1: Lint & Type Check (~1min)
    │   ├── ESLint (frontend)
    │   ├── TypeScript strict check
    │   ├── Ruff (Python)
    │   └── mypy type check
    │
    ├── Stage 2: Unit Tests (~2min)
    │   ├── Backend pytest (parallel x4)
    │   ├── Frontend Jest
    │   └── Coverage Report
    │
    ├── Stage 3: Integration Tests (~3min)
    │   ├── Docker compose up (test DB + services)
    │   ├── API integration tests
    │   └── Docker compose down
    │
    └── Stage 4: E2E Smoke (~5min)  [PR only]
        ├── Playwright (Chromium)
        └── Core flow verification
```

### 4.2 合并到 Main 额外步骤

```
    ├── Stage 5: Full E2E Matrix (~15min)
    │   ├── Chromium / Firefox / WebKit
    │   └── iPad / iPad Pro
    │
    └── Stage 6: Performance Check (~10min)
        ├── ASR pipeline benchmark
        └── Frontend Lighthouse audit
```

---

## 5. 测试角色与职责

| 角色 | 职责 |
|------|------|
| **QA 工程师 (Dave)** | 测试框架搭建、质量验收标准制定、WER 基准测试、CI 配置、测试用例评审 |
| **后端工程师 (Charlie)** | ASR/LLM 管线单元测试编写、API 集成测试 |
| **前端工程师 (Alice)** | 组件单元测试、E2E 用例编写 |
| **DevOps (Ella)** | CI 流水线运维、测试环境管理 |

---

## 6. 测试运行命令速查

```bash
# Backend
cd backend
pytest tests/ -v --cov=. --cov-report=html        # 全部测试 + 覆盖率
pytest tests/ -m "not slow" -n auto                # 快速测试（并行）
pytest tests/ -m "asr" -v                          # 仅 ASR 测试
pytest tests/ -m "performance" -v                  # 性能测试

# Frontend
cd frontend
npm test                                           # 全部测试
npm run test:coverage                              # 覆盖率

# E2E
cd tests
npx playwright test                                # 全部 E2E
npx playwright test --project=chromium             # 仅 Chrome
npx playwright test --project=iPad                 # 仅 iPad

# WER Benchmark
cd tests/wer
python wer_benchmark.py init                       # 初始化测试清单
python wer_benchmark.py evaluate --model whisper-large-v3  # 运行评估
python wer_benchmark.py report                     # 生成报告
```

---

*Dave | QA 工程师 | 2026-04-29*
