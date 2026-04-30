import client from './client';
import type { Video, VideoListResponse, PaginatedResponse } from '@/types';

export async function getVideos(): Promise<VideoListResponse> {
  const { data } = await client.get<VideoListResponse>('/videos');
  return data;
}

export async function getVideo(id: string): Promise<Video> {
  const { data } = await client.get<Video>(`/videos/${id}`);
  return data;
}

export async function uploadVideo(file: File, onProgress?: (pct: number) => void) {
  const form = new FormData();
  form.append('file', file);

  const { data } = await client.post<Video>('/videos/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    },
  });
  return data;
}

export async function deleteVideo(id: string): Promise<void> {
  await client.delete(`/videos/${id}`);
}

export async function getVideoHistory(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<Video>> {
  const { data } = await client.get<PaginatedResponse<Video>>('/videos/history', {
    params: { page, page_size: pageSize },
  });
  return data;
}
