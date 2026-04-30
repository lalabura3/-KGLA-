'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useVideos, useDeleteVideo } from '@/lib/hooks/useVideo';
import { VideoCard, VideoGrid, VideoUploader } from '@/components/video';
import { Tabs, Modal, Spinner, Alert, ToastProvider } from '@/components/ui';
import { ROUTES } from '@/lib/constants';
import type { Video } from '@/types';

export default function DashboardPage() {
  const router = useRouter();
  const { data, isLoading, error } = useVideos();
  const deleteVideo = useDeleteVideo();
  const [deleteTarget, setDeleteTarget] = useState<Video | null>(null);
  const [activeTab, setActiveTab] = useState('all');

  const videos = data?.videos || [];

  const handleViewGraph = (video: Video) => {
    router.push(ROUTES.GRAPH(video.id));
  };

  const handleViewNotes = (video: Video) => {
    router.push(ROUTES.LEARN(video.id));
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    await deleteVideo.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  const filteredVideos = activeTab === 'all'
    ? videos
    : videos.filter((v) => v.status === activeTab);

  const tabs = [
    { id: 'all', label: `全部 (${videos.length})`, content: null },
    { id: 'completed', label: '已完成', content: null },
    { id: 'processing', label: '处理中', content: null },
    { id: 'failed', label: '失败', content: null },
  ];

  return (
    <ToastProvider>
      <div className="space-y-8">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">仪表盘</h1>
          <p className="mt-1 text-sm text-gray-500">上传视频并管理你的学习内容</p>
        </div>

        {/* Upload Section */}
        <section>
          <h2 className="mb-3 text-lg font-semibold text-gray-800">上传新视频</h2>
          <VideoUploader />
        </section>

        {/* Video list */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">视频列表</h2>
          </div>

          {error ? (
            <Alert variant="error">
              加载视频列表失败：{typeof error === 'object' && 'detail' in error ? (error as { detail: string }).detail : '未知错误'}
            </Alert>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Spinner size="lg" />
            </div>
          ) : videos.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 py-16">
              <span className="text-4xl">📂</span>
              <h3 className="mt-3 text-lg font-semibold text-gray-700">暂无视频</h3>
              <p className="mt-1 text-sm text-gray-500">上传你的第一个视频开始学习吧</p>
            </div>
          ) : (
            <Tabs
              tabs={tabs.map((t) => ({
                ...t,
                content: (
                  <VideoGrid key={t.id}>
                    {filteredVideos.map((video) => (
                      <VideoCard
                        key={video.id}
                        video={video}
                        onViewGraph={() => handleViewGraph(video)}
                        onViewNotes={() => handleViewNotes(video)}
                        onDelete={() => setDeleteTarget(video)}
                      />
                    ))}
                    {filteredVideos.length === 0 && (
                      <div className="col-span-full py-8 text-center text-gray-400">
                        该分类下暂无视频
                      </div>
                    )}
                  </VideoGrid>
                ),
              }))}
              defaultTab="all"
            />
          )}
        </section>

        {/* Delete confirmation modal */}
        <Modal
          open={!!deleteTarget}
          onClose={() => setDeleteTarget(null)}
          title="确认删除"
          size="sm"
        >
          <p className="text-sm text-gray-600">
            确定要删除视频「{deleteTarget?.title}」吗？此操作不可撤销。
          </p>
          <div className="mt-4 flex justify-end gap-3">
            <button
              onClick={() => setDeleteTarget(null)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleDeleteConfirm}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              disabled={deleteVideo.isPending}
            >
              {deleteVideo.isPending ? '删除中...' : '确认删除'}
            </button>
          </div>
        </Modal>
      </div>
    </ToastProvider>
  );
}
