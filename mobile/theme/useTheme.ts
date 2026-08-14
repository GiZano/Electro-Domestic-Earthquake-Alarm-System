import { THEMES, type AppColors, type ThemeMode } from "./index";
import { useThemeStore } from "../store/useThemeStore";

export interface AppTheme {
  mode: ThemeMode;
  isDark: boolean;
  colors: AppColors;
}

/** Reactive access to the active palette (MIC dark / RESEARCH light). */
export function useAppTheme(): AppTheme {
  const mode = useThemeStore((state) => state.themeMode);
  return { mode, isDark: mode === "dark", colors: THEMES[mode] };
}