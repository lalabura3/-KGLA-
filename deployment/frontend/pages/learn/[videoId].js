import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import dynamic from 'next/dynamic';
import { getVideo, getNotes, updateSegment } from '../lib/api';
import Link from 'next/link';

// Dynamic import for KnowledgeGraph (requires browser APIs)
const KnowledgeGraph = dynamic(() => import('../../components/KnowledgeGraph'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-gray-400">加载图谱中...</div>
    </div>
  ),
});

export default function LearnPage() {
  const router = useRouter();
  const { videoId } = router.query;
  const [video, setVideo] = useState(null);
  const [notes, setNotes] = useState(null);
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeSegment, setActiveSegment] = useState(null);
  const [editingSegment, setEditingSegment] = useState(null);
  const [editContent, setEditContent] = useState('');
  const videoRef = useRef(null);

  // Load data
  useEffect(() => {
    if (!videoId) return;
    loadData();
  }, [videoId]);

  // Poll for processing completion
  useEffect(() => {
    if (video?.status === 'completed' && notes && graph) return;
    if (!video || video.status === 'failed') return;

    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [video]);

  async function loadData() {
    try {
      const [v, n, g] = await Promise.all([
        getVideo(videoId),
        getNotes(videoId).catch(() => null),
        import('../../lib/api').then((m) => m.getGraph(videoId)).catch(() => null),
      ]);
      setVideo(v);
      if (n) setNotes(n);
      if (g && g.nodes?.length > 0) setGraph(g);
    } catch (err) {
      console.error('Load failed:', err);
    } finally {
      setLoading(false);
    }
  }

  // Scroll to active segment
  useEffect(() => {
    if (activeSegment && !editingSegment) {
      const el = document.getElementById(`segment-${activeSegment}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [activeSegment]);

  // Format time
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleSeek = (time) => {
    setCurrentTime(time);
    // Find which segment this time belongs to
    if (notes?.segments) {
      const seg = notes.segments.find(
        (s) => time >= s.start_time && time < s.end_time
      );
      if (seg) setActiveSegment(seg.segment_index);
    }
  };

  const handleEditSegment = (segment) => {
    setEditingSegment(segment.id);
    setEditContent(segment.content || segment.summary);
  };

  const handleSaveEdit = async () => {
    if (!editingSegment || !videoId) return;
    try {
      await updateSegment(videoId, editingSegment, editContent);
      setEditingSegment(null);
      loadData();
    } catch (err) {
      alert('保存失败');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">🧠</div>
          <p className="text-gray-400">加载中...</p>
        </div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-4xl mb-4">😅</div>
          <p className="text-gray-600 mb-4">视频未找到</p>
          <Link href="/" className="text-primary-500 hover:underline">返回首页</Link>
        </div>
      </div>
    );
  }

  const isProcessing = !['completed', 'graph_done'].includes(video.status);

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>{video.title} — 学知图谱</title>
      </Head>

      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-400 hover:text-gray-600">← 返回</Link>
            <div className="w-px h-5 bg-gray-200" />
            <h1 className="text-sm font-medium text-gray-700 truncate max-w-md">{video.title}</h1>
          </div>
          <div className="flex items-center gap-3">
            {graph && graph.nodes?.length > 0 && (
              <Link
                href={`/graph/${videoId}`}
                className="text-sm text-primary-500 hover:text-primary-600 font-medium"
              >
                🕸️ 全屏图谱
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {isProcessing ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-gray-100">
            <div className="text-5xl mb-4 animate-bounce">⏳</div>
            <h2 className="text-xl font-semibold text-gray-700 mb-2">AI 正在处理您的视频</h2>
            <p className="text-gray-400 mb-4">
              {video.status === 'uploaded' ? '等待处理...' :
               video.status === 'processing' ? '正在提取语音和分段...' :
               video.status === 'asr_done' ? '正在生成笔记...' :
               video.status === 'notes_done' ? '正在构建知识图谱...' :
               '处理中...'}
            </p>
            <div className="max-w-xs mx-auto bg-gray-100 rounded-full h-2">
              <div className="bg-primary-500 h-2 rounded-full animate-pulse" style={{
                width: video.status === 'processing' ? '30%' :
                       video.status === 'asr_done' ? '50%' :
                       video.status === 'notes_done' ? '70%' :
                       video.status === 'graph_done' ? '90%' : '15%'
              }} />
            </div>
          </div>
        ) : (
          <div className="flex gap-6 h-[calc(100vh-120px)]">
            {/* Left panel: Notes */}
            <div className="w-[45%] bg-white rounded-2xl border border-gray-100 overflow-hidden flex flex-col">
              {/* Notes header */}
              <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                <h2 className="font-semibold text-gray-700">📝 AI 笔记</h2>
                <span className="text-xs text-gray-400">{notes?.total_segments || 0} 个片段</span>
              </div>

              {/* Notes content */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {notes?.segments?.map((seg) => (
                  <div
                    key={seg.id}
                    id={`segment-${seg.segment_index}`}
                    className={`note-card cursor-pointer transition-all ${
                      activeSegment === seg.segment_index ? 'ring-2 ring-primary-500 border-primary-500' : ''
                    }`}
                    onClick={() => handleSeek(seg.start_time)}
                  >
                    {/* Segment header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                          {formatTime(seg.start_time)}
                        </span>
                        <h3 className="text-sm font-medium text-gray-700">{seg.title}</h3>
                      </div>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEditSegment(seg); }}
                        className="text-xs text-gray-400 hover:text-gray-600"
                      >
                        ✏️
                      </button>
                    </div>

                    {/* Content */}
                    {editingSegment === seg.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full text-sm border border-gray-200 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-primary-500 min-h-[100px]"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex gap-2 justify-end">
                          <button
                            onClick={(e) => { e.stopPropagation(); setEditingSegment(null); }}
                            className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700"
                          >
                            取消
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleSaveEdit(); }}
                            className="px-3 py-1.5 text-xs bg-primary-500 text-white rounded-lg hover:bg-primary-600"
                          >
                            保存
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-600 leading-relaxed">
                        {seg.summary || seg.content}
                      </p>
                    )}

                    {/* Keywords from graph */}
                    {graph?.nodes?.filter((n) => n.segment_index === seg.segment_index).length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {graph.nodes
                          .filter((n) => n.segment_index === seg.segment_index)
                          .slice(0, 5)
                          .map((n) => (
                            <span
                              key={n.id}
                              className="px-2 py-0.5 bg-accent-50 text-accent-600 rounded text-xs"
                            >
                              #{n.name}
                            </span>
                          ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Right panel: Graph + info */}
            <div className="flex-1 flex flex-col gap-4">
              {/* Video placeholder / info */}
              <div className="bg-white rounded-2xl border border-gray-100 p-5">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-xl">🎬</span>
                  <div>
                    <h3 className="font-medium text-gray-700 text-sm">{video.title}</h3>
                    <p className="text-xs text-gray-400">
                      {Math.floor(video.duration / 60)} 分 {Math.round(video.duration % 60)} 秒
                      {video.source_url && ` · 源: ${video.source_url.slice(0, 30)}...`}
                    </p>
                  </div>
                </div>
                <div className="relative bg-gray-100 rounded-xl h-16 flex items-center justify-center">
                  <div className="text-xs text-gray-400">
                    视频播放器集成说明：部署后配置视频文件路径即可播放
                  </div>
                  {/* Timeline visualization */}
                  {notes?.segments && (
                    <div className="absolute bottom-2 left-3 right-3 flex gap-0.5">
                      {notes.segments.map((seg) => (
                        <button
                          key={seg.id}
                          onClick={() => handleSeek(seg.start_time)}
                          className={`flex-1 h-1.5 rounded-full transition-all ${
                            currentTime >= seg.start_time && currentTime < seg.end_time
                              ? 'bg-primary-500 scale-y-150'
                              : 'bg-gray-300 hover:bg-gray-400'
                          }`}
                          title={`${seg.title} (${formatTime(seg.start_time)})`}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Knowledge Graph */}
              <div className="flex-1 bg-white rounded-2xl border border-gray-100 overflow-hidden relative">
                <div className="absolute top-3 left-4 z-10">
                  <h2 className="font-semibold text-gray-700 text-sm">🕸️ 知识图谱</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {graph?.nodes?.length || 0} 个知识点 · {graph?.relations?.length || 0} 条关系
                  </p>
                </div>

                {graph?.nodes?.length > 0 ? (
                  <KnowledgeGraph
                    nodes={graph.nodes}
                    relations={graph.relations}
                    onNodeClick={(node) => {
                      handleSeek(node.timestamp);
                    }}
                    highlightNodeId={null}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-gray-400 text-sm">正在构建知识图谱...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
