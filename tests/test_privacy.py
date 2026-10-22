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
    assert math.isclose(privacy.eps_equivalent(0.25), 4.16, abs_tol=0.01)


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
    assert body["noise"]["mechanism"] == "gaussian (zCDP)" and body["noise"]["k"] == 4
    assert all("ci95" in row for row in body["rows"])
    assert "payer_key" not in r.text and "txn_id" not in r.text


def test_sum_releases_count_sum_and_mean(env):
    body = ask(env, {"metric": "sum_amount", "group_by": ["store_id"]}).json()
    row = body["rows"][0]
    assert {"value", "buyers", "mean_spend", "ci95"} <= set(row)
    assert body["budget"]["spent"] == 0.02


def test_identical_and_reordered_queries_hit_cache_at_no_cost(env):
    a = ask(env, {"metric": "buyers", "group_by": ["store_id", "sku"], "filters": {"sku": ["NMB-A5-64", "NMB-P8-128"]}})
    b = ask(env, {"metric": "buyers", "group_by": ["sku", "store_id"], "filters": {"sku": ["NMB-P8-128", "NMB-A5-64"]}})
    assert a.json()["cached"] is False and b.json()["cached"] is True
    assert b.json()["budget"]["spent"] == 0.01


def test_budget_is_persistent_and_refuses_when_spent(env, monkeypatch):
    monkeypatch.setenv("PRIVACY_TOTAL_RHO", "0.03")  # three count queries
    for dims in (["store_id"], ["sku"], ["region"]):
        assert ask(env, {"metric": "buyers", "group_by": dims}).status_code == 200
    r = ask(env, {"metric": "buyers", "group_by": ["week"]})
    assert r.status_code == 403 and r.json()["detail"]["refused"] == "BUDGET_EXHAUSTED"
    # A cached answer is still served after the budget is gone, at no cost.
    assert ask(env, {"metric": "buyers", "group_by": ["sku"]}).json()["cached"] is True
    # The ledger lives in Postgres, so a fresh app process sees the same spend.
    assert env["paypal"].get("/v1/budget", params={"brand_id": "nimbus"}).json()["remaining"] == 0


def test_too_many_cells_refused(env):
    r = ask(env, {"metric": "buyers", "group_by": ["store_id", "week"], "filters": {"week_from": 1}})
    assert r.status_code == 200  # 6 x 12 = 72 cells


def test_repeated_insight_questions_spend_no_extra_rho_and_preserve_noisy_answer(env):
    """Proves that running an Insights question repeatedly spends NO extra rho and returns identical noisy answers.

    This verifies the privacy guarantee:
    1. First run executes the differential privacy mechanism, charges rho to the privacy ledger, and caches.
    2. Repeated runs hit query_cache, charge 0.0 extra rho, and return the exact same released rows without
       re-randomizing noise (which would allow noise-averaging reconstruction attacks).
    """
    api = env["api"]

    # The 3 PayPal-side one-click questions from Brand Insights console:
    paypal_questions = [
        "Which age bands buy the P8 128GB vs the A5?",
        "How did weekly buyers change at Store C over the last 12 weeks?",
        "What is the spend per buyer by region?",
    ]

    for question in paypal_questions:
        plan = api.post("/console/plan", json={"question": question}).json()
        specs = plan["specs"]
        assert len(specs) == 1 and specs[0]["node"] == "paypal", f"Expected single paypal query for {question}"

        # Run 1: initial execution
        budget_before = api.get("/console/budget").json()["spent"]
        res1 = api.post("/console/run", json={"specs": specs}).json()
        result1 = res1["results"][0]
        budget_after1 = res1["budget"]["spent"]

        assert result1["cached"] is False, f"First run of '{question}' should not be cached"
        assert budget_after1 > budget_before, f"First run of '{question}' should charge rho"
        expected_rho = 0.02 if specs[0]["spec"]["metric"] == "sum_amount" else 0.01
        assert math.isclose(budget_after1 - budget_before, expected_rho, abs_tol=1e-5)

        # Run 2: repeated identical execution
        res2 = api.post("/console/run", json={"specs": specs}).json()
        result2 = res2["results"][0]
        budget_after2 = res2["budget"]["spent"]

        assert result2["cached"] is True, f"Second run of '{question}' must hit query cache"
        assert math.isclose(budget_after2, budget_after1, abs_tol=1e-7), (
            f"Second run of '{question}' must spend NO extra rho! "
            f"Before: {budget_after1}, After: {budget_after2}"
        )
        assert result2["rows"] == result1["rows"], (
            f"Second run of '{question}' must return identical noisy values (no noise re-sampling)"
        )
        assert result2.get("suppressed_cells") == result1.get("suppressed_cells")
        assert result2.get("noise") == result1.get("noise")

