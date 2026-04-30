/** 设计系统 Token 常量 */

export const COLORS = {
  primary: {
    50: '#eef2ff',
    100: '#e0e7ff',
    200: '#c7d2fe',
    500: '#6366f1',
    600: '#4f46e5',
    700: '#4338ca',
  },
  success: '#16a34a',
  warning: '#f59e0b',
  error: '#dc2626',
  info: '#2563eb',
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    500: '#6b7280',
    700: '#374151',
    900: '#111827',
  },
} as const;

export const TYPOGRAPHY = {
  fontFamily: {
    sans: 'var(--font-geist-sans), system-ui, -apple-system, sans-serif',
    mono: 'var(--font-geist-mono), Menlo, monospace',
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },
} as const;

export const RADIUS = {
  sm: '0.375rem',
  md: '0.5rem',
  lg: '0.75rem',
  xl: '1rem',
  full: '9999px',
} as const;

export const SHADOW = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
} as const;

export const SPACING = {
  0: '0',
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
} as const;

/** 视频状态 → 中文 + Badge 颜色映射 */
export const VIDEO_STATUS_MAP = {
  uploaded: { label: '已上传', color: 'info' as const },
  processing: { label: '处理中', color: 'warning' as const },
  asr_done: { label: '语音识别完成', color: 'info' as const },
  notes_done: { label: '笔记生成完成', color: 'info' as const },
  graph_done: { label: '图谱生成完成', color: 'info' as const },
  completed: { label: '已完成', color: 'success' as const },
  failed: { label: '处理失败', color: 'error' as const },
} as const;

/** 知识点类型 → 颜色 */
export const NODE_COLORS = {
  concept: '#6366f1',
  term: '#06b6d4',
  formula: '#f59e0b',
  method: '#10b981',
  example: '#ec4899',
  person: '#8b5cf6',
  event: '#ef4444',
} as const;
