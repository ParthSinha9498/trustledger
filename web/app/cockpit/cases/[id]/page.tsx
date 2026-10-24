"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import DataBoundary from "@/components/cockpit/DataBoundary";
import StatusPill from "@/components/cockpit/StatusPill";
import StepTimeline, { Cites, citationsOf, linkSteps } from "@/components/cockpit/StepTimeline";
import SupplyChainPanel from "@/components/cockpit/supply-chain/SupplyChainPanel";
import { prettyId, productName, REASON_TEXT } from "@/components/cockpit/format";
import { api, errorText, type Budget, type CaseDetail, type Step } from "@/lib/api";
import cs from "./case.module.css";

/** Short reason for the page title: "<reason> at <store> · <product>". */
const REASON_TITLE: Record<string, string> = {
  NOT_IN_CHANNEL: "Out-of-channel serial",
  ALREADY_SOLD: "Already-sold serial",
  UNKNOWN_SERIAL: "Unknown serial",
  SKU_MISMATCH: "Serial for a different product",
};
const FINISHED = new Set(["complete", "failed", "waiting_capacity"]);

type Store = { store_id: string; name?: string };
type CaseExtra = CaseDetail & { failure_count?: number; skus?: string[] };

/** true / false once known on the client; null before the first check (so nothing heavy mounts on SSR). */
function useNarrow(query = "(max-width: 700px)"): boolean | null {
  const [narrow, setNarrow] = useState<boolean | null>(null);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setNarrow(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return narrow;
}

function FindingItem({ f }: { f: Step }) {
  return (
    <li>
      <a href={`#step-${f.n}`} className="tl-n">#{f.n}</a>{" "}
      {String((f.payload as { text?: string }).text ?? "")}{" "}
      <Cites citations={citationsOf(f.payload)} />
    </li>
  );
}

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [c, setC] = useState<CaseExtra | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [liveBudget, setLiveBudget] = useState<Budget | null>(null);
  const [stores, setStores] = useState<Record<string, string>>({});
  const narrow = useNarrow();

  useEffect(() => {
    let live = true;
    const load = () => api<CaseExtra>(`/cases/${id}`)
      .then((d) => { if (live) { setC(d); setErr(null); } })
      .catch((e) => live && setErr(errorText(e)));
    load();
    const t = setInterval(load, 3000);
    return () => { live = false; clearInterval(t); };
  }, [id]);

  useEffect(() => {
    api<Store[]>("/stores")
      .then((rows) => setStores(Object.fromEntries(rows.filter((s) => s.name).map((s) => [s.store_id, s.name as string]))))
      .catch(() => setStores({}));
  }, []);

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
  if (!c) {
    return (
      <main className="wide">
        <p className="crumbs muted"><Link href="/cockpit">Investigations</Link> / loading...</p>
        <div className="case-header card elevated" style={{ minHeight: 180 }}>
          <div>
            <div className="skeleton" style={{ width: "min(420px, 90%)", height: 32, marginBottom: 16 }} />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <div className="skeleton" style={{ width: 90, height: 26, borderRadius: "var(--radius-pill)" }} />
              <div className="skeleton" style={{ width: 120, height: 26, borderRadius: "var(--radius-pill)" }} />
            </div>
            <div className="skeleton" style={{ width: "70%", height: 16, marginTop: 14 }} />
          </div>
          <div className="case-budget">
            <div className="skeleton" style={{ height: 60, width: "100%", marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 16, width: "70%" }} />
          </div>
        </div>
        <div className="card" style={{ height: 220, marginTop: 16 }}>
          <div className="skeleton" style={{ width: 160, height: 24, marginBottom: 16 }} />
          <div className="skeleton" style={{ width: "100%", height: 18, marginBottom: 10 }} />
          <div className="skeleton" style={{ width: "75%", height: 18 }} />
        </div>
      </main>
    );
  }

  const storeName = stores[c.store_id] ?? prettyId(c.store_id);
  const product = productName(c.sku);
  const finished = FINISHED.has(c.status);
  // Deferred before anything ran: no mode to claim (neither live AI nor the offline mock).
  const waitingNoRun = c.status === "waiting_capacity" && !(c.steps?.length);
  // A scripted stand-in run is never shown as AI. Older rows were stored as "live"; their summary gives them away.
  const isMock = c.agent_mode === "mock" || c.agent_model === "scripted-mock" || /LLM_MODE=mock/.test(c.summary ?? "");
  const isReplay = !isMock && c.agent_mode === "replay";
  const isInterrupted = !isMock && ((c.status === "failed" && c.agent_mode === "live") ||
    (c.status === "waiting_capacity" && (c.steps?.length ?? 0) > 0));
  const recorded = c.replay_recorded_at || new Date(c.created_at).toLocaleDateString();

  const [summary, nextActions] = (c.summary ?? "").split(/\n\s*Next actions:\s*\n/);
  const actions = (nextActions ?? "").split("\n").map((l) => l.replace(/^\s*-\s*/, "").trim()).filter(Boolean);
  const oneFinding = findings.length === 1;

  const modeChip = waitingNoRun ? null : isMock ? (
    <span className={`pill ${cs.mock}`} title="LLM_MODE=mock: a fixed offline script ran, no AI model was called">Offline mock run, not AI</span>
  ) : isReplay ? (
    <span className={`pill ${cs.mock}`}>Replay of a recorded {c.agent_model && !/mock|scripted/.test(c.agent_model) ? "live " : ""}run</span>
  ) : isInterrupted ? (
    <span className={`pill ${cs.mock}`}>Interrupted live attempt</span>
  ) : null;

  const modeMeta = waitingNoRun ? <>Waiting for AI capacity</>
    : isMock ? <>Scripted stand-in: same fixed plan every time</>
    : isReplay ? <>Recorded {recorded}{c.agent_model ? <> · <code>{c.agent_model}</code></> : null}</>
    : !finished ? <>Investigation running</>
    : <>Live AI investigation{c.agent_model ? <> · <code>{c.agent_model}</code></> : null}</>;

  const summaryCard = (
    <section className="card elevated">
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
      {oneFinding && (
        <div className={cs.finding}>
          <h3>Finding</h3>
          <ol className="findings"><FindingItem f={findings[0]} /></ol>
        </div>
      )}
      <p className="muted small">The brand decides authenticity. The agent reports the earliest observed point of divergence in the available evidence; it never declares a product counterfeit.</p>
    </section>
  );

  return (
    <main className="wide">
      <p className="crumbs"><Link href="/cockpit">Investigations</Link> / {c.case_id}</p>
      <div className="case-header card elevated">
        <div>
          <h1 className={cs.title}>{REASON_TITLE[c.reason_code] ?? REASON_TEXT[c.reason_code] ?? c.reason_code} at {storeName} · {product}</h1>
          <div className={cs.chips}>
            <StatusPill status={c.status} />
            <span className={`pill ${cs.chip}`}>{c.confidence ? `${c.confidence.charAt(0).toUpperCase()}${c.confidence.slice(1)} confidence` : "Confidence pending"}</span>
            {modeChip}
          </div>
          <p className={cs.meta}>
            {modeMeta}
            {c.serial && <> · Serial <code>{c.serial}</code></>}
            {(c.failure_count ?? 1) > 1 && <> · {c.failure_count} failed scans</>}
            {" "}· Opened {new Date(c.created_at).toLocaleString()}
          </p>
          {isMock && !waitingNoRun ? (
            <div className={`${cs.notice} ${cs.noticeWarn}`}>
              <strong>Offline mock run, not AI.</strong> This case was processed by a fixed offline script (LLM_MODE=mock) so the app works without a model. Its steps are real queries against the nodes, but the plan and wording are scripted.
            </div>
          ) : isInterrupted ? (
            <div className={`${cs.notice} ${cs.noticeBad}`}>
              <strong>Interrupted live attempt:</strong> {c.agent_reason || c.summary || "Live investigation was interrupted before completion."}
            </div>
          ) : c.status === "waiting_capacity" ? (
            <div className={`${cs.notice} ${cs.noticeWarn}`}>
              <strong>{c.agent_reason || "Capacity reached"}:</strong> This case will be investigated live when capacity frees up.
            </div>
          ) : c.agent_reason ? (
            <div className={cs.notice}><strong>Notice:</strong> {c.agent_reason}</div>
          ) : null}
        </div>
        <div className="case-budget">
          <BudgetMeter budget={budget} />
          <p className="muted small">{paypalQueries} PayPal-side quer{paypalQueries === 1 ? "y" : "ies"} in this case. Brand-side counts are exact and don&apos;t touch the privacy limit.</p>
        </div>
      </div>

      {findings.length > 1 ? (
        <div className="case-grid">
          {summaryCard}
          <section className="card elevated">
            <h2>Findings <span className="count">{findings.length}</span></h2>
            <ol className="findings">{findings.map((f) => <FindingItem key={f.n} f={f} />)}</ol>
          </section>
        </div>
      ) : summaryCard}

      <section className="card">
        <h2>Evidence</h2>
        <p className="muted">What each query returned. Brand-side counts are exact business data; PayPal-side answers are privacy-protected estimates about buyers, shown with ± ranges.</p>
        {/* AG Charts Community has no map series, so results chart by region/store as bars. */}
        <StepTimeline steps={c.steps} isReplay={isReplay} />
      </section>

      <section className="card">
        <h2>What the agent could see</h2>
        <p className="muted">Each question travels to the node that owns the data; only an aggregate comes back. Raw records never leave the brand or PayPal.</p>
        <DataBoundary steps={c.steps} />
      </section>

      <section className="card">
        <h2>Supply chain for {product} at {storeName}</h2>
        <p className="muted">Batches of this product that were shipped to {storeName} or turned up there.</p>
        {narrow !== null && (
          <SupplyChainPanel sku={c.sku} storeId={c.store_id} narrow={narrow} mobileNote={
            <div className={cs.supplyLink}>
              <p>The week-by-week timeline needs a wider screen.</p>
              <Link className="button secondary"
                href={`/cockpit/supply-chain?sku=${encodeURIComponent(c.sku)}&store=${encodeURIComponent(c.store_id)}`}>
                Open supply chain
              </Link>
            </div>
          } />
        )}
      </section>
    </main>
  );
}
