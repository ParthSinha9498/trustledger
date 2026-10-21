"use client";
// Client-only Bryntum Scheduler. Import through SupplyTimelineClient (next/dynamic, ssr: false).
import "@bryntum/scheduler/fontawesome/css/fontawesome.css";
import "@bryntum/scheduler/fontawesome/css/solid.css";
import "@bryntum/scheduler/scheduler.css";
import "@bryntum/scheduler/svalbard-light.css";
import "./supply-timeline.css";

import { StringHelper, type DependencyModelConfig, type EventModelConfig, type ResourceModelConfig } from "@bryntum/scheduler";
import { BryntumScheduler } from "@bryntum/scheduler-react";
import { useMemo } from "react";
import { weekToDate, type SupplyChain, type SupplyEvent } from "@/lib/api";

const TIER_LABEL = { brand: "Brand", distributor: "Distributor", store: "Store" } as const;
const KIND_COLOR: Record<SupplyEvent["kind"], string> = {
  dispatch: "indigo", distributor: "blue", store: "teal", off_channel: "red",
};
const KIND_LABEL: Record<SupplyEvent["kind"], string> = {
  dispatch: "Dispatched by brand", distributor: "Held at distributor",
  store: "In channel at store", off_channel: "Sold outside the batch's channel",
};
// Bryntum dependency types: 0 = start-to-start, 2 = end-to-start.
const DEP_TYPE = { start_to_start: 0, end_to_start: 2 } as const;

export default function SupplyTimeline({ data, compact = false }: { data: SupplyChain; compact?: boolean }) {
  const byId = useMemo(() => new Map(data.events.map((e) => [e.id, e])), [data.events]);
  const names = useMemo(() => new Map(data.resources.map((r) => [r.id, r.name])), [data.resources]);

  const resources = useMemo<ResourceModelConfig[]>(() => data.resources.map((r) => ({
    id: r.id,
    name: r.name,
    // Column fields (read by the grid columns below).
    tier: TIER_LABEL[r.tier],
    region: r.region ?? "",
  }) as ResourceModelConfig), [data.resources]);

  const events = useMemo<EventModelConfig[]>(() => data.events.map((e) => ({
    id: e.id,
    resourceId: e.resource_id,
    name: e.kind === "off_channel" ? `${e.units} units off-channel` : `${e.batch_id} · ${e.units}`,
    startDate: weekToDate(e.start_week),
    endDate: weekToDate(e.end_week),
    eventColor: KIND_COLOR[e.kind],
    cls: e.highlight ? "leak" : "",
  })), [data.events]);

  const dependencies = useMemo<DependencyModelConfig[]>(() => data.dependencies.map((d) => ({
    id: d.id,
    fromEvent: d.from,
    toEvent: d.to,
    type: DEP_TYPE[d.type ?? "end_to_start"],
    cls: d.highlight ? "leak" : "",
  })), [data.dependencies]);

  const start = weekToDate(Math.max(1, data.week_range.from));
  const end = weekToDate(data.week_range.to + 1);

  return (
    <div className={`supply-timeline${compact ? " compact" : ""}`}>
      <BryntumScheduler
        startDate={start}
        endDate={end}
        viewPreset="weekAndMonth"
        rowHeight={compact ? 40 : 46}
        barMargin={5}
        readOnly
        eventStyle="filled"
        eventLayout="stack"
        columns={[
          { text: "Tier", field: "tier", width: 100 },
          { text: "Name", field: "name", width: 190 },
          { text: "Region", field: "region", width: 90 },
        ]}
        resources={resources}
        events={events}
        dependencies={dependencies}
        dependenciesFeature
        eventMenuFeature={false}
        scheduleMenuFeature={false}
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
              `Batch ${enc(e.batch_id)} · ${enc(e.sku)}`,
              `${enc(where)} · weeks ${e.start_week}–${e.end_week - 1}`,
              e.kind === "off_channel" ? `${e.units} units sold here` : `${e.units} units in batch`,
            ];
            if (e.sold != null) lines.push(`${e.sold} sold in channel`);
            return lines.join("<br>");
          },
        }}
      />
    </div>
  );
}
