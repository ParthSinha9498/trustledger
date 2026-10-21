"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import StatusPill from "@/components/cockpit/StatusPill";
import StepTimeline, { Cites, citationsOf, linkSteps } from "@/components/cockpit/StepTimeline";
import SupplyChainPanel from "@/components/cockpit/SupplyChainPanel";
import { api, errorText, type Budget, type CaseDetail } from "@/lib/api";

const REASON_TEXT: Record<string, string> = {
  NOT_IN_CHANNEL: "Not in this store's supply chain",
  ALREADY_SOLD: "Serial already sold",
  UNKNOWN_SERIAL: "Unknown serial",
  SKU_MISMATCH: "Serial belongs to a different product",
};

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [c, setC] = useState<CaseDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [liveBudget, setLiveBudget] = useState<Budget | null>(null);

  useEffect(() => {
    let live = true;
    const load = () => api<CaseDetail>(`/cases/${id}`)
      .then((d) => { if (live) { setC(d); setErr(null); } })
      .catch((e) => live && setErr(errorText(e)));
    load();
    const t = setInterval(load, 3000);
    return () => { live = false; clearInterval(t); };
  }, [id]);

  useEffect(() => {
    api<Budget>("/console/budget").then(setLiveBudget).catch(() => setLiveBudget(null));
  }, [c?.steps.length]);

  const findings = useMemo(() => (c?.steps ?? []).filter((s) => s.kind === "finding"), [c]);
  // Budget as last reported inside the case (PayPal results or get_budget), else the live one.
  const budget = useMemo<Budget | null>(() => {
    for (const s of [...(c?.steps ?? [])].reverse()) {
      if (s.kind !== "tool_result") continue;
      const r = (s.payload as { tool?: string; result?: Record<string, unknown> }).result ?? {};
      const tool = (s.payload as { tool?: string }).tool;
      if (r.budget && typeof r.budget === "object") return r.budget as Budget;
      if (tool === "get_budget" && typeof r.remaining === "number") return r as unknown as Budget;
    }
    return liveBudget;
  }, [c, liveBudget]);
  const paypalQueries = useMemo(() => (c?.steps ?? []).filter((s) =>
    s.kind === "tool_call" && (s.payload as { tool?: string }).tool === "query_paypal_node").length, [c]);

  if (err && !c) return <main><div className="refusal">Couldn&apos;t load case: {err}</div></main>;
  if (!c) return <main><p className="muted">Loading…</p></main>;

  const [summary, nextActions] = (c.summary ?? "").split(/\n\s*Next actions:\s*\n/);
  const actions = (nextActions ?? "").split("\n").map((l) => l.replace(/^\s*-\s*/, "").trim()).filter(Boolean);

  return (
    <main className="wide">
      <p className="crumbs"><Link href="/cockpit">Investigations</Link> / {c.case_id}</p>
      <div className="case-header card">
        <div>
          <h1>Case {c.case_id}</h1>
          <div className="meta">
            <StatusPill status={c.status} />
            <span><span className="muted">Store</span> {c.store_id}</span>
            <span><span className="muted">Product</span> {c.sku}</span>
            {c.serial && <span><span className="muted">Serial</span> {c.serial}</span>}
            <span><span className="muted">Reason</span> {REASON_TEXT[c.reason_code] ?? c.reason_code}</span>
            <span><span className="muted">Opened</span> {new Date(c.created_at).toLocaleString()}</span>
          </div>
        </div>
        <div className="case-budget">
          <BudgetMeter budget={budget} />
          <p className="muted small">{paypalQueries} PayPal-side quer{paypalQueries === 1 ? "y" : "ies"} in this case. Brand-side queries are exact and free.</p>
        </div>
      </div>

      <div className="case-grid">
        <section className="card">
          <h2>Summary</h2>
          {c.summary ? (
            <>
              <p className="summary">{linkSteps(summary.trim())}</p>
              {actions.length > 0 && (
                <>
                  <h3>Suggested next actions</h3>
                  <ul>{actions.map((a) => <li key={a}>{linkSteps(a)}</li>)}</ul>
                </>
              )}
            </>
          ) : (
            <p className="muted">{c.status === "failed" ? "The investigation failed." : "The agent is still investigating. The summary appears when it finishes."}</p>
          )}
          <p className="muted small">The brand decides authenticity. The agent reports the earliest observed point of divergence in the available evidence; it never declares a product counterfeit.</p>
        </section>
        <section className="card">
          <h2>Findings <span className="count">{findings.length}</span></h2>
          {findings.length ? (
            <ol className="findings">
              {findings.map((f) => (
                <li key={f.n}>
                  <a href={`#step-${f.n}`} className="tl-n">#{f.n}</a>{" "}
                  {String((f.payload as { text?: string }).text ?? "")}{" "}
                  <Cites citations={citationsOf(f.payload)} />
                </li>
              ))}
            </ol>
          ) : <p className="muted">No findings recorded yet.</p>}
        </section>
      </div>

      <section className="card">
        <h2>Supply chain for {c.sku}</h2>
        <SupplyChainPanel sku={c.sku} compact />
      </section>

      <section className="card">
        <h2>Investigation steps</h2>
        <p className="muted">Every query the agent ran and what came back. Results are aggregates only: exact for brand business data, differentially private for PayPal-side buyer data.</p>
        {/* AG Charts Community has no map series, so results chart by region/store as bars. */}
        <StepTimeline steps={c.steps} />
      </section>
    </main>
  );
}
