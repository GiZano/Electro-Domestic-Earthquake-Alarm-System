import { create } from 'zustand';
import type { ThemeMode } from '../theme';

interface ThemeState {
  /** "dark" = MIC mode (military command), "light" = RESEARCH mode (scientific). */
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  themeMode: 'dark',
  setThemeMode: (themeMode) => set({ themeMode }),
  toggleTheme: () => set((state) => ({ themeMode: state.themeMode === 'dark' ? 'light' : 'dark' })),
}));
