'use client';

import Link from 'next/link';
import { useAuth } from '@/providers/AuthProvider';
import { Button } from '@/components/ui';
import { ROUTES } from '@/lib/constants';

export function Header() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href={ROUTES.HOME} className="flex items-center gap-2 font-bold text-xl text-indigo-600">
          📚 LearnGraph
        </Link>
        <nav className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              <Link href={ROUTES.DASHBOARD}>
                <Button variant="ghost" size="sm">仪表盘</Button>
              </Link>
              <Link href={ROUTES.HISTORY}>
                <Button variant="ghost" size="sm">历史</Button>
              </Link>
              <Button variant="outline" size="sm" onClick={logout}>退出</Button>
            </>
          ) : (
            <Button variant="primary" size="sm">登录</Button>
          )}
        </nav>
      </div>
    </header>
  );
}
