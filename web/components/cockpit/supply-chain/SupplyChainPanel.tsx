"use client";
import { useEffect, useState, type ReactNode } from "react";
import { api, errorText, type SupplyChain } from "@/lib/api";
import SupplyChainView from "./SupplyChainView";

/** Fetches the brand's own supply chain (exact business data) for one product/store and renders it. */
export default function SupplyChainPanel({ sku, storeId, narrow, mobileNote }: {
  sku?: string; storeId?: string; narrow: boolean; mobileNote?: ReactNode;
}) {
  const [data, setData] = useState<SupplyChain | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    const qs = new URLSearchParams();
    if (sku) qs.set("sku", sku);
    if (storeId) qs.set("store_id", storeId);
    setErr(null);
    api<SupplyChain>(`/supply-chain${qs.size ? `?${qs}` : ""}`)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(errorText(e)));
    return () => { live = false; };
  }, [sku, storeId]);

  if (err) return <div className="refusal">Supply chain unavailable: {err}</div>;
  if (!data) return <div className="sc-loading muted">Loading supply chain…</div>;
  return <SupplyChainView data={data} narrow={narrow} nested mobileNote={mobileNote} />;
}
