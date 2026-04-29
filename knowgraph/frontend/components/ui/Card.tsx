import { cn } from '@/lib/utils/cn';
import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
  onClick?: () => void;
}

const paddings = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export function Card({ children, className, padding = 'md', hover, onClick }: CardProps) {
  const Component = onClick ? 'button' : 'div';
  return (
    <Component
      className={cn(
        'w-full rounded-xl border border-gray-200 bg-white shadow-sm',
        paddings[padding],
        hover && 'transition-shadow hover:shadow-md',
        onClick && 'cursor-pointer text-left',
        className,
      )}
      onClick={onClick}
    >
      {children}
    </Component>
  );
}
