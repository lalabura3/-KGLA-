'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useVideoHistory } from '@/lib/hooks/useVideo';
import { VideoCard, VideoGrid } from '@/components/video';
import { Input, Pagination, Spinner, Alert, EmptyState } from '@/components/ui';
import { ROUTES } from '@/lib/constants';
import { useDebounce } from '@/lib/hooks/useDebounce';
import type { Video } from '@/types';

const PAGE_SIZE = 12;

export default function HistoryPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [searchText, setSearchText] = useState('');
  const debouncedSearch = useDebounce(searchText, 300);

  const { data, isLoading, error } = useVideoHistory(page, PAGE_SIZE);

  // ── Filter by search locally (client-side since API doesn't support search param) ──
  const allItems = data?.items || [];
  const total = data?.total || 0;

  const filteredItems = debouncedSearch
    ? allItems.filter(
        (v) =>
          v.title.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
          v.filename.toLowerCase().includes(debouncedSearch.toLowerCase()),
      )
    : allItems;

  const handleViewGraph = useCallback(
    (video: Video) => router.push(ROUTES.GRAPH(video.id)),
    [router],
  );

  const handleViewNotes = useCallback(
    (video: Video) => router.push(ROUTES.LEARN(video.id)),
    [router],
  );

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Page header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">学习历史</h1>
        <p className="mt-1 text-sm text-gray-500">查看你所有上传过的视频和处理记录</p>
      </div>

      {/* ── Search bar ── */}
      <div className="relative max-w-md">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>
        <Input
          value={searchText}
          onChange={(e) => {
            setSearchText(e.target.value);
            setPage(1);
          }}
          placeholder="搜索视频标题或文件名..."
          className="pl-10"
          aria-label="搜索学习记录"
        />
      </div>

      {/* ── Content ── */}
      {error ? (
        <Alert variant="error">
          加载历史记录失败：{typeof error === 'object' && 'detail' in error ? (error as { detail: string }).detail : '未知错误'}
        </Alert>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : allItems.length === 0 ? (
        <EmptyState
          icon={<span className="text-4xl">📋</span>}
          title="暂无学习记录"
          description="上传视频开始学习后，你的学习记录会显示在这里"
        />
      ) : debouncedSearch && filteredItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <svg className="h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <h3 className="mt-4 text-lg font-semibold text-gray-700">未找到匹配结果</h3>
          <p className="mt-1 text-sm text-gray-500">
            未搜索到「{debouncedSearch}」，请尝试其他关键词
          </p>
        </div>
      ) : (
        <>
          {/* ── Video grid ── */}
          <VideoGrid>
            {filteredItems.map((video) => (
              <VideoCard
                key={video.id}
                video={video}
                onViewGraph={() => handleViewGraph(video)}
                onViewNotes={() => handleViewNotes(video)}
              />
            ))}
          </VideoGrid>

          {/* ── Pagination ── */}
          <Pagination
            current={page}
            total={total}
            pageSize={PAGE_SIZE}
            onChange={handlePageChange}
            className="pt-2"
          />
        </>
      )}
    </div>
  );
}
