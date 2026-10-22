"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getReceipt, money, readableError, type Receipt } from "@/lib/paypal";
import s from "@/components/checkout/checkout.module.css";

function when(ts?: string) {
  if (!ts) return null;
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString();
}

export default function ReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const [r, setR] = useState<Receipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getReceipt(id).then(setR).catch((e) => setError(readableError(e))); }, [id]);

  if (error) return <main><div className={s.receiptWrap}><div className={s.error}>Receipt not found: {error}</div></div></main>;
  if (!r) return <main><p className="muted">Loading receipt…</p></main>;

  const verified = r.brand_verified;
  const headline = verified ? "Brand verified purchase"
    : r.status === "AWAITING_PAYMENT" ? "Verified, awaiting payment"
      : r.status === "BLOCKED" ? "Not verified: no payment created" : "Not completed";

  return (
    <main>
      <div className={s.receiptWrap}>
        <article className={s.receipt} aria-label="Receipt">
          <header className={`${s.receiptHead} ${verified || r.status === "AWAITING_PAYMENT" ? "" : s.receiptHeadBad}`}>
            <div className={`${s.badge} ${verified ? s.badgeOk : s.badgeBad}`}
              style={verified ? undefined : { width: 52, height: 52, fontSize: 28 }} aria-hidden>
              {verified ? "✓" : r.status === "AWAITING_PAYMENT" ? "…" : "✕"}
            </div>
            <div>
              <h1>{headline}</h1>
              <p>Receipt {r.checkout_id}{when(r.created_at) ? ` · ${when(r.created_at)}` : ""}</p>
            </div>
          </header>
          <div className={s.receiptBody}>
            <p className={s.product}>{r.product}</p>
            <p className={s.storeLine}>{r.store_name}</p>
            <div className={s.total}><span>{verified ? "Paid with PayPal" : "Amount"}</span><span>{money(r.amount)}</span></div>
            <dl className={s.facts}>
              <dt>Serial</dt><dd>{r.serial}</dd>
              <dt>SKU</dt><dd>{r.sku}</dd>
              <dt>Verification ID</dt><dd>{r.verification_id ?? "—"}</dd>
              <dt>PayPal order ID</dt><dd>{r.paypal_order_id ?? "None (never created)"}</dd>
            </dl>
            {verified && (
              <div style={{ marginTop: "18px", padding: "14px 16px", borderRadius: "10px", background: "var(--ok-bg)", border: "1px solid var(--ok-border)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, color: "var(--ok)", fontSize: "14px", marginBottom: "4px" }}>
                  <span aria-hidden>✓</span> Proof of Brand Authenticity
                </div>
                <p style={{ margin: 0, fontSize: "13px", color: "var(--fg)", lineHeight: 1.45 }}>
                  The brand verified this unit at the store checkout prior to payment. The verification ID is stored on the
                  PayPal order in its <code>custom_id</code> field, so the payment points to the brand verification.
                </p>
              </div>
            )}
            {r.status === "AWAITING_PAYMENT" && (
              <div className={s.links}><a href={`/pay/${r.checkout_id}`}>Go to payment →</a></div>
            )}
            <div className={`${s.links} ${s.noPrint}`}>
              <a href="/pos">New checkout</a>
              <a href="#" onClick={(e) => { e.preventDefault(); window.print(); }}>Print</a>
            </div>
          </div>
        </article>
      </div>
    </main>
  );
}
