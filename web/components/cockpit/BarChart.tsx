"use client";
import type { AgChartOptions } from "ag-charts-community";
import { AgCharts } from "ag-charts-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { slot } from "./chartTheme";  // also registers the Community modules
import styles from "./cockpit-charts.module.css";
import { useDarkMode } from "./useDarkMode";

// Community only (no Enterprise key): bar charts, no map series or error bars, so ± ranges live in the tooltip.

/** One category on the axis. Each series key holds a number; `<key>__ci` holds its ± range when there is one. */
export type BarDatum = { label: string } & Record<string, string | number | undefined>;
export type BarSeries = { key: string; name: string };

/** Below this width a ranking always runs sideways and a trend thins its ticks. */
const NARROW = 520;

const fmt = (v: unknown) => (typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "");

/** Bar chart with recessive axes. One series ranks in one hue; several (e.g. one per product) group side by side.
 *  When category labels would not fit under their columns, a ranking turns its bars sideways (labels left of each
 *  bar, wrapped, never rotated); an ordered axis (weeks, age bands) keeps its columns and shows fewer, unrotated ticks. */
export default function BarChart({ data, series, title, height = 240, ordered = false }: {
  data: BarDatum[];
  series: BarSeries[];
  title?: string;
  height?: number;
  /** Categories have a natural order (weeks, age bands): keep vertical columns in that order. */
  ordered?: boolean;
}) {
  const dark = useDarkMode();
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const narrow = width > 0 && width < NARROW;
  // Labels under columns get one band each and wrap to about two lines (~6px per character at 11px).
  const longest = Math.max(0, ...data.map((d) => d.label.length));
  const band = width > 0 ? (width - 60) / Math.max(1, data.length) : Infinity;
  const crowded = (longest * 6.2) / 2 > band;
  const sideways = !ordered && (narrow || crowded);
  const multi = series.length > 1;
  const row = (narrow ? 40 : 32) + (multi ? 12 * (series.length - 1) : 0);  // px per category when sideways
  const chartHeight = sideways ? Math.max(height, data.length * row + 50 + (multi ? 30 : 0)) : height;

  const options = useMemo<AgChartOptions>(() => {
    const muted = dark ? "#94a3b8" : "#64748b";
    const categoryLabel = sideways
      ? { autoRotate: false, wrapping: "on-space" as const, truncate: true, fontSize: 11, color: muted }
      : narrow || crowded
        ? { autoRotate: false, avoidCollisions: true, minSpacing: 8, wrapping: "never" as const, fontSize: 11, color: muted }
        : { fontSize: 11, color: muted };
    return {
      data,
      theme: dark ? "ag-default-dark" : "ag-default",
      background: { fill: "transparent" },
      padding: { top: 8, right: 8, bottom: 8, left: 8 },
      series: series.map((s, i) => ({
        type: "bar" as const,
        direction: sideways ? "horizontal" as const : "vertical" as const,
        xKey: "label",
        yKey: s.key,
        yName: s.name,
        fill: multi ? slot(i, dark) : dark ? "#7aa2ff" : "#1f4fd1",
        cornerRadius: 4,
        tooltip: {
          renderer: ({ datum }: { datum: BarDatum }) => {
            const ci = datum[`${s.key}__ci`];
            return {
              heading: String(datum.label),
              title: s.name,
              data: [{ label: "Value", value: fmt(datum[s.key]) + (typeof ci === "number" ? ` ± ${fmt(ci)}` : "") }],
            };
          },
        },
      })),
      axes: {
        x: {
          type: "category",
          position: sideways ? "left" : "bottom",
          label: categoryLabel,
          // Label column: up to 40% of the card; longer labels wrap or end in an ellipsis (full text in the tooltip).
          ...(sideways ? { thickness: Math.min(220, Math.round(width * 0.4)) } : {}),
        },
        y: {
          type: "number",
          position: sideways ? "bottom" : "left",
          nice: true,
          label: { fontSize: 11, color: muted, formatter: ({ value }: { value: unknown }) => fmt(value) },
          ...(narrow ? { interval: { minSpacing: 48 } } : {}),
        },
      },
      legend: multi
        ? { enabled: true, position: "top", item: { label: { fontSize: 12 }, marker: { shape: "square", size: 10 } } }
        : { enabled: false },
    } as AgChartOptions;
  }, [data, series, multi, dark, narrow, crowded, sideways, width]);

  return (
    <div ref={box} style={{ width: "100%", minWidth: 0 }}>
      {/* Title in HTML so it wraps on a phone instead of being cut off inside the canvas. */}
      {title && data.length > 0 && <div className={styles.barTitle}>{title}</div>}
      {data.length > 0 && (width > 0
        ? <AgCharts options={options} style={{ height: chartHeight, width: "100%" }} />
        : <div style={{ height }} />)}
    </div>
  );
}
