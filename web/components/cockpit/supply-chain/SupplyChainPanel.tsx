"use client";
import { useEffect, useState, type ReactNode } from "react";
import { api, errorText, type SupplyChain } from "@/lib/api";
import SupplyChainView from "./SupplyChainView";

function fetchChain(sku?: string, storeId?: string) {
  const qs = new URLSearchParams();
  if (sku) qs.set("sku", sku);
  if (storeId) qs.set("store_id", storeId);
  return api<SupplyChain>(`/supply-chain${qs.size ? `?${qs}` : ""}`);
}

/** Fetches the brand's own supply chain (exact business data) for one product/store and renders it.
 *  If no batch of the product ever reached the store (a not-in-channel case), shows the whole product instead. */
export default function SupplyChainPanel({ sku, storeId, storeName, narrow, mobileNote }: {
  sku?: string; storeId?: string; storeName?: string; narrow: boolean; mobileNote?: ReactNode;
}) {
  const [data, setData] = useState<SupplyChain | null>(null);
  const [widened, setWidened] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setErr(null);
    setWidened(false);
    fetchChain(sku, storeId)
      .then(async (d) => {
        if (storeId && sku && d.totals.batches === 0) {
          const all = await fetchChain(sku);
          if (live) { setData(all); setWidened(true); }
        } else if (live) setData(d);
      })
      .catch((e) => live && setErr(errorText(e)));
    return () => { live = false; };
  }, [sku, storeId]);

  if (err) return <div className="refusal">Supply chain unavailable: {err}</div>;
  if (!data) return <div className="sc-loading muted">Loading supply chain…</div>;
  return (
    <>
      {widened && (
        <p className="sc-summary sc-summary-bad">
          No batch of this product was ever shipped to {storeName ?? "this store"}. Showing every batch of the product instead.
        </p>
      )}
      <SupplyChainView data={data} narrow={narrow} nested mobileNote={mobileNote} />
    </>
  );
}
