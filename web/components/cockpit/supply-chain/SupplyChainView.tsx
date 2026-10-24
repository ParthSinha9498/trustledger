"use client";
import "./supply-chain.css";
import dynamic from "next/dynamic";
import { useMemo, useState, type ReactNode } from "react";
import type { SupplyChain } from "@/lib/api";
import OffChannelTable, { offChannelSummary } from "./OffChannelTable";

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

/** Stats, the off-channel table and the Bryntum timeline for one supply-chain response.
 *  Used by the supply chain page and, filtered to the case's store and product, by the case page. */
export default function SupplyChainView({ data, narrow, nested = false, mobileNote }: {
  data: SupplyChain;
  narrow: boolean;
  /** Inside another card section (case page): smaller headings. */
  nested?: boolean;
  /** Replaces the default "needs a wider screen" note on a phone. */
  mobileNote?: ReactNode;
}) {
  const [showAll, setShowAll] = useState(false);
  const names = useMemo(() => new Map(data.resources.map((r) => [r.id, r.name])), [data.resources]);
  const off = data.off_channel;
  const focus = useMemo(() => (off.length && !showAll ? new Set(off.map((o) => o.batch_id)) : null), [off, showAll]);
  const H = nested ? "h3" : "h2";

  return (
    <div className={`sc-view${nested ? " sc-nested" : ""}`}>
      <div className="stat-row">
        <Stat label="Batches" value={data.totals.batches} />
        <Stat label="Units shipped" value={data.totals.units} />
        <Stat label="Units sold where they weren't shipped" value={data.totals.off_channel_units}
          bad={data.totals.off_channel_units > 0} />
      </div>

      <div className="sc-section">
        <H>Units sold where they weren&apos;t shipped</H>
        {off.length ? (
          <>
            <p className="sc-summary sc-summary-bad">{offChannelSummary(off, names)}</p>
            <OffChannelTable rows={off} names={names} narrow={narrow} />
          </>
        ) : data.totals.batches === 0 ? (
          <p className="sc-summary muted">No batches in this view.</p>
        ) : (
          <p className="sc-summary muted">Every unit in this view sold at a store its batch was shipped to.</p>
        )}
      </div>

      <div className="sc-section">
        <div className="sc-head">
          <H>Timeline</H>
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
          <div className="sc-mobile-note muted">
            {mobileNote ?? <>The week-by-week timeline needs a wider screen. The table above lists every batch that
              sold somewhere it wasn&apos;t shipped to.</>}
          </div>
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
                ? `Showing the ${focus.size} batch${focus.size === 1 ? "" : "es"} in the table, and every place they passed through. Lines follow each batch from the brand to the distributor to the stores.`
                : "Lines follow each batch from the brand to the distributor to the stores. Scroll sideways for earlier weeks."}
            </p>
          </>
        )}
      </div>

      <p className="muted sc-note">
        The brand&apos;s own shipping records (batches, shipments, units sold per store), visible only to this
        brand. No serial numbers or buyer data.
      </p>
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
