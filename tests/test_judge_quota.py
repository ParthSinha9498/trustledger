"""Judge password gate, per-IP question limits, daily case cap. Offline (mock PayPal, mock LLM)."""
import pytest

SCAN = {"serial": "FAKE-JUDGE", "sku": "NMB-P8-128", "amount": 899.0}
PLAN = {"question": "How many units sold this week?"}


@pytest.fixture()
def judged(env, monkeypatch):
    monkeypatch.setenv("JUDGE_PASSWORD", "let-me-in")
    return env["api"]


def test_missing_key_is_401(judged):
    r = judged.get("/stores")
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == {"code": "judge_key_required", "message": "Enter the judge password"}
    assert body["code"] == "judge_key_required" and body["detail"]["code"] == "judge_key_required"


def test_wrong_key_is_401(judged):
    assert judged.get("/stores", headers={"X-Judge-Key": "nope"}).status_code == 401


def test_correct_key_passes(judged):
    assert judged.get("/stores", headers={"X-Judge-Key": "let-me-in"}).status_code == 200


def test_exempt_paths_and_preflight(judged):
    assert judged.get("/health").status_code == 200
    assert judged.get("/openapi.json").status_code == 200
    # Webhook is signed by PayPal, so it is reached without the judge key (it then fails its own signature check).
    assert judged.post("/paypal/webhooks", json={}).status_code != 401
    assert judged.options("/stores", headers={"Origin": "http://localhost:3000",
                                              "Access-Control-Request-Method": "GET"}).status_code != 401


def test_no_password_means_no_gate(env, monkeypatch):
    monkeypatch.setenv("JUDGE_PASSWORD", "")
    assert env["api"].get("/stores").status_code == 200


def test_plan_limit_is_5_per_minute(env, monkeypatch):
    monkeypatch.setenv("JUDGE_PASSWORD", "let-me-in")
    key = {"X-Judge-Key": "let-me-in"}
    api = env["api"]
    for _ in range(5):
        assert api.post("/console/plan", json=PLAN, headers=key).status_code == 200
    r = api.post("/console/plan", json=PLAN, headers=key)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"


def test_daily_case_cap(env, monkeypatch):
    monkeypatch.setenv("MAX_CASES_PER_DAY", "2")
    api = env["api"]
    ids = [api.post("/checkout/scan", json=SCAN | {"store_id": s}).json() for s in ("store_a", "store_b", "store_c")]
    assert all(r["status"] == "NOT_VERIFIED" for r in ids)
    assert ids[0]["case_id"] and ids[1]["case_id"]
    assert ids[2]["case_id"] is None
