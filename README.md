# 🧠 学知图谱 (KnowGraph) — AI 视频知识图谱学习工具

> **把看视频的被动学习，变成构建知识体系的主动学习**

学知图谱是一个 AI 驱动的视频学习辅助工具。上传任意教学视频（B站、YouTube、本地文件等），自动完成语音识别、AI 笔记生成、知识图谱构建，帮你从视频中提炼出结构化的知识体系。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🎬 **视频导入** | 本地上传 + 视频链接导入 |
| 📝 **AI 笔记** | 自动生成带时间戳跳转的结构化笔记 |
| 🕸️ **知识图谱** | 自动提取知识点并建立关联关系，交互式可视化 |
| 🎯 **掌握度标记** | 标记知识点掌握程度，图谱颜色实时反映 |
| 🔍 **图谱搜索** | 搜索知识点，快速定位 |
| 💬 **AI 问答** | 基于视频内容的智能问答（RAG） |

---

## 🚀 快速开始

### 环境要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| Docker | 24+ | 24+ |
| GPU（可选） | 6GB 显存 | NVIDIA 4090 |
| 内存 | 8GB | 16GB+ |
| CPU | 4 核 | 8 核 |

### 一键 Docker 部署（推荐）

```bash
# 1. 进入部署目录
cd deployment

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key
# 推荐使用 DeepSeek API（百万 token ~1 元）

# 3. 启动核心服务（先不启动 GPU 容器）
docker compose up -d --build postgres redis backend frontend

# 4. 访问前端
open http://localhost:3000
```

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🌐 前端界面 | http://localhost:3000 | Web 应用 |
| 🔌 API 文档 | http://localhost:8000/docs | FastAPI Swagger |
| 🎙️ Whisper | http://localhost:8001/health | 语音识别服务（需 GPU） |
| 🤖 LLM | http://localhost:8002/health | AI 推理服务 |

### 手动运行（无 Docker）

```bash
# 后端（部署版）
cd deployment/backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 前端（独立运行）
cd frontend
npm install
npm run dev    # 开发模式，热重载
# 或 npm run build && npm start  # 生产模式
```

---

## ⚠️ 常见问题与踩坑记录

### Windows 环境

**Q: `cp` 命令不存在**
```bash
# Windows 用 copy 替代
copy .env.example .env
```

**Q: `.env.example` 文件不存在**
```bash
# 手动创建 .env 文件
notepad .env
# 粘贴以下内容：
# LLM_MODE=api
# LLM_API_KEY=sk-your-key
# LLM_API_BASE=https://api.deepseek.com
# LLM_MODEL=deepseek-chat
```

---

### Docker 网络问题（国内用户常见）

**Q: 拉取镜像时报错 `proxyconnect tcp: dial tcp 127.0.0.1:7897`**

Docker Desktop 配了代理但代理没开。解决方案：

```bash
# 临时清除代理环境变量
set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=localhost,127.0.0.1,.aliyuncs.com,.docker.io
```

**Q: 拉取镜像超时 / DNS 解析到境外 IP 被墙**
```
Error: failed to resolve reference "docker.io/library/redis:7-alpine"
     dial tcp 128.242.240.157:443: connectex: ... host has failed to respond
```

解决方式（任选一种）：

1. **打开代理软件**，然后在命令行设置：
   ```bash
   set HTTP_PROXY=http://127.0.0.1:7897
   set HTTPS_PROXY=http://127.0.0.1:7897
   ```

2. **手动拉取镜像**（代理模式下）：
   ```bash
   docker pull postgres:16-alpine
   docker pull redis:7-alpine
   docker pull nginx:1.25-alpine
   docker pull node:20-alpine
   docker pull python:3.11-slim
   ```

3. **在 Docker Desktop 设置中配置代理**：
   Settings → Resources → Proxies，填入 `http://127.0.0.1:7897`

**Q: 拉取大文件时报 EOF：**
```
Error: failed to copy: httpReadSeeker: failed open: EOF
```
网络不稳定，重新拉一次即可：
```bash
docker pull python:3.11-slim
```

---

### Docker 构建问题

**Q: `docker compose` 默认会构建所有服务，包括 GPU 容器**

比如 `docker compose up -d --build` 会尝试拉取 `nvidia/cuda` 镜像并构建 Whisper/LLM 服务，没有 GPU 时会失败。

**解决方案**：先只启动核心服务：
```bash
docker compose up -d --build postgres redis backend frontend
```

**Q: `npm ci` 报错（缺少 package-lock.json）**
```
The 'npm ci' command can only install with an existing package-lock.json
```

**解决方案**：修改 `deployment/frontend/Dockerfile`，将第 4 行的
```
RUN npm ci
```
改为：
```
RUN npm install
```

**Q: `backend` 依赖了 `whisper` 和 `llm` 容器**
```
target llm: failed to solve: failed to fetch oauth token
```

**解决方案**：修改 `deployment/docker-compose.yml`，在 `backend` 的 `depends_on` 中注释掉 whisper 和 llm：
```yaml
depends_on:
  postgres:
    condition: service_healthy
  redis:
    condition: service_healthy
  # whisper:
  #   condition: service_healthy
  # llm:
  #   condition: service_healthy
```

---

### 单卡 GPU 适配

Docker Compose 默认配置是为双 4090 设计的（Whisper #0，LLM #1-2）。如果你只有一张卡：

修改 `docker-compose.yml` 中 LLM 服务的 GPU 配置：
```yaml
llm:
  # ...
  environment:
    - NVIDIA_VISIBLE_DEVICES=0    # 改为 0，不是 1,2
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ["0"]     # 改为 "0"，不是 "1", "2"
            capabilities: [gpu]
```

---

### Docker version 警告

```
the attribute \`version\` is obsolete, it will be ignored
```
这是无害警告，Docker Compose V2 不再需要 `version` 字段。可以忽略或删除 `docker-compose.yml` 第一行的 `version: '3.8'`。

---

### 后端启动问题

部署版后端在 `deployment/backend/` 下有完整的 `main.py`，而项目根目录下的 `backend/` 是拆分为 `asr/`、`graph/`、`notes/` 三个模块的源码，**没有统一的入口文件**。如需手动运行后端，请使用 `deployment/backend/` 版本。

---

## 🏗️ 技术栈

| 层面 | 技术 |
|------|------|
| **前端** | Next.js 14 + React 18 + TypeScript + Tailwind CSS |
| **后端 API** | Python FastAPI + SQLAlchemy + SQLite/PostgreSQL |
| **图谱可视化** | vis-network (D3.js 力导向图) |
| **语音识别** | faster-whisper (large-v3)，GPU 加速 |
| **LLM** | DeepSeek API / Qwen 本地部署 |
| **部署** | Docker Compose + NVIDIA Container Toolkit |

## 📂 项目结构

```
-KGLA-/
├── deployment/              # 生产部署配置
│   ├── docker-compose.yml   # 服务编排
│   ├── .env.example         # 环境变量模板
│   ├── ai-services/         # GPU 推理服务（Whisper + LLM）
│   ├── backend/             # 部署版后端
│   ├── frontend/            # 部署版前端
│   ├── infra/               # Nginx + 监控
│   └── scripts/             # 部署脚本
├── backend/                 # 后端源码
│   ├── asr/                 # 语音识别模块
│   ├── graph/               # 图谱构建模块
│   └── notes/               # 笔记生成模块
├── frontend/                # 前端源码（Next.js App Router）
│   ├── app/                 # 页面（dashboard, learn, graph, history）
│   ├── components/          # UI 组件库 + 业务组件
│   ├── lib/                 # API 客户端 + Hooks
│   └── types/               # TypeScript 类型定义
├── docs/                    # 项目文档
└── README.md
```

## 🔧 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/videos/upload` | 上传视频文件 |
| POST | `/api/videos/link` | 导入视频链接 |
| GET | `/api/videos/` | 视频列表 |
| GET | `/api/videos/{id}` | 视频详情 |
| GET | `/api/graph/{video_id}` | 知识图谱数据 |
| PUT | `/api/graph/mastery` | 更新掌握度 |
| POST | `/api/qa` | AI 问答 |

完整 API 文档启动后访问 `http://localhost:8000/docs`。

## 🧠 AI Pipeline

```
用户上传视频
    ↓
ASR 语音识别 (Whisper large-v3)
    → 逐字稿 + 时间轴
    ↓
语义分段 (LLM)
    → 按知识点划分段落
    ↓
知识点提取 (LLM)
    → 概念/术语/公式等实体
    ↓
关系推断 (LLM)
    → 前置/包含/相似/因果等关系
    ↓
图谱构建 → 前端可视化
```

## 🏆 项目里程碑

- ✅ PRD 产品设计 & 技术评审 (8.3/10)
- ✅ 后端框架 & 数据库设计
- ✅ AI Pipeline (ASR + LLM + 图谱构建)
- ✅ 前端 4 页面 + 23 组件
- ✅ 集成测试 77/77 全绿
- ✅ Docker 部署方案 & 监控
- ✅ 代码审计通过
- 🟢 **当前：双 4090 部署测试**
- ⬜ Phase 2：体验完善（笔记编辑、学习仪表盘）
- ⬜ Phase 3：进阶功能（跨视频图谱、学习路径推荐）

---

## 📄 许可证

MIT
