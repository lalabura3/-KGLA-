// ── 视频生命周期状态 ──
export type VideoStatus =
  | 'uploaded'
  | 'processing'
  | 'asr_done'
  | 'notes_done'
  | 'graph_done'
  | 'completed'
  | 'failed';

// ── 知识点类型 ──
export type NodeType =
  | 'concept'
  | 'term'
  | 'formula'
  | 'method'
  | 'example'
  | 'person'
  | 'event';

// ── 掌握程度 ──
export type MasteryLevel = 'not_learned' | 'learning' | 'mastered';

// ── 关系类型 ──
export type RelationType =
  | 'prerequisite'
  | 'contains'
  | 'similar'
  | 'contrast'
  | 'causal'
  | 'sequence'
  | 'related';

// ── 视频 ──
export interface Video {
  id: string;
  title: string;
  filename: string;
  duration: number;
  source_url?: string;
  status: VideoStatus;
  user_id: string;
  thumbnail_url?: string;
  created_at: string;
  updated_at: string;
}

// ── 笔记段落 ──
export interface NoteSegment {
  id: string;
  segment_index: number;
  title: string;
  content: string;
  summary: string;
  start_time: number;
  end_time: number;
  keyframe_url?: string;
}

// ── 笔记 ──
export interface Notes {
  video_id: string;
  total_segments: number;
  segments: NoteSegment[];
}

// ── 知识点节点 ──
export interface KnowledgeNode {
  id: string;
  name: string;
  description: string;
  node_type: NodeType;
  importance: number;
  mastery: MasteryLevel;
  timestamp: number;
  segment_index?: number;
  source_video_id: string;
}

// ── 知识点关系 ──
export interface Relation {
  id: string;
  source_node_id: string;
  target_node_id: string;
  relation_type: RelationType;
  weight?: number;
}

// ── 知识图谱 ──
export interface KnowledgeGraph {
  video_id: string;
  nodes: KnowledgeNode[];
  relations: Relation[];
}

// ── 图谱引擎接口（T3 预留，T9/T18 实现） ──
export interface GraphOptions {
  width: number;
  height: number;
  mode: 'cluster' | 'focus' | 'path';
  darkMode?: boolean;
}

export interface ModeParams {
  nodeId?: string;
  depth?: number;
  startNodeId?: string;
  endNodeId?: string;
}

export interface GraphEngine {
  init(container: HTMLElement, options: GraphOptions): void;
  setData(nodes: KnowledgeNode[], relations: Relation[]): void;
  setMode(mode: 'cluster' | 'focus' | 'path', params?: ModeParams): void;
  highlightNode(id: string): void;
  zoomTo(id: string, scale: number): void;
  destroy(): void;
}
