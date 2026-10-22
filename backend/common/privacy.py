"""Differential privacy for the PayPal-side node. See ../DP_RESEARCH.md for the reasoning and sources.

Privacy unit: one buyer (payer_key) across a whole query and across all of a brand's queries.
Accounting: zero-concentrated DP (zCDP). Per-query rho values add up exactly.
Mechanism: Gaussian via OpenDP (discrete Gaussian for counts, float Gaussian for clamped sums).

Contribution bounding (done in SQL by the node): each buyer is kept in at most K cells of a query
(a pseudo-random subset), and each buyer's spend per cell is clamped to SUM_CLAMP. So the L2
sensitivity is sqrt(K) for counts and SUM_CLAMP * sqrt(K) for sums.
"""
import itertools
import math
import os
import uuid

import opendp.prelude as dp
from psycopg.types.json import Jsonb

dp.enable_features("contrib")

K_DEFAULT = 4                 # max cells per buyer per query
FIXED_PER_BUYER_DIMS = {"age_band", "gender"}   # a buyer has one value, so K = 1 suffices
SUM_CLAMP = 1000.0            # max spend per buyer per cell (top product price is 999)
DELTA = 1e-8                  # only used to report an (eps, delta) equivalent
DISPLAY_FLOOR_MIN = 10        # suppress noisy counts below max(10, 2 sigma)

RELEASE_RHO = 0.20            # One-time private release spend under zCDP
RELEASE_EPS = 3.69            # eps equivalent via OpenDP at delta=1e-8 for rho=0.20

# Canonical 6-marginal workload config for private release
WORKLOAD = [
    {
        "id": "M1",
        "dims": ["store_id", "sku", "week"],
        "metric": "buyers",
        "k": 4,
        "rho": 0.060,
    },
    {
        "id": "M2",
        "dims": ["store_id", "sku", "age_band"],
        "metric": "buyers",
        "k": 2,
        "rho": 0.035,
    },
    {
        "id": "M3",
        "dims": ["store_id", "age_band", "gender"],
        "metric": "buyers",
        "k": 2,
        "rho": 0.025,
    },
    {
        "id": "M4",
        "dims": ["store_id"],
        "metric": "both",
        "k": 1,
        "rho_count": 0.015,
        "rho_sum": 0.020,
        "rho": 0.035,
    },
    {
        "id": "M5",
        "dims": ["sku", "week"],
        "metric": "buyers",
        "k": 4,
        "rho": 0.020,
    },
    {
        "id": "M6",
        "dims": ["store_id", "sku"],
        "metric": "both",
        "k": 2,
        "rho_count": 0.010,
        "rho_sum": 0.015,
        "rho": 0.025,
    },
]

RHO_COUNT = 0.01              # interactive legacy query
RHO_SUM_COUNT = 0.005         # interactive legacy query
RHO_SUM_SUM = 0.015           # interactive legacy query
_TOL = 1e-9


def total_rho() -> float:
    """Per brand, per dataset. Never reset by the calendar."""
    return float(os.environ.get("PRIVACY_TOTAL_RHO", "0.25"))


def rho_for(metric: str) -> float:
    return RHO_SUM_COUNT + RHO_SUM_SUM if metric == "sum_amount" else RHO_COUNT


def k_for(group_by: list[str]) -> int:
    return 1 if set(group_by) <= FIXED_PER_BUYER_DIMS else K_DEFAULT


def _sigma(l2: float, rho: float) -> float:
    # Gaussian mechanism under zCDP: rho = (l2 / sigma)^2 / 2
    return l2 / math.sqrt(2 * rho)


def eps_equivalent(rho: float, delta: float = DELTA) -> float:
    if rho <= 0:
        return 0.0
    m = dp.m.make_gaussian(dp.atom_domain(T=float, nan=False), dp.absolute_distance(T=float),
                           scale=1 / math.sqrt(2 * rho))
    return float(dp.c.make_zCDP_to_approxDP(m).map(1.0).epsilon(delta))


def _noisy_counts(values: list[int], k: int, rho: float) -> tuple[list[int], float]:
    l2 = math.sqrt(k)
    sigma = _sigma(l2, rho)
    meas = dp.m.make_gaussian(dp.vector_domain(dp.atom_domain(T=int)), dp.l2_distance(T=float), scale=sigma)
    assert meas.map(l2) <= rho + _TOL, "OpenDP cost exceeds the charged rho"
    return list(meas(values)), sigma


def _noisy_sums(values: list[float], k: int, rho: float) -> tuple[list[float], float]:
    l2 = SUM_CLAMP * math.sqrt(k)
    sigma = _sigma(l2, rho)
    meas = dp.m.make_gaussian(dp.vector_domain(dp.atom_domain(T=float, nan=False)),
                              dp.l2_distance(T=float), scale=sigma)
    assert meas.map(l2) <= rho + _TOL, "OpenDP cost exceeds the charged rho"
    return list(meas(values)), sigma


def release(keys: list[tuple], counts: list[int], sums: list[float], metric: str, k: int) -> dict:
    """Release one DP answer over the FULL public cell domain (zeros included, so keys reveal nothing).

    Suppression uses only the noisy count (post-processing, no extra privacy cost).
    """
    rows: list[dict] = []
    suppressed = 0
    if metric == "buyers":
        noisy, sigma = _noisy_counts(counts, k, RHO_COUNT)
        floor = max(DISPLAY_FLOOR_MIN, 2 * sigma)
        for key, n in zip(keys, noisy):
            if n < floor:
                suppressed += 1
                continue
            rows.append({"key": key, "value": int(n), "ci95": round(1.96 * sigma, 1)})
        noise = {"sigma": round(sigma, 2)}
    elif metric == "sum_amount":
        noisy_n, sigma_n = _noisy_counts(counts, k, RHO_SUM_COUNT)
        noisy_s, sigma_s = _noisy_sums(sums, k, RHO_SUM_SUM)
        floor = max(DISPLAY_FLOOR_MIN, 2 * sigma_n)
        for key, n, s in zip(keys, noisy_n, noisy_s):
            if n < floor:
                suppressed += 1
                continue
            s = max(s, 0.0)
            rows.append({"key": key, "value": round(s, 2), "ci95": round(1.96 * sigma_s, 2),
                         "buyers": int(n), "mean_spend": round(s / n, 2)})
        noise = {"sigma": round(sigma_s, 2), "sigma_buyers": round(sigma_n, 2)}
    else:
        raise ValueError(metric)
    rho = rho_for(metric)
    noise |= {
        "mechanism": "gaussian (zCDP)",
        "rho": rho,
        "eps_equivalent": round(eps_equivalent(rho), 3),
        "delta": DELTA,
        "k": k,
        "clamp": SUM_CLAMP,
        "display_floor": round(floor, 1),
    }
    return {"rows": rows, "suppressed_cells": suppressed, "noise": noise}


def build_release(brand: str, release_id: str | None = None) -> dict:
    """Build a one-time private release for a brand by measuring the canonical 6-marginal workload.

    Post-processing guarantees:
    - Measures noisy cells unsuppressed under zCDP Gaussian mechanism
    - Each buyer is truncated to at most K cells per marginal
    - Total rho = 0.20 charged once to the ledger
    - Stores release in private_releases and private_release_marginals
    """
    from backend import config, db

    rel_id = release_id or f"rel_{brand}_{uuid.uuid4().hex[:10]}"
    with db.connect("paypal_side") as c:
        if c.execute("SELECT 1 FROM private_releases WHERE release_id=%s", (rel_id,)).fetchone():
            rel_id = f"{rel_id}_{uuid.uuid4().hex[:6]}"

    # Check ledger spend first
    with db.connect("paypal_side") as c:
        row = c.execute("SELECT rho_spent FROM privacy_ledger WHERE brand_id=%s", (brand,)).fetchone()
        spent = row["rho_spent"] if row else 0.0
        if spent + RELEASE_RHO > total_rho() + 1e-9:
            raise ValueError(f"Insufficient privacy budget for private release: spent {spent}, needs {RELEASE_RHO}, total {total_rho()}")

    AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
    GENDERS = ["female", "male", "other"]

    with db.connect("paypal_side") as c:
        stores = sorted(r["store_id"] for r in c.execute("SELECT store_id FROM catalog_stores WHERE brand_id=%s", (brand,)))
        skus = sorted(r["sku"] for r in c.execute("SELECT sku FROM catalog_skus WHERE brand_id=%s", (brand,)))
    weeks = list(range(1, config.current_week() + 1))

    domain_map = {
        "store_id": stores,
        "sku": skus,
        "week": weeks,
        "age_band": AGE_BANDS,
        "gender": GENDERS,
    }

    marginals_data = []

    with db.connect("paypal_side") as c, c.transaction():
        for m in WORKLOAD:
            m_id = m["id"]
            dims = m["dims"]
            k = m["k"]
            metric = m["metric"]

            domains = [domain_map[d] for d in dims]
            all_keys = list(itertools.product(*domains))

            dim_cols = ", ".join(dims)
            by_buyer = ", ".join(["payer_key"] + dims)
            dim_text = "concat_ws('|', " + ", ".join(f"{d}::text" for d in dims) + ")"

            # K-truncation SQL: each buyer is kept in at most K cells of this marginal
            sql = f"""
                WITH buyer_cells AS (
                    SELECT {by_buyer}, LEAST(SUM(amount), %s) AS spend
                    FROM transactions
                    WHERE brand_id = %s
                    GROUP BY {by_buyer}
                ),
                truncated AS (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY payer_key
                        ORDER BY md5(payer_key || {dim_text} || %s)
                    ) AS rn
                    FROM buyer_cells
                )
                SELECT {dim_cols}, COUNT(*) AS buyers, COALESCE(SUM(spend), 0) AS spend
                FROM truncated
                WHERE rn <= %s
                GROUP BY {dim_cols}
            """
            exact_map = {}
            for r in c.execute(sql, (SUM_CLAMP, brand, m_id, k)):
                key_tuple = tuple(r[d] for d in dims)
                exact_map[key_tuple] = (int(r["buyers"]), float(r["spend"]))

            true_counts = [exact_map.get(key, (0, 0.0))[0] for key in all_keys]
            true_sums = [exact_map.get(key, (0, 0.0))[1] for key in all_keys]

            if metric == "buyers":
                noisy_counts, sigma_b = _noisy_counts(true_counts, k, m["rho"])
                noisy_sums = [None] * len(all_keys)
                sigma_s = None
            elif metric == "both":
                noisy_counts, sigma_b = _noisy_counts(true_counts, k, m["rho_count"])
                noisy_sums, sigma_s = _noisy_sums(true_sums, k, m["rho_sum"])
            else:
                raise ValueError(metric)

            # Insert raw noisy cells unsuppressed
            for key, nb, ns in zip(all_keys, noisy_counts, noisy_sums):
                cell_dict = dict(zip(dims, key))
                marginals_data.append((
                    rel_id, m_id, Jsonb(cell_dict), float(nb), float(ns) if ns is not None else None,
                    float(sigma_b), float(sigma_s) if sigma_s is not None else None
                ))

        # Insert release record
        c.execute(
            """INSERT INTO private_releases (release_id, brand_id, rho_spent, eps_equivalent, created_at)
               VALUES (%s, %s, %s, %s, now())""",
            (rel_id, brand, RELEASE_RHO, RELEASE_EPS)
        )

        # Insert all marginal cells
        c.cursor().executemany(
            """INSERT INTO private_release_marginals
               (release_id, marginal_id, cell_key, noisy_buyers, noisy_spend, sigma_buyers, sigma_spend)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            marginals_data
        )

        # Update privacy ledger
        c.execute("INSERT INTO privacy_ledger (brand_id) VALUES (%s) ON CONFLICT DO NOTHING", (brand,))
        c.execute("UPDATE privacy_ledger SET rho_spent = rho_spent + %s WHERE brand_id = %s", (RELEASE_RHO, brand))

    return {
        "release_id": rel_id,
        "brand_id": brand,
        "rho_spent": RELEASE_RHO,
        "eps_equivalent": RELEASE_EPS,
        "cells_measured": len(marginals_data),
    }

