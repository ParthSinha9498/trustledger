import math

from backend.common import privacy

Q = "/v1/query"


def ask(env, spec):
    return env["paypal"].post(Q, json={"brand_id": "nimbus", "spec": spec})


def test_sensitivity_and_cost_match_opendp():
    # k=4 count: sigma = sqrt(4) / sqrt(2 * 0.01) = 14.14; k=1: 7.07
    out = privacy.release([("a",)], [500], [0.0], "buyers", k=4)
    assert math.isclose(out["noise"]["sigma"], 14.14, abs_tol=0.01)
    out1 = privacy.release([("a",)], [500], [0.0], "buyers", k=1)
    assert math.isclose(out1["noise"]["sigma"], 7.07, abs_tol=0.01)
    assert privacy.k_for(["age_band", "gender"]) == 1 and privacy.k_for(["store_id", "week"]) == 4
    # Epsilon at delta=1e-8 for rho=0.20 via OpenDP is 3.69
    assert math.isclose(privacy.eps_equivalent(0.20), 3.69, abs_tol=0.01)


def test_small_cells_suppressed_with_noise_scaled_floor():
    # Noise is random, so check rates: a 2-buyer cell is almost always hidden, a 500-buyer cell never.
    hidden_tiny = shown_big = 0
    for _ in range(200):
        out = privacy.release([("big",), ("tiny",)], [500, 2], [0.0, 0.0], "buyers", k=4)
        keys = [r["key"] for r in out["rows"]]
        hidden_tiny += ("tiny",) not in keys
        shown_big += ("big",) in keys
    assert shown_big == 200 and hidden_tiny >= 180  # P(2 + N(0, 14.1) >= 28.3) is about 3%
    assert out["noise"]["display_floor"] >= 28  # max(10, 2 * 14.14)


def test_response_reports_noise_and_never_buyer_fields(env):
    r = ask(env, {"metric": "buyers", "group_by": ["store_id", "week"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["noise"]["mechanism"] == "zCDP private release"
    assert body["noise"]["private_release"] is True
    assert all("ci95" in row for row in body["rows"])
    assert "payer_key" not in r.text and "txn_id" not in r.text


def test_sum_releases_count_sum_and_mean(env):
    body = ask(env, {"metric": "sum_amount", "group_by": ["store_id"]}).json()
    row = body["rows"][0]
    assert {"value", "buyers", "mean_spend", "ci95", "ci95_mean_spend"} <= set(row)
    assert body["noise"]["private_release"] is True


def test_private_release_queries_spend_zero_extra_rho(env):
    """Proves that asking 100 questions from the private release spends 0 extra rho."""
    initial_budget = env["paypal"].get("/v1/budget", params={"brand_id": "nimbus"}).json()
    initial_spent = initial_budget["spent"]
    assert initial_spent == 0.20  # release measured once at seed

    specs = [
        {"metric": "buyers", "group_by": ["store_id"]},
        {"metric": "buyers", "group_by": ["sku"]},
        {"metric": "buyers", "group_by": ["age_band", "sku"]},
        {"metric": "buyers", "group_by": ["store_id", "week"]},
        {"metric": "sum_amount", "group_by": ["store_id"]},
    ]

    for i in range(100):
        spec = specs[i % len(specs)]
        res = ask(env, spec)
        assert res.status_code == 200

    final_budget = env["paypal"].get("/v1/budget", params={"brand_id": "nimbus"}).json()
    assert final_budget["spent"] == initial_spent
    assert final_budget["private_release"] is True


def test_uncovered_spec_refused(env):
    """Router rule: refuse (never silently drop) any filter or spec the release cannot apply."""
    # Week filter on demographic marginal (M2/M3 don't have week)
    r = ask(env, {
        "metric": "buyers",
        "group_by": ["age_band", "gender"],
        "filters": {"week_from": 30, "week_to": 35}
    })
    assert r.status_code == 403
    assert r.json()["detail"]["refused"] == "NOT_IN_RELEASE"


def test_release_status_endpoint(env):
    r = env["paypal"].get("/v1/release/status", params={"brand_id": "nimbus"})
    assert r.status_code == 200
    b = r.json()
    assert b["brand_id"] == "nimbus"
    assert b["rho_spent"] == 0.20
    assert b["eps_equivalent"] == 3.69
    assert b["marginal_count"] == 6
    assert b["private_release"] is True


def test_repeated_query_returns_identical_rows(env):
    """Same spec -> identical rows byte for byte."""
    spec = {"metric": "buyers", "group_by": ["store_id"]}
    r1 = ask(env, spec).json()
    r2 = ask(env, spec).json()
    assert r1["rows"] == r2["rows"]
    assert r1["noise"] == r2["noise"]


def test_second_build_release_refused(env):
    """A second build_release is refused because 0.20 + 0.20 > 0.25 total budget."""
    import pytest
    with pytest.raises(ValueError, match="Insufficient privacy budget"):
        privacy.build_release("nimbus")


def test_router_refuses_uncovered_filters(env):
    """age_band/gender filter on M1 (which has week) returns NOT_IN_RELEASE, not empty suppressed answer."""
    r = ask(env, {
        "metric": "buyers",
        "group_by": ["store_id", "week"],
        "filters": {"age_band": ["18-24"]}
    })
    assert r.status_code == 403
    assert r.json()["detail"]["refused"] == "NOT_IN_RELEASE"

    r2 = ask(env, {
        "metric": "buyers",
        "group_by": ["store_id", "week"],
        "filters": {"gender": ["female"]}
    })
    assert r2.status_code == 403
    assert r2.json()["detail"]["refused"] == "NOT_IN_RELEASE"


def test_mean_spend_has_delta_method_ci(env):
    """mean_spend row must contain ci95_mean_spend from delta method."""
    r = ask(env, {"metric": "sum_amount", "group_by": ["store_id"]})
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) > 0
    for row in rows:
        assert "mean_spend" in row
        assert "ci95_mean_spend" in row
        assert row["ci95_mean_spend"] >= 0.0


def test_k_truncation_bounds_buyer_contribution(env, monkeypatch):
    """Verify that build_release bounds single buyer contribution to at most K cells in stored marginals."""
    from backend import db
    brand = "k_trunc_test_brand"
    payer = "k_trunc_test_payer"

    # Mock noise to zero to inspect exact stored cell counts directly
    monkeypatch.setattr(privacy, "_noisy_counts", lambda counts, k, rho: ([float(c) for c in counts], 1.0))
    monkeypatch.setattr(privacy, "_noisy_sums", lambda sums, k, rho: ([float(s) for s in sums], 1.0))

    with db.connect("paypal_side") as c:
        c.execute("INSERT INTO catalog_stores VALUES ('kt_store', %s, 'US-WEST', 'Seattle') ON CONFLICT DO NOTHING", (brand,))
        c.execute("INSERT INTO catalog_skus VALUES ('kt_sku', %s) ON CONFLICT DO NOTHING", (brand,))
        # Insert a single buyer into 10 distinct week cells (weeks 1 to 10)
        for w in range(1, 11):
            c.execute(
                "INSERT INTO transactions VALUES (%s, %s, %s, 'kt_store', 'kt_sku', 50, 'US-WEST', 'Seattle', %s, %s, '35-44', 'female', 'simulated')",
                (f"KT_TX_{w}", f"KT_ORD_{w}", brand, w, payer)
            )

    # Build release through the real production pipeline
    rel = privacy.build_release(brand)
    rel_id = rel["release_id"] if isinstance(rel, dict) else rel

    # Assert on the cells build_release actually stored in private_release_marginals
    with db.connect("paypal_side") as c:
        # Marginal M1 has dims (store_id, sku, week) and K=4
        rows_m1 = c.execute(
            "SELECT cell_key, noisy_buyers, noisy_spend FROM private_release_marginals WHERE release_id = %s AND marginal_id = 'M1'",
            (rel_id,)
        ).fetchall()

    # The buyer was active in 10 cells, but stored contribution must be capped at K=4 cells
    active_cells = [r for r in rows_m1 if r["noisy_buyers"] > 0]
    assert len(active_cells) == 4
    assert sum(r["noisy_buyers"] for r in active_cells) == 4.0
    assert all(r["noisy_buyers"] <= 1.0 for r in active_cells)




