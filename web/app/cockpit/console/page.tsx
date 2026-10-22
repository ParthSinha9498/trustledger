"use client";
import { useEffect, useState } from "react";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import ResultView from "@/components/cockpit/ResultView";
import SpecEditor from "@/components/cockpit/SpecEditor";
import { fmtNum, label } from "@/components/cockpit/format";
import { api, errorText, type Budget, type PlanResponse, type PlannedSpec, type QueryResult, type RunResponse } from "@/lib/api";
import styles from "./insights.module.css";

/** Business questions the planner answers in mock and live mode (kept in sync with tests/test_console.py). */
const EXAMPLES = [
  "Where did the P8 128GB sell, by region, in the last 8 weeks?",
  "Which age bands buy the P8 128GB vs the A5?",
  "How did weekly buyers change at Store C over the last 12 weeks?",
  "What is the spend per buyer by region?",
];

const newSpec = (): PlannedSpec => ({ node: "brand", spec: { metric: "sold_units", group_by: ["store_id"], filters: {} } });

/** Strip UI-only/legacy fields before sending (epsilon is ignored by the zCDP engine). */
const toWire = (specs: PlannedSpec[]) => specs.map(({ node, spec }) => ({
  node, spec: { metric: spec.metric, group_by: spec.group_by, filters: spec.filters ?? {} },
}));

/** Where an answer came from. A count is shown only when it is exact (brand-side sold units). */
function sourceText(r: QueryResult): string {
  const metric = r.spec?.metric ?? r.metric;
  if (r.node === "paypal") return "from verified PayPal purchases";
  if (metric === "sold_units") {
    const units = (r.rows ?? []).reduce((n, row) => n + (typeof row.value === "number" ? row.value : 0), 0);
    return `from ${fmtNum(units)} verified sale${units === 1 ? "" : "s"}`;
  }
  return metric === "shipped_units" ? "from the brand's shipment records" : "from the brand's verification records";
}

export default function InsightsPage() {
  const [question, setQuestion] = useState("");
  const [specs, setSpecs] = useState<PlannedSpec[]>([]);
  const [rationale, setRationale] = useState<string | null>(null);
  const [results, setResults] = useState<QueryResult[] | null>(null);
  const [seconds, setSeconds] = useState<number | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [busy, setBusy] = useState<"ask" | "run" | "explain" | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<Budget>("/console/budget").then(setBudget).catch(() => setBudget(null));
  }, []);

  async function execute(list: PlannedSpec[], explain: boolean, started: number) {
    const r = await api<RunResponse>("/console/run", { method: "POST", body: JSON.stringify({ specs: toWire(list), explain }) });
    setResults(r.results ?? []);
    if (r.budget) setBudget(r.budget);
    if (!explain) setSeconds((performance.now() - started) / 1000);  // explanation time is not answer time
    setExplanation(explain ? (r.explanation ?? "No explanation was returned.") : null);
  }

  /** Question -> planned queries -> answer, timed end to end. */
  async function ask(q = question) {
    if (!q.trim()) return;
    const started = performance.now();
    setBusy("ask"); setErr(null); setResults(null); setExplanation(null); setSeconds(null);
    let planned: PlannedSpec[] = [];
    try {
      const r = await api<PlanResponse>("/console/plan", { method: "POST", body: JSON.stringify({ question: q }) });
      planned = (r.specs ?? []).map((s) => ({ node: s.node, spec: { ...s.spec, group_by: s.spec?.group_by ?? [], filters: s.spec?.filters ?? {} } }));
      setSpecs(planned);
      setRationale(r.rationale ?? null);
    } catch {
      setErr("Live planning unavailable right now, try an example question.");
      setBusy(null);
      return;
    }
    try {
      if (planned.length) await execute(planned, false, started);
    } catch (e) {
      setErr(`Couldn't answer: ${errorText(e)}`);
    } finally { setBusy(null); }
  }

  async function run(explain: boolean) {
    if (!specs.length) return;
    setBusy(explain ? "explain" : "run"); setErr(null);
    try {
      await execute(specs, explain, performance.now());
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
          <h1>Brand Insights</h1>
          <p className={styles.subtitle}>Answers from verified purchases, privacy-protected.</p>
        </div>
        <div className="head-budget"><BudgetMeter budget={budget} /></div>
      </div>

      <section className="card">
        <form className={`ask ${styles.ask}`}onSubmit={(e) => { e.preventDefault(); ask(); }}>
          <input aria-label="Question" value={question} onChange={(e) => setQuestion(e.target.value)}
                 placeholder="Ask a business question, e.g. Where did the P8 128GB sell in the last 8 weeks?" />
          <button type="submit" disabled={busy !== null || !question.trim()}>{busy === "ask" ? "Answering…" : "Get answer"}</button>
          <button type="button" className="secondary" onClick={() => setSpecs((s) => [...s, newSpec()])}>Add query by hand</button>
        </form>
        <div className="chips examples">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" className="chip" disabled={busy !== null} onClick={() => { setQuestion(q); ask(q); }}>{q}</button>
          ))}
        </div>
        {err && <div className="refusal" role="alert">{err}</div>}
      </section>

      {results && (
        <section className={`card elevated ${styles.heroAnswerCard}`}>
          <div className={styles.heroHeader}>
            <div className={styles.heroHeaderLeft}>
              <h2 className={styles.heroAnswerTitle}>Answer</h2>
              <span className="pill pill-ok">From verified purchases</span>
            </div>
            <button type="button" className="secondary" disabled={busy !== null} onClick={() => run(true)}>
              {busy === "explain" ? "Explaining…" : "Explain"}
            </button>
          </div>
          {explanation && <div className="explanation"><strong>Explanation</strong><p>{explanation}</p></div>}
          {results.length === 0 && <p className="muted">No results returned.</p>}
          {results.map((r, i) => {
            const spec = r.spec ?? specs[i]?.spec;
            const node = r.node ?? specs[i]?.node;
            const title = spec ? `${label(spec.metric)}${spec.group_by?.length ? ` by ${spec.group_by.map(label).join(" and ")}` : ""}` : `Answer ${i + 1}`;
            return (
              <div key={i} className={styles.resultHeroBlock}>
                {!r.refused && seconds != null && (
                  <div className={styles.heroBanner}>
                    <div className={styles.heroTiming}>
                      <span className={styles.timingHighlight}>Answered in {seconds.toFixed(seconds < 1 ? 2 : 1)} s</span>
                      <span>{sourceText({ ...r, node, spec })}.</span>
                    </div>
                    <div className={styles.vsSurveyHero}>
                      <span className={styles.surveyTag}>A survey:</span> weeks, self-reported.
                    </div>
                  </div>
                )}
                <div className={styles.chartHeroContainer}>
                  <ResultView result={{ ...r, node, spec }} title={title} />
                </div>
              </div>
            );
          })}
        </section>
      )}

      {(specs.length > 0 || rationale) && (
        <section className={`card ${styles.secondarySection}`}>
          <div className={styles.secondaryHeader}>
            <h2 className={styles.secondaryTitle}>
              <span>Query Plan & Execution</span>
              <span className="count">{specs.length}</span>
            </h2>
          </div>
          <p className="muted small">Each question becomes structured queries (never SQL). Only aggregates come back; PayPal-side answers carry noise and spend privacy budget. Edit a query and re-run to refine.</p>
          {rationale && <p className="rationale">{rationale}</p>}
          {specs.map((s, i) => (
            <SpecEditor key={i} index={i} value={s} onChange={(v) => update(i, v)} onRemove={() => remove(i)} />
          ))}
          <div className="row actions">
            <button type="button" className="secondary" onClick={() => setSpecs([...specs, newSpec()])}>Add query</button>
            <span className="spacer" />
            {exhausted && needsBudget && <span className="text-bad small">Privacy budget exhausted: PayPal-side queries will be refused unless cached.</span>}
            <button type="button" className="secondary" disabled={busy !== null || !specs.length} onClick={() => run(false)}>
              {busy === "run" ? "Running…" : `${results ? "Re-run" : "Run"} ${specs.length} quer${specs.length === 1 ? "y" : "ies"}`}
            </button>
          </div>
        </section>
      )}

    </main>
  );
}
