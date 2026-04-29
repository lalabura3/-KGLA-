# 学知图谱 (KGLA - Knowledge Graph Learning Agent)

AI驱动的视频学习平台，自动将教学视频转写→生成笔记→构建知识图谱。

## 架构

```
knowgraph/
├── backend/          # FastAPI 后端
│   ├── asr/          # ASR Pipeline (Whisper + VAD)
│   ├── notes/        # AI笔记生成
│   └── graph/        # 知识图谱构建
├── frontend/         # Next.js 前端
├── tests/            # 集成测试 (pytest 77/77 ✅)
├── deployment/       # Docker Compose 三阶段部署
└── docs/             # 全量文档
```

## 快速开始

```bash
# 部署
cd deployment && bash deploy.sh

# 访问
# http://localhost:3000 (前端)
# http://localhost:8000/docs (API)
```

## 技术栈

- **后端**: FastAPI + PostgreSQL + Redis + Celery
- **ASR**: Whisper + Silero VAD
- **LLM**: DeepSeek API
- **前端**: Next.js 14 + React 18 + Tailwind CSS + d3-force
- **部署**: Docker Compose + NVIDIA Container Toolkit
- **CI**: GitHub Actions

## 任务产出

| 阶段 | 负责人 | 状态 |
|------|--------|------|
| T13-T18 后端全链路 | Charlie | ✅ |
| T15+T19+T26-T28 前端 | Alice | ✅ |
| T05+T21 测试 (77/77) | Dave | ✅ |
| T20 PRD验收 (8.3/10) | Bob | ✅ |
| T04 代码审计 | Frank | ✅ |
| T22 三阶段部署 | Ella | ✅ |
