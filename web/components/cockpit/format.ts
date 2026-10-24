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

/** Plain-language privacy note for a PayPal-side result. The ± on each value carries the numbers. */
export function noiseText(n?: Noise): string | null {
  if (!n) return null;
  return n.display_floor != null ? "Small random noise added · tiny groups hidden" : "Small random noise added";
}

/** Display names for the fictional catalogue (mirrors backend seed PRODUCTS). */
export const PRODUCT_NAMES: Record<string, string> = {
  "NMB-P8-128": "Nimbus P8 128GB", "NMB-P8-256": "Nimbus P8 256GB", "NMB-A5-64": "Nimbus A5 64GB",
};
export const productName = (sku: string) => PRODUCT_NAMES[sku] ?? sku;

/** "store_a" -> "Store A" when no name is known. */
export function prettyId(id: string): string {
  const m = id.match(/^(store|dist)_(\w+)$/i);
  if (!m) return id;
  return `${m[1].toLowerCase() === "store" ? "Store" : "Distributor"} ${m[2].toUpperCase()}`;
}

export const REASON_TEXT: Record<string, string> = {
  NOT_IN_CHANNEL: "Not in this store's supply chain",
  ALREADY_SOLD: "Serial already sold",
  UNKNOWN_SERIAL: "Unknown serial",
  SKU_MISMATCH: "Serial belongs to a different product",
};

export function budgetTotal(b: Budget): number {
  return b.total ?? b.daily ?? b.spent + b.remaining;
}
