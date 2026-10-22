"""PayPal-side node: transaction data with buyer demographics, behind differential privacy.

Stands in for a capability PayPal would run internally. Raw rows and buyer keys never leave
this service. Every answer is a zCDP Gaussian release over the full public cell domain, with
each buyer bounded to K cells per query and spend clamped (see backend/common/privacy.py).
Demographics (age_band, gender) are simulated: PayPal's public API doesn't expose them.

The caller (our platform API/worker, authenticated by the node token) sets brand_id from its
own auth context. This demo uses one shared node token; a production deployment would issue per-brand
node credentials so brand_id is bound to the authenticated caller rather than chosen by it.
"""
import hashlib
import hmac
import itertools
import json
import uuid

from fastapi import Depends, FastAPI, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend import config, db
from backend.common import privacy
from backend.common.auth import require_node_token
from backend.common.query_spec import MAX_CELLS, QuerySpec, SpecRefused, validate_for_node

app = FastAPI(title="TrustLedger PayPal-side node")

AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["female", "male", "other"]


@app.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------- budget ledger (persistent)

def budget(brand: str) -> dict:
    with db.connect("paypal_side") as c:
        row = c.execute("SELECT rho_spent FROM privacy_ledger WHERE brand_id=%s", (brand,)).fetchone()
    spent = row["rho_spent"] if row else 0.0
    total = privacy.total_rho()
    remaining = max(0.0, total - spent)
    return {
        "unit": "rho (zCDP)",
        "spent": round(spent, 4),
        "remaining": round(remaining, 4),
        "total": total,
        "daily": total,  # kept for older clients; the budget is per dataset, not per day
        "eps_equivalent_total": round(privacy.eps_equivalent(total), 2),
        "release_rho": privacy.RELEASE_RHO,
        "private_release": True,
        "guarantee": "Answered from the private release: no further budget spent",
    }


def _charge(brand: str, rho: float) -> bool:
    """Atomically add rho if it fits in the total. Returns False when the budget would be exceeded."""
    with db.connect("paypal_side") as c:
        c.execute("INSERT INTO privacy_ledger (brand_id) VALUES (%s) ON CONFLICT DO NOTHING", (brand,))
        row = c.execute(
            "UPDATE privacy_ledger SET rho_spent = rho_spent + %s "
            "WHERE brand_id = %s AND rho_spent + %s <= %s + 1e-12 RETURNING rho_spent",
            (rho, brand, rho, privacy.total_rho()),
        ).fetchone()
    return row is not None


@app.get("/v1/budget", dependencies=[Depends(require_node_token)])
def get_budget(brand_id: str):
    return budget(brand_id)


# ---------------------------------------------------------------- queries

def _data_version() -> str:
    with db.connect("paypal_side") as c:
        return c.execute("SELECT value FROM meta WHERE key='data_version'").fetchone()["value"]


def _cache_key(brand: str, spec: QuerySpec) -> str:
    """Canonical form: sorted dims and filter lists, so reworded-but-equal queries share a key."""
    f = spec.filters.model_dump(exclude_none=True)
    canonical = {
        "metric": spec.metric,
        "group_by": sorted(spec.group_by),
        "filters": {k: sorted(v) if isinstance(v, list) else v for k, v in sorted(f.items())},
    }
    raw = json.dumps({"brand": brand, "spec": canonical, "v": _data_version()}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _domain(dim: str, brand: str, spec: QuerySpec) -> list:
    """Public domain of a dimension. Store and SKU catalogs are public, not buyer data."""
    f = spec.filters
    if dim in ("store_id", "region", "city"):
        with db.connect("paypal_side") as c:
            vals = sorted({r[dim] for r in c.execute(f"SELECT {dim} FROM catalog_stores WHERE brand_id=%s", (brand,))})
        if dim == "store_id" and f.store_id:
            vals = [v for v in vals if v in f.store_id]
        if dim == "region" and f.region:
            vals = [v for v in vals if v in f.region]
        return vals
    if dim == "sku":
        with db.connect("paypal_side") as c:
            vals = sorted(r["sku"] for r in c.execute("SELECT sku FROM catalog_skus WHERE brand_id=%s", (brand,)))
        return [v for v in vals if not f.sku or v in f.sku]
    if dim == "week":
        lo, hi = f.week_from or 1, f.week_to or config.current_week()
        return list(range(lo, hi + 1))
    if dim == "age_band":
        return AGE_BANDS
    if dim == "gender":
        return GENDERS
    raise ValueError(dim)


class QueryRequest(BaseModel):
    brand_id: str
    spec: QuerySpec
    purpose: str = "console"


import math


class MarginalReleaseEngine:
    def __init__(self, brand_id: str):
        self.brand_id = brand_id

    def get_latest_release(self) -> dict:
        with db.connect("paypal_side") as c:
            row = c.execute(
                "SELECT * FROM private_releases WHERE brand_id=%s ORDER BY created_at DESC LIMIT 1",
                (self.brand_id,)
            ).fetchone()
        if not row:
            raise SpecRefused("NOT_IN_RELEASE", f"No private release found for brand '{self.brand_id}'")
        return row

    def query(self, spec: QuerySpec) -> dict:
        release = self.get_latest_release()
        rel_id = release["release_id"]
        dims = list(spec.group_by)
        f = spec.filters

        # Identify required dimensions by group_by and filters
        needed_dims = set(dims)
        filter_dims = set()
        f_store_id = getattr(f, "store_id", None)
        f_region = getattr(f, "region", None)
        f_city = getattr(f, "city", None)
        f_sku = getattr(f, "sku", None)
        f_week_from = getattr(f, "week_from", None)
        f_week_to = getattr(f, "week_to", None)
        f_age_band = getattr(f, "age_band", None)
        f_gender = getattr(f, "gender", None)

        if f_store_id:
            filter_dims.add("store_id")
        if f_region or f_city:
            filter_dims.add("store_id")
        if f_sku:
            filter_dims.add("sku")
        if f_week_from is not None or f_week_to is not None:
            filter_dims.add("week")
        if f_age_band:
            filter_dims.add("age_band")
        if f_gender:
            filter_dims.add("gender")

        # Map region/city in group_by to store_id for marginal coverage check
        req_dims = set()
        for d in needed_dims:
            if d in ("region", "city"):
                req_dims.add("store_id")
            else:
                req_dims.add(d)

        with db.connect("paypal_side") as c:
            cat_stores = c.execute("SELECT store_id, region, city FROM catalog_stores WHERE brand_id=%s", (self.brand_id,)).fetchall()
            cat_skus = c.execute("SELECT sku FROM catalog_skus WHERE brand_id=%s", (self.brand_id,)).fetchall()

        num_stores = len(cat_stores) or 6
        num_skus = len(cat_skus) or 3

        # Check each marginal in WORKLOAD
        candidates = []
        for m in privacy.WORKLOAD:
            m_dims = set(m["dims"])
            if spec.metric == "sum_amount" and m["metric"] != "both":
                continue

            if not req_dims.issubset(m_dims):
                continue

            # Strict router rule: refuse if any requested filter cannot be applied
            if not filter_dims.issubset(m_dims):
                continue

            # Cells summed per output group: computed dynamically from catalog domain
            summed_dims = m_dims - req_dims
            n = 1
            if "store_id" in summed_dims:
                if f_store_id:
                    n_store = len(f_store_id)
                elif f_region:
                    n_store = max(1, len([s for s in cat_stores if s["region"] in f_region]))
                elif f_city:
                    n_store = max(1, len([s for s in cat_stores if s["city"] in f_city]))
                elif "region" in dims:
                    n_store = max(1, num_stores // max(1, len(set(s["region"] for s in cat_stores))))
                elif "city" in dims:
                    n_store = max(1, num_stores // max(1, len(set(s["city"] for s in cat_stores))))
                else:
                    n_store = num_stores
                n *= n_store
            if "sku" in summed_dims:
                n *= (len(f_sku) if f_sku else num_skus)
            if "week" in summed_dims:
                w_lo = f_week_from or 1
                w_hi = f_week_to or config.current_week()
                n *= max(1, (w_hi - w_lo + 1))
            if "age_band" in summed_dims:
                n *= (len(f_age_band) if f_age_band else len(AGE_BANDS))
            if "gender" in summed_dims:
                n *= (len(f_gender) if f_gender else len(GENDERS))

            rho_val = m["rho"] if spec.metric == "buyers" else m["rho_sum"]
            l2_val = math.sqrt(m["k"]) if spec.metric == "buyers" else (privacy.SUM_CLAMP * math.sqrt(m["k"]))
            sigma_base = privacy._sigma(l2_val, rho_val)
            query_sigma = sigma_base * math.sqrt(n)
            candidates.append({
                "marginal": m,
                "n": n,
                "query_sigma": query_sigma,
            })

        if not candidates:
            raise SpecRefused("NOT_IN_RELEASE", "Spec cannot be answered from the current private release.")

        best = min(candidates, key=lambda c: (c["query_sigma"], c["n"]))
        chosen_m = best["marginal"]
        m_id = chosen_m["id"]

        with db.connect("paypal_side") as c:
            store_meta = {}
            if any(d in ("region", "city") for d in dims) or f_region or f_city:
                for r in cat_stores:
                    store_meta[r["store_id"]] = {"region": r["region"], "city": r["city"]}

            cells = c.execute(
                "SELECT cell_key, noisy_buyers, noisy_spend, sigma_buyers, sigma_spend "
                "FROM private_release_marginals WHERE release_id=%s AND marginal_id=%s",
                (rel_id, m_id)
            ).fetchall()

        grouped = {}
        for row in cells:
            key = row["cell_key"]
            if f_store_id and key.get("store_id") not in f_store_id:
                continue
            if f_sku and key.get("sku") not in f_sku:
                continue
            if f_week_from is not None and key.get("week") is not None and key.get("week") < f_week_from:
                continue
            if f_week_to is not None and key.get("week") is not None and key.get("week") > f_week_to:
                continue
            if f_region and key.get("store_id"):
                if store_meta.get(key["store_id"], {}).get("region") not in f_region:
                    continue
            if f_city and key.get("store_id"):
                if store_meta.get(key["store_id"], {}).get("city") not in f_city:
                    continue
            if f_age_band and key.get("age_band") not in f_age_band:
                continue
            if f_gender and key.get("gender") not in f_gender:
                continue

            g_vals = []
            for d in dims:
                if d == "region" and "store_id" in key:
                    g_vals.append(store_meta.get(key["store_id"], {}).get("region"))
                elif d == "city" and "store_id" in key:
                    g_vals.append(store_meta.get(key["store_id"], {}).get("city"))
                else:
                    g_vals.append(key.get(d))
            g_key = tuple(g_vals)

            if g_key not in grouped:
                grouped[g_key] = {"buyers": 0.0, "spend": 0.0, "count": 0, "sigma_b": row["sigma_buyers"], "sigma_s": row["sigma_spend"]}
            grouped[g_key]["buyers"] += row["noisy_buyers"]
            if row["noisy_spend"] is not None:
                grouped[g_key]["spend"] += row["noisy_spend"]
            grouped[g_key]["count"] += 1

        rows = []
        suppressed = 0
        actual_n = best["n"]

        # Privacy order: Clamp individual spend first (LEAST(SUM(amount), SUM_CLAMP)), add calibrated noise, and then apply display floor suppression (clamp-before-suppression).
        for g_key, data in grouped.items():
            cell_n = data["count"] or actual_n
            sigma_query_b = data["sigma_b"] * math.sqrt(cell_n)
            ci95_b = round(1.96 * sigma_query_b, 1)
            clamped_b = max(0, int(round(data["buyers"])))

            floor_b = max(10.0, 2.0 * sigma_query_b)
            if clamped_b < floor_b:
                suppressed += 1
                continue

            row_dict = dict(zip(dims, g_key))
            if spec.metric == "buyers":
                row_dict["value"] = clamped_b
                row_dict["ci95"] = ci95_b
            elif spec.metric == "sum_amount":
                sigma_query_s = (data["sigma_s"] or 0.0) * math.sqrt(cell_n)
                ci95_s = round(1.96 * sigma_query_s, 2)
                clamped_s = max(0.0, round(data["spend"], 2))
                row_dict["value"] = clamped_s
                row_dict["ci95"] = ci95_s
                row_dict["buyers"] = clamped_b
                if clamped_b > 0:
                    mean_val = round(clamped_s / clamped_b, 2)
                    se_mean = math.sqrt(sigma_query_s**2 + (mean_val**2) * (sigma_query_b**2)) / clamped_b
                    row_dict["mean_spend"] = mean_val
                    row_dict["ci95_mean_spend"] = round(1.96 * se_mean, 2)
                else:
                    row_dict["mean_spend"] = 0.0
                    row_dict["ci95_mean_spend"] = 0.0
            rows.append(row_dict)

        rows.sort(key=lambda r: [str(r.get(d, "")) for d in dims])
        sigma_rep = best["query_sigma"]
        noise_info = {
            "mechanism": "zCDP private release",
            "release_id": rel_id,
            "marginal_id": m_id,
            "rho": privacy.RELEASE_RHO,
            "eps_equivalent": privacy.RELEASE_EPS,
            "delta": privacy.DELTA,
            "k": chosen_m["k"],
            "cells_summed": actual_n,
            "sigma": round(sigma_rep, 2),
            "ci95": round(1.96 * sigma_rep, 1),
            "display_floor": round(max(10.0, 2.0 * sigma_rep), 1),
            "private_release": True,
            "guarantee": "Answered from the private release: no further budget spent",
        }

        return {
            "node": "paypal",
            "metric": spec.metric,
            "group_by": dims,
            "rows": rows,
            "suppressed_cells": suppressed,
            "noise": noise_info,
            "cached": False,
        }


@app.get("/v1/release/status", dependencies=[Depends(require_node_token)])
def release_status(brand_id: str):
    with db.connect("paypal_side") as c:
        row = c.execute(
            "SELECT * FROM private_releases WHERE brand_id=%s ORDER BY created_at DESC LIMIT 1",
            (brand_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "No private release found for brand")
    return {
        "release_id": row["release_id"],
        "brand_id": row["brand_id"],
        "rho_spent": row["rho_spent"],
        "eps_equivalent": row["eps_equivalent"],
        "delta": privacy.DELTA,
        "marginal_count": len(privacy.WORKLOAD),
        "created_at": str(row["created_at"]),
        "private_release": True,
        "guarantee": "Answered from the private release: no further budget spent",
    }


@app.post("/v1/query", dependencies=[Depends(require_node_token)])
def query(req: QueryRequest):
    spec, brand = req.spec, req.brand_id
    try:
        validate_for_node(spec, "paypal")
    except SpecRefused as e:
        raise HTTPException(403, {"refused": e.code, "detail": e.detail})

    cache_key = _cache_key(brand, spec)
    with db.connect("paypal_side") as c:
        hit = c.execute("SELECT response FROM query_cache WHERE cache_key=%s", (cache_key,)).fetchone()
    if hit:
        return hit["response"] | {"cached": True, "budget": budget(brand)}

    engine = MarginalReleaseEngine(brand)
    try:
        response = engine.query(spec)
    except SpecRefused as e:
        raise HTTPException(403, {"refused": e.code, "detail": e.detail})

    with db.connect("paypal_side") as c:
        c.execute(
            "INSERT INTO query_cache (cache_key, response) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (cache_key, Jsonb(response)),
        )

    return response | {"cached": False, "budget": budget(brand)}


# ---------------------------------------------------------------- ingest

class IngestRequest(BaseModel):
    order_id: str
    brand_id: str
    store_id: str
    sku: str
    amount: float
    payer_ref: str          # PayPal payer id; hashed here, never stored raw
    age_band: str           # simulated
    gender: str             # simulated


@app.post("/v1/ingest", dependencies=[Depends(require_node_token)])
def ingest(req: IngestRequest):
    """Captured sandbox orders land here (stands in for PayPal's internal transaction store).

    New data changes the data version, so cached answers are recomputed (and charged) next time.
    """
    # Keyed hash: without the node's secret, a payer ID can't be turned into its key, so a guessed ID can't be
    # checked against the data (a plain hash of a guessable ID could be).
    key = hmac.new(config.payer_hash_key(), f"payer:{req.payer_ref}".encode(), hashlib.sha256).hexdigest()[:16]
    with db.connect("paypal_side") as c, c.transaction():
        store = c.execute("SELECT region, city FROM catalog_stores WHERE store_id=%s", (req.store_id,)).fetchone()
        c.execute(
            "INSERT INTO transactions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (f"T{uuid.uuid4().hex[:10]}", req.order_id, req.brand_id, req.store_id, req.sku, req.amount,
             store["region"] if store else None, store["city"] if store else None, config.current_week(),
             key, req.age_band, req.gender, "sandbox"),
        )
        c.execute("UPDATE meta SET value = (value::int + 1)::text WHERE key='data_version'")
    return {"ok": True}
