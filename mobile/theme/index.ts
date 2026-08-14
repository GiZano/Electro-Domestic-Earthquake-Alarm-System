/**
 * QuakeGuard Design Tokens — Military (dark) ↔ Scientific (light) modes.
 *
 * Dark palette ("MIC mode"): near-black zinc surfaces, terminal accents —
 * green = live/secure, amber = caution threshold, red = seismic alert.
 * Light palette ("RESEARCH mode"): clean scientific surfaces with the same
 * semantic accents shifted to higher-contrast shades for readable on white.
 */

export type ThemeMode = "dark" | "light";

export interface AppColors {
  // Backgrounds / surfaces
  bg: string;
  surface: string;
  surfaceAlt: string;
  border: string;
  borderStrong: string;

  // Text
  text: string;
  textSecondary: string;
  textMuted: string;

  // Accents (terminal semantics)
  live: string;
  caution: string;
  alert: string;
  info: string;

  // Chart specifics
  gridline: string;
  axis: string;
  tick: string;
}

export const darkColors: AppColors = {
  // Backgrounds / surfaces
  bg: "#09090b",           // zinc-950 — app background
  surface: "#101014",      // cards / panels
  surfaceAlt: "#18181b",   // raised surfaces, callouts
  border: "#27272a",       // zinc-800 — hairline borders
  borderStrong: "#3f3f46", // zinc-700 — axis / gridlines

  // Text
  text: "#e4e4e7",         // zinc-200 — primary
  textSecondary: "#a1a1aa",// zinc-400 — technical / labels
  textMuted: "#71717a",    // zinc-500 — hints, timestamps

  // Accents (terminal semantics)
  live: "#10b981",         // emerald-500 — sensor heartbeat / SYSTEM SECURE
  caution: "#f59e0b",      // amber-500 — approaching threshold
  alert: "#ef4444",        // red-500 — seismic alert
  info: "#38bdf8",         // sky-400 — informational accent (AI report)

  // Chart specifics
  gridline: "#27272a",
  axis: "#3f3f46",
  tick: "#a1a1aa",
};

export const lightColors: AppColors = {
  // Backgrounds / surfaces (clean scientific paper look)
  bg: "#f8fafc",           // slate-50 — app background
  surface: "#ffffff",      // cards / panels
  surfaceAlt: "#f1f5f9",   // raised surfaces, callouts
  border: "#e2e8f0",       // slate-200 — hairline borders
  borderStrong: "#cbd5e1", // slate-300 — axis / gridlines

  // Text
  text: "#0f172a",         // slate-900 — primary
  textSecondary: "#475569",// slate-600 — technical / labels
  textMuted: "#94a3b8",    // slate-400 — hints, timestamps

  // Accents (darker for contrast on light)
  live: "#059669",         // emerald-600 — sensor heartbeat / SYSTEM SECURE
  caution: "#d97706",      // amber-600 — approaching threshold
  alert: "#dc2626",        // red-600 — seismic alert
  info: "#0284c7",         // sky-600 — informational accent (AI report)

  // Chart specifics (soft graph-paper lines)
  gridline: "#e2e8f0",
  axis: "#cbd5e1",
  tick: "#64748b",
};

export const THEMES: Record<ThemeMode, AppColors> = {
  dark: darkColors,
  light: lightColors,
};

/** Backwards-compatible alias: static contexts default to the MIC (dark) theme. */
export const COLORS: AppColors = darkColors;

/** Monospace stack used across the technical UI and the chart tick labels. */
export const MONO = "'SpaceMono-Regular', 'Courier New', monospace";

export const FONTS = {
  mono: "SpaceMono-Regular",
} as const;

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
} as const;