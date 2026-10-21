"use client";
import { MAX_DIMENSIONS, NODE_RULES, SKUS, type NodeName, type PlannedSpec, type QueryFilters } from "@/lib/api";
import { label } from "./format";

const REGIONS = ["West", "Central", "East"];
const STORES = ["store_a", "store_b", "store_c", "store_d", "store_e", "store_f"];
const storeName = (id: string) => `Store ${id.replace("store_", "").toUpperCase()}`;
type ListKey = "sku" | "region" | "store_id";

/** One planned query as editable chips: node, metric, up to two dimensions, filters. */
export default function SpecEditor({ value, onChange, onRemove, index }: {
  value: PlannedSpec;
  onChange: (v: PlannedSpec) => void;
  onRemove: () => void;
  index: number;
}) {
  const { node, spec } = value;
  const rules = NODE_RULES[node];
  const f = spec.filters ?? {};

  const setNode = (n: NodeName) => {
    const r = NODE_RULES[n];
    onChange({
      node: n,
      spec: {
        ...spec,
        metric: r.metrics.includes(spec.metric) ? spec.metric : r.metrics[0],
        group_by: spec.group_by.filter((d) => r.dims.includes(d)),
      },
    });
  };
  const setFilters = (nf: QueryFilters) => {
    const clean: QueryFilters = {};
    for (const [k, v] of Object.entries(nf) as [keyof QueryFilters, unknown][]) {
      if (v == null || (Array.isArray(v) && !v.length) || Number.isNaN(v)) continue;
      (clean as Record<string, unknown>)[k] = v;
    }
    onChange({ node, spec: { ...spec, filters: clean } });
  };
  const toggleDim = (d: string) => {
    const has = spec.group_by.includes(d);
    if (!has && spec.group_by.length >= MAX_DIMENSIONS) return;
    onChange({ node, spec: { ...spec, group_by: has ? spec.group_by.filter((x) => x !== d) : [...spec.group_by, d] } });
  };
  const toggleList = (key: ListKey, v: string) => {
    const cur = f[key] ?? [];
    setFilters({ ...f, [key]: cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v] });
  };
  const week = (key: "week_from" | "week_to", s: string) =>
    setFilters({ ...f, [key]: s === "" ? undefined : Math.max(1, parseInt(s, 10)) });

  return (
    <div className={`spec spec-${node}`}>
      <div className="spec-head">
        <span className="tl-n">Q{index + 1}</span>
        <div className="seg" role="group" aria-label="Node">
          {(["brand", "paypal"] as NodeName[]).map((n) => (
            <button key={n} type="button" className={n === node ? "on" : ""} onClick={() => setNode(n)}>
              {n === "brand" ? "Brand node (exact)" : "PayPal-side (private)"}
            </button>
          ))}
        </div>
        <button type="button" className="ghost" onClick={onRemove} aria-label={`Remove query ${index + 1}`}>Remove</button>
      </div>

      <div className="spec-row">
        <span className="spec-label">Metric</span>
        <div className="chips">
          {rules.metrics.map((m) => (
            <button key={m} type="button" className={`chip chip-metric${spec.metric === m ? " on" : ""}`}
                    onClick={() => onChange({ node, spec: { ...spec, metric: m } })}>{label(m)}</button>
          ))}
        </div>
      </div>

      <div className="spec-row">
        <span className="spec-label">Group by <span className="muted">(max {MAX_DIMENSIONS})</span></span>
        <div className="chips">
          {rules.dims.map((d) => {
            const on = spec.group_by.includes(d);
            const disabled = !on && spec.group_by.length >= MAX_DIMENSIONS;
            return (
              <button key={d} type="button" disabled={disabled} className={`chip chip-dim${on ? " on" : ""}`}
                      onClick={() => toggleDim(d)}>{label(d)}</button>
            );
          })}
        </div>
      </div>

      <div className="spec-row">
        <span className="spec-label">Filters</span>
        <div className="chips">
          {SKUS.map((s) => (
            <button key={s} type="button" className={`chip chip-filter${f.sku?.includes(s) ? " on" : ""}`}
                    onClick={() => toggleList("sku", s)}>{s}</button>
          ))}
          <span className="chip-sep" />
          {REGIONS.map((r) => (
            <button key={r} type="button" className={`chip chip-filter${f.region?.includes(r) ? " on" : ""}`}
                    onClick={() => toggleList("region", r)}>{r}</button>
          ))}
          <span className="chip-sep" />
          {STORES.map((s) => (
            <button key={s} type="button" className={`chip chip-filter${f.store_id?.includes(s) ? " on" : ""}`}
                    onClick={() => toggleList("store_id", s)}>{storeName(s)}</button>
          ))}
          <span className="chip-sep" />
          <label className="inline">Weeks
            <input type="number" min={1} max={52} value={f.week_from ?? ""} placeholder="from"
                   onChange={(e) => week("week_from", e.target.value)} />
            –
            <input type="number" min={1} max={52} value={f.week_to ?? ""} placeholder="to"
                   onChange={(e) => week("week_to", e.target.value)} />
          </label>
        </div>
      </div>
      {node === "paypal" && (
        <p className="muted small">Spends privacy budget ({spec.metric === "sum_amount" ? "rho 0.02" : "rho 0.01"}) unless the same query was run before.</p>
      )}
    </div>
  );
}
