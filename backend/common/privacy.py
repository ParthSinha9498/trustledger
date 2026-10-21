"""Differential privacy for the PayPal-side node. See ../DP_RESEARCH.md for the reasoning and sources.

Privacy unit: one buyer (payer_key) across a whole query and across all of a brand's queries.
Accounting: zero-concentrated DP (zCDP). Per-query rho values add up exactly.
Mechanism: Gaussian via OpenDP (discrete Gaussian for counts, float Gaussian for clamped sums).

Contribution bounding (done in SQL by the node): each buyer is kept in at most K cells of a query
(a pseudo-random subset), and each buyer's spend per cell is clamped to SUM_CLAMP. So the L2
sensitivity is sqrt(K) for counts and SUM_CLAMP * sqrt(K) for sums.
"""
import math
import os

import opendp.prelude as dp

dp.enable_features("contrib")

K_DEFAULT = 4                 # max cells per buyer per query
FIXED_PER_BUYER_DIMS = {"age_band", "gender"}   # a buyer has one value, so K = 1 suffices
SUM_CLAMP = 1000.0            # max spend per buyer per cell (top product price is 999)
DELTA = 1e-8                  # only used to report an (eps, delta) equivalent
DISPLAY_FLOOR_MIN = 10        # suppress noisy counts below max(10, 2 sigma)

RHO_COUNT = 0.01              # one count query
RHO_SUM_COUNT = 0.005         # sum query: count part (shown, and used for suppression + mean)
RHO_SUM_SUM = 0.015           # sum query: sum part
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
