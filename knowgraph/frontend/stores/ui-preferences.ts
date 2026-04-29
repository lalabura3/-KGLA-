import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type GraphMode = 'cluster' | 'focus' | 'path';
export type SidebarState = 'expanded' | 'collapsed';

interface UIPreferences {
  graphMode: GraphMode;
  setGraphMode: (mode: GraphMode) => void;
  sidebar: SidebarState;
  toggleSidebar: () => void;
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIPreferences = create<UIPreferences>()(
  persist(
    (set) => ({
      graphMode: 'cluster',
      setGraphMode: (graphMode) => set({ graphMode }),
      sidebar: 'expanded',
      toggleSidebar: () =>
        set((s) => ({ sidebar: s.sidebar === 'expanded' ? 'collapsed' : 'expanded' })),
      theme: 'system',
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-preferences' },
  ),
);
