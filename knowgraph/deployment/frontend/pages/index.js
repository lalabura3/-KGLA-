import { useState, useEffect } from 'react';
import Head from 'next/head';
import VideoUpload from '../components/VideoUpload';
import { getVideos, getVideoStatus } from '../lib/api';
import Link from 'next/link';

export default function Home() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [pollingIds, setPollingIds] = useState(new Set());

  // Load videos
  useEffect(() => {
    loadVideos();
  }, []);

  // Poll processing status
  useEffect(() => {
    if (pollingIds.size === 0) return;
    const interval = setInterval(async () => {
      const newPolling = new Set(pollingIds);
      for (const id of pollingIds) {
        try {
          const status = await getVideoStatus(id);
          if (status.status === 'completed' || status.status === 'failed') {
            newPolling.delete(id);
          }
        } catch (e) {}
      }
      setPollingIds(newPolling);
      await loadVideos();
    }, 3000);
    return () => clearInterval(interval);
  }, [pollingIds]);

  async function loadVideos() {
    try {
      const data = await getVideos();
      setVideos(data.videos || []);
      // Start polling for processing videos
      const processing = new Set(
        (data.videos || [])
          .filter((v) => ['uploaded', 'processing', 'asr_done', 'notes_done', 'graph_done'].includes(v.status))
          .map((v) => v.id)
      );
      setPollingIds(processing);
    } catch (err) {
      console.error('Failed to load videos:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleUploadComplete(video) {
    setShowUpload(false);
    setPollingIds((prev) => new Set([...prev, video.id]));
    loadVideos();
  }

  const statusBadge = (status) => {
    const styles = {
      uploaded: 'bg-gray-100 text-gray-600',
      processing: 'bg-blue-100 text-blue-600 animate-pulse',
      asr_done: 'bg-yellow-100 text-yellow-700',
      notes_done: 'bg-yellow-100 text-yellow-700',
      graph_done: 'bg-yellow-100 text-yellow-700',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    };
    const labels = {
      uploaded: '等待处理',
      processing: '处理中...',
      asr_done: '语音识别完成',
      notes_done: '笔记生成完成',
      graph_done: '图谱生成中',
      completed: '已完成',
      failed: '处理失败',
    };
    return (
      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100'}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="min-h-screen">
      <Head>
        <title>学知图谱 — AI 学习助手</title>
        <meta name="description" content="AI驱动的视频学习与知识图谱工具" />
      </Head>

      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🧠</span>
            <h1 className="text-lg font-bold text-gray-800">学知图谱</h1>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/history" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">
              📋 学习记录
            </Link>
            <div className="w-8 h-8 bg-accent-100 rounded-full flex items-center justify-center text-accent-600 font-medium text-sm">
              熊
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Quick actions */}
        <div className="mb-8">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="bg-primary-500 hover:bg-primary-600 text-white px-6 py-3 rounded-xl font-medium transition-all active:scale-[0.98] shadow-sm"
          >
            {showUpload ? '收起' : '📤 导入视频'}
          </button>
        </div>

        {showUpload && (
          <div className="mb-8">
            <VideoUpload onUploadComplete={handleUploadComplete} />
          </div>
        )}

        {/* Stats */}
        {videos.length > 0 && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
              <div className="text-2xl font-bold text-gray-800">{videos.length}</div>
              <div className="text-sm text-gray-400 mt-1">📹 已学习视频</div>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
              <div className="text-2xl font-bold text-gray-800">
                {videos.filter((v) => v.status === 'completed').length}
              </div>
              <div className="text-sm text-gray-400 mt-1">✅ 已完成解析</div>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
              <div className="text-2xl font-bold text-primary-600">
                {videos.reduce((sum, v) => sum + Math.round(v.duration / 60), 0)}
              </div>
              <div className="text-sm text-gray-400 mt-1">⏱️ 累计分钟</div>
            </div>
          </div>
        )}

        {/* Video list */}
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-4">
            {videos.length > 0 ? '📚 我的视频' : ''}
          </h2>

          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-xl p-5 border border-gray-100">
                  <div className="shimmer h-5 w-48 mb-3" />
                  <div className="shimmer h-3 w-32" />
                </div>
              ))}
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4">🎯</div>
              <h3 className="text-lg font-medium text-gray-600 mb-2">开始你的学习之旅</h3>
              <p className="text-gray-400 mb-6">
                上传一个教学视频，AI 将自动为你生成笔记和知识图谱
              </p>
              <button
                onClick={() => setShowUpload(true)}
                className="bg-primary-500 hover:bg-primary-600 text-white px-8 py-3 rounded-xl font-medium transition-all"
              >
                📤 上传第一个视频
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {videos.map((video) => (
                <Link
                  key={video.id}
                  href={video.status === 'completed' ? `/learn/${video.id}` : '#'}
                  className={`block bg-white rounded-xl p-5 border border-gray-100 hover:border-primary-200 hover:shadow-sm transition-all ${
                    video.status === 'completed' ? 'cursor-pointer' : 'cursor-default opacity-70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-gray-800 truncate">{video.title}</h3>
                      <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
                        <span>🎬 {video.filename}</span>
                        {video.duration > 0 && (
                          <span>⏱️ {Math.floor(video.duration / 60)} 分 {Math.round(video.duration % 60)} 秒</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      {statusBadge(video.status)}
                      {video.status === 'completed' && (
                        <span className="text-gray-300">→</span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
