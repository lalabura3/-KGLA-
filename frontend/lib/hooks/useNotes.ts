'use client';

import { useQuery } from '@tanstack/react-query';
import { getNotes } from '@/lib/api';

export function useNotes(videoId: string) {
  return useQuery({
    queryKey: ['notes', videoId],
    queryFn: () => getNotes(videoId),
    enabled: !!videoId,
    staleTime: 60_000,
  });
}
