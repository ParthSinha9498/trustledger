"use client";
import type { ColDef } from "ag-grid-community";
import Grid from "@/components/Grid";
import type { OffChannel } from "@/lib/api";
import { joinNames, productName, weekLabel } from "./format";

type Row = {
  batch: string;
  product: string;
  distributor: string;
  shippedTo: string;
  soldAt: string;
  units: number;
  firstWeek: number;
};

function columns(narrow: boolean): ColDef<Row>[] {
  // On a phone keep the four columns that tell the story; the summary above names the distributor.
  const cols: ColDef<Row>[] = [
    { headerName: "Batch", field: "batch", minWidth: narrow ? 64 : 90, maxWidth: 120 },
    { headerName: "Product", field: "product", minWidth: 150, hide: narrow },
    { headerName: "Distributor", field: "distributor", minWidth: 170, hide: narrow },
    { headerName: "Shipped to", field: "shippedTo", minWidth: narrow ? 80 : 120 },
    {
      headerName: "Sold at", field: "soldAt", minWidth: narrow ? 72 : 110,
      cellStyle: { color: "var(--bad)", fontWeight: 600 },
    },
    {
      headerName: "Units", field: "units", minWidth: narrow ? 64 : 90, maxWidth: 120, sort: "desc",
      type: "rightAligned", filter: false, valueFormatter: (p) => (p.value as number).toLocaleString(),
    },
    {
      headerName: "First sold there", field: "firstWeek", minWidth: 150, filter: false, hide: narrow,
      valueFormatter: (p) => `Week of ${weekLabel(p.value as number)}`,
    },
  ];
  // No filter buttons on a phone: they squeeze the headers to "Bat…".
  if (!narrow) return cols;
  const fixed: Record<string, Partial<ColDef<Row>>> = {
    batch: { flex: 0, width: 62, minWidth: 62 },
    shippedTo: { headerName: "Sent to", flex: 1, minWidth: 64 },
    soldAt: { flex: 1, minWidth: 64 },
    units: { flex: 0, width: 86, minWidth: 86 },
  };
  return cols.map((c) => ({ ...c, ...fixed[c.field as string], filter: false, suppressHeaderMenuButton: true }));
}

/** One row per (batch, store) where units sold at a store the batch was never shipped to. */
export default function OffChannelTable({ rows, names, narrow = false }: {
  rows: OffChannel[]; names: Map<string, string>; narrow?: boolean;
}) {
  const name = (id: string) => names.get(id) ?? id;
  const data: Row[] = rows.map((o) => ({
    batch: o.batch_id,
    product: productName(o.sku),
    distributor: name(o.distributor_id),
    shippedTo: joinNames(o.channel_store_ids.map(name)),
    soldAt: name(o.sold_store_id),
    units: o.units,
    firstWeek: o.first_week,
  }));
  return (
    <div className="sc-grid">
      <Grid rows={data} columns={columns(narrow)} key={narrow ? "narrow" : "wide"} autoHeight={data.length <= 12} height={420} />
    </div>
  );
}

/** Plain one-line summary of the off-channel rows, built only from the rows themselves. */
export function offChannelSummary(rows: OffChannel[], names: Map<string, string>): string {
  const name = (id: string) => names.get(id) ?? id;
  const units = rows.reduce((n, o) => n + o.units, 0);
  const batches = new Set(rows.map((o) => o.batch_id)).size;
  const stores = [...new Set(rows.map((o) => o.sold_store_id))].map(name);
  const dists = [...new Set(rows.map((o) => o.distributor_id))].map(name);
  const b = batches === 1 ? "1 batch" : `${batches} batches`;
  const who = batches === 1 ? "It" : dists.length > 1 ? "They" : batches === 2 ? "Both" : `All ${batches}`;
  return `${units.toLocaleString()} units from ${b} sold at ${joinNames(stores)}, where the brand never shipped `
    + `${batches === 1 ? "that batch" : "those batches"}. ${who} passed through ${joinNames(dists)}, so the `
    + `earliest point they could have left the planned route is after ${dists.length === 1 ? "that distributor" : "those distributors"}.`;
}
