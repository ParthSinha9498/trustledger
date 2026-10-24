"use client";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { Budget, QueryResult, Step } from "@/lib/api";
import ResultView from "./ResultView";
import st from "./step-timeline.module.css";
import { fmtNum, label, productName, REASON_TEXT } from "./format";

const KIND: Record<string, { label: string; cls: string }> = {
  thought: { label: "Thought", cls: "k-thought" },
  tool_call: { label: "Tool call", cls: "k-call" },
  tool_result: { label: "Result", cls: "k-result" },
  finding: { label: "Finding", cls: "k-finding" },
};

const TOOL_LABEL: Record<string, string> = {
  get_case: "Read case facts",
  query_brand_node: "Query brand node",
  query_paypal_node: "Query PayPal-side node",
  get_budget: "Check privacy limit",
  record_finding: "Record finding",
};

type Payload = Record<string, unknown>;

const QUERY_TOOLS = new Set(["query_brand_node", "query_paypal_node"]);
const FACT_LABELS: Record<string, string> = {
  skus: "Products", failure_count: "Failures in this case", investigation_run: "Run", current_week: "Current week",
};

/** Steps worth showing first: query results (tables and charts) and findings. */
function isKeyStep(s: Step): boolean {
  if (s.kind === "finding") return true;
  if (s.kind !== "tool_result") return false;
  const p = s.payload as Payload;
  return QUERY_TOOLS.has(String(p.tool ?? "")) || "rows" in ((p.result ?? {}) as Payload);
}

/** "Verification failures by Store and Reason" for a query spec. */
function queryTitle(args: Payload | undefined): string | undefined {
  const metric = typeof args?.metric === "string" ? args.metric : null;
  if (!metric) return undefined;
  const by = Array.isArray(args?.group_by) ? (args.group_by as string[]).map(label) : [];
  return by.length ? `${label(metric)} by ${by.join(" and ")}` : label(metric);
}

/** Turn "step:3", "step 3" or "#3" references into links to the step's anchor. */
export function linkSteps(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\b(?:steps?[:\s#]*)(\d+)\b/gi;
  let last = 0;
  for (const m of text.matchAll(re)) {
    const i = m.index ?? 0;
    out.push(text.slice(last, i));
    out.push(<a key={i} href={`#step-${m[1]}`} className="cite">step {m[1]}</a>);
    last = i + m[0].length;
  }
  out.push(text.slice(last));
  return out;
}

export function citationsOf(p: Payload): string[] {
  const c = p.citations;
  return Array.isArray(c) ? c.map(String) : [];
}

export function Cites({ citations }: { citations: string[] }) {
  if (!citations.length) return null;
  return (
    <span className="cites">
      {citations.map((c) => {
        const n = c.match(/(\d+)/)?.[1];
        return n ? <a key={c} href={`#step-${n}`} className="cite">step {n}</a> : <span key={c} className="cite">{c}</span>;
      })}
    </span>
  );
}

function plain(v: unknown): string {
  if (Array.isArray(v)) return v.map(plain).join(", ");
  if (v && typeof v === "object") return Object.entries(v).map(([k, x]) => `${label(k)}: ${plain(x)}`).join(" · ");
  return String(v ?? "");
}

function SpecLine({ args }: { args: Payload }) {
  const metric = typeof args.metric === "string" ? args.metric : null;
  if (!metric) {
    const entries = Object.entries(args).filter(([, v]) => v != null && v !== "");
    return entries.length ? (
      <div className="chips static">
        {entries.map(([k, v]) => <span key={k} className="chip chip-filter">{label(k)}: {plain(v)}</span>)}
      </div>
    ) : null;
  }
  const groupBy = Array.isArray(args.group_by) ? (args.group_by as string[]) : [];
  const filters = (args.filters ?? {}) as Record<string, unknown>;
  return (
    <div className="chips static">
      <span className="chip chip-metric">{label(metric)}</span>
      {groupBy.map((g) => <span key={g} className="chip chip-dim">by {label(g)}</span>)}
      {Object.entries(filters).filter(([, v]) => v != null && v !== "").map(([k, v]) => (
        <span key={k} className="chip chip-filter">{label(k)}: {Array.isArray(v) ? v.join(", ") : String(v)}</span>
      ))}
    </div>
  );
}

function factValue(k: string, v: unknown): string {
  if (k === "sku") return productName(String(v));
  if (k === "skus" && Array.isArray(v)) return v.map((x) => productName(String(x))).join(", ");
  if (k === "reason_code") return REASON_TEXT[String(v)] ?? String(v);
  return plain(v);
}

function Facts({ result }: { result: Payload }) {
  return (
    <dl className="facts">
      {Object.entries(result).map(([k, v]) => (
        <div key={k}><dt>{FACT_LABELS[k] ?? label(k)}</dt><dd>{factValue(k, v)}</dd></div>
      ))}
    </dl>
  );
}

/** get_budget, in words: no rho/epsilon outside the privacy page. */
function LimitFacts({ budget }: { budget: Budget }) {
  if (budget.private_release) {
    return <p className="small" style={{ margin: 0 }}>PayPal-side answers come from a one-time privacy-protected snapshot: asking more reveals nothing new about any buyer.</p>;
  }
  const total = budget.total ?? budget.daily ?? budget.spent + budget.remaining;
  const pct = total > 0 ? Math.round((100 * budget.remaining) / total) : 0;
  return <p className="small" style={{ margin: 0 }}>{fmtNum(pct)}% of this brand&apos;s privacy limit is left.</p>;
}

function StepBody({ step }: { step: Step }) {
  const p = step.payload as Payload;
  switch (step.kind) {
    case "thought":
      return <p className="thought">{String(p.text ?? "")}</p>;
    case "tool_call": {
      const tool = String(p.tool ?? "");
      const args = (p.args ?? {}) as Payload;
      if (tool === "record_finding") {
        return (
          <div>
            <div className="tool-name">{TOOL_LABEL[tool]}</div>
            <blockquote className={st.quote}>
              {String(args.text ?? "")} <Cites citations={citationsOf(args)} />
            </blockquote>
          </div>
        );
      }
      return (
        <div>
          <div className="tool-name">{TOOL_LABEL[tool] ?? tool}</div>
          <SpecLine args={(p.args ?? {}) as Payload} />
        </div>
      );
    }
    case "tool_result": {
      const tool = String(p.tool ?? "");
      const result = (p.result ?? {}) as Payload;
      const forStep = typeof p.for_step === "number" ? p.for_step : null;
      const head = forStep ? <div className="muted small">Result of <a className="cite" href={`#step-${forStep}`}>step {forStep}</a></div> : null;
      if (QUERY_TOOLS.has(tool) || "rows" in result || "refused" in result) {
        const r = result as QueryResult;
        const node = r.node ?? (tool === "query_paypal_node" ? "paypal" : "brand");
        return <>{head}<ResultView result={{ ...r, node }} /></>;
      }
      if (tool === "get_budget" && typeof result.remaining === "number") {
        return <>{head}<LimitFacts budget={result as unknown as Budget} /></>;
      }
      return <>{head}<Facts result={result} /></>;
    }
    case "finding":
      return (
        <div className="finding">
          <p>{String(p.text ?? "")}</p>
          <Cites citations={citationsOf(p)} />
        </div>
      );
    default:
      return <pre>{JSON.stringify(p, null, 2)}</pre>;
  }
}

/** Findings and query results first; thoughts and tool calls behind "Show all N steps". */
export default function StepTimeline({ steps: allSteps, isReplay = false }: { steps: Step[]; isReplay?: boolean }) {
  // Token usage is bookkeeping, not part of the investigation story.
  const steps = useMemo(() => allSteps.filter((s) => s.kind !== "usage"), [allSteps]);
  const keySteps = useMemo(() => steps.filter(isKeyStep), [steps]);
  const calls = useMemo(() => new Map(steps.filter((s) => s.kind === "tool_call").map((s) => [s.n, s.payload as Payload])), [steps]);
  const [expanded, setExpanded] = useState(false);
  const [playbackCount, setPlaybackCount] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  // Nothing worth highlighting yet (still running): show everything.
  const showAll = expanded || keySteps.length === 0;
  const listed = showAll ? steps : keySteps;

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setPlaybackCount((curr: number | null) => {
        const next = (curr ?? 0) + 1;
        if (next >= steps.length) {
          setPlaying(false);
          return null; // show all
        }
        return next;
      });
    }, 350);
    return () => clearInterval(interval);
  }, [playing, steps.length]);

  // A citation can point at a hidden thought or tool call: expand, then scroll to it.
  useEffect(() => {
    if (showAll) return;
    const shown = new Set(listed.map((s) => s.n));
    const reveal = (n: number) => {
      if (shown.has(n) || !steps.some((s) => s.n === n)) return;
      setExpanded(true);
      setTimeout(() => document.getElementById(`step-${n}`)?.scrollIntoView({ block: "start" }), 60);
    };
    const fromHash = () => {
      const m = window.location.hash.match(/^#step-(\d+)$/);
      if (m) reveal(Number(m[1]));
    };
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement | null)?.closest?.("a[href^='#step-']");
      const m = a?.getAttribute("href")?.match(/^#step-(\d+)$/);
      if (m) reveal(Number(m[1]));
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    document.addEventListener("click", onClick);
    return () => { window.removeEventListener("hashchange", fromHash); document.removeEventListener("click", onClick); };
  }, [showAll, listed, steps]);

  if (!steps.length) return <p className="muted">Waiting for the agent to start…</p>;

  const visibleSteps = playbackCount !== null ? listed.slice(0, playbackCount) : listed;
  const hidden = steps.length - keySteps.length;

  return (
    <>
      <div className={st.toolbar}>
        <p className="muted small" style={{ margin: 0 }}>
          {showAll
            ? `All ${steps.length} steps: the agent's reasoning, every tool call and what came back.`
            : `Showing the evidence: ${keySteps.length} of ${steps.length} steps (query results and findings).`}
        </p>
        <div className={st.actions}>
          {keySteps.length > 0 && hidden > 0 && (
            <button type="button" className="secondary small" aria-expanded={showAll}
                    onClick={() => { setExpanded(!expanded); setPlaying(false); setPlaybackCount(null); }}>
              {expanded ? "Show evidence only" : `Show all ${steps.length} steps`}
            </button>
          )}
          {isReplay && (
            <button
              type="button"
              className="secondary small"
              onClick={() => {
                if (playing) {
                  setPlaying(false);
                  setPlaybackCount(null);
                } else {
                  setExpanded(true);
                  setPlaybackCount(1);
                  setPlaying(true);
                }
              }}
            >
              {playing ? `Playing step ${playbackCount ?? 1} of ${steps.length}… (Stop)` : "Replay Steps"}
            </button>
          )}
        </div>
      </div>
      <ol className="timeline">
        {visibleSteps.map((s) => {
          const k = KIND[s.kind] ?? { label: s.kind, cls: "" };
          const p = s.payload as Payload;
          const forStep = typeof p.for_step === "number" ? p.for_step : null;
          const title = s.kind === "tool_result" && forStep ? queryTitle(calls.get(forStep)?.args as Payload | undefined) : undefined;
          return (
            <li key={s.n} id={`step-${s.n}`} className={`tl-item ${k.cls}`}>
              <div className="tl-marker" aria-hidden />
              <div className="tl-content">
                <div className={`tl-head ${st.head}`}>
                  <span className="tl-n">#{s.n}</span>
                  <span className={`kind ${k.cls}`}>{k.label}</span>
                  {title && <span className={st.title}>{title}</span>}
                  {s.at && <time className="muted small">{new Date(s.at).toLocaleTimeString()}</time>}
                </div>
                <StepBody step={s} />
              </div>
            </li>
          );
        })}
      </ol>
    </>
  );
}
