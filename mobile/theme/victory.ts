import type { AppColors } from "./index";
import { MONO, darkColors } from "./index";

/**
 * Builds the custom QuakeGuard Victory theme from a palette — military dark or
 * research light. No VictoryTheme.material: a technical-instrument aesthetic
 * with transparent canvas, hairline axes, faint horizontal gridlines only, and
 * monospaced tick labels so the seismograph reads like a precision terminal.
 */
export function createQuakeGuardTheme(colors: AppColors) {
  return {
    chart: {
      background: "transparent",
      padding: { top: 8, bottom: 34, left: 46, right: 12 },
    },
    axis: {
      style: {
        axis: {
          stroke: "transparent",
          strokeWidth: 0,
        },
        ticks: {
          stroke: colors.axis,
          strokeWidth: 1,
          size: 4,
          padding: 4,
        },
        grid: {
          stroke: "transparent",
          strokeWidth: 0,
        },
        tickLabels: {
          fontFamily: MONO,
          fontSize: 10,
          fill: colors.tick,
          padding: 6,
        },
      },
    },
    dependentAxis: {
      style: {
        axis: {
          stroke: "transparent",
          strokeWidth: 0,
        },
        ticks: {
          stroke: colors.axis,
          strokeWidth: 1,
          size: 4,
          padding: 4,
        },
        // Weak horizontal gridlines only (the "paper" of the seismograph).
        grid: {
          stroke: colors.gridline,
          strokeWidth: 1,
          strokeDasharray: "4 6",
        },
        tickLabels: {
          fontFamily: MONO,
          fontSize: 10,
          fill: colors.tick,
          padding: 6,
        },
      },
    },
    line: {
      style: {
        data: {
          stroke: colors.live,
          strokeWidth: 2,
        },
        labels: {
          fontFamily: MONO,
          fontSize: 10,
          fill: colors.tick,
        },
      },
    },
  };
}

/** MIC-mode (dark) theme, kept for static/backward-compatible usage. */
export const quakeGuardTheme = createQuakeGuardTheme(darkColors);