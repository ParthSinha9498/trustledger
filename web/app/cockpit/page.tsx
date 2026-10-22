"use client";
import type { ColDef } from "ag-grid-community";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Grid from "@/components/Grid";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import StatusPill from "@/components/cockpit/StatusPill";
import { api, errorText, type Budget, type Case } from "@/lib/api";

const REASON: Record<string, string> = {
  NOT_IN_CHANNEL: "Not in channel", ALREADY_SOLD: "Already sold",
  UNKNOWN_SERIAL: "Unknown serial", SKU_MISMATCH: "SKU mismatch",
};

export default function Cockpit() {
  const [cases, setCases] = useState<Case[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const router = useRouter();

  useEffect(() => {
    let live = true;
    const load = () => api<Case[]>("/cases")
      .then((d) => { if (live) { setCases(d); setErr(null); } })
      .catch((e) => live && setErr(errorText(e)));
    load();
    api<Budget>("/console/budget").then((b) => live && setBudget(b)).catch(() => {});
    const t = setInterval(load, 4000);
    return () => { live = false; clearInterval(t); };
  }, []);

  const columns = useMemo<ColDef<Case>[]>(() => [
    { field: "case_id", headerName: "Case", minWidth: 150 },
    { field: "store_id", headerName: "Store", maxWidth: 130 },
    { field: "sku", headerName: "Product", minWidth: 130 },
    { field: "reason_code", headerName: "Reason", valueFormatter: (p) => REASON[p.value as string] ?? p.value },
    { field: "agent_mode", headerName: "Mode", maxWidth: 110, valueFormatter: (p) => p.value === "replay" ? "Replay" : "Live" },
    { field: "status", headerName: "Status", maxWidth: 150, cellRenderer: (p: { value: string }) => <StatusPill status={p.value} /> },
    { field: "confidence", headerName: "Confidence", maxWidth: 130, valueFormatter: (p) => p.value ? String(p.value).toUpperCase() : "–" },
    { field: "findings", headerName: "Findings", maxWidth: 110, type: "numericColumn" },
    { field: "created_at", headerName: "Opened", sort: "desc", valueFormatter: (p) => p.value ? new Date(p.value as string).toLocaleString() : "" },
  ], []);

  const counts = useMemo(() => {
    const c = { open: 0, investigating: 0, waiting_capacity: 0, complete: 0, failed: 0 } as Record<string, number>;
    for (const x of cases ?? []) c[x.status] = (c[x.status] ?? 0) + 1;
    return c;
  }, [cases]);

  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Investigations</h1>
          <p className="muted">Each failed verification opens a case. The agent investigates using only privacy-protected aggregates.</p>
        </div>
        <div className="head-budget"><BudgetMeter budget={budget} compact /></div>
      </div>
      <div className="stat-row">
        <div className="stat"><div className="stat-value">{cases?.length ?? "–"}</div><div className="stat-label">Cases</div></div>
        <div className="stat"><div className="stat-value">{(counts.open ?? 0) + (counts.investigating ?? 0)}</div><div className="stat-label">In progress</div></div>
        <div className="stat"><div className="stat-value">{counts.complete ?? 0}</div><div className="stat-label">Complete</div></div>
        <div className="stat links">
          <Link href="/cockpit/console">Ask a question →</Link>
          <Link href="/cockpit/supply-chain">Supply chain →</Link>
          <Link href="/privacy">How privacy is protected →</Link>
        </div>
      </div>
      <section className="card elevated">
        {err && <div className="refusal">Couldn&apos;t load cases: {err}</div>}
        {cases && cases.length === 0 ? (
          <p className="muted">No cases yet. A failed verification at the store checkout (try serial X123 at Store B) opens one.</p>
        ) : (
          <Grid<Case> rows={cases ?? []} columns={columns} height={460}
                      onRowClick={(c) => router.push(`/cockpit/cases/${c.case_id}`)} />
        )}
      </section>
    </main>
  );
}
