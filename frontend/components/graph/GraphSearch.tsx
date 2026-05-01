'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useNodeSearch } from '@/lib/hooks/useGraph';
import { useDebounce } from '@/lib/hooks/useDebounce';
import { cn } from '@/lib/utils/cn';
import type { KnowledgeNode } from '@/types';

interface GraphSearchProps {
  videoId: string;
  onSearchResult?: (nodes: KnowledgeNode[], query: string) => void;
  onHighlightNode?: (nodeId: string | null) => void;
  className?: string;
}

export function GraphSearch({
  videoId,
  onSearchResult,
  onHighlightNode,
  className,
}: GraphSearchProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const { data, isLoading } = useNodeSearch(videoId, debouncedQuery);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = data?.nodes || [];

  // Notify parent of search results
  useEffect(() => {
    if (debouncedQuery.length > 0) {
      onSearchResult?.(results, debouncedQuery);
    } else {
      onSearchResult?.([], '');
    }
  }, [results, debouncedQuery, onSearchResult]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleClear = useCallback(() => {
    setQuery('');
    setIsOpen(false);
    onSearchResult?.([], '');
    onHighlightNode?.(null);
    inputRef.current?.focus();
  }, [onSearchResult, onHighlightNode]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    }
    if (e.key === 'ArrowDown' && results.length > 0) {
      e.preventDefault();
      // Focus first result
      const firstBtn = containerRef.current?.querySelector('[data-result-item]') as HTMLElement;
      firstBtn?.focus();
    }
  };

  const handleSelect = (node: KnowledgeNode) => {
    setQuery(node.name);
    setIsOpen(false);
    onHighlightNode?.(node.id);
  };

  const showDropdown = isOpen && query.length > 0;

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Search input */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => query.length > 0 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="搜索知识点..."
          className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-10 pr-10 text-sm text-gray-900 placeholder-gray-400 outline-none transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
        />
        {/* Loading spinner or clear button */}
        {isLoading && debouncedQuery.length > 0 ? (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <svg className="h-4 w-4 animate-spin text-indigo-400" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" className="opacity-75" />
            </svg>
          </div>
        ) : query.length > 0 ? (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-400 hover:text-gray-600"
            aria-label="清除搜索"
          >
            <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        ) : null}
      </div>

      {/* Dropdown results */}
      {showDropdown && (
        <div className="absolute z-50 mt-1.5 w-full rounded-lg border border-gray-200 bg-white shadow-lg">
          {/* Search status */}
          {debouncedQuery.length === 0 && (
            <div className="px-4 py-3 text-xs text-gray-400">输入关键词开始搜索...</div>
          )}

          {isLoading && debouncedQuery.length > 0 && (
            <div className="px-4 py-3 text-xs text-gray-400 flex items-center gap-2">
              搜索中...
            </div>
          )}

          {/* Results */}
          {!isLoading && debouncedQuery.length > 0 && results.length === 0 && (
            <div className="px-4 py-6 text-center">
              <svg className="mx-auto h-8 w-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              <p className="mt-2 text-sm text-gray-500">未找到匹配的知识点</p>
              <p className="text-xs text-gray-400">尝试使用不同的关键词</p>
            </div>
          )}

          {!isLoading && results.length > 0 && (
            <>
              <div className="px-4 py-2 text-xs font-medium text-gray-400">
                找到 {results.length} 个结果
              </div>
              <div className="max-h-64 overflow-y-auto">
                {results.map((node, idx) => (
                  <button
                    key={node.id}
                    data-result-item
                    onClick={() => handleSelect(node)}
                    onMouseEnter={() => onHighlightNode?.(node.id)}
                    onMouseLeave={() => onHighlightNode?.(null)}
                    className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-indigo-50 transition-colors"
                  >
                    {/* Node type indicator */}
                    <span
                      className="mt-0.5 h-2 w-2 shrink-0 rounded-full"
                      style={{ background: getNodeTypeColor(node.node_type) }}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {highlightMatch(node.name, debouncedQuery)}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
                        {node.description
                          ? highlightMatch(node.description.length > 80 ? node.description.slice(0, 80) + '...' : node.description, debouncedQuery)
                          : '暂无描述'}
                      </p>
                      <div className="mt-1 flex items-center gap-2">
                        <span className="text-xs text-gray-400">{node.node_type}</span>
                        <span className="text-xs text-gray-400">·</span>
                        <span className="text-xs text-gray-400">重要性 {node.importance}/10</span>
                      </div>
                    </div>
                    {/* Keyboard shortcut hint for first result */}
                    {idx === 0 && (
                      <kbd className="mt-0.5 shrink-0 rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[10px] text-gray-400">
                        ⏎
                      </kbd>
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** Get node type display color */
function getNodeTypeColor(nodeType: string): string {
  const colors: Record<string, string> = {
    concept: '#6366f1',
    term: '#06b6d4',
    formula: '#f59e0b',
    method: '#10b981',
    example: '#ec4899',
    person: '#8b5cf6',
    event: '#ef4444',
    CONCEPT: '#6366f1',
    PERSON: '#8b5cf6',
    TECHNOLOGY: '#06b6d4',
    METHODOLOGY: '#10b981',
    EXAMPLE: '#ec4899',
  };
  return colors[nodeType] || '#6366f1';
}

/** Highlight matching text with <mark> */
function highlightMatch(text: string, query: string): React.ReactNode {
  if (!query || query.length === 0) return text;

  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="rounded-sm bg-yellow-200 px-0.5 text-gray-900">
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
