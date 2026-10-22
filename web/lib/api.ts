export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Error carrying the HTTP status and parsed body, so pages can show refusals clearly. */
export class ApiError extends Error {
  constructor(public status: number, public body: unknown, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    let body: unknown = text;
    try { body = JSON.parse(text); } catch { /* plain text */ }
    throw new ApiError(res.status, body, `${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

/** Human-readable message from any error thrown by `api`. */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    const b = e.body as { detail?: unknown } | string | null;
    const detail = b && typeof b === "object" && "detail" in b ? b.detail : b;
    if (detail && typeof detail === "object") {
      const d = detail as { refused?: string; detail?: string; error?: string };
      if (d.refused) return refusalText(d.refused) + (d.detail ? ` (${d.detail})` : "");
      if (d.error) return d.error;
      return JSON.stringify(detail);
    }
    if (e.status === 404) return "Not found (the endpoint may not be available yet).";
    return `${e.status}: ${detail || "request failed"}`;
  }
  if (e instanceof Error) return e.message.includes("fetch") ? "Can't reach the TrustLedger API." : e.message;
  return String(e);
}

const REFUSALS: Record<string, string> = {
  BUDGET_EXHAUSTED: "Privacy budget exhausted",
  DIMENSION_NOT_ALLOWED: "Dimension not allowed on this node",
  METRIC_NOT_ALLOWED: "Metric not available on this node",
  TOO_MANY_CELLS: "Too many result cells",
  WRONG_BRAND: "Not your brand's data",
};

export function refusalText(refused: unknown): string {
  if (typeof refused === "string") return REFUSALS[refused] ?? refused;
  if (refused && typeof refused === "object") {
    const r = refused as { refused?: string; detail?: string };
    if (r.refused) return (REFUSALS[r.refused] ?? r.refused) + (r.detail ? ` (${r.detail})` : "");
  }
  return JSON.stringify(refused);
}

export type ScanResult = {
  status: "VERIFIED" | "NOT_VERIFIED";
  checkout_id: string;
  verification_id?: string;
  paypal_order_id: string | null;
  paypal_mode?: string;
  reason?: string;
  reason_code?: string;
  case_id?: string;
};

export type Case = {
  case_id: string;
  store_id: string;
  sku: string;
  serial?: string;
  reason_code: string;
  status: string;
  summary: string | null;
  findings: number;
  confidence?: "low" | "medium" | "high" | string | null;
  created_at: string;
};

export type StepKind = "thought" | "tool_call" | "tool_result" | "finding";
export type Step = { step_id?: string; n: number; kind: StepKind | string; payload: Record<string, unknown>; at: string };
export type CaseDetail = Case & { steps: Step[] };

// ---------------------------------------------------------------- queries and privacy

export type NodeName = "brand" | "paypal";

export type QueryFilters = {
  sku?: string[];
  region?: string[];
  store_id?: string[];
  week_from?: number;
  week_to?: number;
};

/** Mirrors backend/common/query_spec.py. `epsilon` is ignored by the zCDP engine (fixed cost per metric). */
export type QuerySpec = {
  metric: string;
  group_by: string[];
  filters: QueryFilters;
  epsilon?: number;
};

export const NODE_RULES: Record<NodeName, { metrics: string[]; dims: string[] }> = {
  brand: {
    metrics: ["shipped_units", "sold_units", "verification_failures"],
    dims: ["region", "city", "store_id", "sku", "week", "distributor_id", "reason_code"],
  },
  paypal: {
    metrics: ["buyers", "sum_amount"],
    dims: ["region", "city", "store_id", "sku", "week", "age_band", "gender"],
  },
};
export const MAX_DIMENSIONS = 2;

/** PayPal-side budget (zCDP). Older fields are optional so either engine version renders. */
export type Budget = {
  unit?: string;
  spent: number;
  remaining: number;
  total?: number;
  daily?: number;
  eps_equivalent_total?: number;
  queries_left_estimate?: number;
  unlimited_queries?: boolean;
  release_id?: string;
};

export type Noise = {
  mechanism?: string;
  rho?: number;
  eps_equivalent?: number;
  delta?: number;
  k?: number;
  clamp?: number;
  sigma?: number;
  sigma_buyers?: number;
  display_floor?: number;
  epsilon?: number;
};

export type ResultRow = Record<string, unknown> & { value?: number | null; ci95?: number };

/** Shape shared by node query results (case steps) and console results. */
export type QueryResult = {
  node?: NodeName;
  metric?: string;
  group_by?: string[];
  spec?: QuerySpec;
  rows?: ResultRow[];
  refused?: unknown;
  suppressed_cells?: number;
  noise?: Noise;
  exact?: boolean;
  cached?: boolean;
  budget?: Budget;
};

// ---------------------------------------------------------------- console API

export type PlannedSpec = { node: NodeName; spec: QuerySpec };
export type PlanResponse = { specs: PlannedSpec[]; rationale: string };
export type RunResponse = {
  results: QueryResult[];
  budget: Budget;
  explanation: string | null;
};

// ---------------------------------------------------------------- supply chain (Bryntum)

export type SupplyResource = {
  id: string;
  name: string;
  tier: "brand" | "distributor" | "store";
  region: string | null;
  city: string | null;
};

export type SupplyEvent = {
  id: string;
  resource_id: string;
  batch_id: string;
  sku: string;
  kind: "dispatch" | "distributor" | "store" | "off_channel";
  name: string;
  start_week: number;
  end_week: number; // exclusive
  units: number;
  sold?: number;
  highlight: boolean;
};

export type SupplyDependency = {
  id: string;
  from: string;
  to: string;
  type?: "start_to_start" | "end_to_start";
  highlight?: boolean;
};

export type OffChannel = {
  batch_id: string;
  sku: string;
  distributor_id: string;
  channel_store_ids: string[];
  sold_store_id: string;
  units: number;
  first_week: number;
  last_week: number;
};

export type SupplyChain = {
  brand_id: string;
  filters: { sku: string | null; store_id: string | null };
  current_week: number;
  week_range: { from: number; to: number };
  resources: SupplyResource[];
  events: SupplyEvent[];
  dependencies: SupplyDependency[];
  off_channel: OffChannel[];
  totals: { batches: number; units: number; off_channel_units: number };
  exact: boolean;
};

/** Week N of the demo year starts on Monday 2026-01-05 + 7*(N-1) days. */
export function weekToDate(week: number): Date {
  return new Date(2026, 0, 5 + 7 * (week - 1));
}

export const SKUS = ["NMB-P8-128", "NMB-P8-256", "NMB-A5-64"];
