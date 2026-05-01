import client from './client';
import type { KnowledgeGraph, NodeSearchResult } from '@/types';

export async function getGraph(videoId: string): Promise<KnowledgeGraph> {
  const { data } = await client.get<KnowledgeGraph>(`/videos/${videoId}/graph`);
  return data;
}

export async function searchNodes(
  videoId: string,
  query: string,
): Promise<NodeSearchResult> {
  const { data } = await client.get<NodeSearchResult>(`/videos/${videoId}/graph/search`, {
    params: { q: query },
  });
  return data;
}

export async function getNodeDetail(videoId: string, nodeId: string) {
  const { data } = await client.get(`/videos/${videoId}/graph/nodes/${nodeId}`);
  return data;
}

export async function updateMastery(
  videoId: string,
  nodeId: string,
  mastery: string,
) {
  const { data } = await client.patch(
    `/videos/${videoId}/graph/nodes/${nodeId}/mastery`,
    { mastery },
  );
  return data;
}
