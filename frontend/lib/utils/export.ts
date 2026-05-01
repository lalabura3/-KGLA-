import type { Notes, NoteSegment } from '@/types';

function fmtTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Convert notes to Markdown string */
export function notesToMarkdown(
  segments: NoteSegment[],
  title?: string,
): string {
  const lines: string[] = [];

  if (title) {
    lines.push(`# ${title}`);
    lines.push('');
  }

  lines.push(`> 共 ${segments.length} 个笔记段落 · 导出时间 ${new Date().toLocaleString('zh-CN')}`);
  lines.push('');
  lines.push('---');
  lines.push('');

  for (const seg of segments) {
    const timeRange = `${fmtTimestamp(seg.start_time)} – ${fmtTimestamp(seg.end_time)}`;
    lines.push(`## ${seg.title || `段落 ${seg.segment_index + 1}`}`);
    lines.push('');
    lines.push(`> ⏱ ${timeRange}`);
    lines.push('');

    if (seg.summary && seg.summary !== seg.content) {
      lines.push(`**摘要：** ${seg.summary}`);
      lines.push('');
    }

    lines.push(seg.content);
    lines.push('');

    if (seg.keyframe_url) {
      lines.push(`![关键帧](${seg.keyframe_url})`);
      lines.push('');
    }

    lines.push('---');
    lines.push('');
  }

  return lines.join('\n');
}

/** Convert notes to JSON string */
export function notesToJSON(notes: Notes, title?: string): string {
  return JSON.stringify(
    {
      title: title || '未命名',
      exported_at: new Date().toISOString(),
      total_segments: notes.total_segments,
      segments: notes.segments.map((seg) => ({
        index: seg.segment_index,
        title: seg.title,
        content: seg.content,
        summary: seg.summary,
        start_time: seg.start_time,
        end_time: seg.end_time,
        keyframe_url: seg.keyframe_url || null,
      })),
    },
    null,
    2,
  );
}

/** Trigger file download in browser */
export function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export type ExportFormat = 'markdown' | 'json';

/** Export notes in the given format */
export function exportNotes(notes: Notes, format: ExportFormat, title?: string) {
  const baseName = title
    ? title.replace(/[^\w\u4e00-\u9fff-]/g, '_').slice(0, 60)
    : 'notes_export';

  if (format === 'json') {
    const json = notesToJSON(notes, title);
    downloadBlob(json, `${baseName}.json`, 'application/json');
  } else {
    const md = notesToMarkdown(notes.segments, title);
    downloadBlob(md, `${baseName}.md`, 'text/markdown');
  }
}
