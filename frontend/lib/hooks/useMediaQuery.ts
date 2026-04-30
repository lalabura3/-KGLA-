'use client';

import { useEffect, useState } from 'react';

/**
 * 响应式媒体查询 Hook
 *
 * @example
 * const isMobile = useMediaQuery('(max-width: 768px)');
 * const isDark = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);

    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

/** 预定义断点查询 */
export const BREAKPOINTS = {
  sm: '(min-width: 640px)',
  md: '(min-width: 768px)',
  lg: '(min-width: 1024px)',
  xl: '(min-width: 1280px)',
  '2xl': '(min-width: 1536px)',
} as const;

/** 预定义断点 hooks */
export function useIsMobile() {
  return !useMediaQuery(BREAKPOINTS.md);
}

export function useIsTablet() {
  return useMediaQuery(BREAKPOINTS.md) && !useMediaQuery(BREAKPOINTS.lg);
}

export function useIsDesktop() {
  return useMediaQuery(BREAKPOINTS.lg);
}
