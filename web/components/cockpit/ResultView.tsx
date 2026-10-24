"use client";
import type { ColDef } from "ag-grid-community";
import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import Grid from "@/components/Grid";
import { refusalText, type QueryResult, type ResultRow } from "@/lib/api";
import BarChart, { type BarDatum, type BarSeries } from "./BarChart";
import { dimsOf, displayValue, fmtNum, label, NAMED_DIMS, noiseText, rowLabel } from "./format";
import { useEntityNames } from "./useEntityNames";

const MAX_BARS = 24;
/** Dimensions with a natural order: the chart keeps that order (as the table does) instead of ranking. */
const ORDERED = new Set(["week", "age_band"]);
const SCROLLBAR = 16;

function useSize(ref: RefObject<HTMLElement | null>, mounted: boolean): { w: number; h: number } {
  const [size, setSize] = useState({ w: 0, h: 0 });
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setSize({ w: Math.round(e.contentRect.width), h: Math.round(e.contentRect.height) }));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, mounted]);
  return size;
}

/** Rendered width of a grid cell's text (13px, the grid's font). Falls back to an estimate before the DOM exists. */
let ctx: CanvasRenderingContext2D | null = null;
function textWidth(text: string, bold = false): number {
  if (typeof document === "undefined") return text.length * 7.6;
  ctx ??= document.createElement("canvas").getContext("2d");
  if (!ctx) return text.length * 7.6;
  ctx.font = `${bold ? 600 : 400} 13px ${getComputedStyle(document.body).fontFamily}`;
  return ctx.measureText(text).width;
}

const orderKey = (d: string, v: unknown) => (d === "week" ? Number(v) : String(v ?? ""));
const byOrder = (d: string) => (a: unknown, b: unknown) => {
  const x = orderKey(d, a), y = orderKey(d, b);
  return x < y ? -1 : x > y ? 1 : 0;
};

/** One node query result: provenance badges, AG Grid, bar chart, privacy notes. Never raw rows. */
export default function ResultView({ result, title }: { result: QueryResult; title?: string }) {
  const rows = useMemo(() => result.rows ?? [], [result.rows]);
  const dims = useMemo(() => dimsOf(result), [result]);
  const isPaypal = result.node === "paypal" || (!result.exact && result.noise != null);
  const metric = result.metric ?? result.spec?.metric ?? "value";
  const names = useEntityNames({ stores: dims.includes("store_id"), distributors: dims.includes("distributor_id") });

  const gridBox = useRef<HTMLDivElement>(null);
  const bodyBox = useRef<HTMLDivElement>(null);
  const grid = useSize(gridBox, rows.length > 0);
  const body = useSize(bodyBox, rows.length > 0);
  // Small results grow with their rows: no inner scrollbar eating the value column.
  const autoHeight = rows.length <= 12;
  const dense = grid.w > 0 && grid.w < 520;

  const columns = useMemo<ColDef<ResultRow>[]>(() => {
    // Spend shows cents only for small sums: "1,912,801 ± 13,859" carries no false precision and fits a phone.
    const digits = metric === "sum_amount" && rows.some((r) => typeof r.value === "number" && Math.abs(r.value) < 1000) ? 2 : 0;
    const pad = dense ? 12 : 32;  // horizontal cell padding, both sides (Grid's dense theme: 6px a side)
    // "1,207 ± 26": the only break is before "±", so a narrow cell wraps to "1,207" over "± 26", never "± 2".
    const withCi = (v: unknown, ci: unknown, dg: number) =>
      fmtNum(v, dg) + (typeof ci === "number" ? ` ±\u00a0${fmtNum(ci, dg)}` : "");
    const fmtValue = (r: ResultRow | undefined) => withCi(r?.value, r?.ci95, digits);
    const fmtMean = (r: ResultRow | undefined) => withCi(r?.mean_spend, r?.ci95_mean_spend, 2);
    // Number columns are as wide as their widest cell (headers wrap), so a value and its range are never cut.
    // Label columns may shrink and wrap instead: on a phone the numbers matter more.
    const fit = (header: string, cells: string[]) => Math.ceil(Math.max(
      ...header.split(/\s+/).map((w) => textWidth(w, true) + pad + 8), ...cells.map((c) => textWidth(c) + pad + 4)));
    const parts = (cells: string[]) => cells.flatMap((c) => c.split(" ±").map((x, i) => (i ? `±${x}` : x)));

    // Ids and codes ("store_b", "NOT_IN_CHANNEL") show as names; the raw value stays in the tooltip.
    // Longer names get a wider share of the row; short names ("Store B") keep one line, long ones may wrap
    // down to 64px, so the row still fits a phone.
    const longest = (d: string) => Math.max(label(d).length, ...rows.map((r) => displayValue(d, r[d], names).length));
    const share = (d: string) => Math.min(3, Math.max(1, longest(d) / 12));
    const dimCols: ColDef<ResultRow>[] = dims.map((d) => ({
      headerName: label(d), flex: share(d), filter: false,
      minWidth: longest(d) <= 12 ? fit(label(d), rows.map((r) => displayValue(d, r[d], names))) : 56,
      wrapText: true, autoHeight: true, cellStyle: { lineHeight: "1.35", paddingTop: "8px", paddingBottom: "8px" },
      ...(NAMED_DIMS.has(d) ? {
        colId: d,
        valueGetter: (p) => displayValue(d, p.data?.[d], names),
        tooltipValueGetter: (p) => {
          const raw = p.data?.[d];
          return raw != null && String(raw) !== p.value ? String(raw) : undefined;
        },
      } : { field: d }),
    } as ColDef<ResultRow>));

    const first = rows[0] ?? {};
    const nums: { def: ColDef<ResultRow>; header: string; cells: string[] }[] = [
      { def: { field: "value", flex: 1.2, valueFormatter: (p) => fmtValue(p.data) }, header: label(metric), cells: rows.map(fmtValue) },
    ];
    if ("buyers" in first) nums.push({
      def: { field: "buyers", flex: 1, valueFormatter: (p) => fmtNum(p.value) }, header: "Buyers", cells: rows.map((r) => fmtNum(r.buyers)),
    });
    if ("mean_spend" in first) nums.push({
      def: { field: "mean_spend", flex: 1.2, valueFormatter: (p) => fmtMean(p.data) }, header: "Mean spend", cells: rows.map(fmtMean),
    });
    // One line when everything fits the grid's width; otherwise the range drops to a second line.
    const dimMin = dimCols.reduce((n, c) => n + (c.minWidth ?? 64), 0);
    const oneLine = nums.reduce((n, c) => n + fit(c.header, c.cells), 0);
    const twoLines = !!grid.w && dimMin + oneLine + (autoHeight ? 0 : SCROLLBAR) > grid.w;
    const numMins = nums.map(({ header, cells }) => (twoLines ? fit(header, parts(cells)) : fit(header, cells)));
    // Still too wide (a phone with three number columns): label columns give up width first, down to their
    // longest single word, so the row fits the card and nothing scrolls sideways.
    if (twoLines) {
      let over = dimMin + numMins.reduce((n, w) => n + w, 0) + (autoHeight ? 0 : SCROLLBAR) + 2 - grid.w;
      dimCols.forEach((c, i) => {
        if (over <= 0) return;
        const d = dims[i];
        const floor = fit(label(d), rows.flatMap((r) => displayValue(d, r[d], names).split(/\s+/)));
        const cut = Math.min(over, Math.max(0, (c.minWidth ?? 64) - floor));
        c.minWidth = (c.minWidth ?? 64) - cut;
        over -= cut;
      });
    }
    const numCols: ColDef<ResultRow>[] = nums.map(({ def, header }, i) => ({
      ...def, headerName: header, type: "numericColumn", filter: false, wrapHeaderText: true, autoHeaderHeight: true,
      minWidth: numMins[i],
      ...(twoLines ? { wrapText: true, autoHeight: true, cellStyle: { lineHeight: "1.35", paddingTop: "8px", paddingBottom: "8px" } } : {}),
    }));
    return [...dimCols, ...numCols];
  }, [dims, metric, rows, names, grid.w, autoHeight, dense]);

  // Chart: ordered dimensions (weeks, age bands) keep their order; anything else ranks largest first.
  // Two dimensions with an ordered first one (age band × product) become grouped bars, one series per product.
  const chart = useMemo((): { data: BarDatum[]; series: BarSeries[]; ordered: boolean; cut: boolean } => {
    const valued = rows.filter((r) => typeof r.value === "number");
    const [d0, d1] = dims;
    const ordered = !!d0 && ORDERED.has(d0);
    const seriesVals = d1 ? [...new Set(valued.map((r) => String(r[d1])))] : [];
    if (ordered && dims.length === 2 && seriesVals.length >= 2 && seriesVals.length <= 4) {
      const cats = [...new Set(valued.map((r) => r[d0]))].sort(byOrder(d0));
      const series = seriesVals.map((v, i) => ({ key: `s${i}`, name: displayValue(d1, v, names) }));
      const data = cats.slice(0, MAX_BARS).map((c) => {
        const datum: BarDatum = { label: displayValue(d0, c, names) };
        valued.filter((r) => r[d0] === c).forEach((r) => {
          const i = seriesVals.indexOf(String(r[d1]));
          datum[`s${i}`] = r.value as number;
          if (typeof r.ci95 === "number") datum[`s${i}__ci`] = r.ci95;
        });
        return datum;
      });
      return { data, series, ordered: true, cut: cats.length > MAX_BARS };
    }
    const sorted = ordered && dims.length === 1
      ? [...valued].sort((a, b) => byOrder(d0)(a[d0], b[d0]))
      : [...valued].sort((a, b) => (b.value as number) - (a.value as number));
    return {
      data: sorted.slice(0, MAX_BARS).map((r) => ({ label: rowLabel(r, dims, names), value: r.value as number, value__ci: r.ci95 })),
      series: [{ key: "value", name: label(metric) }],
      ordered: ordered && dims.length === 1,
      cut: sorted.length > MAX_BARS,
    };
  }, [rows, dims, names, metric]);
  // Side by side (wide card): the chart is as tall as the table beside it, so a 2-row table leaves no empty block.
  const sideBySide = grid.w > 0 && body.w > 0 && grid.w < body.w * 0.75;
  const chartHeight = sideBySide ? Math.min(340, Math.max(170, grid.h - 30)) : 240;

  if (result.refused) {
    return (
      <div className="refusal" role="alert">
        <strong>Refused:</strong> {refusalText(result.refused)}
        <div className="muted">The node declined this query. Nothing was released.</div>
      </div>
    );
  }

  return (
    <div className="result">
      <div className="badges">
        {title && <span className="result-title">{title}</span>}
        {isPaypal ? <span className="badge badge-dp">PayPal-side · privacy-protected estimate</span>
          : <span className="badge badge-exact">Brand-side · exact count</span>}
        {result.cached && <span className="badge badge-cached">Repeat question: nothing new revealed</span>}
      </div>
      {rows.length === 0 ? (
        <p className="muted">Nothing to show{result.suppressed_cells ? ": every group was too small to show safely" : ""}.</p>
      ) : (
        // min-width 0 all the way down: on a phone the grid and chart shrink to the card instead of overflowing it.
        <div className="result-body" ref={bodyBox} style={{ minWidth: 0 }}>
          <div ref={gridBox} style={{ minWidth: 0 }}>
            <Grid<ResultRow> rows={rows} columns={columns} autoHeight={autoHeight} height={320} dense={dense} />
          </div>
          {chart.data.length > 1 && (
            <div style={{ minWidth: 0 }}>
              <BarChart data={chart.data} series={chart.series} ordered={chart.ordered} height={chartHeight}
                        title={`${label(metric)} by ${dims.map(label).join(" and ") || "total"}${chart.cut ? ` (${chart.ordered ? "first" : "top"} ${MAX_BARS})` : ""}`} />
            </div>
          )}
        </div>
      )}
      <p className="muted result-notes">
        {isPaypal ? (
          <>
            {noiseText(result.noise) ?? "Small random noise added"}
            {result.suppressed_cells ? ` · ${result.suppressed_cells} small group${result.suppressed_cells === 1 ? "" : "s"} hidden` : ""}
            {rows.some((r) => typeof r.ci95 === "number") ? " · ± shows the likely range" : ""}
          </>
        ) : "Exact count (about businesses, not people): serials, shipments, stores."}
      </p>
    </div>
  );
}
