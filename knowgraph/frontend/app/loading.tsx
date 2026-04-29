import { Skeleton } from '@/components/ui';

export default function LoadingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <div className="flex items-center gap-2">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-indigo-600" />
        <span className="text-lg text-gray-500">加载中…</span>
      </div>
      <div className="w-64 space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  );
}
