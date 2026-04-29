import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { getVideos } from '../lib/api';

export default function HistoryPage() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadVideos();
  }, []);

  async function loadVideos() {
    try {
      const data = await getVideos();
      setVideos(data.videos || []);
    } catch (err) {
      console.error('Failed:', err);
    } finally {
      setLoading(false);
    }
  }

  const completed = videos.filter((v) => v.status === 'completed');
  const processing = videos.filter((v) => v.status !== 'completed' && v.status !== 'failed');

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>学习记录 — 学知图谱</title>
      </Head>

      <header className="bg-white border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-gray-600">← 首页</Link>
          <div className="w-px h-5 bg-gray-200" />
          <h1 className="text-lg font-bold text-gray-800">📋 学习记录</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="shimmer h-16 rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="space-y-8">
            {/* Processing */}
            {processing.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-gray-500 mb-3">处理中 ({processing.length})</h2>
                <div className="space-y-2">
                  {processing.map((v) => (
                    <div key={v.id} className="bg-white rounded-xl p-4 border border-gray-100 opacity-70">
                      <p className="text-sm text-gray-600">{v.title}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Completed */}
            <div>
              <h2 className="text-sm font-semibold text-gray-500 mb-3">
                已完成 ({completed.length})
              </h2>
              {completed.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <p className="mb-2">还没有完成学习的视频</p>
                  <Link href="/" className="text-primary-500 hover:underline text-sm">去导入一个视频</Link>
                </div>
              ) : (
                <div className="space-y-2">
                  {completed.map((v) => (
                    <Link
                      key={v.id}
                      href={`/learn/${v.id}`}
                      className="block bg-white rounded-xl p-4 border border-gray-100 hover:border-primary-200 transition-all hover:shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-gray-800 text-sm">{v.title}</p>
                          <p className="text-xs text-gray-400 mt-1">
                            {Math.floor(v.duration / 60)} 分 {Math.round(v.duration % 60)} 秒
                          </p>
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(v.updated_at).toLocaleDateString('zh-CN')}
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
