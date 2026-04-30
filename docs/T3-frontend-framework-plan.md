# T3 前端框架搭建方案

> 作者：Alice（前端工程师）  
> 日期：2026-04-29  
> 前提：等待 T1(Ella 基础设施) 解锁后启动  
> 预估工期：5 个工作日

---

## 一、目标

在现有 Pages Router 代码基础上，完成以下架构升级：

| 目标 | 当前状态 | 目标状态 |
|------|---------|---------|
| 路由方案 | Pages Router | **App Router**（渐进迁移） |
| 类型系统 | 100% .js | **100% .ts / .tsx** |
| 状态管理 | 零（各页面独立 fetch） | **React Query + Context + zustand** |
| 样式方案 | Tailwind utilities | **Tailwind + CSS Modules + Design Tokens** |
| 可访问性 | 零 | **A11y 基线（AA 级）** |
| 工程化 | 无 ESLint | **ESLint + Prettier + Husky** |

---

## 二、技术决策

### 2.1 路由器选型：App Router 渐进迁移

```
决策：MVP 保持 Pages Router，T3 开始搭建 App Router 骨架
策略：app/ 目录与 pages/ 目录共存（Next.js 14 支持双路由）
过程：
  Phase A → 搭建 app/layout.tsx + app/page.tsx（首页）
  Phase B → 迁移 app/learn/[id]/page.tsx（学习页）
  Phase C → 迁移 app/graph/[id]/page.tsx（图谱页）
  Phase D → 清理 pages/ 目录
```

### 2.2 状态管理分层

```
┌──────────────────────────────────────┐
│           Server State                │
│    @tanstack/react-query v5           │
│    — 视频列表、笔记、图谱数据          │
│    — 自动缓存/去重/重新验证            │
├──────────────────────────────────────┤
│           App State                   │
│    React Context (轻量)               │
│    — AuthContext: 当前用户             │
│    — VideoContext: 当前视频 + 播放状态 │
├──────────────────────────────────────┤
│           UI State                    │
│    zustand (按需)                     │
│    — UI 偏好: 图谱模式、侧栏展开       │
│    — 可序列化持久化                    │
└──────────────────────────────────────┘
```

**选型理由：**
- `react-query`（非 `swr`）：内置 mutation 管理、乐观更新、无限查询，对视频处理状态轮询场景天然支持
- `zustand`（非 `redux`）：体积小（<1KB），API 简洁，按需引入，不强制全局 Provider 嵌套
- Context 仅用于 Auth/Video 这类跨层级必需的场景

### 2.3 D3.js 图谱方案（T9 执行，T3 预留接口）

```ts
// T3 阶段定义接口，T9 阶段实现
interface GraphEngine {
  init(container: HTMLElement, options: GraphOptions): void;
  setData(nodes: KnowledgeNode[], relations: Relation[]): void;
  setMode(mode: 'cluster' | 'focus' | 'path', params?: ModeParams): void;
  highlightNode(id: string): void;
  zoomTo(id: string, scale: number): void;
  destroy(): void;
}
```

---

## 三、TypeScript 类型定义

### 3.1 核心领域模型

```ts
// types/domain.ts

/** 视频生命周期状态 */
export type VideoStatus =
  | 'uploaded'
  | 'processing'
  | 'asr_done'
  | 'notes_done'
  | 'graph_done'
  | 'completed'
  | 'failed';

/** 知识点类型 */
export type NodeType =
  | 'concept'   // 概念
  | 'term'      // 术语
  | 'formula'   // 公式
  | 'method'    // 方法
  | 'example'   // 例子
  | 'person'    // 人物
  | 'event';    // 事件

/** 掌握程度 */
export type MasteryLevel = 'not_learned' | 'learning' | 'mastered';

/** 关系类型 */
export type RelationType =
  | 'prerequisite'  // 前置知识
  | 'contains'      // 包含
  | 'similar'       // 相似
  | 'contrast'      // 对比
  | 'causal'        // 因果
  | 'sequence'      // 顺序
  | 'related';      // 相关

/** 视频 */
export interface Video {
  id: string;
  title: string;
  filename: string;
  duration: number;       // seconds
  source_url?: string;
  status: VideoStatus;
  user_id: string;
  thumbnail_url?: string;
  created_at: string;     // ISO 8601
  updated_at: string;
}

/** 笔记段落 */
export interface NoteSegment {
  id: string;
  segment_index: number;
  title: string;
  content: string;        // Markdown
  summary: string;
  start_time: number;
  end_time: number;
  keyframe_url?: string;
}

/** 笔记 */
export interface Notes {
  video_id: string;
  total_segments: number;
  segments: NoteSegment[];
}

/** 知识点节点 */
export interface KnowledgeNode {
  id: string;
  name: string;
  description: string;
  node_type: NodeType;
  importance: number;     // 0.0 - 1.0
  mastery: MasteryLevel;
  timestamp: number;      // seconds
  segment_index?: number;
  source_video_id: string;
}

/** 知识点关系 */
export interface Relation {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relation_type: RelationType;
  weight?: number;        // 0.0 - 1.0
}

/** 知识图谱 */
export interface KnowledgeGraph {
  video_id: string;
  nodes: KnowledgeNode[];
  relations: Relation[];
}
```

### 3.2 API 响应类型

```ts
// types/api.ts

import type { Video, Notes, KnowledgeGraph, KnowledgeNode, NoteSegment } from './domain';

/** 标准分页响应 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** 视频列表 */
export interface VideoListResponse {
  videos: Video[];
}

/** AI 问答 */
export interface QARequest {
  video_id: string;
  question: string;
}

export interface QAResponse {
  answer: string;
  sources: {
    segment_index: number;
    timestamp: number;
    content_preview: string;
  }[];
}

/** 节点搜索 */
export interface NodeSearchResult {
  nodes: KnowledgeNode[];
}

/** API 错误 */
export interface ApiError {
  detail: string;
  code?: string;
  status: number;
}
```

---

## 四、App Router 目录结构

```
frontend/
├── app/                          # App Router（新增）
│   ├── layout.tsx                # 根 Layout
│   ├── page.tsx                  # 首页 / 仪表盘
│   ├── error.tsx                 # 全局 Error Boundary
│   ├── not-found.tsx             # 404
│   ├── loading.tsx               # 全局 Loading
│   ├── (main)/                   # Route Group: 主布局
│   │   ├── layout.tsx            # Header + 内容区
│   │   ├── learn/
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # 学习页
│   │   │       ├── loading.tsx
│   │   │       └── error.tsx
│   │   ├── graph/
│   │   │   └── [id]/
│   │   │       ├── page.tsx      # 图谱页
│   │   │       └── loading.tsx
│   │   ├── history/
│   │   │   ├── page.tsx          # 学习记录
│   │   │   └── loading.tsx
│   │   └── dashboard/
│   │       └── page.tsx          # 学习仪表盘（新增 P1）
│   └── api/                      # Route Handlers (BFF 层)
│       └── ...
│
├── components/                   # 组件
│   ├── ui/                       # 通用 UI 组件
│   │   ├── Button.tsx
│   │   ├── Badge.tsx
│   │   ├── Skeleton.tsx
│   │   ├── ProgressBar.tsx
│   │   └── EmptyState.tsx
│   ├── video/                    # 视频相关
│   │   ├── VideoUpload.tsx
│   │   ├── VideoPlayer.tsx
│   │   ├── VideoCard.tsx
│   │   └── TimelineBar.tsx
│   ├── notes/                    # 笔记相关
│   │   ├── NoteCard.tsx
│   │   ├── NoteEditor.tsx
│   │   └── SegmentsList.tsx
│   ├── graph/                    # 图谱相关
│   │   ├── KnowledgeGraph.tsx    # d3-force 核心（T9）
│   │   ├── GraphControls.tsx
│   │   ├── NodeDetail.tsx
│   │   └── GraphSearch.tsx
│   └── layout/                   # 布局组件
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── TabBar.tsx
│
├── lib/                          # 工具库
│   ├── api/
│   │   ├── client.ts             # axios 实例
│   │   ├── videos.ts             # 视频 API
│   │   ├── notes.ts              # 笔记 API
│   │   ├── graph.ts              # 图谱 API
│   │   └── qa.ts                 # 问答 API
│   ├── hooks/                    # 自定义 Hooks
│   │   ├── useVideo.ts
│   │   ├── useNotes.ts
│   │   ├── useGraph.ts
│   │   ├── useVideoStatus.ts     # 轮询 Hook
│   │   └── useDebounce.ts
│   ├── utils/
│   │   ├── time.ts               # formatTime 等
│   │   └── cn.ts                 # clsx + tailwind-merge
│   └── constants.ts
│
├── stores/                       # zustand stores
│   └── ui-preferences.ts
│
├── providers/                    # React Context Providers
│   ├── AuthProvider.tsx
│   ├── QueryProvider.tsx
│   └── VideoProvider.tsx
│
├── types/                        # 类型定义
│   ├── domain.ts
│   └── api.ts
│
├── styles/
│   └── globals.css               # 全局样式 + Design Tokens
│
├── pages/                        # Pages Router（过渡期保留）
│   └── ...
│
├── tailwind.config.ts
├── tsconfig.json
├── next.config.ts
├── .eslintrc.json
├── .prettierrc
├── Dockerfile
└── package.json
```

---

## 五、组件树架构

### 5.1 顶层 Layout 层级

```
RootLayout (app/layout.tsx)
├── QueryProvider          ← @tanstack/react-query
│   └── AuthProvider       ← 用户认证上下文
│       └── VideoProvider  ← 当前视频上下文（仅 /learn/* 需要）
│           └── MainLayout (app/(main)/layout.tsx)
│               ├── Header
│               └── {children}
```

### 5.2 学习页组件树

```
app/(main)/learn/[id]/page.tsx
├── Head (metadata)
├── VideoPlayer              ← 视频播放器 + react-player
├── LeftPanel
│   ├── SegmentsList
│   │   └── NoteCard[]
│   │       ├── TimestampBadge
│   │       ├── NoteContent (Markdown render)
│   │       └── KeywordTags
│   └── NoteEditor (modal)
└── RightPanel
    ├── KnowledgeGraph       ← 图谱（保留 vis-network 过渡）
    └── NodeDetail (popover)
```

### 5.3 图谱页组件树

```
app/(main)/graph/[id]/page.tsx
├── Header (搜索 + 筛选)
│   ├── SearchInput
│   ├── MasteryFilter
│   └── GraphStats
├── KnowledgeGraph (全屏)
│   ├── GraphControls (缩放/模式切换)
│   └── Legend
└── SidePanel
    ├── NodeDetail
    ├── RelatedNodes
    └── MasteryToggler
```

---

## 六、API 层重构

### 6.1 新 API Client

```ts
// lib/api/client.ts
import axios, { type AxiosInstance } from 'axios';
import type { ApiError } from '@/types/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  // 从 AuthContext 注入 token，不再硬编码 user_id
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || '请求失败',
      code: error.response?.data?.code,
      status: error.response?.status || 500,
    };
    return Promise.reject(apiError);
  }
);
```

### 6.2 React Query Hooks（示例）

```ts
// lib/hooks/useVideo.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getVideo, getVideos, uploadVideo } from '@/lib/api/videos';
import type { Video } from '@/types/domain';

export function useVideos() {
  return useQuery<Video[]>({
    queryKey: ['videos'],
    queryFn: async () => {
      const res = await getVideos();
      return res.videos;
    },
    staleTime: 5_000, // 5秒内不出新请求
  });
}

export function useVideoStatus(videoId: string) {
  return useQuery({
    queryKey: ['video', videoId, 'status'],
    queryFn: () => getVideo(videoId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // 处理中才轮询，完成或失败后停止
      return status && !['completed', 'failed'].includes(status) ? 3000 : false;
    },
  });
}

export function useUploadVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadVideo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] });
    },
  });
}
```

---

## 七、可访问性基线（AA 级）

| 类别 | 实施项 | 优先级 |
|------|-------|:---:|
| 语义化 | 所有页面使用 `<main>`, `<nav>`, `<section>` 等语义标签 | P0 |
| ARIA | 图谱容器 `role="application"` + `aria-label` | P0 |
| ARIA | 上传区域 `role="button"` + 键盘事件绑定 | P0 |
| 键盘 | 图谱支持 Tab/方向键导航 + +/- 缩放 | P0 |
| 焦点 | 路由切换后焦点移到 `<main>` 或标题 | P0 |
| 焦点 | 可见的 `:focus-visible` 样式（2px primary ring） | P0 |
| 颜色 | 状态标记同时使用颜色+文字+图标，不全依赖颜色 | P1 |
| 颜色 | 所有颜色组合满足 WCAG AA 对比度（≥4.5:1） | P1 |
| 屏幕阅读器 | 图谱节点生成 `aria-live` 区域用于描述 | P1 |
| 屏幕阅读器 | 动态内容使用 `aria-live="polite"` | P1 |

---

## 八、工程化

### 8.1 新增 dependencies

```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.x",
    "zustand": "^4.x",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "@types/react": "^18.x",
    "@types/react-dom": "^18.x",
    "@types/d3": "^7.x",
    "eslint": "^8.x",
    "eslint-config-next": "^14.x",
    "@typescript-eslint/parser": "^7.x",
    "prettier": "^3.x",
    "prettier-plugin-tailwindcss": "^0.5.x"
  }
}
```

### 8.2 tsconfig.json 关键配置

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## 九、Design Tokens（增强）

```css
/* styles/globals.css 追加部分 */
:root {
  /* Spacing scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* Radius */
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1rem;
  --radius-xl: 1.5rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 400ms ease;
  --transition-spring: 500ms cubic-bezier(0.34, 1.56, 0.64, 1);

  /* Focus ring */
  --focus-ring: 0 0 0 3px rgba(12, 142, 224, 0.4);
}

/* Focus visible 统一处理 */
:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
```

---

## 十、实施步骤（5 天）

### Day 1：基础设施

- [ ] 初始化 TypeScript：`tsconfig.json`、`next-env.d.ts`
- [ ] 安装新依赖：react-query, zustand, clsx, tailwind-merge
- [ ] 创建 `types/domain.ts` + `types/api.ts`
- [ ] 创建 `lib/utils/cn.ts`（clsx + tailwind-merge 封装）
- [ ] 配置 ESLint + Prettier

### Day 2：状态管理层

- [ ] 实现 `lib/api/client.ts`（移除 `user_id` 硬编码）
- [ ] 拆分 API 模块：`videos.ts`, `notes.ts`, `graph.ts`, `qa.ts`
- [ ] 实现 React Query Hooks：`useVideos`, `useVideo`, `useVideoStatus`, `useNotes`, `useGraph`, `useDebounce`
- [ ] 实现 `providers/QueryProvider.tsx`

### Day 3：Layout 系统 + App Router 骨架

- [ ] 创建 `app/layout.tsx`（RootLayout）
- [ ] 创建 `app/(main)/layout.tsx`（Header + 内容区）
- [ ] 创建 `components/layout/Header.tsx`
- [ ] 实现 `props/loading.tsx`（全局骨架屏）
- [ ] 实现 `app/error.tsx` + `app/not-found.tsx`
- [ ] 迁移首页 `app/page.tsx`（使用 useVideos hook）
- [ ] 实现 `components/ui/Skeleton.tsx`, `EmptyState.tsx`, `Badge.tsx`

### Day 4：通用组件 + 可访问性

- [ ] `ProgressBar.tsx`
- [ ] `NoteCard.tsx`（从 learn page 提取，用 TypeScript 重写）
- [ ] `SegmentsList.tsx`（提取 + 虚拟化滚动）
- [ ] `VideoUpload.tsx` → 迁移为 `.tsx` + aria 属性 + 键盘事件
- [ ] 补充所有现有组件的 aria 标签
- [ ] 统一 `:focus-visible` 样式

### Day 5：集成验证

- [ ] 确保 `pages/` 路由仍然可用（向后兼容）
- [ ] 验证 `npm run build` 无 type errors
- [ ] 验证 Axios interceptor 流（auth token 注入）
- [ ] 验证 React Query 缓存/轮询正常工作
- [ ] 输出 T3 完成报告

---

## 十一、风险与依赖

| 风险 | 缓解措施 |
|------|---------|
| App Router + Pages Router 共存可能有路由冲突 | 先测路由优先级，用 Route Group 隔离 |
| vis-network → d3-force 迁移影响 T3 进度 | T3 不碰图谱，仅定义接口，T9 再实现 |
| TypeScript 类型定义与后端 API 不一致 | T3 先按 PRD 定义，联调时校正 |
| react-query 与现有 axios 冲突 | 两者互补不冲突，queryFn 内部调用 axios |

---

**T3 产出清单：**

| 文件 | 说明 |
|------|------|
| `types/domain.ts` | 核心领域模型类型定义 |
| `types/api.ts` | API 请求/响应类型 |
| `lib/api/client.ts` | 重构后的 API 客户端 |
| `lib/hooks/*.ts` | React Query Hooks |
| `providers/QueryProvider.tsx` | Query Provider |
| `app/layout.tsx` | 根 Layout |
| `app/(main)/layout.tsx` | 主布局 |
| `components/ui/*.tsx` | 通用 UI 组件库 |
| `tsconfig.json` | TypeScript 配置 |
| `.eslintrc.json` | ESLint 配置 |
| `.prettierrc` | Prettier 配置 |
