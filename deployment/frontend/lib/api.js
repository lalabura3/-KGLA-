// API client for the backend
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败';
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

export default api;

// ─── Video APIs ───

export async function uploadVideo(file, title, onProgress) {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  formData.append('user_id', '1');

  const response = await api.post('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  });
  return response.data;
}

export async function importVideoLink(url, title) {
  const formData = new URLSearchParams();
  formData.append('url', url);
  if (title) formData.append('title', title);
  formData.append('user_id', '1');

  const response = await api.post('/videos/link', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response.data;
}

export async function getVideos() {
  const response = await api.get('/videos/', { params: { user_id: 1 } });
  return response.data;
}

export async function getVideo(id) {
  const response = await api.get(`/videos/${id}`);
  return response.data;
}

export async function getVideoStatus(id) {
  const response = await api.get(`/videos/${id}/status`);
  return response.data;
}

export async function deleteVideo(id) {
  const response = await api.delete(`/videos/${id}`);
  return response.data;
}

// ─── Notes APIs ───

export async function getNotes(videoId) {
  const response = await api.get(`/notes/${videoId}`);
  return response.data;
}

export async function updateSegment(videoId, segmentId, content) {
  const response = await api.put(`/notes/${videoId}/segment/${segmentId}`, {
    segment_id: segmentId,
    content,
  });
  return response.data;
}

// ─── Graph APIs ───

export async function getGraph(videoId) {
  const response = await api.get(`/graph/${videoId}`);
  return response.data;
}

export async function updateMastery(nodeId, mastery) {
  const response = await api.put('/graph/mastery', {
    node_id: nodeId,
    mastery,
  });
  return response.data;
}

export async function searchNodes(videoId, query) {
  const response = await api.get(`/graph/search/${videoId}`, {
    params: { query_str: query },
  });
  return response.data;
}

// ─── QA API ───

export async function askQuestion(videoId, question) {
  const response = await api.post('/qa', { video_id: videoId, question });
  return response.data;
}
