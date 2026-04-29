# T16 — ASR Pipeline 实现

> 作者：Charlie（后端工程师）
> 日期：2026-04-29
> 依赖：T14（后端框架与数据库设计）

---

## 产出概览

| 文件 | 说明 |
|------|------|
| `backend/models/video.py` | Video ORM 模型（含 progress 字段） |
| `backend/models/video_segment.py` | VideoSegment ORM 模型（ASR 转写结果） |
| `backend/models/knowledge.py` | KnowledgeNode + Relation 模型（为 T18 预留） |
| `backend/models/__init__.py` | 模型全量导出 |
| `backend/services/asr_service.py` | ASR Pipeline 核心服务（FFmpeg → VAD → Whisper → 后处理） |
| `backend/services/vad_service.py` | 语音活动检测（Silero VAD + 能量阈值回退） |
| `backend/utils/term_dictionary.py` | 专业术语词典（CS/ML/数学领域 50+ 术语） |
| `backend/tasks/asr_tasks.py` | Celery 异步任务（幂等 Pipeline 编排） |
| `backend/celery_app.py` | Celery 应用配置 |
| `backend/routers/asr.py` | ASR REST API + WebSocket 进度推送 |

---

## 1. Pipeline 架构

```
Video Upload → Celery Task "process_video_asr"
  │
  ├─ Stage 1: extract_audio (FFmpeg)
  │     video.mp4 → mono 16kHz WAV
  │     进度: 0% → 20%
  │
  ├─ Stage 2: VAD (Silero / Energy-based fallback)
  │     检测语音区域 → VADSegment[]
  │     进度: 20% → 30%
  │
  ├─ Stage 3: transcribe (Whisper HTTP → faster-whisper large-v3)
  │     音频 + 术语词典 → ASRSegment[]
  │     进度: 30% → 85%
  │
  └─ Stage 4: post_process
       术语注入 + VAD边界对齐 + 持久化
       进度: 85% → 100%
```

## 2. 关键设计决策

### 2.1 幂等性
每个阶段写入前检查前置条件：
```python
# 已存在 segments → 跳过 ASR
if not await _has_segments(db, video_id):
    await _run_asr_stage(...)
```

### 2.2 进度推送
双通道：
- **轮询**：`GET /api/v1/videos/{id}/asr/status` → `Video.progress`
- **实时**：`WS /ws/video/{id}/asr` → Redis pub/sub `video:{id}:progress`

### 2.3 VAD 策略
首选 Silero VAD（轻量 PyTorch），不可用时回退能量阈值检测。

### 2.4 术语词典注入
两种方式注入到 Whisper：
1. `initial_prompt`：将高频术语注入 system prompt
2. `hotwords`：将术语列表传入 faster-whisper 的 `hotwords` 参数
3. 后处理：对已知误转录进行规则替换

## 3. API 端点

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/videos/{id}/asr/transcribe` | 启动 ASR 转写 |
| GET | `/api/v1/videos/{id}/asr/status` | 查询转写进度 |
| GET | `/api/v1/videos/{id}/asr/segments` | 分段预览（含上下文） |
| PATCH | `/api/v1/videos/{id}/asr/segments/{sid}` | 手动修正分段 |
| WS | `/ws/video/{id}/asr` | WebSocket 实时进度 |

### 分段预览响应示例
```json
[
  {
    "segment": {
      "id": "uuid",
      "segment_index": 0,
      "start_time": 0.0,
      "end_time": 3.5,
      "text": "今天我们来讲一下深度学习的基础概念",
      "confidence": 0.95,
      "words": ["今天", "我们", ...],
      "is_manually_edited": false
    },
    "prev_text": null,
    "next_text": "深度学习是机器学习的一个分支"
  }
]
```

## 4. 部署配置

```yaml
# docker-compose.yml 新增服务
whisper:
  image: studyai/whisper:large-v3
  ports: ["8001:8001"]
  volumes:
    - whisper_models:/models
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

celery-worker:
  build: ./backend
  command: celery -A backend.celery_app worker -l info -c 2
  depends_on: [redis, postgres, whisper]
  environment:
    - WHISPER_SERVICE_URL=http://whisper:8001
```

## 5. 测试要点

- [ ] FFmpeg 提取音频：正常视频 / 无音轨视频 / 损坏文件
- [ ] VAD：纯语音 / 静音 / 带背景音乐
- [ ] Whisper 转写：中文 / 英文 / 中英混合
- [ ] 术语词典：注入 CS 术语后识别率提升验证
- [ ] 分段修正：文本修正时间戳保留 / 时间戳修正边界检查
- [ ] WebSocket：连接中断重连 / 多客户端同时订阅
