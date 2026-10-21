const CLS: Record<string, string> = {
  open: "pill-open", investigating: "pill-run", complete: "pill-ok", failed: "pill-bad",
};

export default function StatusPill({ status }: { status: string }) {
  return <span className={`pill ${CLS[status] ?? ""}`}>{status === "investigating" ? "investigating…" : status}</span>;
}
