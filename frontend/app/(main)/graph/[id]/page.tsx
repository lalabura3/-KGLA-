'use client';

import { useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { useGraph } from '@/lib/hooks/useGraph';
import { useUIPreferences } from '@/stores/ui-preferences';
import { KnowledgeGraphViewer, GraphControls, NodeDetailPanel, GraphSearch } from '@/components/graph';
import { updateMastery } from '@/lib/api/graph';
import { Spinner, Alert, Breadcrumb } from '@/components/ui';
import { ROUTES } from '@/lib/constants';
import type { KnowledgeNode, MasteryLevel } from '@/types';
import type { GraphMode } from '@/stores/ui-preferences';

export default function GraphPage() {
  const params = useParams<{ id: string }>();
  const videoId = params?.id || '';
  const { data, isLoading, error } = useGraph(videoId);
  const { graphMode, setGraphMode } = useUIPreferences();
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMatchedIds, setSearchMatchedIds] = useState<Set<string>>(new Set());
  const [highlightNodeId, setHighlightNodeId] = useState<string | null>(null);

  const nodes = data?.nodes || [];
  const relations = data?.relations || [];

  const handleNodeClick = (node: KnowledgeNode) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  };

  // Search callbacks
  const handleSearchResult = useCallback((results: KnowledgeNode[], query: string) => {
    setSearchQuery(query);
    setSearchMatchedIds(new Set(results.map((n) => n.id)));
    if (results.length === 0) setHighlightNodeId(null);
  }, []);

  const handleHighlightNode = useCallback((nodeId: string | null) => {
    setHighlightNodeId(nodeId);
  }, []);

  const handleMasteryChange = useCallback(
    async (nodeId: string, newMastery: MasteryLevel) => {
      // Optimistic update in local state
      setSelectedNode((prev) =>
        prev?.id === nodeId ? { ...prev, mastery: newMastery } : prev,
      );
      try {
        await updateMastery(videoId, nodeId, newMastery);
      } catch {
        // Revert on error — refetch will correct it
      }
    },
    [videoId],
  );

  const handleModeChange = (mode: GraphMode) => {
    setGraphMode(mode);
    setSelectedNode(null);
  };

  const relatedNodes = selectedNode
    ? relations
        .filter((r) => r.source_node_id === selectedNode.id || r.target_node_id === selectedNode.id)
        .map((r) => {
          const otherId = r.source_node_id === selectedNode.id ? r.target_node_id : r.source_node_id;
          const otherNode = nodes.find((n) => n.id === otherId);
          return {
            id: otherId,
            name: otherNode?.name || otherId,
            relation: r.relation_type,
          };
        })
    : [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner size="lg" label="加载知识图谱..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8">
        <Alert variant="error">
          加载知识图谱失败：{'detail' in (error as any) ? (error as any).detail : '未知错误'}
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: '仪表盘', href: ROUTES.DASHBOARD },
          { label: '知识图谱' },
        ]}
      />

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">知识图谱</h1>
        <p className="mt-1 text-sm text-gray-500">
          {nodes.length > 0
            ? `${nodes.length} 个知识点，${relations.length} 条关系 — 点击节点查看详情`
            : '暂无图谱数据'}
        </p>
      </div>

      {nodes.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 py-20">
          <span className="text-4xl">🕸️</span>
          <h3 className="mt-3 text-lg font-semibold text-gray-700">图谱尚未生成</h3>
          <p className="mt-1 text-sm text-gray-500">视频处理完成后会自动生成知识图谱</p>
        </div>
      ) : (
        <>
          {/* Controls & Search */}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <GraphControls
              mode={graphMode}
              onModeChange={handleModeChange}
              nodeCount={nodes.length}
              relationCount={relations.length}
            />
            <GraphSearch
              videoId={videoId}
              onSearchResult={handleSearchResult}
              onHighlightNode={handleHighlightNode}
              className="w-full sm:w-72"
            />
          </div>

          {/* Main layout */}
          <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
            {/* Graph canvas */}
            <KnowledgeGraphViewer
              nodes={nodes}
              relations={relations}
              mode={graphMode}
              onNodeClick={handleNodeClick}
              selectedNodeId={selectedNode?.id}
              searchQuery={searchQuery}
              searchMatchedIds={searchMatchedIds}
              highlightNodeId={highlightNodeId ?? undefined}
            />

            {/* Detail panel */}
            <NodeDetailPanel
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onMasteryChange={handleMasteryChange}
              relatedNodes={relatedNodes}
            />
          </div>
        </>
      )}
    </div>
  );
}
