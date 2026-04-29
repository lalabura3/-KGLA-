# T28: 视频上传 + 图谱组件 — 完成报告

## 概述

完成前端 Part3，包含完整视频上传流程与 D3.js 交互式知识图谱可视化。

## 视频上传功能

### 组件 (`components/video/`)

| 组件 | 文件 | 说明 |
|------|------|------|
| **VideoUploader** | `VideoUploader.tsx` | 上传流程封装：拖拽选文件 → 进度跟踪 → 自动跳转学习页。集成 FileUpload(拖拽区) + UploadProgress(进度条) + useUploadVideo(API mutation) |
| **VideoCard** | `VideoCard.tsx` | 视频卡片：缩略图/时长/状态 Badge/操作按钮。处理中态显示半透明遮罩+Spinner |
| **VideoGrid** | `VideoCard.tsx` | 响应式视频卡片网格容器 |

### 页面 (`app/(main)/dashboard/page.tsx`)
- 视频上传区 + 视频列表（含 Tab 筛选：全部/已完成/处理中/失败）
- 删除确认弹窗
- 加载态/空态/错误态全覆盖
- 集成 ToastProvider 消息提示

## 知识图谱可视化

### 组件 (`components/graph/`)

| 组件 | 文件 | 说明 |
|------|------|------|
| **KnowledgeGraphViewer** | `KnowledgeGraphViewer.tsx` | **D3.js 力导向图**：节点/关系可视化，颜色按知识类型、大小按重要性。支持拖拽/缩放/平移，节点悬停发光，选中高亮+关联边高亮+非选中节点淡化。图例自动生成。响应式 ResizeObserver |
| **GraphControls** | `GraphControls.tsx` | 图谱控制栏：聚类/聚焦/路径 三模式切换，节点/关系统计 |
| **NodeDetailPanel** | `NodeDetailPanel.tsx` | 节点详情侧面板：名称/类型Tag/掌握度Badge/重要性进度条/描述/时间戳/关联知识点列表 |

### 页面 (`app/(main)/graph/[id]/page.tsx`)
- 面包屑导航
- 图谱主画布 + 右侧详情面板 双栏布局
- 模式切换联动 Zustand store

## 技术要点

- **D3 v7**: forceSimulation + forceLink + forceManyBody + forceCollision + forceCenter
- **力导向参数**: 连接距离120px、电荷强度-300、碰撞半径自适应节点大小
- **交互**: d3-drag 拖拽节点、d3-zoom 缩放画布、点击选中节点
- **动画**: SVG filter 阴影+发光、CSS transition 状态切换
- **性能**: ResizeObserver 自适应容器、alphaTarget 拖拽优化
- **0 TypeScript 编译错误**

## 与 T27 联动

- 复用 FileUpload / UploadProgress / Alert / Toast / Breadcrumb / Badge / Tag / Spinner / Modal / Toggle / Tabs
- 设计 Token: NODE_COLORS, VIDEO_STATUS_MAP, GRAPH_DEFAULTS
- Types: Video, KnowledgeNode, Relation, NodeType, MasteryLevel
- API Hooks: useVideos, useUploadVideo, useDeleteVideo, useGraph
- Store: useUIPreferences (graphMode)

## 完整前端文件清单

### 新增 (9 files)
- `components/video/VideoCard.tsx`
- `components/video/VideoUploader.tsx`
- `components/video/index.ts`
- `components/graph/KnowledgeGraphViewer.tsx`
- `components/graph/GraphControls.tsx`
- `components/graph/NodeDetailPanel.tsx`
- `components/graph/index.ts`
- `app/(main)/dashboard/page.tsx`
- `app/(main)/graph/[id]/page.tsx`
