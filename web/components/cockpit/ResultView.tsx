"use client";
import type { ColDef } from "ag-grid-community";
import { useMemo } from "react";
import Grid from "@/components/Grid";
import { refusalText, type QueryResult, type ResultRow } from "@/lib/api";
import BarChart from "./BarChart";
import { dimsOf, fmtNum, label, noiseText, rowLabel } from "./format";

const MAX_BARS = 24;

/** One node query result: provenance badges, AG Grid, bar chart, privacy notes. Never raw rows. */
export default function ResultView({ result, title }: { result: QueryResult; title?: string }) {
  const rows = useMemo(() => result.rows ?? [], [result.rows]);
  const dims = useMemo(() => dimsOf(result), [result]);
  const isPaypal = result.node === "paypal" || (!result.exact && result.noise != null);
  const metric = result.metric ?? result.spec?.metric ?? "value";

  const columns = useMemo<ColDef<ResultRow>[]>(() => {
    const digits = metric === "sum_amount" ? 2 : 0;
    const fmtValue = (r: ResultRow | undefined) => {
      const ci = r?.ci95;
      return fmtNum(r?.value, digits) + (typeof ci === "number" ? ` ± ${fmtNum(ci, digits)}` : "");
    };
    const fmtMean = (r: ResultRow | undefined) => {
      const ci = r?.ci95_mean_spend;
      return fmtNum(r?.mean_spend, 2) + (typeof ci === "number" ? ` ± ${fmtNum(ci, 2)}` : "");
    };
    // Number columns are as wide as their widest cell (headers wrap), so "2,972 ± 14" is never cut to "2,9".
    // Label columns may shrink and ellipsize instead: on a phone the numbers matter more.
    const fit = (header: string, cells: string[]) => Math.ceil(Math.max(
      ...header.split(/\s+/).map((w) => w.length * 7.6 + 34), ...cells.map((c) => c.length * 7.8 + 30)));
    const num = { type: "numericColumn", filter: false, wrapHeaderText: true, autoHeaderHeight: true } as const;
    const cols: ColDef<ResultRow>[] = dims.map((d) => ({ field: d, headerName: label(d), flex: 1, minWidth: 64, filter: false }));
    cols.push({
      field: "value",
      headerName: label(metric),
      ...num,
      minWidth: fit(label(metric), rows.map(fmtValue)),
      flex: 1.2,
      valueFormatter: (p) => fmtValue(p.data),
    });
    const first = rows[0] ?? {};
    if ("buyers" in first) cols.push({
      field: "buyers", headerName: "Buyers", ...num, flex: 1,
      minWidth: fit("Buyers", rows.map((r) => fmtNum(r.buyers))), valueFormatter: (p) => fmtNum(p.value),
    });
    if ("mean_spend" in first) cols.push({
      field: "mean_spend",
      headerName: "Mean spend",
      ...num,
      minWidth: fit("Mean spend", rows.map(fmtMean)),
      flex: 1.2,
      valueFormatter: (p) => fmtMean(p.data),
    });
    return cols;
  }, [dims, metric, rows]);

  const chart = useMemo(() => rows
    .filter((r) => typeof r.value === "number")
    // A weekly series reads as a trend in week order; everything else ranks largest first.
    .sort((a, b) => (dims.length === 1 && dims[0] === "week" ? Number(a.week) - Number(b.week) : (b.value as number) - (a.value as number)))
    .slice(0, MAX_BARS)
    .map((r) => ({ label: rowLabel(r, dims), value: r.value as number, ci95: r.ci95 })), [rows, dims]);

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
        <div className="result-body" style={{ minWidth: 0 }}>
          {/* Small results grow with their rows: no inner scrollbar eating the value column. */}
          <Grid<ResultRow> rows={rows} columns={columns} autoHeight={rows.length <= 8} height={320} />
          {chart.length > 1 && (
            <div style={{ minWidth: 0 }}>
              <BarChart data={chart} valueName={label(metric)}
                        title={`${label(metric)} by ${dims.map(label).join(" and ") || "total"}${rows.length > MAX_BARS ? ` (top ${MAX_BARS})` : ""}`} />
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
