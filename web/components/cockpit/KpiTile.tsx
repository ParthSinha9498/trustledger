"use client";
import type { AgChartOptions } from "ag-charts-community";
import { AgCharts } from "ag-charts-react";
import { useMemo, type ReactNode } from "react";
import styles from "./cockpit-charts.module.css";
import { chartTheme, ink } from "./chartTheme";
import { useDarkMode } from "./useDarkMode";

export type Spark = { kind: "spark"; points: { x: string; y: number }[]; name: string };
export type Donut = { kind: "donut"; segments: { label: string; value: number; color: (dark: boolean) => string }[]; name: string };

/** KPI tile: big number, plain label, one line of context, and a small AG Chart when the data supports it. */
export default function KpiTile({ value, label, sub, chart, tone }: {
  value: ReactNode;
  label: string;
  sub?: ReactNode;
  chart?: Spark | Donut | null;
  tone?: "bad" | "ok" | "accent";
}) {
  const dark = useDarkMode();
  const options = useMemo<AgChartOptions | null>(() => {
    if (!chart) return null;
    const c = ink(dark);
    const base = { theme: chartTheme(dark), background: { visible: false }, padding: { top: 2, right: 2, bottom: 2, left: 2 },
                   legend: { enabled: false } };
    if (chart.kind === "spark") {
      const color = tone === "bad" ? c.bad : tone === "ok" ? c.ok : c.accent;
      return {
        ...base,
        data: chart.points,
        series: [{ type: "area", xKey: "x", yKey: "y", yName: chart.name, fill: color, fillOpacity: 0.16,
                   stroke: color, strokeWidth: 2, marker: { enabled: false } }],
        axes: {
          x: { type: "category", position: "bottom", label: { enabled: false }, line: { enabled: false },
               gridLine: { enabled: false }, paddingInner: 0, paddingOuter: 0 },
          y: { type: "number", position: "left", label: { enabled: false }, line: { enabled: false },
               gridLine: { enabled: false }, min: 0 },
        },
      };
    }
    const segs = chart.segments.filter((s) => s.value > 0);
    return {
      ...base,
      data: segs.map((s) => ({ label: s.label, value: s.value })),
      series: [{ type: "donut", angleKey: "value", legendItemKey: "label",
                 innerRadiusRatio: 0.62, fills: segs.map((s) => s.color(dark)), strokes: segs.map(() => c.card),
                 strokeWidth: 2, sectorLabel: { enabled: false }, calloutLabel: { enabled: false } }],
    };
  }, [chart, dark, tone]);

  const hasData = chart && (chart.kind === "spark" ? chart.points.some((p) => p.y > 0) : chart.segments.some((s) => s.value > 0));
  return (
    <div className={`${styles.kpi} ${tone ? styles[`kpi_${tone}`] : ""}`}>
      <div className={styles.kpiText}>
        <div className={styles.kpiValue}>{value}</div>
        <div className={styles.kpiLabel}>{label}</div>
        {sub && <div className={styles.kpiSub}>{sub}</div>}
      </div>
      {options && hasData && (
        <div className={chart?.kind === "donut" ? styles.kpiDonut : styles.kpiSpark} role="img" aria-label={chart?.name}>
          <AgCharts options={options} style={{ height: "100%", width: "100%" }} />
        </div>
      )}
    </div>
  );
}
