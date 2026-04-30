# T27: 设计系统 + 通用组件 — 完成报告

## 概述

完成前端 Part2 设计系统与通用组件建设，为后续 T28 (视频上传+图谱组件) 提供完整的 UI 基础设施。

## 设计系统增强

### Tailwind 配置 (`tailwind.config.ts`)
- 完整 Primary 色阶 (50-900)
- 语义色 success/warning/error/info 各带 light/dark 变体
- 圆角/阴影/spacing 全量映射
- 动画系统: fade-in/out, slide-in, zoom-in-95, spin-slow, pulse-soft, shimmer
- 预设动画工具类
- `darkMode: 'class'` 暗色模式基础

### CSS 变量系统 (`globals.css`)
- 完整 Design Token (色板 / 圆角 / 阴影 / 字号 / spacing / z-index)
- Dark mode CSS 变量覆盖
- `prefers-reduced-motion` 全站支持
- 工具类: `container-responsive`, `skeleton-shimmer`, `skip-to-content`, `text-balance`, `scrollbar-hide`
- focus-visible / selection 统一样式

## 新增通用组件 (6个)

| 组件 | 文件 | 用途 |
|------|------|------|
| **FileUpload** | `components/ui/FileUpload.tsx` | 拖拽上传区 + 上传进度条，支持文件校验 (类型/大小/数量) |
| **Alert** | `components/ui/Alert.tsx` | 通知横幅，4 种变体 (info/success/warning/error)，可关闭 |
| **Table** | `components/ui/Table.tsx` | 通用数据表格，支持空态/加载态/行点击，泛型列定义 |
| **Pagination** | `components/ui/Pagination.tsx` | 分页组件，智能省略号，显示总数 |
| **Breadcrumb** | `components/ui/Breadcrumb.tsx` | 面包屑导航，支持 Link，aria 语义 |
| **Tag** | `components/ui/Tag.tsx` | 标签/芯片，9 色，可选 dot/移除，含知识点类型色映射 |

## 新增 Hooks

| Hook | 文件 | 用途 |
|------|------|------|
| **useMediaQuery** | `lib/hooks/useMediaQuery.ts` | 通用响应式媒体查询 |
| **useIsMobile** | 同上 | `!md` 断点判断 |
| **useIsTablet** | 同上 | `md && !lg` 断点判断 |
| **useIsDesktop** | 同上 | `>= lg` 断点判断 |

## 增强现有组件

- **Modal**: 新增 focus trap (Tab/Shift+Tab 循环)，backdrop blur，Escape 关闭
- **Table**: 加载态 skeleton rows，空态插画，键盘无障碍

## 组件清单 (共 23 个)

Button, Badge, Skeleton, ProgressBar, EmptyState, Input, Textarea, Select, Card, Modal, Toast, Tooltip, Tabs, DropdownMenu, Avatar, Spinner, Toggle, **FileUpload**, **Alert**, **Table**, **Pagination**, **Breadcrumb**, **Tag**

## TypeScript 编译

`npx tsc --noEmit` 零错误通过。
