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
    const cols: ColDef<ResultRow>[] = dims.map((d) => ({ field: d, headerName: label(d) }));
    cols.push({
      field: "value",
      headerName: label(metric),
      type: "numericColumn",
      minWidth: 180,
      flex: 1.5,
      valueFormatter: (p) => {
        const ci = p.data?.ci95;
        return fmtNum(p.value, metric === "sum_amount" ? 2 : 0) + (typeof ci === "number" ? ` ± ${fmtNum(ci, metric === "sum_amount" ? 2 : 0)}` : "");
      },
    });
    const first = rows[0] ?? {};
    if ("buyers" in first) cols.push({ field: "buyers", headerName: "Buyers", type: "numericColumn", minWidth: 140, flex: 1.2, valueFormatter: (p) => fmtNum(p.value) });
    if ("mean_spend" in first) cols.push({ field: "mean_spend", headerName: "Mean spend", type: "numericColumn", minWidth: 140, flex: 1.2, valueFormatter: (p) => fmtNum(p.value, 2) });
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
        {isPaypal ? <span className="badge badge-dp">PayPal-side · differentially private</span>
          : <span className="badge badge-exact">Brand-side · exact business aggregate</span>}
        {result.cached && <span className="badge badge-cached">cached, no budget spent</span>}
      </div>
      {rows.length === 0 ? (
        <p className="muted">No cells to show{result.suppressed_cells ? " (all suppressed)" : ""}.</p>
      ) : (
        <div className="result-body">
          <Grid<ResultRow> rows={rows} columns={columns} height={Math.min(320, 48 + rows.length * 34)} />
          {chart.length > 1 && (
            <BarChart data={chart} valueName={label(metric)}
                      title={`${label(metric)} by ${dims.map(label).join(" and ") || "total"}${rows.length > MAX_BARS ? ` (top ${MAX_BARS})` : ""}`} />
          )}
        </div>
      )}
      <p className="muted result-notes">
        {isPaypal ? (
          <>
            {noiseText(result.noise) ?? "Noisy release"}
            {result.suppressed_cells ? ` · ${result.suppressed_cells} cell${result.suppressed_cells === 1 ? "" : "s"} suppressed` : ""}
            {rows.some((r) => typeof r.ci95 === "number") ? " · ± is the 95% interval" : ""}
            {result.budget ? ` · budget left ${fmtNum(result.budget.remaining, 3)}` : ""}
          </>
        ) : "Exact counts about businesses (serials, shipments, stores). No noise, no budget."}
      </p>
    </div>
  );
}
