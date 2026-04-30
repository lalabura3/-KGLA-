'use client';

import { cn } from '@/lib/utils/cn';
import { useUIPreferences } from '@/stores/ui-preferences';

export function Sidebar() {
  const { sidebar } = useUIPreferences();

  return (
    <aside
      className={cn(
        'hidden border-r border-gray-200 bg-white transition-all duration-300 lg:block',
        sidebar === 'expanded' ? 'w-64' : 'w-0 overflow-hidden border-r-0',
      )}
      aria-label="侧边导航"
    >
      <div className="flex h-full flex-col p-4">
        <nav className="flex flex-col gap-2">
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              学习记录
            </p>
          </div>
        </nav>
      </div>
    </aside>
  );
}
