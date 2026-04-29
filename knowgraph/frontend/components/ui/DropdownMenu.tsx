'use client';

import { cn } from '@/lib/utils/cn';
import { useState, useRef, useEffect, type ReactNode } from 'react';

interface DropdownItem {
  key: string;
  label: string;
  icon?: ReactNode;
  danger?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

interface DropdownMenuProps {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
}

export function DropdownMenu({ trigger, items, align = 'left' }: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {trigger}
      </button>
      {open && (
        <div
          className={cn(
            'absolute z-50 mt-2 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg',
            'animate-in fade-in zoom-in-95 duration-150',
            align === 'right' ? 'right-0' : 'left-0',
          )}
          role="menu"
        >
          {items.map((item) => (
            <button
              key={item.key}
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                item.onClick();
                setOpen(false);
              }}
              className={cn(
                'flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50',
                item.danger && 'text-red-600 hover:bg-red-50',
                item.disabled && 'cursor-not-allowed opacity-50',
              )}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
