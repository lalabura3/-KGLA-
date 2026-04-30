'use client';

import { cn } from '@/lib/utils/cn';
import { Badge, Tag } from '@/components/ui';
import { NODE_COLORS } from '@/lib/design-tokens';
import { nodeTypeColor } from '@/components/ui/Tag';
import type { KnowledgeNode, MasteryLevel } from '@/types';

const masteryLabels: Record<MasteryLevel, { label: string; color: 'success' | 'warning' | 'neutral' }> = {
  mastered: { label: '已掌握', color: 'success' },
  learning: { label: '学习中', color: 'warning' },
  not_learned: { label: '未学习', color: 'neutral' },
};

interface NodeDetailPanelProps {
  node: KnowledgeNode | null;
  onClose?: () => void;
  relatedNodes?: { id: string; name: string; relation: string }[];
  className?: string;
}

export function NodeDetailPanel({ node, onClose, relatedNodes = [], className }: NodeDetailPanelProps) {
  if (!node) {
    return (
      <div className={cn('rounded-xl border border-dashed border-gray-200 bg-gray-50 p-6 text-center', className)}>
        <p className="text-sm text-gray-400">点击节点查看详情</p>
      </div>
    );
  }

  const color = NODE_COLORS[node.node_type] || '#6366f1';
  const mastery = masteryLabels[node.mastery] || masteryLabels.not_learned;

  return (
    <div className={cn('rounded-xl border border-gray-200 bg-white', className)}>
      {/* Header */}
      <div className="flex items-start justify-between border-b border-gray-100 px-5 py-4">
        <div className="flex items-center gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-white text-sm font-bold"
            style={{ background: color }}
          >
            {node.name[0]}
          </span>
          <div>
            <h3 className="font-semibold text-gray-900">{node.name}</h3>
            <div className="mt-1 flex items-center gap-2">
              <Tag color={nodeTypeColor[node.node_type] || 'gray'} size="sm" dot>
                {node.node_type}
              </Tag>
              <Badge status={mastery.color}>{mastery.label}</Badge>
              <span className="text-xs text-gray-400">
                重要性 {node.importance}/10
              </span>
            </div>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100" aria-label="关闭">
            <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        )}
      </div>

      {/* Description */}
      <div className="px-5 py-4">
        <p className="text-sm text-gray-600 leading-relaxed">{node.description}</p>

        {/* Progress bar for importance */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>重要性</span>
            <span>{node.importance}/10</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${(node.importance / 10) * 100}%`,
                background: color,
              }}
            />
          </div>
        </div>

        {/* Time info */}
        {node.timestamp > 0 && (
          <p className="mt-3 text-xs text-gray-400">
            📍 视频时间 {formatTimestamp(node.timestamp)}
            {node.segment_index !== undefined && ` · 第 ${node.segment_index + 1} 段`}
          </p>
        )}
      </div>

      {/* Related nodes */}
      {relatedNodes.length > 0 && (
        <div className="border-t border-gray-100 px-5 py-4">
          <h4 className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            相关知识点
          </h4>
          <div className="space-y-1.5">
            {relatedNodes.map((rn) => (
              <div
                key={rn.id}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-gray-50"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-gray-300" />
                <span className="text-gray-700">{rn.name}</span>
                <span className="ml-auto text-xs text-gray-400">{rn.relation}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
