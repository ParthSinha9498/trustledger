"""PayPal-side node: transaction data with buyer demographics, behind differential privacy.

Stands in for a capability PayPal would run internally. Raw rows and buyer keys never leave
this service. Every answer is a zCDP Gaussian release over the full public cell domain, with
each buyer bounded to K cells per query and spend clamped (see backend/common/privacy.py).
Demographics (age_band, gender) are simulated: PayPal's public API doesn't expose them.

The caller (our platform API/worker, authenticated by the node token) sets brand_id from its
own auth context. TODO(production): per-brand node credentials so brand_id can't be chosen by
the caller.
"""
import hashlib
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
        "queries_left_estimate": int(remaining // privacy.RHO_COUNT + 1e-9),
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


@app.post("/v1/query", dependencies=[Depends(require_node_token)])
def query(req: QueryRequest):
    spec, brand = req.spec, req.brand_id
    try:
        validate_for_node(spec, "paypal")
    except SpecRefused as e:
        raise HTTPException(403, {"refused": e.code, "detail": e.detail})

    dims = list(spec.group_by)
    domains = [_domain(d, brand, spec) for d in dims]
    keys = list(itertools.product(*domains))
    if len(keys) > MAX_CELLS:
        raise HTTPException(403, {"refused": "TOO_MANY_CELLS", "detail": f"{len(keys)} cells > {MAX_CELLS}"})

    cache_key = _cache_key(brand, spec)
    with db.connect("paypal_side") as c:
        hit = c.execute("SELECT response FROM query_cache WHERE cache_key=%s", (cache_key,)).fetchone()
    if hit:
        return hit["response"] | {"cached": True, "budget": budget(brand)}

    rho = privacy.rho_for(spec.metric)
    if not _charge(brand, rho):
        raise HTTPException(403, {"refused": "BUDGET_EXHAUSTED", "budget": budget(brand)})

    k = privacy.k_for(dims)
    where, params = ["brand_id = %s"], [brand]
    f = spec.filters
    for col, values in (("sku", f.sku), ("region", f.region), ("store_id", f.store_id)):
        if values:
            where.append(f"{col} = ANY(%s)")
            params.append(values)
    if f.week_from:
        where.append("week >= %s"); params.append(f.week_from)
    if f.week_to:
        where.append("week <= %s"); params.append(f.week_to)

    # dims come from a validated whitelist, so interpolating them is safe.
    dim_cols = ", ".join(dims)
    by_buyer = ", ".join(["payer_key"] + dims)
    dim_text = "concat_ws('|', " + ", ".join(f"{d}::text" for d in dims) + ")" if dims else "''"
    sql = f"""
        WITH bc AS (
            SELECT {by_buyer}, LEAST(SUM(amount), %s) AS spend
            FROM transactions WHERE {' AND '.join(where)} GROUP BY {by_buyer}
        ), r AS (
            -- keep each buyer in at most k cells of this query (pseudo-random, stable per query)
            SELECT *, ROW_NUMBER() OVER (PARTITION BY payer_key ORDER BY md5(payer_key || {dim_text} || %s)) AS rn
            FROM bc
        )
        SELECT {dim_cols + ', ' if dims else ''}COUNT(*) AS buyers, COALESCE(SUM(spend), 0) AS spend
        FROM r WHERE rn <= %s {'GROUP BY ' + dim_cols if dims else ''}
    """
    exact: dict[tuple, tuple[int, float]] = {}
    with db.connect("paypal_side") as c:
        for r in c.execute(sql, [privacy.SUM_CLAMP, *params, cache_key, k]):
            exact[tuple(r[d] for d in dims)] = (int(r["buyers"]), float(r["spend"]))

    counts = [exact.get(key, (0, 0.0))[0] for key in keys]
    sums = [exact.get(key, (0, 0.0))[1] for key in keys]
    released = privacy.release(keys, counts, sums, spec.metric, k)
    rows = [dict(zip(dims, r.pop("key"))) | r for r in released["rows"]]

    response = {
        "node": "paypal",
        "metric": spec.metric,
        "group_by": dims,
        "rows": rows,
        "suppressed_cells": released["suppressed_cells"],
        "noise": released["noise"],
        "cached": False,
    }
    with db.connect("paypal_side") as c:
        c.execute("INSERT INTO query_cache (cache_key, response) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                  (cache_key, Jsonb(response)))
    return response | {"budget": budget(brand)}


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
    key = hashlib.sha256(f"payer:{req.payer_ref}".encode()).hexdigest()[:16]
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
