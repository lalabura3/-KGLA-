'use client';

import { cn } from '@/lib/utils/cn';
import Link from 'next/link';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
  separator?: string;
}

export function Breadcrumb({ items, className, separator = '/' }: BreadcrumbProps) {
  return (
    <nav aria-label="面包屑导航" className={cn('flex items-center', className)}>
      <ol className="flex items-center gap-1.5 text-sm">
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} className="flex items-center gap-1.5">
              {i > 0 && (
                <span className="text-gray-400 select-none" aria-hidden="true">
                  {separator}
                </span>
              )}
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="text-gray-500 hover:text-primary-600 transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  className={cn(
                    isLast ? 'font-medium text-gray-900' : 'text-gray-500',
                  )}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
