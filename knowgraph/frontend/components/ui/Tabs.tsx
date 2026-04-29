'use client';

import { cn } from '@/lib/utils/cn';
import { useState, type ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
  disabled?: boolean;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
  className?: string;
  onChange?: (tabId: string) => void;
}

export function Tabs({ tabs, defaultTab, className, onChange }: TabsProps) {
  const [active, setActive] = useState(defaultTab || tabs[0]?.id || '');

  const handleChange = (id: string) => {
    setActive(id);
    onChange?.(id);
  };

  const activeTab = tabs.find((t) => t.id === active);

  return (
    <div className={className}>
      <div className="flex border-b border-gray-200" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.id === active}
            aria-controls={`tabpanel-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => !tab.disabled && handleChange(tab.id)}
            className={cn(
              'px-4 py-2.5 text-sm font-medium transition-colors',
              'border-b-2 -mb-px',
              tab.id === active
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700',
              tab.disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab && (
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab.id}`}
          aria-labelledby={activeTab.id}
          className="pt-4"
        >
          {activeTab.content}
        </div>
      )}
    </div>
  );
}
