'use client';

import { useEffect, useRef } from 'react';
import type { Video, VideoStatus } from '@/types';
import { POLLING_INTERVAL, MAX_POLL_ATTEMPTS } from '@/lib/constants';
import { getVideo } from '@/lib/api';

interface UseVideoStatusOptions {
  videoId: string;
  onStatusChange?: (status: VideoStatus) => void;
  onCompleted?: (video: Video) => void;
  onFailed?: (video: Video) => void;
}

/**
 * 轮询视频处理状态。
 * 当状态为 processing/asr_done/notes_done/graph_done 时持续轮询，
 * 直到 completed 或 failed，或达到最大轮询次数。
 */
export function useVideoStatus({
  videoId,
  onStatusChange,
  onCompleted,
  onFailed,
}: UseVideoStatusOptions) {
  const attemptsRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const callbacksRef = useRef({ onStatusChange, onCompleted, onFailed });
  callbacksRef.current = { onStatusChange, onCompleted, onFailed };

  useEffect(() => {
    if (!videoId) return;

    const poll = async () => {
      try {
        const video = await getVideo(videoId);
        callbacksRef.current.onStatusChange?.(video.status);

        if (video.status === 'completed') {
          stopPolling();
          callbacksRef.current.onCompleted?.(video);
        } else if (video.status === 'failed') {
          stopPolling();
          callbacksRef.current.onFailed?.(video);
        } else if (++attemptsRef.current >= MAX_POLL_ATTEMPTS) {
          stopPolling();
        }
      } catch {
        // 网络错误时不中断轮询
        if (++attemptsRef.current >= MAX_POLL_ATTEMPTS) stopPolling();
      }
    };

    const stopPolling = () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = undefined;
      }
    };

    // 立即执行第一次
    poll();
    timerRef.current = setInterval(poll, POLLING_INTERVAL);

    return stopPolling;
  }, [videoId]);
}
