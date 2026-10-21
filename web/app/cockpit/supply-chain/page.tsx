"use client";
import { useState } from "react";
import SupplyChainPanel from "@/components/cockpit/SupplyChainPanel";
import { SKUS } from "@/lib/api";

const STORES = ["store_a", "store_b", "store_c", "store_d", "store_e", "store_f"];

export default function SupplyChainPage() {
  const [sku, setSku] = useState("");
  const [store, setStore] = useState("");
  return (
    <main className="wide">
      <div className="page-head">
        <div>
          <h1>Supply chain</h1>
          <p className="muted">Batches moving from the brand to distributors to stores, by week. Red bars are units that sold at a store outside the batch&apos;s channel.</p>
        </div>
      </div>
      <section className="card">
        <div className="row filters">
          <label>Product
            <select value={sku} onChange={(e) => setSku(e.target.value)}>
              <option value="">All products</option>
              {SKUS.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>Store
            <select value={store} onChange={(e) => setStore(e.target.value)}>
              <option value="">All stores</option>
              {STORES.map((s) => <option key={s} value={s}>Store {s.slice(-1).toUpperCase()}</option>)}
            </select>
          </label>
        </div>
        <SupplyChainPanel sku={sku || undefined} storeId={store || undefined} />
      </section>
    </main>
  );
}
