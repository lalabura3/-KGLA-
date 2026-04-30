/* eslint-disable react-hooks/exhaustive-deps */
import { useEffect, useRef, useState, useCallback } from 'react';

export default function KnowledgeGraph({ nodes, relations, onNodeClick, highlightNodeId }) {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [networkReady, setNetworkReady] = useState(false);

  // Color mapping for node types
  const typeColors = {
    concept: { background: '#dbeafe', border: '#3b82f6', font: '#1e40af' },
    term: { background: '#fce7f3', border: '#ec4899', font: '#9d174d' },
    formula: { background: '#fef3c7', border: '#f59e0b', font: '#92400e' },
    method: { background: '#d1fae5', border: '#10b981', font: '#065f46' },
    example: { background: '#ede9fe', border: '#8b5cf6', font: '#5b21b6' },
    person: { background: '#e0e7ff', border: '#6366f1', font: '#3730a3' },
    event: { background: '#ffe4e6', border: '#f43f5e', font: '#9f1239' },
  };

  // Mastery colors
  const masteryColors = {
    not_learned: { background: '#f1f5f9', border: '#94a3b8' },
    learning: { background: '#fef9c3', border: '#eab308' },
    mastered: { background: '#d1fae5', border: '#22c55e' },
  };

  // Initialize vis-network
  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;

    let cleanup = false;

    async function initNetwork() {
      const { Network } = await import('vis-network');
      const { DataSet } = await import('vis-data');

      if (cleanup || !containerRef.current) return;

      // Create datasets
      const visNodes = new DataSet(
        nodes.map((n) => {
          const typeColor = typeColors[n.node_type] || typeColors.concept;
          const masteryColor = masteryColors[n.mastery] || masteryColors.not_learned;

          return {
            id: n.id,
            label: n.name,
            title: n.description || n.name,
            size: 15 + n.importance * 20,
            color: {
              background: n.mastery === 'not_learned' ? typeColor.background : masteryColor.background,
              border: n.mastery === 'not_learned' ? typeColor.border : masteryColor.border,
              highlight: { background: '#dbeafe', border: '#2563eb' },
            },
            font: {
              color: typeColor.font,
              size: 12 + n.importance * 6,
              face: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            },
            borderWidth: n.mastery === 'not_learned' ? 2 : 3,
            borderWidthSelected: 4,
            shape: n.importance > 0.7 ? 'star' : 'dot',
          };
        })
      );

      const relationTypeStyles = {
        prerequisite: { color: '#f87171', width: 2, dashes: false, arrows: 'to' },
        contains: { color: '#60a5fa', width: 2, dashes: false, arrows: 'to' },
        similar: { color: '#a78bfa', width: 1.5, dashes: true, arrows: 'to' },
        contrast: { color: '#f472b6', width: 1.5, dashes: [5, 5], arrows: 'to' },
        causal: { color: '#f97316', width: 2, dashes: false, arrows: 'to' },
        sequence: { color: '#34d399', width: 2, dashes: false, arrows: 'to' },
        related: { color: '#94a3b8', width: 1, dashes: [3, 3], arrows: 'to' },
      };

      const visEdges = new DataSet(
        (relations || []).map((r) => {
          const style = relationTypeStyles[r.relation_type] || relationTypeStyles.related;
          return {
            id: r.id,
            from: r.source_node_id,
            to: r.target_node_id,
            label: r.relation_type,
            ...style,
            smooth: { type: 'curvedCW', roundness: 0.1 },
            font: {
              size: 9,
              color: '#94a3b8',
              strokeWidth: 0,
              align: 'middle',
            },
          };
        })
      );

      // Network options
      const options = {
        nodes: {
          shape: 'dot',
          scaling: { min: 10, max: 40 },
          shadow: { enabled: true, size: 4 },
        },
        edges: {
          smooth: { type: 'curvedCW', roundness: 0.1 },
          shadow: { enabled: true, size: 2 },
        },
        physics: {
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -40,
            centralGravity: 0.005,
            springLength: 200,
            springConstant: 0.02,
            damping: 0.4,
          },
          stabilization: { iterations: 200 },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          navigationButtons: true,
          keyboard: true,
          zoomView: true,
          dragView: true,
        },
        layout: {
          improvedLayout: true,
        },
      };

      const network = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);
      networkRef.current = network;
      setNetworkReady(true);

      // Click handler
      network.on('click', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const nodeData = nodes.find((n) => n.id === nodeId);
          setSelectedNode(nodeData);
          onNodeClick?.(nodeData);
        } else {
          setSelectedNode(null);
        }
      });

      // Hover effects
      network.on('hoverNode', (params) => {
        document.body.style.cursor = 'pointer';
      });
      network.on('blurNode', () => {
        document.body.style.cursor = 'default';
      });
    }

    initNetwork();

    return () => {
      cleanup = true;
      networkRef.current?.destroy();
    };
  }, [nodes, relations]);

  // Highlight node
  useEffect(() => {
    if (networkRef.current && highlightNodeId) {
      networkRef.current.selectNodes([highlightNodeId]);
      networkRef.current.focus(highlightNodeId, { scale: 1.5, animation: { duration: 500 } });
    }
  }, [highlightNodeId]);

  // Resize handler
  useEffect(() => {
    const handleResize = () => networkRef.current?.redraw();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="graph-container" style={{ height: '100%', minHeight: '400px' }} />

      {/* Node detail panel */}
      {selectedNode && (
        <div className="absolute bottom-4 left-4 right-4 bg-white rounded-xl shadow-lg border border-gray-100 p-4 max-w-sm">
          <div className="flex justify-between items-start mb-2">
            <h4 className="font-semibold text-gray-800 text-sm">{selectedNode.name}</h4>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            >
              ✕
            </button>
          </div>
          <p className="text-xs text-gray-500 mb-2">{selectedNode.description}</p>
          <div className="flex gap-2 text-xs">
            <span className="px-2 py-1 bg-gray-100 rounded-full text-gray-600">
              {selectedNode.node_type}
            </span>
            <span className={`px-2 py-1 rounded-full ${
              selectedNode.mastery === 'mastered' ? 'bg-green-100 text-green-700' :
              selectedNode.mastery === 'learning' ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {selectedNode.mastery === 'mastered' ? '已掌握' :
               selectedNode.mastery === 'learning' ? '学习中' : '未学习'}
            </span>
            {selectedNode.timestamp > 0 && (
              <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded-full">
                {Math.floor(selectedNode.timestamp / 60)}:{(selectedNode.timestamp % 60).toString().padStart(2, '0')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-3 right-3 bg-white/90 backdrop-blur rounded-lg px-3 py-2 text-xs shadow-sm border border-gray-100">
        <div className="text-gray-500 font-medium mb-1">图例</div>
        {Object.entries({
          concept: '概念', term: '术语', formula: '公式',
          method: '方法', example: '例子'
        }).map(([key, label]) => (
          <div key={key} className="flex items-center gap-1.5 py-0.5">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: (typeColors[key] || typeColors.concept).border }}
            />
            <span className="text-gray-600">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
