"""End to end in mock mode: Store A pays, Store C is blocked and investigated."""
from backend.api.paypal_client import paypal
from backend.worker.main import process_one

SCAN = {"serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}


def test_store_a_pays_store_c_blocked_and_investigated(env):
    api = env["api"]
    orders_before = len(paypal._mock_orders)

    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    assert a["status"] == "VERIFIED" and a["paypal_order_id"]
    assert paypal._mock_orders[a["paypal_order_id"]]["body"]["purchase_units"][0]["custom_id"] == a["verification_id"]
    receipt = api.post(f"/checkout/{a['checkout_id']}/capture").json()
    assert receipt["brand_verified"] is True

    b = api.post("/checkout/scan", json=SCAN | {"store_id": "store_c"}).json()
    assert b["status"] == "NOT_VERIFIED" and b["paypal_order_id"] is None and b["case_id"]
    assert b["reason_code"] == "NOT_IN_CHANNEL"
    # Exactly one PayPal order was created: Store C's payment never exists.
    assert len(paypal._mock_orders) == orders_before + 1

    assert process_one() is True
    case = api.get(f"/cases/{b['case_id']}").json()
    assert case["status"] == "complete"
    kinds = [s["kind"] for s in case["steps"]]
    assert "tool_result" in kinds and "finding" in kinds


def test_webhook_approved_then_capture(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    hook = {"event_type": "CHECKOUT.ORDER.APPROVED", "resource": {"id": a["paypal_order_id"]}}
    assert api.post("/paypal/webhooks", json=hook).json()["updated"] == 1
    assert api.post(f"/checkout/{a['checkout_id']}/capture").json()["brand_verified"] is True
