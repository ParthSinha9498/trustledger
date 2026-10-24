import { AllCommunityModule, ModuleRegistry, type AgChartTheme } from "ag-charts-community";

// Community only (no Enterprise key): bar, area, line and donut series. No map series or error bars.
ModuleRegistry.registerModules([AllCommunityModule]);

/** Categorical slots in fixed order (validated light/dark steps). Color follows the entity, never its rank. */
const SLOTS_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"];
const SLOTS_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"];
export const slot = (i: number, dark: boolean) => (dark ? SLOTS_DARK : SLOTS_LIGHT)[i % SLOTS_LIGHT.length];

/** Ink and surfaces matching globals.css (canvas can't read CSS variables). */
export const ink = (dark: boolean) => dark
  ? { fg: "#f1f5f9", muted: "#94a3b8", line: "#222b3c", card: "#131924", accent: "#60a5fa", ok: "#10b981", warn: "#fbbf24", bad: "#f87171", neutral: "#475569" }
  : { fg: "#0f172a", muted: "#64748b", line: "#e2e8f0", card: "#ffffff", accent: "#2563eb", ok: "#047857", warn: "#b45309", bad: "#b91c1c", neutral: "#cbd5e1" };

export function chartTheme(dark: boolean): AgChartTheme {
  const c = ink(dark);
  return {
    baseTheme: dark ? "ag-default-dark" : "ag-default",
    params: {
      fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      backgroundColor: "transparent",
      foregroundColor: c.fg,
      textColor: c.fg,
      subtleTextColor: c.muted,
      axisLineColor: c.line,
      tooltipBackgroundColor: c.card,
      tooltipTextColor: c.fg,
    },
  };
}
