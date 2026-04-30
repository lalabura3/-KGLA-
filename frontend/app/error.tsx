'use client';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <h1 className="text-2xl font-bold text-gray-900">出了点问题</h1>
      <p className="mt-2 text-gray-500">{error.message || '页面加载失败，请稍后重试'}</p>
      <button
        onClick={reset}
        className="mt-6 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        重试
      </button>
    </div>
  );
}
