import { cn } from '@/lib/utils/cn';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const sizeStyles = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-10 w-10 border-3',
};

export function Spinner({ size = 'md', className, label = '加载中' }: SpinnerProps) {
  return (
    <div
      className={cn(
        'animate-spin rounded-full border-gray-200 border-t-indigo-600',
        sizeStyles[size],
        className,
      )}
      role="status"
      aria-label={label}
    >
      <span className="sr-only">{label}</span>
    </div>
  );
}
