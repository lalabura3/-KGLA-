'use client';

import { cn } from '@/lib/utils/cn';
import { Badge, Button, ProgressBar, Spinner, Tooltip } from '@/components/ui';
import { VIDEO_STATUS_MAP } from '@/lib/design-tokens';
import type { Video } from '@/types';

interface VideoCardProps {
  video: Video;
  onViewGraph?: () => void;
  onViewNotes?: () => void;
  onDelete?: () => void;
  className?: string;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const isProcessing = (status: string) =>
  ['uploaded', 'processing', 'asr_done', 'notes_done', 'graph_done'].includes(status);

export function VideoCard({ video, onViewGraph, onViewNotes, onDelete, className }: VideoCardProps) {
  const statusInfo = VIDEO_STATUS_MAP[video.status] || { label: video.status, color: 'neutral' as const };
  const processing = isProcessing(video.status);

  return (
    <div
      className={cn(
        'group rounded-xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md',
        className,
      )}
    >
      {/* Thumbnail area */}
      <div className="relative aspect-video overflow-hidden rounded-t-xl bg-gradient-to-br from-indigo-100 to-purple-100">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <svg className="h-12 w-12 text-indigo-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
            </svg>
          </div>
        )}

        {/* Duration badge */}
        {video.duration > 0 && (
          <span className="absolute bottom-2 right-2 rounded bg-black/70 px-1.5 py-0.5 text-xs text-white font-mono">
            {formatDuration(video.duration)}
          </span>
        )}

        {/* Processing overlay */}
        {processing && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[1px]">
            <span className="rounded-full bg-white/90 px-3 py-1.5 text-sm font-medium text-indigo-600 flex items-center gap-2">
              <Spinner size="sm" />
              处理中
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <Tooltip content={video.title}>
            <h3 className="font-medium text-gray-900 truncate">{video.title}</h3>
          </Tooltip>
          <Badge status={statusInfo.color as 'success' | 'warning' | 'error' | 'info'}>
            {statusInfo.label}
          </Badge>
        </div>

        <p className="mt-1 text-xs text-gray-500">
          {video.filename} · {formatDate(video.created_at)}
        </p>

        {/* Progress for processing */}
        {processing && (
          <ProgressBar
            value={0}
            max={100}
            className="mt-3"
            label="进度"
          />
        )}

        {/* Actions */}
        <div className="mt-3 flex gap-2">
          {video.status === 'completed' && (
            <>
              <Button variant="primary" size="sm" onClick={onViewGraph}>
                查看图谱
              </Button>
              <Button variant="outline" size="sm" onClick={onViewNotes}>
                查看笔记
              </Button>
            </>
          )}
          {onDelete && (
            <Button variant="ghost" size="sm" className="ml-auto text-gray-400 hover:text-red-600" onClick={onDelete}>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/** Video card grid wrapper */
export function VideoGrid({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('grid gap-6 sm:grid-cols-2 lg:grid-cols-3', className)}>
      {children}
    </div>
  );
}
