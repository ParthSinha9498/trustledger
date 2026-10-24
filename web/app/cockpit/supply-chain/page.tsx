"use client";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { productName } from "@/components/cockpit/format";
import SupplyChainView from "@/components/cockpit/supply-chain/SupplyChainView";
import { api, errorText, SKUS, type SupplyChain } from "@/lib/api";

function useNarrow(query = "(max-width: 700px)"): boolean {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia(query);
    setNarrow(mq.matches);
    const on = (e: MediaQueryListEvent) => setNarrow(e.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return narrow;
}

export default function SupplyChainPage() {
  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Supply chain</h1>
          <p className="muted">
            Where each batch went: from the brand, to a distributor, to the stores it was shipped to. Red marks
            units that sold at a store the brand never shipped that batch to.
          </p>
        </div>
      </div>
      {/* The filters come from the query string (?sku=, ?store=), which is only known in the browser. */}
      <Suspense fallback={<section className="card elevated sc-panel"><div className="sc-loading muted">Loading supply chain…</div></section>}>
        <SupplyChainBody />
      </Suspense>
    </main>
  );
}

function SupplyChainBody() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  // Links from a case page open with that case's product and store already picked.
  const [sku, setSku] = useState(() => {
    const s = params.get("sku") ?? "";
    return SKUS.includes(s) ? s : "";
  });
  const [store, setStore] = useState(() => params.get("store") ?? params.get("store_id") ?? "");
  const [data, setData] = useState<SupplyChain | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const narrow = useNarrow();

  useEffect(() => {
    let live = true;
    const qs = new URLSearchParams();
    if (sku) qs.set("sku", sku);
    if (store) qs.set("store_id", store);
    setErr(null);
    api<SupplyChain>(`/supply-chain${qs.size ? `?${qs}` : ""}`)
      .then((d) => live && setData(d))
      .catch((e) => live && setErr(errorText(e)));
    return () => { live = false; };
  }, [sku, store]);

  // Keep the address in step with the filters, so a filtered view can be shared or reloaded.
  useEffect(() => {
    const qs = new URLSearchParams();
    if (sku) qs.set("sku", sku);
    if (store) qs.set("store", store);
    const next = qs.size ? `${pathname}?${qs}` : pathname;
    if (next !== `${pathname}${window.location.search}`) router.replace(next, { scroll: false });
  }, [sku, store, pathname, router]);

  // The brand's partner list is the same whatever the filter, so it also feeds the store picker.
  const stores = useMemo(() => (data?.resources ?? []).filter((r) => r.tier === "store"), [data?.resources]);
  // Drop a ?store= that names no known store, so the address and the picker agree.
  useEffect(() => {
    if (store && data && !stores.some((s) => s.id === store)) setStore("");
  }, [store, data, stores]);

  return (
    <section className="card elevated sc-panel">
      <div className="row filters sc-filters">
        <label>Product
          <select value={sku} onChange={(e) => setSku(e.target.value)}>
            <option value="">All products</option>
            {SKUS.map((s) => <option key={s} value={s}>{productName(s)}</option>)}
          </select>
        </label>
        <label>Store
          <select value={store} onChange={(e) => setStore(e.target.value)}>
            <option value="">All stores</option>
            {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
      </div>

      {err && <div className="refusal">Supply chain unavailable: {err}</div>}
      {!err && !data && <div className="sc-loading muted">Loading supply chain…</div>}
      {!err && data && <SupplyChainView data={data} narrow={narrow} />}
    </section>
  );
}
