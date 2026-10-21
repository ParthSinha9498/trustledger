"""Feature coverage for endpoints and guarantees not exercised elsewhere (mock PayPal + mock LLM)."""
import json

from fastapi.testclient import TestClient

from backend import db
from backend.api.main import app as api_app
from backend.api.paypal_client import paypal
from backend.worker import main as worker
from backend.worker.mock_llm import ScriptedLLM

SCAN = {"serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}
BUYER_FIELDS = ("payer_key", "payer_ref", "txn_id", "email")


def test_health_and_stores(env):
    api = env["api"]
    assert api.get("/health").json() == {"ok": True, "paypal_mode": "mock"}
    ids = [s["store_id"] for s in api.get("/stores").json()]
    assert {"store_a", "store_b"} <= set(ids)


def test_receipt_only_brand_verified_after_capture(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    assert api.get(f"/receipts/{a['checkout_id']}").json()["brand_verified"] is False  # not paid yet
    api.post(f"/checkout/{a['checkout_id']}/capture")
    r = api.get(f"/receipts/{a['checkout_id']}").json()
    assert r["brand_verified"] is True and r["verification_id"] == a["verification_id"]
    assert r["product"] == "Nimbus P8 128GB" and r["store_name"]
    assert api.get("/receipts/chk_does_not_exist").status_code == 404


def test_blocked_checkout_can_never_be_paid(env):
    api = env["api"]
    orders_before = len(paypal._mock_orders)
    b = api.post("/checkout/scan", json=SCAN | {"store_id": "store_b"}).json()
    assert b["status"] == "NOT_VERIFIED"
    r = api.post(f"/checkout/{b['checkout_id']}/capture")
    assert 400 <= r.status_code < 500
    assert api.get(f"/receipts/{b['checkout_id']}").json()["brand_verified"] is False
    assert len(paypal._mock_orders) == orders_before


def test_worker_endpoints_need_node_token(env):
    bare = TestClient(api_app)  # no X-Node-Token
    assert bare.post("/internal/cases/claim").status_code == 401
    assert bare.post("/internal/cases/c1/steps", json={}).status_code == 401
    assert bare.post("/internal/cases/c1/finish", json={}).status_code == 401
    wrong = TestClient(api_app, headers={"X-Node-Token": "nope"})
    assert wrong.post("/internal/cases/claim").status_code == 401


def test_webhook_with_bad_signature_is_rejected(env, monkeypatch):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    monkeypatch.setattr(paypal, "verify_webhook", lambda headers, event: False)
    hook = {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": a["paypal_order_id"]}}
    assert api.post("/paypal/webhooks", json=hook).status_code == 400
    with db.connect("platform") as pc:
        status = pc.execute("SELECT status FROM checkouts WHERE checkout_id=%s", (a["checkout_id"],)).fetchone()
    assert status["status"] == "AWAITING_PAYMENT"  # forged event changed nothing


def test_capture_completed_webhook_marks_paid(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    hook = {"event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"id": "CAP-1", "supplementary_data": {"related_ids": {"order_id": a["paypal_order_id"]}}}}
    assert api.post("/paypal/webhooks", json=hook).json()["updated"] == 1
    assert api.get(f"/receipts/{a['checkout_id']}").json()["brand_verified"] is True


def _ingest(env, ref="PAYER-SECRET-42"):
    return env["paypal"].post("/v1/ingest", json={
        "order_id": "ORD-1", "brand_id": "nimbus", "store_id": "store_a", "sku": "NMB-P8-128",
        "amount": 899.0, "payer_ref": ref, "age_band": "25-34", "gender": "f"})


def test_ingest_invalidates_cache_and_hashes_payer(env):
    q = {"brand_id": "nimbus", "spec": {"metric": "buyers", "group_by": ["store_id"]}}
    first = env["paypal"].post("/v1/query", json=q).json()
    assert env["paypal"].post("/v1/query", json=q).json()["cached"] is True
    assert _ingest(env).json() == {"ok": True}
    again = env["paypal"].post("/v1/query", json=q).json()
    assert again["cached"] is False  # new data: recomputed and charged again
    assert again["budget"]["spent"] > first["budget"]["spent"]
    with db.connect("paypal_side") as c:
        dump = json.dumps(c.execute("SELECT * FROM transactions WHERE order_id='ORD-1'").fetchall(), default=str)
    assert "ORD-1" in dump and "PAYER-SECRET-42" not in dump  # payer id stored only as a hash


def test_ingest_needs_node_token(env):
    from backend.paypal_node.main import app as paypal_app
    r = TestClient(paypal_app).post("/v1/ingest", json={})
    assert r.status_code == 401


def test_agent_never_sends_buyer_fields_to_llm(env, monkeypatch):
    sent: list[str] = []

    class SpyLLM(ScriptedLLM):
        def next_turn(self, messages, tools):
            sent.append(json.dumps(messages, default=str))
            return super().next_turn(messages, tools)

    monkeypatch.setattr(worker, "get_llm", SpyLLM)
    _ingest(env)  # a real payer id exists in the PayPal node
    b = env["api"].post("/checkout/scan", json=SCAN | {"store_id": "store_b"}).json()
    assert worker.process_one() is True
    assert env["api"].get(f"/cases/{b['case_id']}").json()["status"] == "complete"
    prompts = "\n".join(sent)
    assert sent and "PAYER-SECRET-42" not in prompts
    assert not [f for f in BUYER_FIELDS if f'"{f}"' in prompts]
