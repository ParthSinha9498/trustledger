"use client";
import { useEffect, useState } from "react";
import { api, errorText, type SupplyChain } from "@/lib/api";
import SupplyTimeline from "./SupplyTimelineClient";

/** Fetches the brand's own supply chain (exact business data) and renders the Bryntum timeline. */
export default function SupplyChainPanel({ sku, storeId, compact = false }: {
  sku?: string; storeId?: string; compact?: boolean;
}) {
  const [data, setData] = useState<SupplyChain | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const qs = new URLSearchParams();
    if (sku) qs.set("sku", sku);
    if (storeId) qs.set("store_id", storeId);
    setErr(null);
    api<SupplyChain>(`/supply-chain${qs.size ? `?${qs}` : ""}`)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(errorText(e)));
    return () => { live = false; };
  }, [sku, storeId]);

  if (err) return <div className="refusal">Supply chain unavailable: {err}</div>;
  if (!data) return <div className="supply-timeline-loading muted">Loading supply chain…</div>;

  return (
    <div className="supply-panel">
      <div className="stat-row">
        <Stat label="Batches" value={data.totals.batches} />
        <Stat label="Units" value={data.totals.units} />
        <Stat label="Sold off-channel" value={data.totals.off_channel_units} bad={data.totals.off_channel_units > 0} />
      </div>
      <Legend />
      {data.events.length ? <SupplyTimeline data={data} compact={compact} /> :
        <p className="muted">No batches match this filter.</p>}
      {data.off_channel.length > 0 && (
        <ul className="divergence-list">
          {data.off_channel.map((o) => (
            <li key={`${o.batch_id}:${o.sold_store_id}`}>
              <span className="dot dot-bad" aria-hidden />
              Batch <b>{o.batch_id}</b> ({o.sku}) went through <b>{o.distributor_id}</b> to{" "}
              {o.channel_store_ids.join(", ")}, but <b>{o.units}</b> units sold at <b>{o.sold_store_id}</b>{" "}
              (weeks {o.first_week}–{o.last_week}). Earliest observed point of divergence in the available
              evidence: after {o.distributor_id}.
            </li>
          ))}
        </ul>
      )}
      <p className="muted">Exact brand-side business data (batches, shipments, store counts), visible only to this brand. No serials or buyer data.</p>
    </div>
  );
}

function Stat({ label, value, bad }: { label: string; value: number; bad?: boolean }) {
  return (
    <div className={`stat${bad ? " stat-bad" : ""}`}>
      <div className="stat-value">{value.toLocaleString()}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function Legend() {
  const items: [string, string][] = [
    ["#4f46e5", "Dispatched by brand"],
    ["#2563eb", "Held at distributor"],
    ["#0d9488", "In channel at store"],
    ["#d92d20", "Sold outside the batch's channel"],
  ];
  return (
    <div className="legend" aria-label="Legend">
      {items.map(([c, t]) => (
        <span key={t} className="legend-item"><span className="swatch" style={{ background: c }} />{t}</span>
      ))}
      <span className="legend-item muted">Arrows follow the chain: brand → distributor → store</span>
    </div>
  );
}
