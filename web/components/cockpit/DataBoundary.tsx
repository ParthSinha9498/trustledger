"use client";
import { useMemo, useState } from "react";
import type { Step } from "@/lib/api";
import s from "./data-boundary.module.css";

type Node = "brand" | "paypal";
type Exchange = {
  n: number;
  node: Node;
  question: string;
  answer: string;
  kind: "exact" | "private" | "cached" | "refused";
  rho: number;
};

const LABEL: Record<string, string> = {
  verification_failures: "verification failures", sold_units: "units sold", shipped_units: "units shipped",
  buyers: "buyers", sum_amount: "spend", store_id: "store", distributor_id: "distributor", reason_code: "reason",
  age_band: "age band", region: "region", city: "city", sku: "product", week: "week", gender: "gender",
};
const label = (k: string) => LABEL[k] ?? k.replace(/_/g, " ");

function describe(args: Record<string, unknown>): string {
  const metric = label(String(args.metric ?? "?"));
  const by = Array.isArray(args.group_by) && args.group_by.length ? ` by ${args.group_by.map(String).map(label).join(" × ")}` : "";
  const f = (args.filters ?? {}) as Record<string, unknown>;
  const parts = Object.entries(f).filter(([k]) => !k.startsWith("week_")).map(([k, v]) =>
    `${label(k)} ${Array.isArray(v) ? v.join("/") : String(v)}`);
  if (f.week_from || f.week_to) parts.push(`weeks ${f.week_from ?? "…"}–${f.week_to ?? "…"}`);
  return `${metric}${by}${parts.length ? ` · ${parts.join(", ")}` : ""}`;
}

/** Pair each node query with its result: what was asked, and what (aggregate only) came back. */
export function exchangesOf(steps: Step[]): Exchange[] {
  const results = new Map<number, Record<string, unknown>>();
  for (const st of steps) {
    if (st.kind !== "tool_result") continue;
    const p = st.payload as { for_step?: number; result?: Record<string, unknown> };
    if (typeof p.for_step === "number") results.set(p.for_step, p.result ?? {});
  }
  const out: Exchange[] = [];
  for (const st of steps) {
    if (st.kind !== "tool_call") continue;
    const p = st.payload as { tool?: string; args?: Record<string, unknown> };
    if (p.tool !== "query_brand_node" && p.tool !== "query_paypal_node") continue;
    const node: Node = p.tool === "query_brand_node" ? "brand" : "paypal";
    const r = results.get(st.n) ?? {};
    const rows = Array.isArray(r.rows) ? r.rows.length : 0;
    const noise = (r.noise ?? {}) as { sigma?: number; rho?: number };
    let kind: Exchange["kind"]; let answer: string; let rho = 0;
    if (r.refused) {
      kind = "refused";
      const why = typeof r.refused === "object" ? String((r.refused as { refused?: string }).refused ?? "") : String(r.refused);
      answer = `refused · ${why.replace(/_/g, " ").toLowerCase() || "rule"}`;
    } else if (node === "brand") {
      kind = "exact"; answer = `${rows} aggregate row${rows === 1 ? "" : "s"} · exact`;
    } else if (r.cached) {
      kind = "cached"; answer = `${rows} rows · repeat question, nothing new revealed`;
    } else {
      kind = "private"; rho = Number(noise.rho ?? 0);
      const hidden = Number(r.suppressed_cells ?? 0);
      answer = `${rows} group rows · ±${Math.round(Number(noise.sigma ?? 0) * 1.96)} noise${hidden ? ` · ${hidden} tiny groups hidden` : ""}`;
    }
    out.push({ n: st.n, node, question: describe(p.args ?? {}), answer, kind, rho });
  }
  return out;
}

const VAULT: Record<Node, { title: string; holds: string; gives: string }> = {
  brand: { title: "Brand node", holds: "Serials · batches · shipments · verification log",
           gives: "Answers with business-level counts only" },
  paypal: { title: "PayPal-side node", holds: "Transactions · hashed buyer IDs · demographics",
            gives: "Answers with noisy aggregates only" },
};

function Vault({ node }: { node: Node }) {
  const v = VAULT[node];
  return (
    <div className={`${s.vault} ${s[node]}`}>
      <div className={s.lock} aria-hidden="true">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <strong>{v.title}</strong>
      <span className={s.holds}>{v.holds}</span>
      <span className={s.stays}>Stays here</span>
      <span className={s.gives}>{v.gives}</span>
    </div>
  );
}

export default function DataBoundary({ steps }: { steps: Step[] }) {
  const ex = useMemo(() => exchangesOf(steps), [steps]);
  const [run, setRun] = useState(0);
  if (!ex.length) return null;
  return (
    <div className={s.wrap} key={run}>
      <Vault node="brand" />
      <ol className={s.lanes} aria-label="Questions the agent sent and what came back">
        <li className={s.agent} aria-hidden>AI agent</li>
        {ex.map((e, i) => (
          <li key={e.n} className={`${s.lane} ${s[e.node]}`} style={{ ["--i" as string]: i }}>
            <span className={`${s.q} ${s.question}`} title="Question sent to the node">
              {e.node === "brand" && "← "}<a href={`#step-${e.n}`} className={s.n}>#{e.n}</a> {e.question}{e.node === "paypal" && " →"}
            </span>
            <span className={`${s.q} ${s.answer} ${s[e.kind]}`} title="What came back">{e.answer}</span>
          </li>
        ))}
      </ol>
      <Vault node="paypal" />
      <div className={s.footer}>
        <span><b>{ex.length}</b> questions sent</span>
        <span><b>0</b> records left a node</span>
        <span><b>{ex.filter((e) => e.kind === "private").length}</b> answers with privacy noise</span>
        <button type="button" className="secondary" onClick={() => setRun((r) => r + 1)}>Replay</button>
      </div>
    </div>
  );
}
