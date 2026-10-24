"use client";
import "./supply-chain.css";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { api, errorText, SKUS, type SupplyChain } from "@/lib/api";
import OffChannelTable, { offChannelSummary } from "./OffChannelTable";
import { productName } from "./format";

// Bryntum touches the DOM, so it only renders in the browser.
const Timeline = dynamic(() => import("./Timeline"), {
  ssr: false,
  loading: () => <div className="sc-loading muted">Loading timeline…</div>,
});

const LEGEND: [string, string][] = [
  ["#4f46e5", "Sent out by the brand"],
  ["#2563eb", "At the distributor"],
  ["#0d9488", "At the store it was shipped to"],
  ["#d92d20", "Sold at a store it was never shipped to"],
];

function useNarrow(query = "(max-width: 700px)"): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(query);
    setNarrow(mq.matches);
    const on = (e: MediaQueryListEvent) => setNarrow(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return narrow;
}

export default function SupplyChainPage() {
  const [sku, setSku] = useState("");
  const [store, setStore] = useState("");
  const [data, setData] = useState<SupplyChain | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const narrow = useNarrow();

  useEffect(() => {
    let live = true;
    const qs = new URLSearchParams();
    if (sku) qs.set("sku", sku);
    if (store) qs.set("store_id", store);
    setErr(null);
    api<SupplyChain>(`/supply-chain${qs.size ? `?${qs}` : ""}`)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(errorText(e)));
    return () => { live = false; };
  }, [sku, store]);

  // The brand's partner list is the same whatever the filter, so it also feeds the store picker.
  const names = useMemo(() => new Map((data?.resources ?? []).map((r) => [r.id, r.name])), [data?.resources]);
  const stores = useMemo(() => (data?.resources ?? []).filter((r) => r.tier === "store"), [data?.resources]);
  const off = useMemo(() => data?.off_channel ?? [], [data?.off_channel]);
  const focus = useMemo(() => (off.length && !showAll ? new Set(off.map((o) => o.batch_id)) : null), [off, showAll]);

  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Supply chain</h1>
          <p className="muted">
            Where each batch went: from the brand, to a distributor, to the stores it was shipped to. Red marks
            units that sold at a store the brand never shipped that batch to.
          </p>
        </div>
      </div>
      <section className="card elevated sc-panel">
        <div className="row filters sc-filters">
          <label>Product
            <select value={sku} onChange={(e) => setSku(e.target.value)}>
              <option value="">All products</option>
              {SKUS.map((s) => <option key={s} value={s}>{productName(s)}</option>)}
            </select>
          </label>
          <label>Store
            <select value={store} onChange={(e) => setStore(e.target.value)}>
              <option value="">All stores</option>
              {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
        </div>

        {err && <div className="refusal">Supply chain unavailable: {err}</div>}
        {!err && !data && <div className="sc-loading muted">Loading supply chain…</div>}
        {!err && data && (
          <>
            <div className="stat-row">
              <Stat label="Batches" value={data.totals.batches} />
              <Stat label="Units shipped" value={data.totals.units} />
              <Stat label="Units sold where they weren't shipped" value={data.totals.off_channel_units}
                bad={data.totals.off_channel_units > 0} />
            </div>

            <div className="sc-section">
              <h2>Units sold where they weren&apos;t shipped</h2>
              {off.length ? (
                <>
                  <p className="sc-summary sc-summary-bad">{offChannelSummary(off, names)}</p>
                  <OffChannelTable rows={off} names={names} narrow={narrow} />
                </>
              ) : (
                <p className="sc-summary muted">Every unit in this view sold at a store its batch was shipped to.</p>
              )}
            </div>

            <div className="sc-section">
              <div className="sc-head">
                <h2>Timeline</h2>
                {off.length > 0 && !narrow && (
                  <div className="seg" role="group" aria-label="Batches on the timeline">
                    <button type="button" className={showAll ? "" : "on"} aria-pressed={!showAll}
                      onClick={() => setShowAll(false)}>Only those batches</button>
                    <button type="button" className={showAll ? "on" : ""} aria-pressed={showAll}
                      onClick={() => setShowAll(true)}>All batches</button>
                  </div>
                )}
              </div>
              {narrow ? (
                <p className="sc-mobile-note muted">
                  The week-by-week timeline needs a wider screen. The table above lists every batch that sold
                  somewhere it wasn&apos;t shipped to.
                </p>
              ) : !data.events.length ? (
                <p className="muted">No batches match this filter.</p>
              ) : (
                <>
                  <div className="sc-legend" aria-label="Legend">
                    {LEGEND.map(([c, t]) => (
                      <span key={t}><span className="sc-swatch" style={{ background: c }} />{t}</span>
                    ))}
                    <span><span className="sc-now" aria-hidden />This week</span>
                  </div>
                  <Timeline data={data} focusBatches={focus} />
                  <p className="sc-note muted">
                    {focus
                      ? `Showing the ${focus.size} batches in the table, and every place they passed through. Lines follow each batch from the brand to the distributor to the stores.`
                      : "Lines follow each batch from the brand to the distributor to the stores. Scroll sideways for earlier weeks."}
                  </p>
                </>
              )}
            </div>

            <p className="muted sc-note">
              The brand&apos;s own shipping records (batches, shipments, units sold per store), visible only to this
              brand. No serial numbers or buyer data.
            </p>
          </>
        )}
      </section>
    </main>
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
