"use client";
import { AllCommunityModule, ModuleRegistry, type AgChartOptions } from "ag-charts-community";
import { AgCharts } from "ag-charts-react";
import { useMemo } from "react";
import { useDarkMode } from "./useDarkMode";

// Community only (no Enterprise key): bar charts, no map series or error bars.
ModuleRegistry.registerModules([AllCommunityModule]);

export type BarDatum = { label: string; value: number; ci95?: number };

/** One-series bar chart: one hue, thin rounded bars, recessive axes. */
export default function BarChart({ data, title, valueName = "value", height = 240 }: {
  data: BarDatum[];
  title?: string;
  valueName?: string;
  height?: number;
}) {
  const dark = useDarkMode();
  const options = useMemo<AgChartOptions>(() => ({
    data,
    theme: dark ? "ag-default-dark" : "ag-default",
    background: { fill: "transparent" },
    title: title ? { text: title, fontSize: 13, fontWeight: 600 } : undefined,
    padding: { top: 8, right: 8, bottom: 8, left: 8 },
    series: [{
      type: "bar",
      xKey: "label",
      yKey: "value",
      yName: valueName,
      fill: dark ? "#7aa2ff" : "#1f4fd1",
      cornerRadius: 4,
    }],
    legend: { enabled: false },
  }), [data, title, valueName, dark]);
  if (!data.length) return null;
  return <AgCharts options={options} style={{ height, width: "100%" }} />;
}
