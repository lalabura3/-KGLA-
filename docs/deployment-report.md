# T22 生产部署与监控上线 — 部署报告

> **任务**: T22 生产部署与监控上线  
> **执行人**: Ella (p-mojhffoinvpwa9-worker7)  
> **日期**: 2026-04-29  
> **状态**: ✅ 部署完成

---

## 1. 部署架构总览

```
┌─ User ─────────────┐
│ 浏览器 → localhost │
└──────────────────┬─┘
                   │
            ┌──────▼──────┐
            │   Nginx:80   │  ← 反向代理 + WebSocket 支持
            └──────┬──────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
   ┌────▼───┐ ┌────▼───┐   ┌─┴────┐
   │ Frontend│ │Backend │   │ Docs │
   │ :3000   │ │ :8000  │   │/docs │
   └────────┘ └──┬─────┘   └──────┘
                  │
         ┌────────┼────────┐
         │        │        │
    ┌────▼──┐ ┌──▼───┐ ┌──▼────┐
    │Whisper│ │  LLM │ │Celery │
    │ GPU#0 │ │GPU#1-2│ │Worker │
    │ :8001 │ │ :8002 │ └───────┘
    └───────┘ └───────┘
         │              │
    ┌────▼──────┐ ┌────▼────┐
    │PostgreSQL │ │  Redis  │
    │ :5432     │ │ :6379   │
    └───────────┘ └─────────┘

=== Monitoring Stack ===
┌─ Prometheus ─┬─ Grafana ─┬─ GPU Exp ─┬─ Node Exp ┐
│  :9090       │  :3001    │  :9835    │  :9100    │
└──────────────┴───────────┴───────────┴───────────┘
```

## 2. 部署内容清单

### 2.1 核心栈（docker-compose.yml）

| 服务 | 角色 | 端口 | 依赖 | GPU |
|------|------|------|------|-----|
| `postgres` | PostgreSQL 16 数据库 | 5432 | — | — |
| `redis` | Redis 7 消息队列/缓存 | 6379 | — | — |
| `backend` | FastAPI 应用 (workers=2) | 8000 | postgres, redis, whisper, llm | — |
| `celery-worker` | Celery 异步任务处理 | — | postgres, redis | — |
| `whisper` | faster-whisper large-v3 ASR | 8001 | — | GPU#0 |
| `llm` | LLM 推理 (DeepSeek/本地) | 8002 | — | GPU#1-2 |
| `frontend` | Next.js 14 standalone | 3000 | backend | — |
| `nginx` | 反向代理 | 80 | frontend, backend | — |

### 2.2 AI 推理 GPU 分区

| GPU | 服务 | 模型 | 显存预估 |
|-----|------|------|---------|
| GPU#0 (设备0) | Whisper ASR | faster-whisper large-v3 | ~5-6 GB |
| GPU#1-2 (设备1,2) | LLM Service | INT4 量化模型 | ~8-10 GB |
| GPU#3 | 缓冲 | — | — |

总显存规划：72GB (4×4090)，实际使用 ~14-16GB，余量充足。

**降级能力**：
- ASR 服务支持 CPU 降级（无需 GPU）
- LLM 服务支持 API 模式（DeepSeek/OpenAI，绕过本地 GPU）

### 2.3 监控栈（monitoring/docker-compose.monitoring.yml）

| 服务 | 角色 | 端口 |
|------|------|------|
| `prometheus` | 指标收集，15s 采集间隔，30天保留 | 9090 |
| `grafana` | 可视化面板（含 nvidia-gpu-dashboard 插件） | 3001 |
| `nvidia-gpu-exporter` | GPU 使用率/显存/温度指标导出 | 9835 |
| `node-exporter` | 节点 CPU/内存/磁盘/网络指标 | 9100 |

### 2.4 Nginx 路由配置

| 路由 | 后端 | 说明 |
|------|------|------|
| `/` | frontend:3000 | 前端页面 + WebSocket Upgrade |
| `/api/` | backend:8000 | REST API（read_timeout 300s） |
| `/ws/` | backend:8000 | WebSocket 实时进度推送 |
| `/docs`, `/redoc` | backend:8000 | API 文档 |
| `client_max_body_size` | 500M | 支持大视频上传 |

### 2.5 部署及运维脚本

| 脚本 | 路径 | 说明 |
|------|------|------|
| `deploy.sh` | `scripts/deploy.sh` | 一键部署（环境检查→构建→启动→验证） |
| `gpu-check.sh` | `infra/gpu-check.sh` | GPU 环境诊断（驱动/显存/CUDA/NVIDIA Toolkit） |

### 2.6 环境配置

- `.env.example` — 完整的配置模板
- LLM 支持 API 模式（DeepSeek/OpenAI）和本地模式（双 4090）
- 所有配置可通过环境变量覆盖

## 3. 一键启动命令

```bash
# 1. 进入部署目录
cd deployment

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 3. 一键部署（含 GPU 检测和迁移执行）
bash scripts/deploy.sh

# 4. 验证
curl http://localhost/api/health

# 5. 查看日志
docker compose logs -f

# 6. 启动监控栈（可选）
docker compose -f infra/monitoring/docker-compose.monitoring.yml up -d

# 7. 访问
# 前端: http://localhost
# API:  http://localhost/api/v1
# Docs: http://localhost/docs
# Grafana: http://localhost:3001 (admin/admin)
```

## 4. 健康检查端点

| 端点 | 预期响应 | 说明 |
|------|---------|------|
| `GET /api/health` | `{"status":"ok","version":"0.1.0",...}` | 后端健康 |
| `GET /` | `{"message":"学知图谱 API",...}` | 根路由 |
| `GET /docs` | Swagger UI | API 文档 |
| `http://localhost:3000` | HTML 页面 | 前端页面 |
| `http://localhost:9090` | Prometheus UI | 监控（可选） |
| `http://localhost:3001` | Grafana Login | 仪表盘（可选） |

## 5. 部署产出文件

### 部署包结构

```
deployment/
├── docker-compose.yml                          # 核心 Docker 编排
├── .env.example                                # 环境变量模板
├── README.md                                   # 项目说明
├── PRD.md                                      # 产品需求文档
├── backend/                                    # 后端源码
│   ├── Dockerfile                              # 多阶段构建
│   ├── requirements.txt                        # Python 依赖
│   ├── main.py                                 # FastAPI 入口
│   ├── config.py                               # 配置管理
│   ├── database.py                             # 数据库引擎
│   ├── models/                                 # SQLAlchemy ORM
│   ├── routers/                                # FastAPI 路由
│   │   ├── videos.py                           # 视频上传/处理
│   │   ├── notes.py                            # AI 笔记
│   │   ├── graph.py                            # 知识图谱
│   │   └── qa.py                               # AI 问答
│   ├── services/                               # 业务逻辑层
│   │   ├── video_processor.py                  # 视频处理
│   │   ├── asr_service.py                      # ASR 转写
│   │   ├── note_generator.py                   # 笔记生成
│   │   ├── graph_builder.py                    # 图谱构建
│   │   └── llm_service.py                      # LLM 调用
│   └── schemas/                                # 数据模型
├── frontend/                                   # 前端源码
│   ├── Dockerfile                              # 多阶段构建 (standalone)
│   ├── package.json                            # Next.js 依赖
│   ├── pages/                                  # 页面组件
│   ├── components/                             # UI 组件
│   ├── lib/                                    # API 客户端
│   └── styles/                                 # 全局样式
├── ai-services/                                # AI 推理服务
│   ├── Dockerfile.whisper                      # Whisper ASR 容器
│   ├── Dockerfile.llm                          # LLM 推理容器
│   ├── whisper_service.py                      # ASR HTTP 服务
│   ├── llm_service.py                          # LLM HTTP 服务
│   └── start.sh                                # 启动脚本
├── infra/
│   ├── nginx/default.conf                      # Nginx 配置
│   ├── gpu-check.sh                            # GPU 诊断脚本
│   └── monitoring/
│       ├── docker-compose.monitoring.yml       # 监控栈编排
│       ├── prometheus.yml                      # Prometheus 配置
│       ├── grafana-datasources.yml              # Grafana 数据源
│       └── grafana-dashboards/                 # GPU Dashboard JSON
└── scripts/
    └── deploy.sh                               # 一键部署脚本
```

## 6. 注意事项

1. **LLM API Key**: 部署前必须在 `.env` 中填入 `LLM_API_KEY`，否则 LLM 服务无法工作
2. **GPU**: Whisper 和 LLM 服务通过 profile 门控，无 GPU 环境会自动跳过
3. **数据库迁移**: 后端启动时自动执行 `init_db()` 建表
4. **Nginx**: 默认不带 profile 启动时不启用 Nginx，需 `docker compose --profile full up -d`
5. **上传限制**: Nginx `client_max_body_size 500M`，对应 `MAX_UPLOAD_SIZE_MB` 环境变量
6. **日志**: 所有容器使用 json-file 驱动，保留最近 3 个文件（每个 10MB）

## 7. 部署状态概要

| 阶段 | 组件 | 状态 |
|------|------|------|
| ① 核心栈 | PostgreSQL + Redis + Backend + Frontend | ✅ 就绪 |
| ② GPU 推理 | Whisper (GPU#0) + LLM (GPU#1-2) + Celery | ✅ 配置文件就绪（按需启动） |
| ③ 监控运维 | Nginx + Prometheus + Grafana | ✅ 就绪 |

---

*Deployment by Ella (DevOps Engineer)*
