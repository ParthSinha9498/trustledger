/** Display names for ids shown in the cockpit. Unknown ids fall back to a readable form, never a raw code. */

export const REASONS = ["NOT_IN_CHANNEL", "ALREADY_SOLD", "UNKNOWN_SERIAL", "SKU_MISMATCH"] as const;
export const REASON_LABEL: Record<string, string> = {
  NOT_IN_CHANNEL: "Not in channel", ALREADY_SOLD: "Already sold",
  UNKNOWN_SERIAL: "Unknown serial", SKU_MISMATCH: "Wrong product",
};
export const reasonName = (code?: string | null) =>
  code ? REASON_LABEL[code] ?? code.toLowerCase().replace(/_/g, " ") : "Unknown reason";

export const PRODUCT_NAME: Record<string, string> = {
  "NMB-P8-128": "Nimbus P8 128GB", "NMB-P8-256": "Nimbus P8 256GB", "NMB-A5-64": "Nimbus A5 64GB",
};
export const productName = (sku?: string | null) => (sku ? PRODUCT_NAME[sku] ?? sku : "");

/** "store_b" -> "Store B" unless the platform gave us a name. */
export const storeName = (id?: string | null, names?: Record<string, string>) =>
  !id ? "" : names?.[id] ?? (id.startsWith("store_") ? `Store ${id.slice(6).toUpperCase()}` : id);

/** Short, stable case reference: "case_d25d92d08e" -> "#D25D92". */
export const shortCase = (id: string) => `#${id.replace(/^case_/, "").slice(0, 6).toUpperCase()}`;
