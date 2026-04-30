import client from './client';
import type { Notes } from '@/types';

export async function getNotes(videoId: string): Promise<Notes> {
  const { data } = await client.get<Notes>(`/videos/${videoId}/notes`);
  return data;
}
