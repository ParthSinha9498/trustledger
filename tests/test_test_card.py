"""One-click sandbox test-card payment (POST /checkout/{id}/pay-test-card), offline in mock mode."""
import pytest

from backend.api.paypal_client import PayPalClient, CardPaymentUnavailable, paypal

SCAN = {"serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}


def test_refuses_unknown_checkout(env):
    assert env["api"].post("/checkout/chk_doesnotexist/pay-test-card").status_code == 404


def test_refuses_blocked_checkout_which_has_no_order(env):
    api = env["api"]
    orders_before = len(paypal._mock_orders)
    b = api.post("/checkout/scan", json=SCAN | {"store_id": "store_c"}).json()
    assert b["status"] == "NOT_VERIFIED" and b["paypal_order_id"] is None

    r = api.post(f"/checkout/{b['checkout_id']}/pay-test-card")
    assert r.status_code == 409
    assert len(paypal._mock_orders) == orders_before  # still no PayPal order anywhere
    assert api.get(f"/receipts/{b['checkout_id']}").json()["status"] == "BLOCKED"


def test_refuses_live_mode(env, monkeypatch):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    monkeypatch.setattr(paypal, "mode", "live")
    r = api.post(f"/checkout/{a['checkout_id']}/pay-test-card")
    assert r.status_code == 403
    monkeypatch.setattr(paypal, "mode", "mock")
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "AWAITING_PAYMENT"


def test_client_refuses_live_mode_too(monkeypatch):
    monkeypatch.setenv("PAYPAL_MODE", "live")
    with pytest.raises(CardPaymentUnavailable):
        PayPalClient().pay_with_test_card("ORDER1")


def test_pays_a_verified_checkout_and_receipt_shows_the_verification_id(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN | {"store_id": "store_a"}).json()
    assert a["status"] == "VERIFIED"

    r = api.post(f"/checkout/{a['checkout_id']}/pay-test-card")
    assert r.status_code == 200
    rec = r.json()
    assert rec["status"] == "CAPTURED" and rec["brand_verified"] is True
    assert rec["verification_id"] == a["verification_id"]
    assert rec["paypal_order_id"] == a["paypal_order_id"]
    order = paypal._mock_orders[a["paypal_order_id"]]
    assert order["status"] == "COMPLETED"
    assert order["body"]["purchase_units"][0]["custom_id"] == a["verification_id"]

    # Paid once: a second click is refused rather than paying again.
    assert api.post(f"/checkout/{a['checkout_id']}/pay-test-card").status_code == 409
