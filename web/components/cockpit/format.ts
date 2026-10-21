import type { Budget, Noise, QueryResult, ResultRow } from "@/lib/api";

export const DIM_LABELS: Record<string, string> = {
  region: "Region", city: "City", store_id: "Store", sku: "Product", week: "Week",
  distributor_id: "Distributor", reason_code: "Reason", age_band: "Age band", gender: "Gender",
};
export const METRIC_LABELS: Record<string, string> = {
  shipped_units: "Shipped units", sold_units: "Sold units", verification_failures: "Verification failures",
  buyers: "Buyers", sum_amount: "Spend (USD)",
};
export const label = (k: string) => DIM_LABELS[k] ?? METRIC_LABELS[k] ?? k;

export function fmtNum(v: unknown, digits = 0): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return v == null ? "" : String(v);
  return v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

/** Dimension columns in a result: group_by when present, else every non-measure key. */
export function dimsOf(result: QueryResult): string[] {
  if (result.group_by?.length) return result.group_by;
  if (result.spec?.group_by?.length) return result.spec.group_by;
  const first = result.rows?.[0];
  if (!first) return [];
  return Object.keys(first).filter((k) => !MEASURES.has(k));
}
export const MEASURES = new Set(["value", "ci95", "buyers", "mean_spend"]);

export function rowLabel(row: ResultRow, dims: string[]): string {
  return dims.length ? dims.map((d) => String(row[d] ?? "")).join(" · ") : "Total";
}

/** "Gaussian noise σ=14.1, cells under 28 hidden" */
export function noiseText(n?: Noise): string | null {
  if (!n) return null;
  const parts: string[] = [];
  const mech = n.mechanism ? n.mechanism.charAt(0).toUpperCase() + n.mechanism.slice(1) : "DP";
  if (n.sigma != null) parts.push(`${mech} noise σ=${fmtNum(n.sigma, 1)}`);
  else if (n.epsilon != null) parts.push(`${mech} noise ε=${n.epsilon}`);
  else parts.push(`${mech} noise`);
  if (n.display_floor != null) parts.push(`cells under ${fmtNum(n.display_floor, 0)} hidden`);
  return parts.join(", ");
}

export function budgetTotal(b: Budget): number {
  return b.total ?? b.daily ?? b.spent + b.remaining;
}
