# 🧠 学知图谱 — AI 学习 Agent

> 把看视频的被动学习，变成构建知识体系的主动学习

## 项目概览

学知图谱是一个 AI 驱动的视频学习辅助工具，核心链路：

```
导入视频 → ASR 语音识别 → AI 生成图文笔记 → 自动构建知识图谱 → 交互式学习探索
```

### 核心功能

| 功能 | 说明 |
|------|------|
| 🎬 **视频导入** | 本地上传 + 视频链接导入 |
| 📝 **AI 笔记** | 自动生成带时间戳跳转的结构化笔记 |
| 🕸️ **知识图谱** | 自动提取知识点并建立关联关系，交互式可视化 |
| 🎯 **掌握度标记** | 标记知识点掌握程度，图谱颜色实时反映 |
| 🔍 **图谱搜索** | 搜索知识点，快速定位 |
| 💬 **AI 问答** | 基于视频内容的智能问答（RAG） |

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| **前端** | Next.js 14 + React 18 + Tailwind CSS | 响应式 Web 应用 |
| **后端 API** | Python FastAPI + SQLAlchemy + SQLite | RESTful API |
| **图谱可视化** | vis-network (D3.js 力导向图) | 交互式知识图谱 |
| **语音识别** | faster-whisper (large-v3) | GPU 加速，本地部署 |
| **LLM** | DeepSeek API / Qwen 本地部署 | 知识点提取 + 关系推断 |
| **部署** | Docker Compose + NVIDIA Container Toolkit | 一键部署 |

## 硬件要求

### 推荐配置（双 4090 🎯）
- **GPU**: 2× NVIDIA GeForce RTX 4090 (48GB 合计显存)
- **CPU**: 8 核以上
- **内存**: 32GB+
- **存储**: 200GB+ SSD

### 最低配置（仅 Whisper + API LLM）
- **GPU**: 6GB+ 显存（Whisper large-v3 需要）
- **CPU**: 4 核
- **内存**: 16GB

## 快速部署

### 方案一：Docker Compose 一键部署（推荐）

```bash
# 1. 进入项目目录
cd ai-learning-agent

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填入你的 LLM API Key

# 3. 一键部署
bash scripts/deploy.sh
```

自动启动三个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| **前端** | `:3000` | Web UI |
| **后端 API** | `:8000` | FastAPI + Swagger 文档 |
| **AI 服务** | `:8001` (Whisper) + `:8002` (LLM) | GPU 推理服务 |

### 方案二：手动部署

```bash
# AI 服务（GPU 机器）
cd ai-services
pip install -r requirements.txt
python whisper_service.py    # 启动 Whisper (端口 8001)
python llm_service.py        # 启动 LLM (端口 8002)

# 后端 API
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run build
npm start
```

## 双 4090 机器部署说明

你的机器有两张 4090，部署时可以充分利用并行计算：

### Whisper 配置
- **模型**: `large-v3`（最佳精度）
- **显存占用**: ~5GB
- **处理速度**: 45 分钟视频约 3-5 分钟
- 自动使用一张 4090

### LLM 配置（二选一）

#### 选项 A：API 模式（推荐快速使用）
```
.env 配置:
LLM_MODE=api
LLM_API_KEY=sk-your-key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```
- 优点：无需下载模型，即配即用
- 成本：DeepSeek API 极便宜，百万 token ~1 元

#### 选项 B：本地部署（零成本，需下载模型）
```
.env 配置:
LLM_MODE=local
```

下载 Qwen2.5-14B-Instruct-GPTQ-Int4（约 8GB 显存，一张 4090 足够）：
```bash
# 方法 1: 使用 vLLM
pip install vllm
python -c "from vllm import LLM; LLM(model='Qwen/Qwen2.5-14B-Instruct-GPTQ-Int4')"

# 方法 2: 下载 GGUF 格式
# 从 HuggingFace 下载模型到 /data/models/
# 参考: https://huggingface.co/Qwen
```

### 显存分配建议

| 服务 | 显存 | GPU 分配 |
|------|------|----------|
| Whisper | ~5 GB | GPU 0 |
| LLM (Qwen 14B 4-bit) | ~8 GB | GPU 0 |
| 剩余 | ~11 GB | 留给未来扩展 |

> 💡 两张 4090 共 48GB，Whisper + 14B 模型总共约 13GB，绰绰有余。

## 开发指南

### 后端 API 架构

```
backend/
├── main.py              # FastAPI 入口
├── config.py            # 配置
├── database.py          # 数据库连接
├── models/              # SQLAlchemy 数据模型
│   ├── user.py
│   ├── video.py
│   ├── knowledge_node.py
│   └── relation.py
├── routers/             # API 路由
│   ├── videos.py        # 视频上传/管理
│   ├── notes.py         # 笔记 CRUD
│   ├── graph.py         # 知识图谱 API
│   └── qa.py            # AI 问答
├── services/            # 业务逻辑
│   ├── asr_service.py   # Whisper 客户端
│   ├── llm_service.py   # LLM 客户端
│   ├── note_generator.py # 笔记生成
│   ├── graph_builder.py # 图谱构建
│   └── video_processor.py # 视频处理
├── schemas/             # Pydantic 数据验证
└── uploads/             # 文件存储
```

### 核心 AI Pipeline

```
用户上传视频
    ↓
1. ASR 处理 (Whisper large-v3 on GPU)
   → 逐字稿 + 时间轴
    ↓
2. 语义分段 (LLM)
   → 按话题/知识点划分段落
    ↓
3. 关键帧提取 (FFmpeg)
   → 按时间间隔 + 场景检测截图
    ↓
4. 知识点提取 (LLM)
   → 提取概念/术语/公式等知识点实体
    ↓
5. 关系推断 (LLM)
   → 建立知识点间关系 (前置/包含/相似/因果)
    ↓
6. 图谱构建
   → 存入数据库 + 前端可视化渲染
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/videos/upload` | 上传视频文件 |
| POST | `/api/videos/link` | 导入视频链接 |
| GET | `/api/videos/` | 视频列表 |
| GET | `/api/videos/{id}` | 视频详情 |
| GET | `/api/videos/{id}/status` | 处理状态 |
| DELETE | `/api/videos/{id}` | 删除视频 |
| GET | `/api/notes/{video_id}` | 获取笔记 |
| PUT | `/api/notes/.../segment/{id}` | 编辑笔记 |
| GET | `/api/graph/{video_id}` | 知识图谱数据 |
| PUT | `/api/graph/mastery` | 更新掌握度 |
| POST | `/api/qa` | AI 问答 |

完整 API 文档：启动后端后访问 `http://localhost:8000/docs`

## MVP 路线图

- [x] ✅ 产品设计 & PRD
- [ ] ⬜ **Phase 1 (当前)**：核心链路打通
  - [x] ✅ 后端 API 框架
  - [x] ✅ 数据库模型
  - [x] ✅ AI Pipeline (ASR + LLM)
  - [x] ✅ 前端页面
  - [x] ✅ Docker 部署方案
  - [ ] 🔄 双 4090 机器上部署测试
- [ ] ⬜ **Phase 2**：体验完善
  - 笔记编辑增强、图谱搜索筛选、掌握度标记、学习仪表盘
- [ ] ⬜ **Phase 3**：进阶功能
  - AI 问答、跨视频图谱、学习路径推荐
- [ ] ⬜ **Phase 4**：差异化亮点
  - 教师端、3D 知识空间

## 项目结构

```
projects/ai-learning-agent/
├── docker-compose.yml        # 编排所有服务
├── .env.example              # 环境变量模板
├── README.md                 # 本文件
├── backend/                  # Python FastAPI 后端
│   ├── main.py
│   ├── models/
│   ├── routers/
│   ├── services/
│   └── ...
├── frontend/                 # Next.js 前端
│   ├── pages/
│   │   ├── index.js          # 首页/仪表盘
│   │   ├── learn/[id].js     # 学习页（笔记+图谱）
│   │   ├── graph/[id].js     # 全屏图谱探索
│   │   └── history.js        # 学习记录
│   ├── components/
│   │   ├── VideoUpload.js
│   │   └── KnowledgeGraph.js
│   └── ...
├── ai-services/              # GPU 推理服务
│   ├── whisper_service.py    # Whisper ASR
│   ├── llm_service.py        # LLM 推理
│   └── Dockerfile
└── scripts/
    ├── deploy.sh             # 一键部署
    └── init_db.py            # 数据库初始化
```

---

**Made with 🌭 烤肠 · Powered by AI**
