import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import dynamic from 'next/dynamic';
import { getVideo, getGraph, updateMastery, searchNodes } from '../../lib/api';
import Link from 'next/link';

const KnowledgeGraph = dynamic(() => import('../../components/KnowledgeGraph'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-gray-400 animate-pulse">Loading graph...</div>
    </div>
  ),
});

export default function GraphPage() {
  const router = useRouter();
  const { videoId } = router.query;
  const [video, setVideo] = useState(null);
  const [graph, setGraph] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [masteryFilter, setMasteryFilter] = useState('all');

  useEffect(() => {
    if (!videoId) return;
    loadData();
  }, [videoId]);

  async function loadData() {
    try {
      const [v, g] = await Promise.all([
        getVideo(videoId),
        getGraph(videoId).catch(() => ({ nodes: [], relations: [] })),
      ]);
      setVideo(v);
      setGraph(g);
    } catch (err) {
      console.error('Load failed:', err);
    } finally {
      setLoading(false);
    }
  }

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (query.trim().length < 1) {
      setSearchResults([]);
      return;
    }
    try {
      const results = await searchNodes(videoId, query);
      setSearchResults(results);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const handleMasteryUpdate = async (nodeId, mastery) => {
    try {
      await updateMastery(nodeId, mastery);
      loadData(); // Refresh graph
    } catch (err) {
      alert('更新失败');
    }
  };

  const filteredNodes = graph?.nodes?.filter((n) => {
    if (masteryFilter === 'all') return true;
    return n.mastery === masteryFilter;
  }) || [];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-white text-center">
          <div className="text-4xl mb-4 animate-pulse">🕸️</div>
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      <Head>
        <title>{video?.title || '知识图谱'} — 学知图谱</title>
      </Head>

      {/* Header bar */}
      <div className="flex items-center justify-between px-6 py-3 bg-gray-800/80 backdrop-blur border-b border-gray-700">
        <div className="flex items-center gap-4">
          <Link href={`/learn/${videoId}`} className="text-gray-400 hover:text-white transition-colors">
            ← 返回学习页
          </Link>
          <div className="w-px h-5 bg-gray-600" />
          <h1 className="text-sm font-medium">🕸️ 知识图谱探索</h1>
          <span className="text-xs text-gray-400">{video?.title}</span>
        </div>
        <div className="flex items-center gap-3">
          {/* Mastery filter */}
          <select
            value={masteryFilter}
            onChange={(e) => setMasteryFilter(e.target.value)}
            className="bg-gray-700 text-white text-xs px-3 py-1.5 rounded-lg border border-gray-600 focus:outline-none"
          >
            <option value="all">全部节点</option>
            <option value="not_learned">未学习</option>
            <option value="learning">学习中</option>
            <option value="mastered">已掌握</option>
          </select>

          {/* Search */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="搜索知识点..."
              className="bg-gray-700 text-white text-xs pl-8 pr-3 py-1.5 rounded-lg border border-gray-600 focus:outline-none focus:border-primary-500 w-48"
            />
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">🔍</span>
          </div>

          <span className="text-xs text-gray-400">
            {graph?.nodes?.length || 0} 节点 · {graph?.relations?.length || 0} 关系
          </span>
        </div>
      </div>

      {/* Main area */}
      <div className="flex-1 flex">
        {/* Graph */}
        <div className="flex-1 relative">
          {graph?.nodes?.length > 0 ? (
            <KnowledgeGraph
              nodes={filteredNodes}
              relations={graph.relations}
              onNodeClick={(node) => setSelectedNode(node)}
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">暂无知识图谱数据</p>
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className="w-72 bg-gray-800/50 border-l border-gray-700 overflow-y-auto">
          {selectedNode ? (
            <div className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-sm">{selectedNode.name}</h3>
                <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-white">
                  ✕
                </button>
              </div>

              <p className="text-xs text-gray-400 mb-4 leading-relaxed">
                {selectedNode.description || '暂无描述'}
              </p>

              <div className="space-y-3">
                {/* Node type */}
                <div>
                  <label className="text-xs text-gray-500 block mb-1">类型</label>
                  <span className="px-2 py-1 bg-gray-700 rounded text-xs">{selectedNode.node_type}</span>
                </div>

                {/* Timestamp */}
                {selectedNode.timestamp > 0 && (
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">视频位置</label>
                    <span className="px-2 py-1 bg-blue-900/50 text-blue-300 rounded text-xs">
                      {Math.floor(selectedNode.timestamp / 60)}:{Math.round(selectedNode.timestamp % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                )}

                {/* Mastery */}
                <div>
                  <label className="text-xs text-gray-500 block mb-1">掌握程度</label>
                  <div className="flex gap-1">
                    {[
                      { value: 'not_learned', label: '未学习', color: 'bg-gray-600' },
                      { value: 'learning', label: '学习中', color: 'bg-yellow-600' },
                      { value: 'mastered', label: '已掌握', color: 'bg-green-600' },
                    ].map(({ value, label, color }) => (
                      <button
                        key={value}
                        onClick={() => handleMasteryUpdate(selectedNode.id, value)}
                        className={`px-2 py-1 text-xs rounded ${
                          selectedNode.mastery === value
                            ? `${color} text-white`
                            : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Related nodes */}
                {graph?.relations && (
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">关联关系</label>
                    <div className="space-y-1">
                      {graph.relations
                        .filter((r) => r.source_node_id === selectedNode.id)
                        .slice(0, 5)
                        .map((r) => {
                          const target = graph.nodes.find((n) => n.id === r.target_node_id);
                          return target ? (
                            <div
                              key={r.id}
                              className="flex items-center gap-1 text-xs text-gray-400 cursor-pointer hover:text-white"
                              onClick={() => setSelectedNode(target)}
                            >
                              <span className="text-gray-600">{r.relation_type}</span>
                              <span>→</span>
                              <span>{target.name}</span>
                            </div>
                          ) : null;
                        })}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : searchResults.length > 0 ? (
            <div className="p-5">
              <h3 className="text-xs text-gray-500 mb-3">搜索结果</h3>
              <div className="space-y-1">
                {searchResults.map((r) => (
                  <div
                    key={r.id}
                    className="text-xs text-gray-300 cursor-pointer hover:text-white py-1.5 px-2 hover:bg-gray-700 rounded"
                    onClick={() => setSelectedNode(r)}
                  >
                    {r.name}
                    <span className="text-gray-500 ml-1">({r.node_type})</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-5 text-center text-gray-500 text-xs mt-20">
              <p>点击节点查看详情</p>
              <p className="mt-2">或搜索知识点</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
