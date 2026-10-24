"use client";
import type { AgChartOptions } from "ag-charts-community";
import { AgCharts } from "ag-charts-react";
import { useMemo, useState, type ReactNode } from "react";
import styles from "./cockpit-charts.module.css";
import { chartTheme, ink, slot } from "./chartTheme";
import { REASONS, reasonName, storeName } from "./names";
import { useDarkMode } from "./useDarkMode";

export type BlockedSummary = {
  current_week: number;
  weeks: number[];
  total: number;
  by_reason: { week: number; reason_code: string; value: number }[];
  by_store: { week: number; store_id: string; value: number }[];
  store_names: Record<string, string>;
};

type Split = "reason" | "store";

/** Stacked weekly columns of blocked checkouts, split by reason or by store (exact brand counts). */
export default function BlockedChart({ data, header, height = 220 }: { data: BlockedSummary; header?: ReactNode; height?: number }) {
  const dark = useDarkMode();
  const [split, setSplit] = useState<Split>("reason");

  const options = useMemo<AgChartOptions>(() => {
    // Entities in a fixed order so a color always means the same reason/store.
    const keys = split === "reason"
      ? [...REASONS, ...new Set(data.by_reason.map((r) => r.reason_code).filter((c) => !(REASONS as readonly string[]).includes(c)))]
      : Object.keys(data.store_names).sort();
    const present = new Set(split === "reason" ? data.by_reason.map((r) => r.reason_code) : data.by_store.map((r) => r.store_id));
    const rows = data.weeks.map((w) => {
      const row: Record<string, number | string> = { week: `Wk ${w}` };
      for (const k of keys) row[k] = 0;
      return row;
    });
    const at = (w: number) => rows[data.weeks.indexOf(w)];
    if (split === "reason") for (const r of data.by_reason) { const row = at(r.week); if (row) row[r.reason_code] = r.value; }
    else for (const r of data.by_store) { const row = at(r.week); if (row) row[r.store_id] = r.value; }
    const c = ink(dark);
    return {
      data: rows,
      theme: chartTheme(dark),
      background: { visible: false },
      padding: { top: 6, right: 4, bottom: 0, left: 0 },
      series: keys.map((k, i) => ({
        type: "bar" as const,
        xKey: "week",
        yKey: k,
        yName: split === "reason" ? reasonName(k) : storeName(k, data.store_names),
        stacked: true,
        fill: slot(i, dark),
        stroke: c.card,
        strokeWidth: 1,
        cornerRadius: 3,
        visible: present.has(k),
        showInLegend: present.has(k),
      })),
      axes: {
        x: { type: "category", position: "bottom", line: { stroke: c.line }, label: { color: c.muted, fontSize: 11 } },
        y: { type: "number", position: "left", nice: true, gridLine: { style: [{ stroke: c.line, lineDash: [3, 3] }] },
             label: { color: c.muted, fontSize: 11 }, interval: { minSpacing: 36 } },
      },
      legend: { position: "top", item: { label: { color: c.fg, fontSize: 12 }, marker: { shape: "square", size: 10 } } },
    };
  }, [data, split, dark]);

  return (
    <div>
      <div className={styles.chartHead}>
        <div className={styles.chartTitle}>{header}</div>
        <div className="seg" role="group" aria-label="Split blocked checkouts by">
          <button type="button" className={split === "reason" ? "on" : ""} aria-pressed={split === "reason"} onClick={() => setSplit("reason")}>By reason</button>
          <button type="button" className={split === "store" ? "on" : ""} aria-pressed={split === "store"} onClick={() => setSplit("store")}>By store</button>
        </div>
      </div>
      <AgCharts options={options} style={{ height, width: "100%" }} />
    </div>
  );
}
