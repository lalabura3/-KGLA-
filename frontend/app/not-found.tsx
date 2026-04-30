import Link from 'next/link';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <span className="text-6xl">🔍</span>
      <h1 className="mt-4 text-2xl font-bold text-gray-900">页面未找到</h1>
      <p className="mt-2 text-gray-500">你访问的页面不存在或已被移除</p>
      <Link
        href="/"
        className="mt-6 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors inline-block"
      >
        返回首页
      </Link>
    </div>
  );
}
