import client from './client';
import type { QARequest, QAResponse } from '@/types';

export async function askQuestion(params: QARequest): Promise<QAResponse> {
  const { data } = await client.post<QAResponse>('/qa', params);
  return data;
}
