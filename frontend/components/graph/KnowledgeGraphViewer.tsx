'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils/cn';
import { NODE_COLORS } from '@/lib/design-tokens';
import { GRAPH_DEFAULTS } from '@/lib/constants';
import type { KnowledgeNode, Relation, NodeType } from '@/types';
import type { GraphMode } from '@/stores/ui-preferences';

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  name: string;
  node_type: NodeType;
  importance: number;
  mastery: string;
  group: string;
  // cluster position
  cx?: number;
  cy?: number;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  id: string;
  relation_type: string;
}

interface KnowledgeGraphViewerProps {
  nodes: KnowledgeNode[];
  relations: Relation[];
  mode?: GraphMode;
  onNodeClick?: (node: KnowledgeNode) => void;
  onNodeContextMenu?: (node: KnowledgeNode, event: MouseEvent) => void;
  onModeChange?: (mode: GraphMode) => void;
  selectedNodeId?: string;
  highlightNodeId?: string;
  searchQuery?: string;
  searchMatchedIds?: Set<string>;
  className?: string;
  darkMode?: boolean;
}

function getNodeRadius(importance: number): number {
  const { NODE_RADIUS_MIN, NODE_RADIUS_MAX } = GRAPH_DEFAULTS;
  return NODE_RADIUS_MIN + (importance / 10) * (NODE_RADIUS_MAX - NODE_RADIUS_MIN);
}

export function KnowledgeGraphViewer({
  nodes,
  relations,
  mode = 'cluster',
  onNodeClick,
  onNodeContextMenu,
  selectedNodeId,
  highlightNodeId,
  searchQuery,
  searchMatchedIds,
  className,
  darkMode = false,
}: KnowledgeGraphViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const bgColor = darkMode ? '#111827' : '#ffffff';
  const textColor = darkMode ? '#e5e7eb' : '#374151';
  const linkColor = darkMode ? '#4b5563' : '#d1d5db';

  const simNodes: SimNode[] = nodes.map((n) => ({
    id: n.id,
    name: n.name,
    node_type: n.node_type,
    importance: n.importance,
    mastery: n.mastery,
    group: n.node_type,
  }));

  const simLinks: SimLink[] = relations.map((r) => ({
    id: r.id,
    source: r.source_node_id,
    target: r.target_node_id,
    relation_type: r.relation_type,
  }));

  const drawGraph = useCallback(() => {
    const container = containerRef.current;
    const svgEl = svgRef.current;
    if (!container || !svgEl || nodes.length === 0) return;

    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    // Clear previous
    d3.select(svgEl).selectAll('*').remove();

    const svg = d3.select(svgEl)
      .attr('viewBox', [0, 0, width, height])
      .attr('width', width)
      .attr('height', height);

    // Defs for markers and filters
    const defs = svg.append('defs');

    // Drop shadow filter
    const filter = defs.append('filter').attr('id', 'node-shadow');
    filter.append('feDropShadow').attr('dx', 0).attr('dy', 1).attr('stdDeviation', 2).attr('flood-opacity', 0.15);

    // Glow for hover
    const glowFilter = defs.append('filter').attr('id', 'node-glow');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', 4).attr('result', 'blur');
    const merge = glowFilter.append('feMerge');
    merge.append('feMergeNode').attr('in', 'blur');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Zoom behavior
    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([GRAPH_DEFAULTS.ZOOM_MIN, GRAPH_DEFAULTS.ZOOM_MAX])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Initial transform
    svg.call(zoom.transform, d3.zoomIdentity.translate(width / 2, height / 2));

    // Set initial positions based on mode
    if (mode === 'cluster') {
      const cols = Math.ceil(Math.sqrt(nodes.length));
      simNodes.forEach((n, i) => {
        n.x = ((i % cols) / cols) * width * 0.8 + width * 0.1;
        n.y = (Math.floor(i / cols) / Math.ceil(nodes.length / cols)) * height * 0.8 + height * 0.1;
      });
    } else {
      simNodes.forEach((n) => {
        n.x = width / 2 + (Math.random() - 0.5) * 200;
        n.y = height / 2 + (Math.random() - 0.5) * 200;
      });
    }

    // Force simulation
    const simulation = d3.forceSimulation<SimNode>(simNodes)
      .force('link', d3.forceLink<SimNode, SimLink>(simLinks)
        .id((d) => d.id)
        .distance(GRAPH_DEFAULTS.LINK_DISTANCE))
      .force('charge', d3.forceManyBody().strength(GRAPH_DEFAULTS.CHARGE_STRENGTH))
      .force('center', d3.forceCenter(0, 0))
      .force('collision', d3.forceCollide<SimNode>().radius((d) => getNodeRadius(d.importance) + 4));

    if (mode === 'cluster') {
      simulation.force('x', d3.forceX<SimNode>(0).strength(0.05));
      simulation.force('y', d3.forceY<SimNode>(0).strength(0.05));
    }

    simulationRef.current = simulation;

    // Draw links
    const linkGroup = g.append('g').attr('class', 'links');
    const link = linkGroup.selectAll<SVGLineElement, SimLink>('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', linkColor)
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)
      .attr('stroke-dasharray', (d) => d.relation_type === 'similar' ? '4,3' : null);

    // Draw nodes
    const nodeGroup = g.append('g').attr('class', 'nodes');
    const node = nodeGroup.selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(
        d3.drag<SVGGElement, SimNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as any,
      );

    // Node circles
    node.append('circle')
      .attr('r', (d) => getNodeRadius(d.importance))
      .attr('fill', (d) => NODE_COLORS[d.node_type] || '#6366f1')
      .attr('stroke', bgColor)
      .attr('stroke-width', 2)
      .attr('filter', 'url(#node-shadow)')
      .attr('opacity', 0.9)
      .on('mouseenter', function () {
        d3.select(this)
          .attr('filter', 'url(#node-glow)')
          .attr('stroke-width', 3);
      })
      .on('mouseleave', function () {
        d3.select(this)
          .attr('filter', 'url(#node-shadow)')
          .attr('stroke-width', 2);
      });

    // Node labels
    node.append('text')
      .text((d) => d.name.length > 6 ? d.name.slice(0, 6) + '...' : d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => getNodeRadius(d.importance) + 14)
      .attr('font-size', 11)
      .attr('font-family', 'var(--font-geist-sans), system-ui, sans-serif')
      .attr('fill', textColor)
      .attr('pointer-events', 'none');

    // Selection highlight ring
    if (selectedNodeId) {
      node.filter((d) => d.id === selectedNodeId)
        .select('circle')
        .attr('stroke', darkMode ? '#f59e0b' : '#f59e0b')
        .attr('stroke-width', 3)
        .attr('stroke-dasharray', '3,2');

      // Dim non-selected nodes
      node.filter((d) => d.id !== selectedNodeId)
        .select('circle')
        .attr('opacity', 0.4);
      link.attr('stroke-opacity', 0.15);
      
      // Highlight connected links
      link.filter((d) => {
        const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
        const targetId = typeof d.target === 'object' ? d.target.id : d.target;
        return sourceId === selectedNodeId || targetId === selectedNodeId;
      }).attr('stroke-opacity', 0.8).attr('stroke-width', 2);
    }

    // Node click
    node.on('click', (_event, d) => {
      const originalNode = nodes.find((n) => n.id === d.id);
      if (originalNode) onNodeClick?.(originalNode);
    });

    // Node right-click context menu
    node.on('contextmenu', (event, d) => {
      event.preventDefault();
      const originalNode = nodes.find((n) => n.id === d.id);
      if (originalNode) onNodeContextMenu?.(originalNode, event as any as MouseEvent);
    });

    node.on('mouseenter', (_event, d) => setHoveredNode(d.id));
    node.on('mouseleave', () => setHoveredNode(null));

    // Search highlight: dim non-matching nodes
    if (searchQuery && searchQuery.length > 0) {
      const matchedSet = searchMatchedIds || new Set<string>();
      node.filter((d) => !matchedSet.has(d.id))
        .select('circle')
        .attr('opacity', 0.15);
      node.filter((d) => !matchedSet.has(d.id))
        .select('text')
        .attr('opacity', 0.15);

      // Highlight matched nodes with glow
      node.filter((d) => matchedSet.has(d.id))
        .select('circle')
        .attr('stroke', darkMode ? '#fbbf24' : '#f59e0b')
        .attr('stroke-width', 3)
        .attr('filter', 'url(#node-glow)');

      // Dim non-matched links
      link.attr('stroke-opacity', 0.08);
      // Highlight links where both ends match
      link.filter((d) => {
        const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
        const targetId = typeof d.target === 'object' ? d.target.id : d.target;
        return matchedSet.has(sourceId as string) || matchedSet.has(targetId as string);
      }).attr('stroke-opacity', 0.5).attr('stroke', darkMode ? '#fbbf24' : '#f59e0b');
    }

    // Highlight specific node (from search hover/select)
    if (highlightNodeId && !(searchQuery && searchQuery.length > 0)) {
      node.filter((d) => d.id === highlightNodeId)
        .select('circle')
        .attr('stroke', darkMode ? '#fbbf24' : '#f59e0b')
        .attr('stroke-width', 3)
        .attr('filter', 'url(#node-glow)');

      // Dim non-highlighted nodes
      node.filter((d) => d.id !== highlightNodeId && d.id !== selectedNodeId)
        .select('circle')
        .attr('opacity', 0.3);
    }

    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [nodes, relations, mode, selectedNodeId, darkMode, bgColor, textColor, linkColor, onNodeClick]);

  useEffect(() => {
    const cleanup = drawGraph();
    return () => cleanup?.();
  }, [drawGraph]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      drawGraph();
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [drawGraph]);

  if (nodes.length === 0) {
    return (
      <div className={cn('flex items-center justify-center rounded-xl border-2 border-dashed border-gray-200 bg-gray-50', className)} style={{ minHeight: 400 }}>
        <div className="text-center">
          <svg className="mx-auto h-12 w-12 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
          </svg>
          <p className="mt-3 text-sm text-gray-500">暂无知识图谱数据</p>
          <p className="text-xs text-gray-400">上传视频并完成处理后即可查看</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden rounded-xl border border-gray-200', darkMode ? 'bg-gray-900' : 'bg-white', className)}
      style={{ minHeight: 500 }}
    >
      <svg ref={svgRef} className="h-full w-full" />
      
      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 rounded-lg bg-white/90 px-3 py-2 shadow-sm backdrop-blur">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1 text-xs text-gray-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {type}
          </div>
        ))}
      </div>
    </div>
  );
}
