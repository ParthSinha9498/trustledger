"use client";
import type { ColDef } from "ag-grid-community";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Grid from "@/components/Grid";
import BlockedChart, { type BlockedSummary } from "@/components/cockpit/BlockedChart";
import BudgetMeter from "@/components/cockpit/BudgetMeter";
import KpiTile from "@/components/cockpit/KpiTile";
import StatusPill from "@/components/cockpit/StatusPill";
import { ink, slot } from "@/components/cockpit/chartTheme";
import { productName, reasonName, shortCase, storeName } from "@/components/cockpit/names";
import kpi from "@/components/cockpit/cockpit-charts.module.css";
import { api, errorText, type Budget, type Case } from "@/lib/api";
import styles from "./cockpit.module.css";

const WEEKS = 4;
type Store = { store_id: string; name: string };
/** /cases rows also carry how many blocked checkouts were grouped into the case. */
type CaseRow = Case & { failure_count?: number };

const CONF: Record<string, { cls: string; dots: number; text: string }> = {
  high: { cls: styles.confHigh, dots: 3, text: "High" },
  medium: { cls: styles.confMedium, dots: 2, text: "Medium" },
  low: { cls: styles.confLow, dots: 1, text: "Low" },
};

function Confidence({ value }: { value?: string | null }) {
  const c = value ? CONF[value.toLowerCase()] : undefined;
  if (!c) return <span className="muted">–</span>;
  return (
    <span className={`${styles.conf} ${c.cls}`} title={`Agent confidence: ${c.text.toLowerCase()}`}>
      <span className={styles.confDots} aria-hidden>
        {[0, 1, 2].map((i) => <i key={i} className={i < c.dots ? styles.on : undefined} />)}
      </span>
      {c.text}
    </span>
  );
}

/**
 * Show a donut only when there are ≥ 2 active slices, avoiding monochromatic or empty grey rings.
 */
function donutOrNull(name: string, segments: { label: string; value: number; color: (dark: boolean) => string }[]) {
  const active = segments.filter((s) => s.value > 0);
  if (active.length < 2) return null;
  return { kind: "donut" as const, name, segments };
}

/**
 * Who ran the investigation. Never defaults to "Live AI": cases start with the DB default agent_mode 'live'
 * before any agent has run, so status comes first, and an unknown mode shows a dash.
 */
type Mode = "Running" | "Waiting" | "Live AI" | "Interrupted" | "Offline mock" | "Replay" | "—";
function modeOf(c: Case): Mode {
  if (c.status === "open" || c.status === "investigating") return "Running";
  if (c.status === "waiting_capacity" && !c.step_count) return "Waiting";
  // Legacy rows from the scripted mock agent were stored as 'live' (same rule as the case page).
  if (c.agent_mode === "mock" || c.agent_model === "scripted-mock" || /LLM_MODE=mock/.test(c.summary ?? "")) return "Offline mock";
  if (c.agent_mode === "live") {
    const interrupted = c.status === "failed" ||
      (c.status === "waiting_capacity" && ((c.step_count ?? 0) > 0 || (c.findings ?? 0) > 0));
    return interrupted ? "Interrupted" : "Live AI";
  }
  if (c.agent_mode === "replay") return "Replay";
  return "—";
}
const MODE_PILL: Record<Mode, string | null> = {
  Running: "pill-run", Waiting: "pill-open", "Live AI": "pill-ok", Interrupted: "pill-open", "Offline mock": "", Replay: "pill-run", "—": null,
};

const shortDate = (v?: string) => v
  ? new Date(v).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";

export default function Cockpit() {
  const [cases, setCases] = useState<CaseRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [stores, setStores] = useState<Record<string, string>>({});
  const [blocked, setBlocked] = useState<BlockedSummary | null>(null);
  const [blockedErr, setBlockedErr] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(max-width: 640px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    let live = true;
    const load = () => api<CaseRow[]>("/cases")
      .then((d) => { if (live) { setCases(d); setErr(null); } })
      .catch((e) => live && setErr(errorText(e)));
    load();
    api<Budget>("/console/budget").then((b) => live && setBudget(b)).catch(() => {});
    api<Store[]>("/stores").then((s) => live && setStores(Object.fromEntries(s.map((x) => [x.store_id, x.name])))).catch(() => {});
    const t = setInterval(load, 4000);
    return () => { live = false; clearInterval(t); };
  }, []);

  // Failed checks change only when a scan is blocked, which also touches a case: refetch on that signal.
  const signal = (cases ?? []).reduce((n, c) => n + (c.failure_count ?? 1), 0);
  useEffect(() => {
    let live = true;
    api<BlockedSummary>(`/cockpit/blocked?weeks=${WEEKS}`)
      .then((d) => { if (live) { setBlocked(d); setBlockedErr(null); } })
      .catch((e) => live && setBlockedErr(errorText(e)));
    return () => { live = false; };
  }, [signal]);

  const names = useMemo(() => ({ ...(blocked?.store_names ?? {}), ...stores }), [blocked, stores]);

  const columns = useMemo<ColDef<CaseRow>[]>(() => [
    { field: "case_id", headerName: "Case", minWidth: 100, maxWidth: 120,
      cellRenderer: (p: { value: string }) => <span className={styles.caseRef}>{shortCase(p.value)}</span> },
    { field: "store_id", headerName: "Store", minWidth: 100, valueFormatter: (p) => storeName(p.value as string, names) },
    { field: "sku", headerName: "Product", minWidth: 150, valueFormatter: (p) => productName(p.value as string) },
    { field: "reason_code", headerName: "Reason", minWidth: 140, valueFormatter: (p) => reasonName(p.value as string) },
    { field: "failure_count", headerName: "Blocked", maxWidth: 110, minWidth: 96, cellClass: "ag-right-aligned-cell",
      headerTooltip: "Blocked checkouts grouped into this case" },
    { field: "status", headerName: "Status", minWidth: 130, cellRenderer: (p: { value: string }) => <StatusPill status={p.value} /> },
    { field: "confidence", headerName: "Confidence", minWidth: 130, cellRenderer: (p: { value?: string }) => <Confidence value={p.value} /> },
    { field: "findings", headerName: "Findings", maxWidth: 110, minWidth: 96, cellClass: "ag-right-aligned-cell" },
    { colId: "mode", headerName: "Run", minWidth: 130, valueGetter: (p) => (p.data ? modeOf(p.data) : ""),
      cellRenderer: (p: { value: Mode }) => MODE_PILL[p.value] == null ? <span className="muted">—</span>
        : <span className={`pill ${MODE_PILL[p.value]}`}>{p.value}</span> },
    { field: "created_at", headerName: "Opened", minWidth: 140, sort: "desc", valueFormatter: (p) => shortDate(p.value as string) },
  ], [names]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const x of cases ?? []) c[x.status] = (c[x.status] ?? 0) + 1;
    return c;
  }, [cases]);
  const findings = (cases ?? []).reduce((n, c) => n + (c.findings ?? 0), 0);
  const conf = useMemo(() => {
    const c: Record<string, number> = { high: 0, medium: 0, low: 0 };
    for (const x of cases ?? []) if (x.confidence && x.confidence in c) c[x.confidence] += 1;
    return c;
  }, [cases]);

  const weekly = useMemo(() => (blocked?.weeks ?? []).map((w) => ({
    x: `Wk ${w}`, y: blocked!.by_reason.filter((r) => r.week === w).reduce((n, r) => n + r.value, 0),
  })), [blocked]);
  const perStore = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of blocked?.by_store ?? []) m[r.store_id] = (m[r.store_id] ?? 0) + r.value;
    return m;
  }, [blocked]);
  const storeOrder = useMemo(() => Object.keys(blocked?.store_names ?? {}).sort(), [blocked]);
  const topStore = Object.entries(perStore).sort((a, b) => b[1] - a[1])[0];
  const topReason = useMemo(() => {
    const m: Record<string, number> = {};
    for (const r of blocked?.by_reason ?? []) m[r.reason_code] = (m[r.reason_code] ?? 0) + r.value;
    return Object.entries(m).sort((a, b) => b[1] - a[1])[0];
  }, [blocked]);
  const inProgress = (counts.open ?? 0) + (counts.investigating ?? 0) + (counts.waiting_capacity ?? 0);

  return (
    <main className="wide">
      <div className={styles.head}>
        <div className={styles.headText}>
          <h1>Investigations</h1>
          <p className="muted">
            When the brand says no at checkout, no PayPal order is created and the AI investigator opens a case.
            It sees only aggregates: exact brand counts and privacy-protected buyer data.
          </p>
        </div>
        <div className={styles.headSide}>
          <BudgetMeter budget={budget} compact />
          <div className={styles.headLinks} role="navigation" aria-label="Cockpit tools">
            <Link href="/cockpit/console">Ask a question →</Link>
            <Link href="/cockpit/supply-chain">Supply chain →</Link>
            <Link href="/privacy">How privacy works →</Link>
          </div>
        </div>
      </div>

      <div className={kpi.kpiRow}>
        <KpiTile tone="bad" value={blocked ? blocked.total : "–"} label="Failed checks"
                 sub={topReason ? `Last ${WEEKS} weeks · mostly ${reasonName(topReason[0]).toLowerCase()}` : `Last ${WEEKS} weeks`}
                 chart={blocked ? { kind: "spark", points: weekly, name: "Failed authenticity checks per week" } : null} />
        <KpiTile value={blocked ? Object.keys(perStore).length : "–"} label="Stores with failed checks"
                 sub={topStore ? `Most: ${storeName(topStore[0], names)} (${topStore[1]})` : "None in this period"}
                 chart={blocked ? donutOrNull("Failed authenticity checks by store", storeOrder.map((s, i) => ({
                   label: storeName(s, names), value: perStore[s] ?? 0, color: (d: boolean) => slot(i, d) }))) : null} />
        <KpiTile tone="accent" value={cases ? cases.length : "–"} label="Investigations"
                 sub={`${inProgress} in progress · ${counts.complete ?? 0} complete`}
                 chart={cases ? donutOrNull("Investigations by status", [
                   { label: "Open", value: counts.open ?? 0, color: (d) => ink(d).warn },
                   { label: "Investigating", value: counts.investigating ?? 0, color: (d) => ink(d).accent },
                   { label: "Waiting for capacity", value: counts.waiting_capacity ?? 0, color: (d) => ink(d).neutral },
                   { label: "Complete", value: counts.complete ?? 0, color: (d) => ink(d).ok },
                   { label: "Failed", value: counts.failed ?? 0, color: (d) => ink(d).bad },
                 ]) : null} />
        <KpiTile tone="ok" value={cases ? findings : "–"} label="Agent findings"
                 sub={conf.high + conf.medium + conf.low
                   ? `Confidence: ${conf.high} high · ${conf.medium} medium · ${conf.low} low`
                   : "Cited from aggregates only, never raw rows"}
                 chart={cases ? donutOrNull("Completed investigations by confidence", [
                   { label: "High", value: conf.high, color: (d) => ink(d).ok },
                   { label: "Medium", value: conf.medium, color: (d) => ink(d).warn },
                   { label: "Low", value: conf.low, color: (d) => ink(d).neutral },
                 ]) : null} />
      </div>

      <section className="card elevated">
        {blockedErr && <div className="refusal">Couldn&apos;t load failed checks: {blockedErr}</div>}
        {!blocked && !blockedErr && <div className={`skeleton ${styles.chartSkeleton}`} />}
        {blocked && (
          <BlockedChart data={{ ...blocked, store_names: names }} header={
            <>
              <h2>Failed authenticity checks by week</h2>
              <p>Exact counts from the brand&apos;s verification API. A failed check means no PayPal order is created.</p>
            </>
          } />
        )}
      </section>

      <section className="card elevated">
        <div className={styles.gridHead}>
          <h2>Cases</h2>
          {cases && cases.length > 0 && <span className="muted small">Click a case to see the agent&apos;s steps and findings.</span>}
        </div>
        {err && <div className="refusal">Couldn&apos;t load cases: {err}</div>}
        {cases && cases.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyIcon} aria-hidden>
              <svg viewBox="0 0 24 24" width="28" height="28"><path d="M12 3 4.5 6v5.5c0 4.4 3.1 8.2 7.5 9.5 4.4-1.3 7.5-5.1 7.5-9.5V6L12 3Z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" /><path d="M9 9l6 6M15 9l-6 6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
            </div>
            <h3>No investigations yet</h3>
            <p className="muted">A blocked checkout opens one. The AI investigator starts within seconds.</p>
            <Link href="/pos" className="button primary">Run a blocked checkout</Link>
            <p className="muted small">Tip: at the store checkout, try serial X123 at Store B.</p>
          </div>
        ) : cases === null && !err ? (
          <div className={`skeleton ${styles.gridSkeleton}`} />
        ) : isMobile ? (
          <div style={{ display: "grid", gap: "10px" }}>
            {(cases ?? []).map((c) => (
              <div
                key={c.case_id}
                onClick={() => router.push(`/cockpit/cases/${c.case_id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") router.push(`/cockpit/cases/${c.case_id}`); }}
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--line)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px",
                  cursor: "pointer",
                  display: "grid",
                  gap: "8px",
                  boxShadow: "var(--shadow-sm)",
                  transition: "border-color var(--transition-fast)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className={styles.caseRef}>{shortCase(c.case_id)}</span>
                    <strong style={{ fontSize: "14px" }}>{storeName(c.store_id, names)}</strong>
                  </div>
                  <StatusPill status={c.status} />
                </div>
                <div style={{ fontSize: "13.5px", color: "var(--fg)" }}>
                  {reasonName(c.reason_code)}
                </div>
                <div className="muted small" style={{ display: "flex", flexWrap: "wrap", gap: "6px 10px", alignItems: "center" }}>
                  <span>{productName(c.sku)}</span>
                  <span>·</span>
                  <span>{c.failure_count ?? 1} blocked</span>
                  {c.findings ? (
                    <>
                      <span>·</span>
                      <span>{c.findings} findings</span>
                    </>
                  ) : null}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "2px", borderTop: "1px dashed var(--line)", paddingTop: "8px" }}>
                  <Confidence value={c.confidence} />
                  <span className="muted small">{shortDate(c.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.casesGrid}>
            <Grid<CaseRow> rows={cases ?? []} columns={columns} autoHeight
                        onRowClick={(c) => router.push(`/cockpit/cases/${c.case_id}`)} />
          </div>
        )}
      </section>
    </main>
  );
}
