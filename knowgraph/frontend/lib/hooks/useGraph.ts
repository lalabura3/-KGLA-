'use client';

import { useQuery } from '@tanstack/react-query';
import { getGraph, searchNodes, getNodeDetail } from '@/lib/api';

export function useGraph(videoId: string) {
  return useQuery({
    queryKey: ['graph', videoId],
    queryFn: () => getGraph(videoId),
    enabled: !!videoId,
    staleTime: 120_000,
  });
}

export function useNodeSearch(videoId: string, query: string) {
  return useQuery({
    queryKey: ['graph', 'search', videoId, query],
    queryFn: () => searchNodes(videoId, query),
    enabled: !!videoId && query.length > 0,
    staleTime: 10_000,
  });
}

export function useNodeDetail(videoId: string, nodeId: string) {
  return useQuery({
    queryKey: ['graph', 'node', videoId, nodeId],
    queryFn: () => getNodeDetail(videoId, nodeId),
    enabled: !!videoId && !!nodeId,
  });
}
