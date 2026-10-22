const CLS: Record<string, string> = {
  open: "pill-open", investigating: "pill-run", complete: "pill-ok", failed: "pill-bad",
  waiting_capacity: "pill-warn",
};

export default function StatusPill({ status }: { status: string }) {
  const text = status === "waiting_capacity" ? "waiting capacity" : (status === "investigating" ? "investigating…" : status);
  return <span className={`pill ${CLS[status] ?? ""}`}>{text}</span>;
}
