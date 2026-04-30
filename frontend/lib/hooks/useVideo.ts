'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getVideos, getVideo, uploadVideo, deleteVideo, getVideoHistory } from '@/lib/api';

export function useVideos() {
  return useQuery({
    queryKey: ['videos'],
    queryFn: getVideos,
    staleTime: 30_000,
  });
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: ['video', id],
    queryFn: () => getVideo(id),
    enabled: !!id,
    staleTime: 10_000,
  });
}

export function useUploadVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadVideo(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['videos'] }),
  });
}

export function useDeleteVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteVideo,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['videos'] }),
  });
}

export function useVideoHistory(page: number, pageSize = 20) {
  return useQuery({
    queryKey: ['videos', 'history', page, pageSize],
    queryFn: () => getVideoHistory(page, pageSize),
    placeholderData: (prev) => prev,
  });
}
