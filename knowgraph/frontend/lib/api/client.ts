import axios from 'axios';
import { API_BASE_URL } from '@/lib/constants';
import type { ApiError } from '@/types';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── 请求拦截：注入认证 Token ──
client.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('auth_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── 响应拦截：统一错误处理 ──
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const apiError: ApiError = {
        detail: error.response.data?.detail || '请求失败',
        code: error.response.data?.code,
        status: error.response.status,
      };
      return Promise.reject(apiError);
    }
    return Promise.reject({ detail: '网络错误', status: 0 } as ApiError);
  },
);

export default client;
