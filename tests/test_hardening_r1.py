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


def test_transport_error_on_capture_keeps_the_claim_until_paypal_is_asked(env, monkeypatch):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    real_capture = paypal.capture_order

    def boom(order_id):
        raise ConnectionError("timeout")

    monkeypatch.setattr(paypal, "capture_order", boom)
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 502
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "CAPTURING"  # outcome unknown
    monkeypatch.setattr(paypal, "capture_order", real_capture)
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 409  # still in flight
    _set_checkout(a["checkout_id"], claimed_at=_ago(5))  # the claim goes stale; reconcile asks PayPal
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "CREATED"  # PayPal never captured it
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 200


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


def _ago(minutes):
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def _set_checkout(checkout_id, **cols):
    from backend import db
    sets = ", ".join(f"{k}=%s" for k in cols)
    with db.connect("platform") as pc:
        pc.execute(f"UPDATE checkouts SET {sets} WHERE checkout_id=%s", (*cols.values(), checkout_id))


def test_a_stale_open_order_is_expired_when_the_unit_is_rescanned(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    _set_checkout(a["checkout_id"], created_at=_ago(31))  # abandoned hold ages out
    b = api.post("/checkout/scan", json=SCAN).json()
    assert b["status"] == "VERIFIED"
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "EXPIRED"
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 409  # the old order can't be paid
    assert api.post(f"/checkout/{b['checkout_id']}/pay-test-card").status_code == 200


def test_a_reserving_checkout_holds_the_unit_so_a_concurrent_scan_is_refused(env):
    api = env["api"]
    from backend import db
    with db.connect("platform") as pc:
        pc.execute("INSERT INTO checkouts (checkout_id, store_id, serial, sku, amount, verification_id, status) "
                   "VALUES ('chk_inflight','store_a','X123','NMB-P8-128',899,'ver_x','RESERVING')")
    r = api.post("/checkout/scan", json=SCAN).json()
    assert r["status"] == "NOT_VERIFIED" and r["reason_code"] == "IN_PROGRESS"


def test_release_frees_the_unit_and_stops_the_old_order(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    assert api.post(f"/checkout/{a['checkout_id']}/release").status_code == 200
    b = api.post("/checkout/scan", json=SCAN).json()
    assert b["status"] == "VERIFIED"
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 409


def test_a_stuck_capture_is_reconciled_with_paypal(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    _set_checkout(a["checkout_id"], status="CAPTURING", claimed_at=_ago(5))
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "CREATED"  # PayPal never captured it
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 200  # released, then paid
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "CAPTURED"


def test_a_stuck_capture_that_paypal_completed_is_recorded_not_recaptured(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    _set_checkout(a["checkout_id"], status="CAPTURING", claimed_at=_ago(5))
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "COMPLETED"
    api.post(f"/checkout/{a['checkout_id']}/capture")
    rec = api.get(f"/receipts/{a['checkout_id']}").json()
    assert rec["status"] == "CAPTURED" and rec["brand_verified"] is True


def test_brand_refusal_on_a_webhook_is_recorded_as_review_not_redelivered(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    # Someone else's order already confirmed this unit with the brand.
    env["brand"].post(f"/v1/verify/{a['verification_id']}/confirm", json={"paypal_order_id": "OTHER-ORDER"})
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "COMPLETED"
    event = {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "CAP-9",
             "supplementary_data": {"related_ids": {"order_id": a["paypal_order_id"]}}}}
    r = api.post("/paypal/webhooks", json=event)
    assert r.status_code == 200 and r.json()["updated"] == 0  # no retry loop
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "REVIEW"


def test_an_unknown_capture_outcome_keeps_the_claim_and_is_not_repaid(env, monkeypatch):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()

    def boom(order_id):
        raise ConnectionError("timeout")

    monkeypatch.setattr(paypal, "capture_order", boom)
    assert api.post(f"/checkout/{a['checkout_id']}/capture").status_code == 502
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "CAPTURING"  # claim kept
    assert api.post("/paypal/webhooks", json={"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"id": "C",
        "supplementary_data": {"related_ids": {"order_id": a["paypal_order_id"]}}}}).status_code == 503  # redeliver
    assert api.post(f"/checkout/{a['checkout_id']}/release").status_code == 409  # can't release a capture in flight


def test_a_stale_capture_is_settled_before_a_rescan_is_judged(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    _set_checkout(a["checkout_id"], status="CAPTURING", claimed_at=_ago(5))
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "CREATED"  # PayPal says not captured
    b = api.post("/checkout/scan", json=SCAN).json()
    # The released order was created moments ago, so it still holds the unit: refused, not double-held.
    assert b["status"] == "NOT_VERIFIED" and b["reason_code"] == "IN_PROGRESS"
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "AWAITING_PAYMENT"


def test_a_recorded_but_unfinished_sale_is_finished_by_the_test_card_retry(env):
    api = env["api"]
    a = api.post("/checkout/scan", json=SCAN).json()
    from backend import db
    # PayPal captured, but the brand confirm failed afterwards: the sale is recorded as PAID_UNRECORDED.
    with db.connect("platform") as pc:
        pc.execute("UPDATE checkouts SET status='PAID_UNRECORDED' WHERE checkout_id=%s", (a["checkout_id"],))
    paypal._mock_orders[a["paypal_order_id"]]["status"] = "COMPLETED"
    assert api.post(f"/checkout/{a['checkout_id']}/pay-test-card").status_code == 200
    assert api.get(f"/receipts/{a['checkout_id']}").json()["status"] == "CAPTURED"
