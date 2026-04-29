'use client';

import { cn } from '@/lib/utils/cn';

interface PaginationProps {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
  className?: string;
  showTotal?: boolean;
}

export function Pagination({
  current,
  total,
  pageSize,
  onChange,
  className,
  showTotal = true,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (totalPages <= 1) return null;

  const pages = getPageNumbers(current, totalPages);

  return (
    <nav
      className={cn('flex items-center justify-between', className)}
      aria-label="分页导航"
    >
      {showTotal && (
        <p className="text-sm text-gray-600">
          共 {total} 条，第 {current} / {totalPages} 页
        </p>
      )}
      <div className="flex items-center gap-1">
        <button
          className="rounded-lg px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={current === 1}
          onClick={() => onChange(current - 1)}
          aria-label="上一页"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M10 12L6 8l4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {pages.map((page, i) =>
          page === '...' ? (
            <span key={`dots-${i}`} className="px-1 text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onChange(page as number)}
              className={cn(
                'min-w-[2rem] rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors',
                page === current
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100',
              )}
              aria-current={page === current ? 'page' : undefined}
            >
              {page}
            </button>
          ),
        )}

        <button
          className="rounded-lg px-2.5 py-1.5 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
          disabled={current === totalPages}
          onClick={() => onChange(current + 1)}
          aria-label="下一页"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M6 12l4-4-4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </nav>
  );
}

/** Generate page number array with ellipsis */
function getPageNumbers(current: number, total: number): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  const pages: (number | '...')[] = [];

  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i);
    pages.push('...');
    pages.push(total);
  } else if (current >= total - 3) {
    pages.push(1);
    pages.push('...');
    for (let i = total - 4; i <= total; i++) pages.push(i);
  } else {
    pages.push(1);
    pages.push('...');
    for (let i = current - 1; i <= current + 1; i++) pages.push(i);
    pages.push('...');
    pages.push(total);
  }

  return pages;
}
