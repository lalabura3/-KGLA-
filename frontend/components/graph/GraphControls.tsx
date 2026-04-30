'use client';

import { cn } from '@/lib/utils/cn';

import type { GraphMode } from '@/stores/ui-preferences';

interface GraphControlsProps {
  mode: GraphMode;
  onModeChange: (mode: GraphMode) => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onFitView?: () => void;
  nodeCount: number;
  relationCount: number;
  className?: string;
}

const modeOptions: { value: GraphMode; label: string; icon: React.ReactNode }[] = [
  {
    value: 'cluster',
    label: '聚类',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="4" cy="6" r="1.5" stroke="currentColor" strokeWidth="1" />
        <circle cx="12" cy="5" r="1.5" stroke="currentColor" strokeWidth="1" />
        <circle cx="11" cy="11" r="1.5" stroke="currentColor" strokeWidth="1" />
      </svg>
    ),
  },
  {
    value: 'focus',
    label: '聚焦',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="4" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="8" cy="8" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    value: 'path',
    label: '路径',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M3 13L8 3L13 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export function GraphControls({
  mode,
  onModeChange,
  nodeCount,
  relationCount,
  className,
}: GraphControlsProps) {
  return (
    <div className={cn('flex items-center gap-4', className)}>
      {/* Mode selector */}
      <div className="flex rounded-lg border border-gray-200 bg-white p-0.5">
        {modeOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onModeChange(opt.value)}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              mode === opt.value
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100',
            )}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Stats */}
      <div className="flex gap-4 text-xs text-gray-500">
        <span>
          <strong className="text-gray-700">{nodeCount}</strong> 节点
        </span>
        <span>
          <strong className="text-gray-700">{relationCount}</strong> 关系
        </span>
      </div>
    </div>
  );
}
