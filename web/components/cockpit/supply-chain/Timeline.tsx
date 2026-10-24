"use client";
// Client-only Bryntum Scheduler (supply chain page and case page). Import through next/dynamic (ssr: false).
import "@bryntum/scheduler/fontawesome/css/fontawesome.css";
import "@bryntum/scheduler/fontawesome/css/solid.css";
import "@bryntum/scheduler/scheduler.css";
import "@bryntum/scheduler/svalbard-light.css";
import "./timeline.css";

import {
  StringHelper, type DependencyModelConfig, type EventModelConfig, type ResourceModelConfig, type ViewPresetConfig,
} from "@bryntum/scheduler";
import { BryntumScheduler } from "@bryntum/scheduler-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { weekToDate, type SupplyChain, type SupplyEvent } from "@/lib/api";
import { productName, weekLabel } from "../format";

const TIER_LABEL = { brand: "Brand", distributor: "Distributor", store: "Store" } as const;
const KIND_COLOR: Record<SupplyEvent["kind"], string> = {
  dispatch: "indigo", distributor: "blue", store: "teal", off_channel: "red",
};
const KIND_LABEL: Record<SupplyEvent["kind"], string> = {
  dispatch: "Sent out by the brand", distributor: "At the distributor",
  store: "At the store it was shipped to", off_channel: "Sold at a store it was never shipped to",
};
// Bryntum dependency types: 0 = start-to-start, 2 = end-to-start.
const DEP_TYPE = { start_to_start: 0, end_to_start: 2 } as const;

const LOCKED_COLS = 215;  // width of the locked "Where" column
const MIN_TICK = 56;      // narrowest week column that still shows "14 Sep" in full
const DAY = 86_400_000;

const PRESET: ViewPresetConfig = {
  base: "weekAndMonth",
  tickWidth: MIN_TICK,
  headers: [
    {
      unit: "month",
      // A month cut short at either end of the axis gets a shorter label, or none, instead of a clipped one.
      renderer: (start: Date, end: Date) => {
        const days = (end.getTime() - start.getTime()) / DAY;
        if (days < 10) return "";
        const month = start.toLocaleDateString("en-GB", { month: "short" }).slice(0, 3);
        return days < 21 ? month : `${month} ${start.getFullYear()}`;
      },
    },
    { unit: "week", dateFormat: "D MMM" },
  ],
} as ViewPresetConfig;

/** Weeks covered by a set of events, padded by a week on each side, and by one more week where the first or
 *  last month would otherwise be too narrow to print its "Oct 2026" label. */
function paddedRange(events: SupplyEvent[], currentWeek: number): [number, number] {
  let from = Math.min(...events.map((e) => e.start_week)) - 1;
  let to = Math.max(...events.map((e) => e.end_week), currentWeek + 1) + 1;   // exclusive
  from = Math.max(1, from);
  const month = (w: number) => weekToDate(w).getMonth();
  if (month(from) !== month(from + 1)) from = Math.max(1, from - 1);
  if (month(to - 1) !== month(to - 2)) to += 1;
  return [from, to];
}

export default function Timeline({ data, focusBatches }: {
  data: SupplyChain;
  /** When set, show only these batches. Rows without bars are left out; stores with off-channel sales come first. */
  focusBatches: Set<string> | null;
}) {
  const ref = useRef<BryntumScheduler>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const names = useMemo(() => new Map(data.resources.map((r) => [r.id, r.name])), [data.resources]);

  const shown = useMemo(() => (focusBatches ? data.events.filter((e) => focusBatches.has(e.batch_id)) : data.events),
    [data.events, focusBatches]);
  const byId = useMemo(() => new Map(shown.map((e) => [e.id, e])), [shown]);

  // Rows: brand, then distributors, then stores with off-channel sales (most units first), then the rest.
  const resources = useMemo<ResourceModelConfig[]>(() => {
    const offUnits = new Map<string, number>();
    for (const e of shown) if (e.kind === "off_channel") offUnits.set(e.resource_id, (offUnits.get(e.resource_id) ?? 0) + e.units);
    const used = new Set(shown.map((e) => e.resource_id));
    const tierRank = (t: string) => (t === "brand" ? 0 : t === "distributor" ? 1 : 2);
    return data.resources
      .filter((r) => used.has(r.id))
      .map((r, i) => ({ r, i }))
      .sort((a, b) => tierRank(a.r.tier) - tierRank(b.r.tier)
        || (offUnits.get(b.r.id) ?? 0) - (offUnits.get(a.r.id) ?? 0) || a.i - b.i)
      .map(({ r }) => ({
        id: r.id,
        name: r.name,
        tier: offUnits.has(r.id) ? "Store, not on the route" : TIER_LABEL[r.tier],
        cls: offUnits.has(r.id) ? "sc-row-off" : "",
      }) as ResourceModelConfig);
  }, [data.resources, shown, focusBatches]);

  const events = useMemo<EventModelConfig[]>(() => shown.map((e) => ({
    id: e.id,
    resourceId: e.resource_id,
    name: e.kind === "off_channel" ? `${e.batch_id} · ${e.units} sold` : e.batch_id,
    startDate: weekToDate(e.start_week),
    endDate: weekToDate(e.end_week),
    eventColor: KIND_COLOR[e.kind],
    cls: e.highlight ? "leak" : "",
  })), [shown]);

  const dependencies = useMemo<DependencyModelConfig[]>(() => data.dependencies
    .filter((d) => byId.has(d.from) && byId.has(d.to))
    .map((d) => ({
      id: d.id, fromEvent: d.from, toEvent: d.to,
      type: DEP_TYPE[d.type ?? "end_to_start"], cls: d.highlight ? "leak" : "",
    })), [data.dependencies, byId]);

  const [fromWeek, toWeek] = useMemo(() => paddedRange(shown.length ? shown : data.events, data.current_week),
    [shown, data.events, data.current_week]);
  const weeks = toWeek - fromWeek;
  // Fit every week on screen when the columns stay readable; otherwise scroll, starting at the latest weeks.
  const fits = width > 0 && (width - LOCKED_COLS) / weeks >= MIN_TICK;
  // A small set grows to show every row; the full chain gets a tall fixed box that scrolls.
  const autoHeight = !!focusBatches || shown.length <= 80;

  useEffect(() => {
    if (fits || !width) return;
    const t = setTimeout(() => {
      ref.current?.instance?.scrollToDate?.(weekToDate(toWeek), { block: "end", animate: false });
    }, 120);
    return () => clearTimeout(t);
  }, [fits, width, toWeek]);

  return (
    <div ref={boxRef} className={`sc-timeline${autoHeight ? " auto" : ""}`}>
      {width > 0 && (
        <BryntumScheduler
          key={`${fits}:${autoHeight}:${fromWeek}:${toWeek}`}
          ref={ref}
          startDate={weekToDate(fromWeek)}
          endDate={weekToDate(toWeek)}
          weekStartDay={1}
          viewPreset={PRESET}
          forceFit={fits}
          autoHeight={autoHeight}
          zoomOnMouseWheel={false}
          zoomOnTimeAxisDoubleClick={false}
          rowHeight={44}
          barMargin={5}
          readOnly
          eventStyle="filled"
          eventLayout="stack"
          columns={[{
            text: "Where", field: "name", width: LOCKED_COLS, htmlEncode: false,
            renderer: ({ record }: { record: { getData: (f: string) => unknown } }) => {
              const enc = StringHelper.encodeHtml;
              return `<div class="sc-who"><span>${enc(String(record.getData("name")))}</span>`
                + `<small>${enc(String(record.getData("tier")))}</small></div>`;
            },
          }]}
          resources={resources}
          events={events}
          dependencies={dependencies}
          dependenciesFeature
          timeRangesFeature={{ showHeaderElements: false }}
          timeRanges={[{ id: "now", name: "This week", startDate: weekToDate(data.current_week) }]}
          eventMenuFeature={false}
          scheduleMenuFeature={false}
          cellMenuFeature={false}
          headerMenuFeature={false}
          eventDragCreateFeature={false}
          eventEditFeature={false}
          eventTooltipFeature={{
            template: ({ eventRecord }: { eventRecord: { id: string | number } }) => {
              const e = byId.get(String(eventRecord.id));
              if (!e) return "";
              const enc = StringHelper.encodeHtml;
              const where = names.get(e.resource_id) ?? e.resource_id;
              const lines = [
                `<b>${enc(KIND_LABEL[e.kind])}</b>`,
                `Batch ${enc(e.batch_id)} · ${enc(productName(e.sku))}`,
                `${enc(where)} · week of ${weekLabel(e.start_week)} to week of ${weekLabel(e.end_week - 1)}`,
                e.kind === "off_channel" ? `${e.units} units sold here` : `${e.units} units in the batch`,
              ];
              if (e.sold != null) lines.push(`${e.sold} sold at this store`);
              return lines.join("<br>");
            },
          }}
        />
      )}
    </div>
  );
}
