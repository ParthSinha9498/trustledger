"use client";
import "./supply-chain.css";
import dynamic from "next/dynamic";
import { useMemo, useState, type ReactNode } from "react";
import type { SupplyChain } from "@/lib/api";
import { joinNames } from "../format";
import OffChannelTable, { offChannelSummary } from "./OffChannelTable";
import type { StoryStep } from "./Timeline";

// Bryntum touches the DOM, so it only renders in the browser.
const Timeline = dynamic(() => import("./Timeline"), {
  ssr: false,
  loading: () => <div className="sc-loading muted">Loading timeline…</div>,
});

const LEGEND: [string, string][] = [
  ["#4f46e5", "Sent out by the brand"],
  ["#2563eb", "At the distributor"],
  ["#0d9488", "Shipped to this store"],
  ["#d92d20", "Sold at a store it wasn't shipped to"],
];

/** "Stores A, D and F" when every name is "Store X"; otherwise the plain list of names. */
function storeList(names: string[]): string {
  if (names.length > 1 && names.every((n) => /^Store \S+$/.test(n))) return `Stores ${joinNames(names.map((n) => n.slice(6)))}`;
  return joinNames(names);
}

/** The three "What you're looking at" lines, built only from this response. Null when nothing sold off-route. */
export function leakStory(data: SupplyChain): [string, string, string] | null {
  const off = data.off_channel;
  if (!off.length) return null;
  const names = new Map(data.resources.map((r) => [r.id, r.name]));
  const name = (id: string) => names.get(id) ?? id;
  const batches = new Set(off.map((o) => o.batch_id)).size;
  const dists = [...new Set(off.map((o) => o.distributor_id))];
  const channel = [...new Set(off.flatMap((o) => o.channel_store_ids))].sort();
  const sold = [...new Set(off.map((o) => o.sold_store_id))].sort();
  const units = data.totals.off_channel_units;
  const distText = joinNames(dists.map(name));

  // "never supplies" only when, in this response, the distributor shipped no batch to that store. The response holds
  // every batch shipped to the filtered store (or to every store when unfiltered), so the check is complete for it.
  const batchDist = new Map(data.events.filter((e) => e.kind === "distributor").map((e) => [e.batch_id, e.resource_id]));
  const supplied = new Set(data.events.filter((e) => e.kind === "store").map((e) => `${batchDist.get(e.batch_id)}>${e.resource_id}`));
  const complete = !data.filters.store_id || sold.includes(data.filters.store_id);
  const never = dists.length === 1 && complete && sold.every((s) => !supplied.has(`${dists[0]}>${s}`));

  return [
    `${batches === 1 ? "This batch was" : `These ${batches} batches were`} shipped by ${distText} to ${storeList(channel.map(name))}.`,
    `${units.toLocaleString()} units from ${batches === 1 ? "it" : "them"} were sold at ${joinNames(sold.map(name))}, `
      + (never ? `which ${distText} ${data.filters.sku ? "never sends this product to" : "never supplies"}.` : `where ${batches === 1 ? "it was" : "none of them was"} shipped.`),
    dists.length === 1
      ? `That mismatch is the leak: the units left the planned route at or after ${distText}.`
      : "That mismatch is the leak: the units left the planned route.",
  ];
}

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
  const story = useMemo(() => leakStory(data), [data]);
  const [hover, setHover] = useState<StoryStep | null>(null);
  const [pinned, setPinned] = useState<StoryStep | null>(null);
  const active = hover ?? pinned;

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
        {story && (narrow ? (
          <div className="sc-story">
            <span className="sc-story-title">What you&apos;re looking at</span>
            <ol className="sc-story-text">
              {story.map((t) => <li key={t}>{t}</li>)}
            </ol>
          </div>
        ) : (
          <div className="sc-story" role="group" aria-label="What you're looking at. Point at or select a line to highlight it on the timeline.">
            <span className="sc-story-title">What you&apos;re looking at</span>
            <ol>
              {story.map((t, i) => {
                const step = (i + 1) as StoryStep;
                return (
                  <li key={t}>
                    <button type="button" className={active === step ? "on" : ""} aria-pressed={pinned === step}
                      onMouseEnter={() => setHover(step)} onMouseLeave={() => setHover(null)}
                      onFocus={() => setHover(step)} onBlur={() => setHover(null)}
                      onClick={() => setPinned(pinned === step ? null : step)}>
                      <span className="sc-story-n" aria-hidden>{step}</span>{t}
                    </button>
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
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
              <span><span className="sc-flag" aria-hidden>⚑</span>First sale at that store</span>
              <span><span className="sc-now" aria-hidden />This week</span>
            </div>
            <Timeline data={data} focusBatches={focus} highlight={story ? active : null} />
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
