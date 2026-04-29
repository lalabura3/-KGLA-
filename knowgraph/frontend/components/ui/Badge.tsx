import { cn } from '@/lib/utils/cn';

type Status = 'success' | 'warning' | 'error' | 'info' | 'neutral';

const statusStyles: Record<Status, string> = {
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  neutral: 'bg-gray-100 text-gray-600',
};

interface BadgeProps {
  children: React.ReactNode;
  status?: Status;
  className?: string;
}

export function Badge({ children, status = 'neutral', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        statusStyles[status],
        className,
      )}
    >
      {children}
    </span>
  );
}
