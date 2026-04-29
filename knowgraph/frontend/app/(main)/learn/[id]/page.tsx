'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useVideo } from '@/lib/hooks/useVideo';
import { useNotes } from '@/lib/hooks/useNotes';
import { useGraph } from '@/lib/hooks/useGraph';
import { VideoPlayer } from '@/components/video';
import {
  Skeleton, Tabs, Spinner, Alert, Badge, Tooltip, Input, Button,
  EmptyState,
} from '@/components/ui';
import { KnowledgeGraphViewer, GraphControls, NodeDetailPanel } from '@/components/graph';
import { askQuestion } from '@/lib/api/qa';
import { cn } from '@/lib/utils/cn';
import type { KnowledgeNode, NoteSegment, QAResponse } from '@/types';

// ── Note segment card ──
function NoteSegmentCard({
  segment,
  isActive,
  onClick,
}: {
  segment: NoteSegment;
  isActive: boolean;
  onClick: (time: number) => void;
}) {
  return (
    <button
      onClick={() => onClick(segment.start_time)}
      className={cn(
        'w-full rounded-lg border p-3 text-left transition-all',
        isActive
          ? 'border-indigo-300 bg-indigo-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2">
          {segment.title || `段落 ${segment.segment_index + 1}`}
        </h4>
        <Badge status="info" className="shrink-0">
          {fmtTime(segment.start_time)}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-gray-500 line-clamp-3 leading-relaxed">
        {segment.summary || segment.content}
      </p>
    </button>
  );
}

// ── Notes panel ──
function NotesPanel({
  segments,
  onSeekTo,
  currentVideoTime,
}: {
  segments: NoteSegment[];
  onSeekTo: (time: number) => void;
  currentVideoTime: number;
}) {
  if (segments.length === 0) {
    return (
      <EmptyState
        icon={<span className="text-3xl">📝</span>}
        title="暂无笔记"
        description="视频处理完成后，AI 将自动生成笔记"
      />
    );
  }

  // Find current segment index
  const currentIdx = segments.findIndex(
    (s) => currentVideoTime >= s.start_time && currentVideoTime < s.end_time,
  );

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 mb-2">
        共 {segments.length} 个段落 · 点击跳转到对应时间
      </p>
      <div className="max-h-[600px] space-y-2 overflow-y-auto pr-1">
        {segments.map((seg, i) => (
          <NoteSegmentCard
            key={seg.id}
            segment={seg}
            isActive={i === currentIdx}
            onClick={onSeekTo}
          />
        ))}
      </div>
    </div>
  );
}

// ── Q&A panel ──
function QAPanel({ videoId }: { videoId: string }) {
  const [question, setQuestion] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const [history, setHistory] = useState<{ q: string; a: QAResponse }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const handleAsk = useCallback(async () => {
    const q = question.trim();
    if (!q || isAsking) return;

    setIsAsking(true);
    setError(null);
    try {
      const res = await askQuestion({ video_id: videoId, question: q });
      setHistory((prev) => [...prev, { q, a: res }]);
      setQuestion('');
    } catch (err: any) {
      setError(err?.detail || '提问失败，请重试');
    } finally {
      setIsAsking(false);
    }
  }, [question, videoId, isAsking]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  // Auto scroll to bottom on new Q&A
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [history]);

  return (
    <div className="flex flex-col h-full">
      <div
        ref={listRef}
        className="flex-1 space-y-4 overflow-y-auto pr-1 min-h-[200px] max-h-[500px]"
      >
        {history.length === 0 && (
          <div className="flex items-center justify-center py-12 text-center">
            <div>
              <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
              </svg>
              <p className="mt-3 text-sm text-gray-500">对视频内容提问</p>
              <p className="text-xs text-gray-400">AI 将基于视频内容为你解答</p>
            </div>
          </div>
        )}

        {history.map((item, i) => (
          <div key={i} className="space-y-2">
            {/* User question */}
            <div className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-sm text-white">
                {item.q}
              </div>
            </div>

            {/* AI answer */}
            <div className="flex gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 text-xs text-white font-bold">
                AI
              </div>
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-700 leading-relaxed">
                <p>{item.a.answer}</p>

                {item.a.sources.length > 0 && (
                  <div className="mt-3 border-t border-gray-100 pt-2">
                    <p className="text-xs font-medium text-gray-500 mb-1">来源：</p>
                    <div className="flex flex-wrap gap-1.5">
                      {item.a.sources.map((src, j) => (
                        <Tooltip key={j} content={src.content_preview}>
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                            📍 {fmtTime(src.timestamp)}
                          </span>
                        </Tooltip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {isAsking && (
          <div className="flex gap-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 text-xs text-white font-bold">
              AI
            </div>
            <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-gray-200 bg-white px-4 py-2.5">
              <Spinner size="sm" />
              <span className="text-sm text-gray-400">思考中...</span>
            </div>
          </div>
        )}

        {error && (
          <Alert variant="error">{error}</Alert>
        )}
      </div>

      {/* Input */}
      <div className="mt-3 border-t border-gray-100 pt-3">
        <div className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你对视频内容的问题..."
            disabled={isAsking}
            className="flex-1"
          />
          <Button
            variant="primary"
            size="sm"
            onClick={handleAsk}
            disabled={!question.trim() || isAsking}
          >
            {isAsking ? (
              <Spinner size="sm" />
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            )}
            <span className="ml-1">提问</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Knowledge graph panel ──
function GraphPanel({
  videoId,
  onSeekTo,
}: {
  videoId: string;
  onSeekTo: (time: number) => void;
}) {
  const { data: graph, isLoading, error } = useGraph(videoId);
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [graphMode, setGraphMode] = useState<'cluster' | 'focus' | 'path'>('cluster');

  const nodes = graph?.nodes || [];
  const relations = graph?.relations || [];

  const handleNodeClick = (node: KnowledgeNode) => {
    setSelectedNode(node);
    if (node.timestamp > 0 && typeof node.timestamp === 'number') {
      // Also seek video to this node's timestamp
      onSeekTo(Number(node.timestamp));
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center py-12"><Spinner size="lg" /></div>;
  }

  if (error) {
    return (
      <Alert variant="error">
        加载知识图谱失败：{typeof error === 'object' && 'detail' in error ? (error as { detail: string }).detail : '未知错误'}
      </Alert>
    );
  }

  if (nodes.length === 0) {
    return (
      <EmptyState
        icon={<span className="text-3xl">🔗</span>}
        title="暂无知识图谱"
        description="视频处理完成后将自动生成知识图谱"
      />
    );
  }

  return (
    <div className="space-y-3">
      <GraphControls
        mode={graphMode}
        onModeChange={setGraphMode}
        nodeCount={nodes.length}
        relationCount={relations.length}
      />
      <div className="grid gap-3 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <KnowledgeGraphViewer
            nodes={nodes}
            relations={relations}
            mode={graphMode}
            onNodeClick={handleNodeClick}
            selectedNodeId={selectedNode?.id}
            className="h-[500px]"
          />
        </div>
        <div>
          <NodeDetailPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            className="h-[500px] overflow-y-auto"
          />
        </div>
      </div>
    </div>
  );
}

// ── Helpers ──
function fmtTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Main page ──
export default function LearnPage({ params }: { params: { id: string } }) {
  const videoId = params.id;
  const { data: video, isLoading: videoLoading, error: videoError } = useVideo(videoId);
  const { data: notes, isLoading: notesLoading } = useNotes(videoId);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [activePanel, setActivePanel] = useState('notes');

  const segments = notes?.segments || [];

  const handleSeekTo = useCallback((time: number) => {
    const v = videoRef.current;
    if (v) {
      v.currentTime = time;
      v.play().catch(() => {});
    }
  }, []);

  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  // ── Loading state ──
  if (videoLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="aspect-video w-full rounded-xl" />
        <Skeleton className="h-6 w-1/3" />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-3">
            <Skeleton className="h-32 rounded-xl" />
            <Skeleton className="h-32 rounded-xl" />
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (videoError) {
    return (
      <div className="space-y-6">
        <Alert variant="error">
          加载视频失败：{typeof videoError === 'object' && 'detail' in videoError ? (videoError as { detail: string }).detail : '未知错误'}
        </Alert>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="space-y-6">
        <EmptyState
          icon={<span className="text-4xl">🎥</span>}
          title="视频不存在"
          description="该视频可能已被删除或 ID 不正确"
        />
      </div>
    );
  }

  // ── Determine video source ──
  const videoSrc = video.source_url || '';

  const tabs = [
    {
      id: 'notes',
      label: `笔记${segments.length > 0 ? ` (${segments.length})` : ''}`,
      content: (
        <NotesPanel
          segments={segments}
          onSeekTo={handleSeekTo}
          currentVideoTime={currentTime}
        />
      ),
    },
    {
      id: 'qa',
      label: 'AI 问答',
      content: <QAPanel videoId={videoId} />,
    },
    {
      id: 'graph',
      label: `知识图谱${(video.status === 'completed') ? '' : ''}`,
      content: (
        <GraphPanel
          videoId={videoId}
          onSeekTo={handleSeekTo}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Video player section ── */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-gray-900 truncate">{video.title}</h1>
            <p className="mt-0.5 text-xs text-gray-500">
              {video.filename} · 状态：
              <Badge status={
                video.status === 'completed' ? 'success' :
                video.status === 'failed' ? 'error' : 'warning'
              }>
                {video.status === 'completed' ? '已完成' :
                 video.status === 'failed' ? '处理失败' :
                 video.status === 'processing' ? '处理中' :
                 video.status === 'uploaded' ? '已上传' : video.status}
              </Badge>
            </p>
          </div>
        </div>

        <VideoPlayer
          src={videoSrc}
          poster={video.thumbnail_url}
          title={video.title}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => {}}
          loadingOverlay={
            <div className="flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2 backdrop-blur-sm">
              <Spinner size="sm" />
              <span className="text-sm text-white">加载视频中...</span>
            </div>
          }
          emptyOverlay={
            <div className="text-center">
              <svg className="mx-auto h-16 w-16 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <p className="mt-3 text-sm text-gray-400">视频源不可用</p>
              <p className="text-xs text-gray-400">视频可能正在处理中</p>
            </div>
          }
          className="shadow-lg"
        />
      </section>

      {/* ── Content panels ── */}
      <section>
        <Tabs
          tabs={tabs}
          defaultTab="notes"
          onChange={setActivePanel}
        />
      </section>
    </div>
  );
}
