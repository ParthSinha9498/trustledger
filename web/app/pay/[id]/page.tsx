"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getReceipt, money, readableError, type Receipt } from "@/lib/paypal";
import PayPalPay from "@/components/checkout/PayPalPay";
import s from "@/components/checkout/checkout.module.css";

/** Customer-facing pay screen for a checkout the store already verified (PLAN B10 "Customer pay"). */
export default function PayPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [r, setR] = useState<Receipt | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReceipt(id).then((rec) => {
      if (rec.status === "CAPTURED") router.replace(`/receipt/${id}`);
      else setR(rec);
    }).catch((e) => setError(readableError(e)));
  }, [id, router]);

  if (error) return <main><div className={s.receiptWrap}><div className={s.error}>Checkout not found: {error}</div></div></main>;
  if (!r) return <main><p className="muted">Loading…</p></main>;

  return (
    <main>
      <div className={s.receiptWrap}>
        <div className={s.receipt}>
          {r.status === "AWAITING_PAYMENT" && r.paypal_order_id ? (
            <>
              <div className={s.receiptHead}>
                <div className={`${s.badge} ${s.badgeOk}`} aria-hidden>✓</div>
                <div>
                  <h1>Brand verified</h1>
                  <p>Verified before your payment was created.</p>
                </div>
              </div>
              <div className={s.receiptBody}>
                <p className={s.product}>{r.product}</p>
                <p className={s.storeLine}>{r.store_name} · Serial <code>{r.serial}</code></p>
                <div className={s.total}><span>Total</span><span>{money(r.amount)}</span></div>
                <div className={s.section}>
                  <PayPalPay checkoutId={r.checkout_id} paypalOrderId={r.paypal_order_id}
                    onPaid={() => router.push(`/receipt/${r.checkout_id}`)} />
                </div>
                <dl className={s.facts}>
                  <dt>Verification ID</dt><dd>{r.verification_id}</dd>
                  <dt>PayPal order</dt><dd>{r.paypal_order_id}</dd>
                </dl>
              </div>
            </>
          ) : (
            <>
              <div className={`${s.receiptHead} ${s.receiptHeadBad}`}>
                <div className={`${s.badge} ${s.badgeBad}`} style={{ width: 52, height: 52, fontSize: 28 }} aria-hidden>✕</div>
                <div>
                  <h1>Not verified</h1>
                  <p>This product didn&apos;t pass the brand check.</p>
                </div>
              </div>
              <div className={s.receiptBody}>
                <p className={s.noPayment}>No PayPal payment was created. An investigation has opened for the brand.</p>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
