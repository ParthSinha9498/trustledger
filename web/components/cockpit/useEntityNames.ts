"use client";
import { useEffect, useState } from "react";
import { api, type SupplyChain } from "@/lib/api";

type Names = Record<string, string>;

// One fetch per page load, shared by every result grid on the page.
let storesP: Promise<Names> | null = null;
let partnersP: Promise<Names> | null = null;

const loadStores = () => (storesP ??= api<{ store_id: string; name?: string }[]>("/stores")
  .then((rows) => Object.fromEntries(rows.filter((s) => s.name).map((s) => [s.store_id, s.name as string])))
  .catch(() => { storesP = null; return {}; }));

// Distributor names live with the brand; its supply-chain view lists every partner by name.
const loadPartners = () => (partnersP ??= api<SupplyChain>("/supply-chain")
  .then((d) => Object.fromEntries(d.resources.map((r) => [r.id, r.name])))
  .catch(() => { partnersP = null; return {}; }));

/** Display names for store ids (and distributor ids when asked). Empty until loaded; callers fall back to prettyId. */
export function useEntityNames({ stores = true, distributors = false } = {}): Names {
  const [names, setNames] = useState<Names>({});
  useEffect(() => {
    let live = true;
    Promise.all([stores ? loadStores() : {}, distributors ? loadPartners() : {}])
      .then(([s, p]) => live && setNames({ ...p, ...s }));
    return () => { live = false; };
  }, [stores, distributors]);
  return names;
}
