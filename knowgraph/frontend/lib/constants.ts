/** API 基础地址（通过环境变量注入） */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

/** 轮询间隔（毫秒） */
export const POLLING_INTERVAL = 5000;

/** 视频处理最大轮询次数 */
export const MAX_POLL_ATTEMPTS = 120;

/** 图谱默认配置 */
export const GRAPH_DEFAULTS = {
  NODE_RADIUS_MIN: 8,
  NODE_RADIUS_MAX: 32,
  LINK_DISTANCE: 120,
  CHARGE_STRENGTH: -300,
  ZOOM_MIN: 0.3,
  ZOOM_MAX: 3,
} as const;

/** 路由路径 */
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  LEARN: (id: string) => `/learn/${id}`,
  GRAPH: (id: string) => `/graph/${id}`,
  HISTORY: '/history',
} as const;
