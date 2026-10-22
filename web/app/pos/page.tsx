"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type ScanResult } from "@/lib/api";
import { money, readableError } from "@/lib/paypal";
import BarcodeScanner from "@/components/checkout/BarcodeScanner";
import PayPalPay from "@/components/checkout/PayPalPay";
import { BlockedVerdict, IdleVerdict, VerifiedVerdict, VerifyingVerdict } from "@/components/checkout/Verdict";
import s from "@/components/checkout/checkout.module.css";

type Store = { store_id: string; name: string; city: string; region?: string };
const SKUS = [
  { sku: "NMB-P8-128", name: "Nimbus P8 128GB", price: 899 },
  { sku: "NMB-P8-256", name: "Nimbus P8 256GB", price: 999 },
  { sku: "NMB-A5-64", name: "Nimbus A5 64GB", price: 399 },
];

export default function Pos() {
  const router = useRouter();
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState("store_a");
  const [serial, setSerial] = useState("X123");
  const [sku, setSku] = useState(SKUS[0].sku);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [checked, setChecked] = useState<{ storeName: string; serial: string; amount: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Store[]>("/stores").then(setStores).catch((e) => setError(`Couldn't load stores: ${readableError(e)}`));
  }, []);

  const product = SKUS.find((p) => p.sku === sku)!;
  const storeName = stores.find((st) => st.store_id === storeId)?.name ?? storeId;

  async function tryGenuine() {
    reset();
    try {
      const d = await api<{ serial: string; sku: string }>(`/demo/serial?store_id=${encodeURIComponent(storeId)}`);
      setSerial(d.serial); setSku(d.sku);
    } catch {
      setError("Demo stock is at Store A (XA…) and Store B (XB…). Pick one of those stores.");
    }
  }

  function reset() { setResult(null); setChecked(null); setError(null); }

  async function verify() {
    const clean = serial.trim();
    if (!clean) { setError("Enter or scan a serial first."); return; }
    setScanning(false); setBusy(true); setError(null); setResult(null);
    setChecked({ storeName, serial: clean, amount: product.price });
    try {
      setResult(await api<ScanResult>("/checkout/scan", {
        method: "POST", body: JSON.stringify({ store_id: storeId, serial: clean, sku, amount: product.price }),
      }));
    } catch (e) {
      setChecked(null);
      setError(`Verification failed to run: ${readableError(e)}`);
    } finally { setBusy(false); }
  }

  return (
    <main>
      <div className={s.layout}>
        <section className="card" aria-labelledby="pos-title">
          <h2 id="pos-title" className={s.title}>Store checkout</h2>
          <p className={`muted ${s.sub}`}>The brand verifies the unit before a PayPal order exists.</p>

          <div className={s.sectionLabel}>Store</div>
          <div className={s.tiles} role="radiogroup" aria-label="Store">
            {(stores.length ? stores : [{ store_id: "store_a", name: "Store A", city: "" }]).map((st) => (
              <button key={st.store_id} type="button" role="radio" aria-checked={st.store_id === storeId}
                className={`${s.tile} ${st.store_id === storeId ? s.tileOn : ""}`} disabled={busy}
                onClick={() => { setStoreId(st.store_id); reset(); }}>
                {st.name}<small>{st.city}</small>
              </button>
            ))}
          </div>

          <div className={s.section}>
            <div className={s.sectionLabel}>Product</div>
            <div className={s.tiles} role="radiogroup" aria-label="Product">
              {SKUS.map((p) => (
                <button key={p.sku} type="button" role="radio" aria-checked={p.sku === sku}
                  className={`${s.tile} ${p.sku === sku ? s.tileOn : ""}`} disabled={busy}
                  onClick={() => { setSku(p.sku); reset(); }}>
                  {p.name}<small>{money(p.price)}</small>
                </button>
              ))}
            </div>
          </div>

          <div className={s.section}>
            <label htmlFor="serial" className={s.sectionLabel} style={{ display: "block" }}>Serial</label>
            <div className={s.serialRow}>
              <input id="serial" value={serial} autoComplete="off" spellCheck={false} disabled={busy}
                onChange={(e) => { setSerial(e.target.value); reset(); }}
                onKeyDown={(e) => { if (e.key === "Enter") verify(); }} />
              <button type="button" className={s.ghost} disabled={busy} onClick={() => setScanning((v) => !v)}>
                {scanning ? "Close camera" : "Scan with camera"}
              </button>
            </div>
            <p className={`muted ${s.hint}`}>
              Demo serials: <code>XA…</code> is Store A stock, <code>XB…</code> is Store B stock. Try one at the
              other store, or make one up, to see a block.{" "}
              <button type="button" className={s.linkButton} disabled={busy} onClick={tryGenuine}>
                Fill an unsold unit from this store
              </button>
            </p>
            {scanning && (
              <BarcodeScanner
                onClose={() => setScanning(false)}
                onDetected={(text) => { setSerial(text); setScanning(false); reset(); }}
              />
            )}
          </div>

          <button type="button" className={s.primary} onClick={verify} disabled={busy}>
            {busy ? "Verifying…" : `Verify and check out · ${money(product.price)}`}
          </button>
          {error && <div className={s.error} role="alert">{error}</div>}
        </section>

        <section aria-label="Verification result" aria-live="polite">
          {!result && !busy && <IdleVerdict />}
          {busy && checked && <VerifyingVerdict serial={checked.serial} storeName={checked.storeName} />}

          {result?.status === "VERIFIED" && result.paypal_order_id && (
            <VerifiedVerdict verificationId={result.verification_id ?? ""} paypalOrderId={result.paypal_order_id}>
              <div className={s.payBox}>
                <div className={s.sectionLabel}>Customer pays</div>
                <p className={s.payAmount}>{money(checked?.amount ?? product.price)}</p>
                <PayPalPay
                  checkoutId={result.checkout_id}
                  paypalOrderId={result.paypal_order_id}
                  onPaid={() => router.push(`/receipt/${result.checkout_id}`)}
                />
                <div className={s.links}>
                  <a href={`/pay/${result.checkout_id}`} target="_blank" rel="noreferrer">Open the pay screen on the customer&apos;s device ↗</a>
                </div>
              </div>
            </VerifiedVerdict>
          )}

          {result?.status === "NOT_VERIFIED" && checked && (
            <BlockedVerdict
              reason={result.reason ?? "Not verified by the brand."}
              reasonCode={result.reason_code}
              caseId={result.case_id}
              storeName={checked.storeName}
              serial={checked.serial}
            />
          )}
        </section>
      </div>
    </main>
  );
}
