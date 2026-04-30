import type { Video, Notes, KnowledgeGraph, KnowledgeNode } from './domain';

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

export type { Video, Notes, KnowledgeGraph, KnowledgeNode };
