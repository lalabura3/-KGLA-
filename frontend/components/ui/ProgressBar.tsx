import { cn } from '@/lib/utils/cn';

interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  className?: string;
  showValue?: boolean;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  className,
  showValue = false,
}: ProgressBarProps) {
  const pct = Math.min(Math.round((value / max) * 100), 100);

  return (
    <div className={cn('w-full', className)}>
      {(label || showValue) && (
        <div className="mb-1 flex justify-between text-sm">
          {label && <span className="text-gray-600">{label}</span>}
          {showValue && <span className="text-gray-500">{pct}%</span>}
        </div>
      )}
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-gray-200"
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        aria-label={label || '进度'}
      >
        <div
          className="h-full rounded-full bg-indigo-600 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
