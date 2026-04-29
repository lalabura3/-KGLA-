import { cn } from '@/lib/utils/cn';
import type { ReactNode } from 'react';

type TagColor =
  | 'indigo'
  | 'blue'
  | 'green'
  | 'yellow'
  | 'red'
  | 'pink'
  | 'purple'
  | 'teal'
  | 'gray';

const colorStyles: Record<TagColor, string> = {
  indigo: 'bg-indigo-100 text-indigo-700',
  blue: 'bg-blue-100 text-blue-700',
  green: 'bg-green-100 text-green-700',
  yellow: 'bg-yellow-100 text-yellow-700',
  red: 'bg-red-100 text-red-700',
  pink: 'bg-pink-100 text-pink-700',
  purple: 'bg-purple-100 text-purple-700',
  teal: 'bg-teal-100 text-teal-700',
  gray: 'bg-gray-100 text-gray-600',
};

const dotStyles: Record<TagColor, string> = {
  indigo: 'bg-indigo-500',
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
  pink: 'bg-pink-500',
  purple: 'bg-purple-500',
  teal: 'bg-teal-500',
  gray: 'bg-gray-400',
};

interface TagProps {
  children: ReactNode;
  color?: TagColor;
  size?: 'sm' | 'md';
  dot?: boolean;
  onClick?: () => void;
  onRemove?: () => void;
  className?: string;
}

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

export function Tag({
  children,
  color = 'gray',
  size = 'sm',
  dot = false,
  onClick,
  onRemove,
  className,
}: TagProps) {
  const Component = onClick ? 'button' : 'span';

  return (
    <Component
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        colorStyles[color],
        sizeStyles[size],
        onClick && 'cursor-pointer hover:opacity-80 transition-opacity',
        className,
      )}
      onClick={onClick}
      type={onClick ? 'button' : undefined}
    >
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', dotStyles[color])} />}
      {children}
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 rounded-full p-0.5 opacity-60 hover:opacity-100 hover:bg-black/10"
          aria-label="移除标签"
          type="button"
        >
          <svg width="10" height="10" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </Component>
  );
}

/** Color mapping for knowledge node types → Tag color */
export const nodeTypeColor: Record<string, TagColor> = {
  concept: 'indigo',
  term: 'teal',
  formula: 'yellow',
  method: 'green',
  example: 'pink',
  person: 'purple',
  event: 'red',
};
