"""Checkout hardening (round 1): server-side price, one unit one order, claimed capture, webhook settles once."""
from backend.api.paypal_client import paypal

SCAN = {"serial": "X123", "sku": "NMB-P8-128", "store_id": "store_a"}


def test_client_amount_is_ignored(env):
    api = env["api"]
    r = api.post("/checkout/scan", json=SCAN | {"amount": 0.01})
    assert r.status_code == 200 and r.json()["status"] == "VERIFIED"
    order = paypal._mock_orders[r.json()["paypal_order_id"]]
    assert order["body"]["purchase_units"][0]["amount"]["value"] == "899.00"


def test_unknown_sku_is_refused(env):
    r = env["api"].post("/checkout/scan", json=SCAN | {"sku": "NOPE"})
    assert r.status_code == 422


def test_second_scan_of_a_held_unit_is_refused_before_any_order(env):
    api = env["api"]
    first = api.post("/checkout/scan", json=SCAN).json()
    orders = len(paypal._mock_orders)
    second = api.post("/checkout/scan", json=SCAN).json()
    assert first["status"] == "VERIFIED"
    assert second["status"] == "NOT_VERIFIED" and second["reason_code"] == "IN_PROGRESS"
    assert second["paypal_order_id"] is None
    assert len(paypal._mock_orders) == orders  # no second PayPal order


def test_brand_confirm_refuses_a_second_order_for_a_sold_unit(env):
    brand = env["brand"]
    v = env["api"].post("/checkout/scan", json=SCAN).json()
    vid = v["verification_id"]
    assert brand.post(f"/v1/verify/{vid}/confirm", json={"paypal_order_id": "ORDER-1"}).status_code == 200
    assert brand.post(f"/v1/verify/{vid}/confirm", json={"paypal_order_id": "ORDER-1"}).status_code == 200  # retry
    assert brand.post(f"/v1/verify/{vid}/confirm", json={"paypal_order_id": "ORDER-2"}).status_code == 409


def test_a_paid_checkout_cannot_be_captured_again(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    assert api.post(f"/checkout/{a['checkout_id']}/pay-test-card").status_code == 200
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 409


def test_transport_error_on_capture_releases_the_claim(env, monkeypatch):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    real_capture = paypal.capture_order

    def boom(order_id):
        raise ConnectionError("timeout")

    monkeypatch.setattr(paypal, "capture_order", boom)
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 502
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "AWAITING_PAYMENT"
    monkeypatch.setattr(paypal, "capture_order", real_capture)  # restore only this method
    r = api.post(f"/checkout/{a['checkout_id']}/capture")
    assert r.status_code == 200, r.text


def test_capture_webhook_records_the_sale_once(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    oid = a["paypal_order_id"]
    paypal._mock_orders[oid]["status"] = "COMPLETED"  # PayPal's order status after capture
    event = {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "CAP-1",
             "supplementary_data": {"related_ids": {"order_id": oid}}}}
    assert api.post("/paypal/webhooks", json=event).json()["updated"] == 1
    rec = api.get(f"/receipts/{a['checkout_id']}").json()
    assert rec["status"] == "CAPTURED" and rec["brand_verified"] is True
    assert api.post("/paypal/webhooks", json=event).json()["updated"] == 0  # replay is a no-op


def test_webhook_does_not_mark_captured_unless_paypal_says_so(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    event = {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "CAP-2",
             "supplementary_data": {"related_ids": {"order_id": a["paypal_order_id"]}}}}
    assert api.post("/paypal/webhooks", json=event).json()["updated"] == 0
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "AWAITING_PAYMENT"
