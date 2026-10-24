import { weekToDate } from "@/lib/api";

/** Display names for the demo catalogue (same names the store checkout shows). */
export const PRODUCT_NAMES: Record<string, string> = {
  "NMB-P8-128": "Nimbus P8 128GB",
  "NMB-P8-256": "Nimbus P8 256GB",
  "NMB-A5-64": "Nimbus A5 64GB",
};

export const productName = (sku: string) => PRODUCT_NAMES[sku] ?? sku;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "7 Sep" for the Monday that starts the given demo week. */
export function weekLabel(week: number): string {
  const d = weekToDate(week);
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

/** "Northline Distribution, Crestway Supply and Store C" */
export function joinNames(names: string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
