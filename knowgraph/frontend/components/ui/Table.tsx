import { cn } from '@/lib/utils/cn';
import type { ReactNode } from 'react';

export interface TableColumn<T> {
  key: string;
  header: string;
  accessor: (row: T) => ReactNode;
  className?: string;
  headerClassName?: string;
  sortable?: boolean;
}

interface TableProps<T> {
  columns: TableColumn<T>[];
  data: T[];
  keyExtractor: (row: T) => string;
  onRowClick?: (row: T) => void;
  className?: string;
  emptyMessage?: string;
  loading?: boolean;
  loadingRows?: number;
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  className,
  emptyMessage = '暂无数据',
  loading = false,
  loadingRows = 5,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className={cn('w-full overflow-x-auto rounded-xl border border-gray-200', className)}>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-3 font-medium text-gray-600',
                    col.headerClassName,
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: loadingRows }).map((_, i) => (
              <tr key={i} className="border-b border-gray-100">
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="skeleton-shimmer h-4 w-3/4 rounded" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 py-16',
          className,
        )}
      >
        <svg
          className="mb-3 h-10 w-10 text-gray-300"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p className="text-sm text-gray-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={cn('w-full overflow-x-auto rounded-xl border border-gray-200', className)}>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  'px-4 py-3 font-medium text-gray-600',
                  col.headerClassName,
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.map((row) => (
            <tr
              key={keyExtractor(row)}
              className={cn(
                'bg-white transition-colors',
                onRowClick && 'cursor-pointer hover:bg-gray-50',
              )}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((col) => (
                <td key={col.key} className={cn('px-4 py-3 text-gray-700', col.className)}>
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
