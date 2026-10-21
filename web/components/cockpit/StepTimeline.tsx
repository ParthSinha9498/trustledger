"use client";
import type { ReactNode } from "react";
import type { QueryResult, Step } from "@/lib/api";
import ResultView from "./ResultView";
import { label } from "./format";

const KIND: Record<string, { label: string; cls: string }> = {
  thought: { label: "Thought", cls: "k-thought" },
  tool_call: { label: "Tool call", cls: "k-call" },
  tool_result: { label: "Tool result", cls: "k-result" },
  finding: { label: "Finding", cls: "k-finding" },
};

const TOOL_LABEL: Record<string, string> = {
  get_case: "Read case facts",
  query_brand_node: "Query brand node",
  query_paypal_node: "Query PayPal-side node",
  get_budget: "Check privacy budget",
  record_finding: "Record finding",
};

type Payload = Record<string, unknown>;

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

function SpecLine({ args }: { args: Payload }) {
  const metric = typeof args.metric === "string" ? args.metric : null;
  if (!metric) {
    const keys = Object.keys(args);
    return keys.length ? <code className="args">{JSON.stringify(args)}</code> : null;
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

function Facts({ result }: { result: Payload }) {
  return (
    <dl className="facts">
      {Object.entries(result).map(([k, v]) => (
        <div key={k}><dt>{label(k)}</dt><dd>{typeof v === "object" ? JSON.stringify(v) : String(v)}</dd></div>
      ))}
    </dl>
  );
}

function StepBody({ step }: { step: Step }) {
  const p = step.payload as Payload;
  switch (step.kind) {
    case "thought":
      return <p className="thought">{String(p.text ?? "")}</p>;
    case "tool_call": {
      const tool = String(p.tool ?? "");
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
      if (tool === "query_brand_node" || tool === "query_paypal_node" || "rows" in result || "refused" in result) {
        const r = result as QueryResult;
        const node = r.node ?? (tool === "query_paypal_node" ? "paypal" : "brand");
        return <>{head}<ResultView result={{ ...r, node }} /></>;
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

export default function StepTimeline({ steps }: { steps: Step[] }) {
  if (!steps.length) return <p className="muted">Waiting for the agent to start…</p>;
  return (
    <ol className="timeline">
      {steps.map((s) => {
        const k = KIND[s.kind] ?? { label: s.kind, cls: "" };
        return (
          <li key={s.n} id={`step-${s.n}`} className={`tl-item ${k.cls}`}>
            <div className="tl-marker" aria-hidden />
            <div className="tl-content">
              <div className="tl-head">
                <span className="tl-n">#{s.n}</span>
                <span className={`kind ${k.cls}`}>{k.label}</span>
                {s.at && <time className="muted small">{new Date(s.at).toLocaleTimeString()}</time>}
              </div>
              <StepBody step={s} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
