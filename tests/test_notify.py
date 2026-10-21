import time

from backend.common import notify


def test_case_events_post_without_buyer_data(env, monkeypatch):
    sent = []
    monkeypatch.setenv("NOTIFY_WEBHOOK_URL", "https://hooks.example.test/x")
    monkeypatch.setattr(notify, "_post", lambda url, payload: sent.append(payload))
    monkeypatch.setattr(notify.threading, "Thread",
                        lambda target, args, daemon: type("T", (), {"start": lambda self: target(*args)})())

    b = env["api"].post("/checkout/scan", json={"store_id": "store_b", "serial": "X123",
                                                "sku": "NMB-P8-128", "amount": 899}).json()
    from backend.worker.main import process_one
    process_one()

    events = [p["event"] for p in sent]
    assert events == ["case_opened", "case_completed"]
    assert all(p["case_id"] == b["case_id"] for p in sent)
    assert "payer" not in str(sent)


def test_no_url_means_no_alert(monkeypatch):
    monkeypatch.delenv("NOTIFY_WEBHOOK_URL", raising=False)
    called = []
    monkeypatch.setattr(notify, "_post", lambda *a: called.append(a))
    notify.case_event("case_opened", {"case_id": "c1"})
    time.sleep(0.05)
    assert called == []
