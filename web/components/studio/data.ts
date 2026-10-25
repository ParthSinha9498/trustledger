// AG Studio data sources for the Studio page, built ONLY from GET /console/release/cells:
//   - one table per private-release marginal (M1-M6): noisy group counts with a hidden variance, so
//     Studio can add cells up and still show a correct combined 95% interval;
//   - one table per exact brand count table (B1-B5): business counts (units, failures), not people.
// No buyer rows, no buyer ids. Marginals are NOT related to each other: noise is independent per
// marginal, and variances only add within one marginal.

import type {
  AgDataSourcesDefinition,
  AgExpressionFieldDefinition,
  AgFieldDefinition,
  AgFormatDefinition,
} from 'ag-studio';
import { createFormats } from 'ag-studio';

// ---------------------------------------------------------------- API payload

export type ReleaseCell = Record<string, string | number | boolean | null> & {
  value: number | null;
  ci95: number | null;
  var: number | null;
  suppressed: boolean;
};
export type Marginal = { id: string; title: string; dims: string[]; metric: string; rows: ReleaseCell[] };
export type BrandTable = { id: string; title: string; dims: string[]; rows: (Record<string, string> & { value: number })[] };
export type ReleaseCells = {
  marginals: Marginal[];
  brand_counts: BrandTable[];
  epsilon: number;
  rho_spent: number;
  delta: number | null;
  release_id: string;
};

// ---------------------------------------------------------------- display names

export const PRODUCT_NAMES: Record<string, string> = {
  'NMB-P8-128': 'Nimbus P8 128GB',
  'NMB-P8-256': 'Nimbus P8 256GB',
  'NMB-A5-64': 'Nimbus A5 64GB',
};
const REASONS: Record<string, string> = {
  NOT_IN_CHANNEL: 'Not in channel',
  ALREADY_SOLD: 'Already sold',
  UNKNOWN_SERIAL: 'Unknown serial',
  SKU_MISMATCH: 'Wrong product',
};
const pretty = (id: string) =>
  id.startsWith('store_') ? `Store ${id.slice(6).toUpperCase()}` : id.startsWith('dist_') ? `Distributor ${id.slice(5)}` : id;

/** Dimension -> [Studio field id, field name]. Raw ids become readable names in the data itself. */
const DIM_FIELDS: Record<string, [string, string]> = {
  store_id: ['store', 'Store'],
  sku: ['product', 'Product'],
  week: ['week', 'Week'],
  age_band: ['ageBand', 'Age band'],
  gender: ['gender', 'Gender'],
  distributor_id: ['distributor', 'Distributor'],
  reason_code: ['reason', 'Failure reason'],
};

export type Names = Record<string, string>;

function dimValue(dim: string, raw: unknown, names: Names): string | number | null {
  if (raw == null) return null;
  const v = String(raw);
  switch (dim) {
    case 'store_id':
    case 'distributor_id':
      return names[v] ?? pretty(v);
    case 'sku':
      return PRODUCT_NAMES[v] ?? v;
    case 'reason_code':
      return REASONS[v] ?? v.toLowerCase().replace(/_/g, ' ');
    case 'week':
      return Number(v);
    default:
      return v;
  }
}

// ---------------------------------------------------------------- formats

const num = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 0 });

const numberBase = {
  dataType: 'number' as const,
  supportedRoles: ['numeric' as const],
  serializer: (v: unknown) => v as number,
  deserializer: (v: unknown) => v as number,
};

/**
 * Noisy (differentially private) estimates. Only `sum` is offered: adding noisy cells is plain
 * post-processing, while averages, minimums or counts of noisy cells would be misleading.
 */
export const noisyEstimateFormat: AgFormatDefinition<'number'> = {
  ...numberBase,
  supportedAggregations: ['sum'],
  blankValue: 'hidden',
  createValueFormatter: () => (v) => (v == null ? 'hidden' : num(v)),
} as AgFormatDefinition<'number'>;

/** A 95% interval half-width ("±"). Shown with a ± so nobody reads it as a count. */
export const intervalFormat: AgFormatDefinition<'number'> = {
  ...numberBase,
  supportedAggregations: ['max'],
  blankValue: '',
  createValueFormatter: () => (v) =>
    v == null ? '' : `± ${Math.abs(v) >= 10_000 ? v.toLocaleString(undefined, { notation: 'compact', maximumFractionDigits: 1 }) : num(v)}`,
} as AgFormatDefinition<'number'>;

/** Exact business counts from the brand (units, failures): any aggregation is fine. */
export const formats = createFormats({
  additionalTypes: { noisyEstimateFormat, intervalFormat },
} as never);

// ---------------------------------------------------------------- sources

const MARGINAL_DESCRIPTIONS: Record<string, string> = {
  M1: 'Weekly buyers per store and product.',
  M2: 'Buyers per store and product, split by age band.',
  M3: 'Buyers per store, split by age band and gender.',
  M4: 'Buyers and total spend (USD) per store.',
  M5: 'Weekly buyers per product across all stores.',
  M6: 'Buyers and total spend (USD) per store and product.',
};

const PRIVACY_NOTE =
  ' Every value is a differentially private estimate from a one-time private release (random noise added, ' +
  'small groups hidden as blank). Add estimates with sum only, and report the matching 95% interval measure ' +
  '(its id ends in "_interval"), which combines the cell variances correctly. Never add up per-cell intervals.';

export const intervalMeasureId = (marginalId: string, spend = false) => `${marginalId}_${spend ? 'spend_' : ''}interval`;

function intervalMeasure(m: Marginal, spend: boolean): AgExpressionFieldDefinition {
  // ci95 of a sum of independent Gaussian cells = 1.96 * sqrt(sum of variances).
  const varField = spend ? 'spendVar' : 'var';
  return {
    id: intervalMeasureId(m.id, spend),
    name: spend ? 'Spend ± (95%)' : 'Buyers ± (95%)',
    description:
      `95% interval half-width for a sum of ${m.id} ${spend ? 'spend' : 'buyer'} estimates: ` +
      `1.96 × square root of the summed cell variances. Use it next to sum(${m.id}.${spend ? 'spend' : 'value'}).`,
    format: 'intervalFormat' as never,
    isMeasure: true,
    expression: {
      operator: 'multiply',
      inputs: [
        { type: 'number', value: 1.96 },
        {
          operator: 'power',
          inputs: [{ id: `${m.id}.${varField}`, aggregation: 'sum' }, { type: 'number', value: 0.5 }],
        },
      ],
    } as never,
  };
}

function marginalSource(m: Marginal, names: Names) {
  const spend = m.metric.includes('spend');
  const data = m.rows.map((r) => {
    const row: Record<string, string | number | boolean | null> = {};
    for (const d of m.dims) row[DIM_FIELDS[d]?.[0] ?? d] = dimValue(d, r[d], names);
    row.value = r.value;
    row.ci95 = r.ci95;
    row.var = r.var;
    row.suppressed = r.suppressed;
    row.hiddenGroups = r.suppressed ? 1 : 0;
    if (spend) {
      row.spend = r.spend as number | null;
      row.spendCi95 = r.spend_ci95 as number | null;
      row.spendVar = r.spend_var as number | null;
    }
    return row;
  });
  const fields: AgFieldDefinition[] = [
    ...m.dims.map((d): AgFieldDefinition => {
      const [id, name] = DIM_FIELDS[d] ?? [d, d];
      return { id, name, format: d === 'week' ? 'integerFormat' : 'textFormat' } as unknown as AgFieldDefinition;
    }),
    { id: 'value', name: 'Buyers', format: 'noisyEstimateFormat', description: 'Noisy count of distinct buyers. Blank = hidden small group.' } as unknown as AgFieldDefinition,
    { id: 'ci95', name: 'Cell 95% interval (±)', format: 'intervalFormat', hide: true, description: 'Per-cell interval. Do not add up.' } as unknown as AgFieldDefinition,
    { id: 'var', name: 'Cell noise variance', format: 'noisyEstimateFormat', hide: true, description: 'Used only by the interval measure.' } as unknown as AgFieldDefinition,
    { id: 'suppressed', name: 'Hidden small group', format: 'booleanFormat', description: 'True when the group was too small to show.' } as unknown as AgFieldDefinition,
    { id: 'hiddenGroups', name: 'Hidden groups', format: 'integerFormat', description: '1 for each hidden group; sum it to see how many groups a total leaves out.' } as unknown as AgFieldDefinition,
  ];
  if (spend) {
    fields.push(
      { id: 'spend', name: 'Spend USD', format: 'noisyEstimateFormat', description: 'Noisy total spend in USD (each buyer capped).' } as unknown as AgFieldDefinition,
      { id: 'spendCi95', name: 'Cell spend 95% interval (±)', format: 'intervalFormat', hide: true } as unknown as AgFieldDefinition,
      { id: 'spendVar', name: 'Cell spend noise variance', format: 'noisyEstimateFormat', hide: true } as unknown as AgFieldDefinition,
    );
  }
  return {
    source: {
      id: m.id,
      name: `${m.id} · ${m.title}`,
      description: (MARGINAL_DESCRIPTIONS[m.id] ?? m.title) + PRIVACY_NOTE,
      data,
      fields,
    },
    expressions: [intervalMeasure(m, false), ...(spend ? [intervalMeasure(m, true)] : [])],
  };
}

function brandSource(b: BrandTable, names: Names) {
  const data = b.rows.map((r) => {
    const row: Record<string, string | number | null> = {};
    for (const d of b.dims) row[DIM_FIELDS[d]?.[0] ?? d] = dimValue(d, r[d], names);
    row.value = r.value;
    return row;
  });
  const fields: AgFieldDefinition[] = [
    ...b.dims.map((d): AgFieldDefinition => {
      const [id, name] = DIM_FIELDS[d] ?? [d, d];
      return { id, name, format: d === 'week' ? 'integerFormat' : 'textFormat' } as unknown as AgFieldDefinition;
    }),
    { id: 'value', name: 'Count (exact)', format: 'integerFormat', description: 'Exact business count from the brand.' } as unknown as AgFieldDefinition,
  ];
  return {
    id: b.id,
    name: `${b.id} · ${b.title}`,
    description: `${b.title}. Exact counts from the brand's own records; they describe stores and products, not people.`,
    data,
    fields,
  };
}

export function buildStudioData(cells: ReleaseCells, names: Names): AgDataSourcesDefinition {
  const marg = cells.marginals.map((m) => marginalSource(m, names));
  return {
    description:
      'TrustLedger brand insights for the fictional brand Nimbus (phones sold through six stores). ' +
      'Tables M1-M6 are a one-time differentially private release of PayPal-side buyer statistics ' +
      `(epsilon about ${cells.epsilon} at delta ${cells.delta ?? '1e-8'}): noisy estimates with 95% intervals, small groups hidden. ` +
      'Tables B1-B5 are exact counts from the brand (units shipped and sold, verification failures). ' +
      'There is no buyer-level data anywhere: never claim a fact about one person. Tables are independent: do not join them.',
    sources: [...marg.map((m) => m.source), ...cells.brand_counts.map((b) => brandSource(b, names))],
    expressions: marg.flatMap((m) => m.expressions),
    formats,
  } as AgDataSourcesDefinition;
}

// ---------------------------------------------------------------- local query (the analyst's tool)

export type QueryRow = Record<string, string | number | null>;

/**
 * Group one release table by some of its dimensions, with optional equality filters. For marginals:
 * estimate = sum of shown cells, interval = 1.96 * sqrt(sum of variances), plus how many cells were hidden.
 * Pure function over the already-loaded release cells: no new noise, no budget.
 */
export function queryRelease(
  cells: ReleaseCells,
  names: Names,
  tableId: string,
  groupBy: string[],
  filters: Record<string, string>,
): { table: string; kind: 'estimate' | 'exact'; rows: QueryRow[] } | { error: string } {
  const m = cells.marginals.find((x) => x.id === tableId);
  const b = cells.brand_counts.find((x) => x.id === tableId);
  const t = m ?? b;
  if (!t) return { error: `Unknown table ${tableId}. Use one of ${[...cells.marginals, ...cells.brand_counts].map((x) => x.id).join(', ')}.` };
  const byField = Object.fromEntries(t.dims.map((d) => [DIM_FIELDS[d]?.[0] ?? d, d]));
  for (const g of [...groupBy, ...Object.keys(filters)]) {
    if (!byField[g]) return { error: `${tableId} has no dimension "${g}". Its dimensions: ${Object.keys(byField).join(', ')}.` };
  }
  const groups = new Map<string, { key: QueryRow; value: number; var: number; spend: number; spendVar: number; hidden: number; cells: number }>();
  for (const r of t.rows as Record<string, unknown>[]) {
    const show = (f: string) => dimValue(byField[f], r[byField[f]], names);
    if (Object.entries(filters).some(([f, v]) => String(show(f)).toLowerCase() !== String(v).toLowerCase())) continue;
    const key: QueryRow = Object.fromEntries(groupBy.map((g) => [g, show(g)]));
    const k = JSON.stringify(key);
    const acc = groups.get(k) ?? { key, value: 0, var: 0, spend: 0, spendVar: 0, hidden: 0, cells: 0 };
    acc.cells += 1;
    if (m) {
      if (r.suppressed) acc.hidden += 1;
      else {
        acc.value += Number(r.value ?? 0);
        acc.var += Number(r.var ?? 0);
        acc.spend += Number(r.spend ?? 0);
        acc.spendVar += Number(r.spend_var ?? 0);
      }
    } else acc.value += Number(r.value ?? 0);
    groups.set(k, acc);
  }
  const spend = !!m?.metric.includes('spend');
  const rows = [...groups.values()].map((g): QueryRow => {
    if (!m) return { ...g.key, count_exact: g.value };
    const allHidden = g.hidden === g.cells;
    const out: QueryRow = {
      ...g.key,
      buyers_estimate: allHidden ? null : Math.round(g.value),
      buyers_interval_95: allHidden ? null : Math.round(1.96 * Math.sqrt(g.var) * 10) / 10,
      hidden_small_groups: g.hidden,
    };
    if (spend) {
      out.spend_usd_estimate = allHidden ? null : Math.round(g.spend);
      out.spend_interval_95 = allHidden ? null : Math.round(1.96 * Math.sqrt(g.spendVar));
    }
    return out;
  });
  return { table: tableId, kind: m ? 'estimate' : 'exact', rows };
}

/** Field ids and titles of every table, for the analyst's prompt. */
export function tableCatalogue(cells: ReleaseCells): string {
  const line = (id: string, title: string, dims: string[], kind: string) =>
    `- ${id} (${kind}): ${title}. Dimensions: ${dims.map((d) => DIM_FIELDS[d]?.[0] ?? d).join(', ')}`;
  return [
    ...cells.marginals.map((m) => line(m.id, m.title, m.dims, m.metric.includes('spend') ? 'noisy buyers + spend' : 'noisy buyers')),
    ...cells.brand_counts.map((b) => line(b.id, b.title, b.dims, 'exact count')),
  ].join('\n');
}
