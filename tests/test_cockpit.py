"""Cockpit overview: failed authenticity checks by reason/store over time, via the brand node's aggregate API."""


def test_blocked_counts_seeded_clone_attempts(env):
    d = env["api"].get("/cockpit/blocked", params={"weeks": 8}).json()
    assert d["exact"] is True and d["current_week"] == 42
    assert d["weeks"] == list(range(35, 43))
    # Seed: 40 clone attempts at store_b in weeks 39..42 (ALREADY_SOLD or NOT_IN_CHANNEL).
    assert d["total"] == 40
    assert sum(r["value"] for r in d["by_store"]) == 40
    assert {r["store_id"] for r in d["by_store"]} == {"store_b"}
    assert {r["reason_code"] for r in d["by_reason"]} == {"ALREADY_SOLD", "NOT_IN_CHANNEL"}
    assert all(39 <= r["week"] <= 42 for r in d["by_reason"])
    assert d["store_names"]["store_b"] == "Store B"


def test_blocked_includes_live_blocks_and_no_serials(env):
    r = env["api"].post("/checkout/scan", json={"store_id": "store_a", "serial": "FAKE-1", "sku": "NMB-P8-128",
                                                 "amount": 799}).json()
    assert r["status"] == "NOT_VERIFIED"
    d = env["api"].get("/cockpit/blocked").json()
    assert d["total"] == 41
    assert any(x["store_id"] == "store_a" and x["week"] == 42 and x["value"] == 1 for x in d["by_store"])
    assert any(x["reason_code"] == "UNKNOWN_SERIAL" for x in d["by_reason"])
    text = str(d)
    assert "FAKE-1" not in text and "NMB1" not in text and "ver_" not in text


def test_blocked_window_bounds(env):
    assert env["api"].get("/cockpit/blocked", params={"weeks": 0}).status_code == 422
    assert env["api"].get("/cockpit/blocked", params={"weeks": 27}).status_code == 422
    d = env["api"].get("/cockpit/blocked", params={"weeks": 2}).json()
    assert d["weeks"] == [41, 42]
    assert all(r["week"] in (41, 42) for r in d["by_reason"] + d["by_store"])


def test_insights_autorun_question_is_a_stored_sample():
    """The Insights page auto-runs its first example on load. It is free only because sample questions use the
    stored plan (no model call) and that plan is brand-side (no privacy budget). Pin both."""
    import re
    from pathlib import Path

    from backend.api.console import SAMPLE_QUESTIONS, mock_plan

    src = (Path(__file__).resolve().parents[1] / "web/app/cockpit/console/page.tsx").read_text()
    block = re.search(r"const EXAMPLES = \[(.*?)\];", src, re.S).group(1)
    first = re.search(r'"([^"]+)"', block).group(1)
    assert first == SAMPLE_QUESTIONS[0]["question"]
    specs, _ = mock_plan(first)
    assert specs and all(s["node"] == "brand" for s in specs)
