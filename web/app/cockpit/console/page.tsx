"use client";
import { useEffect, useState } from "react";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import ResultView from "@/components/cockpit/ResultView";
import SpecEditor from "@/components/cockpit/SpecEditor";
import { label } from "@/components/cockpit/format";
import { api, errorText, type Budget, type PlanResponse, type PlannedSpec, type QueryResult, type RunResponse } from "@/lib/api";

const EXAMPLES = [
  "Where is Nimbus P8 128GB selling outside its expected channel?",
  "Which stores have the most verification failures, by reason?",
  "How do buyers of NMB-P8-128 split by region and age band?",
];

const newSpec = (): PlannedSpec => ({ node: "brand", spec: { metric: "sold_units", group_by: ["store_id"], filters: {} } });

/** Strip UI-only/legacy fields before sending (epsilon is ignored by the zCDP engine). */
const toWire = (specs: PlannedSpec[]) => specs.map(({ node, spec }) => ({
  node, spec: { metric: spec.metric, group_by: spec.group_by, filters: spec.filters ?? {} },
}));

export default function ConsolePage() {
  const [question, setQuestion] = useState("");
  const [specs, setSpecs] = useState<PlannedSpec[]>([]);
  const [rationale, setRationale] = useState<string | null>(null);
  const [results, setResults] = useState<QueryResult[] | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [busy, setBusy] = useState<"plan" | "run" | "explain" | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<Budget>("/console/budget").then(setBudget).catch(() => setBudget(null));
  }, []);

  async function plan(q = question) {
    if (!q.trim()) return;
    setBusy("plan"); setErr(null); setResults(null); setExplanation(null);
    try {
      const r = await api<PlanResponse>("/console/plan", { method: "POST", body: JSON.stringify({ question: q }) });
      setSpecs((r.specs ?? []).map((s) => ({ node: s.node, spec: { ...s.spec, group_by: s.spec?.group_by ?? [], filters: s.spec?.filters ?? {} } })));
      setRationale(r.rationale ?? null);
    } catch (e) {
      setErr(`Couldn't plan this question: ${errorText(e)}. You can add queries by hand below.`);
    } finally { setBusy(null); }
  }

  async function run(explain: boolean) {
    if (!specs.length) return;
    setBusy(explain ? "explain" : "run"); setErr(null);
    try {
      const r = await api<RunResponse>("/console/run", { method: "POST", body: JSON.stringify({ specs: toWire(specs), explain }) });
      setResults(r.results ?? []);
      if (r.budget) setBudget(r.budget);
      setExplanation(explain ? (r.explanation ?? "No explanation was returned.") : null);
    } catch (e) {
      setErr(`Run failed: ${errorText(e)}`);
    } finally { setBusy(null); }
  }

  const update = (i: number, v: PlannedSpec) => { setSpecs(specs.map((s, j) => (j === i ? v : s))); setResults(null); setExplanation(null); };
  const remove = (i: number) => { setSpecs(specs.filter((_, j) => j !== i)); setResults(null); };
  const exhausted = budget != null && budget.remaining <= 0;
  const needsBudget = specs.some((s) => s.node === "paypal");

  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Question console</h1>
          <p className="muted">Ask a question. The planner proposes structured queries (never SQL). Review and edit them, then run. Only aggregates come back.</p>
        </div>
        <div className="head-budget"><BudgetMeter budget={budget} /></div>
      </div>

      <section className="card">
        <form className="ask" onSubmit={(e) => { e.preventDefault(); plan(); }}>
          <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)}
                 placeholder="e.g. Where is NMB-P8-128 selling outside its channel?" />
          <button type="submit" disabled={busy !== null || !question.trim()}>{busy === "plan" ? "Planning…" : "Plan queries"}</button>
        </form>
        <div className="chips examples">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="chip" onClick={() => { setQuestion(q); plan(q); }}>{q}</button>
          ))}
        </div>
        {err && <div className="refusal" role="alert">{err}</div>}
      </section>

      {(specs.length > 0 || rationale || err) && (
        <section className="card">
          <h2>Planned queries</h2>
          {rationale && <p className="rationale">{rationale}</p>}
          {specs.map((s, i) => (
            <SpecEditor key={i} index={i} value={s} onChange={(v) => update(i, v)} onRemove={() => remove(i)} />
          ))}
          <div className="row actions">
            <button type="button" className="secondary" onClick={() => setSpecs([...specs, newSpec()])}>Add query</button>
            <span className="spacer" />
            {exhausted && needsBudget && <span className="text-bad small">Privacy budget exhausted: PayPal-side queries will be refused unless cached.</span>}
            <button type="button" disabled={busy !== null || !specs.length} onClick={() => run(false)}>
              {busy === "run" ? "Running…" : `Run ${specs.length} quer${specs.length === 1 ? "y" : "ies"}`}
            </button>
          </div>
        </section>
      )}

      {results && (
        <section className="card">
          <div className="row between">
            <h2>Results</h2>
            <button type="button" className="secondary" disabled={busy !== null} onClick={() => run(true)}>
              {busy === "explain" ? "Explaining…" : "Explain"}
            </button>
          </div>
          {explanation && <div className="explanation"><strong>Explanation</strong><p>{explanation}</p></div>}
          {results.length === 0 && <p className="muted">No results returned.</p>}
          {results.map((r, i) => {
            const spec = r.spec ?? specs[i]?.spec;
            const title = spec ? `Q${i + 1}: ${label(spec.metric)}${spec.group_by?.length ? ` by ${spec.group_by.map(label).join(" and ")}` : ""}` : `Q${i + 1}`;
            return (
              <div key={i} className="result-block">
                <ResultView result={{ ...r, node: r.node ?? specs[i]?.node, spec }} title={title} />
              </div>
            );
          })}
        </section>
      )}
    </main>
  );
}
