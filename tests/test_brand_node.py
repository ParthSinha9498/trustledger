from backend import db

def verify(env, serial, store, sku="NMB-P8-128"):
    return env["brand"].post("/v1/verify", json={"serial": serial, "sku": sku, "store_id": store}).json()


def test_demo_serial_verifies_at_store_a(env):
    assert verify(env, "X123", "store_a")["result"] == "VERIFIED"


def test_demo_serial_fails_at_store_b(env):
    v = verify(env, "X123", "store_b")
    assert v["result"] == "NOT_VERIFIED" and v["reason_code"] == "NOT_IN_CHANNEL"


def test_unknown_and_already_sold(env):
    assert verify(env, "NOPE", "store_a")["reason_code"] == "UNKNOWN_SERIAL"
    v = verify(env, "X123", "store_a")
    env["brand"].post(f"/v1/verify/{v['verification_id']}/confirm", json={"paypal_order_id": "MOCK-1"})
    assert verify(env, "X123", "store_a")["reason_code"] == "ALREADY_SOLD"


def test_brand_query_is_aggregate_only(env):
    r = env["brand"].post("/v1/query", json={"brand_id": "nimbus",
                                             "spec": {"metric": "sold_units", "group_by": ["store_id", "distributor_id"]}})
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert all(set(row) == {"store_id", "distributor_id", "value"} for row in rows)
    # Planted diversion: dist_1 stock sold at store_c.
    assert any(row["store_id"] == "store_c" and row["distributor_id"] == "dist_1" for row in rows)


def test_demo_stock_is_prefixed_and_verifies(env):
    a = env["api"].get("/demo/serial", params={"store_id": "store_a"}).json()
    b = env["api"].get("/demo/serial", params={"store_id": "store_b"}).json()
    assert a["serial"].startswith("XA") and len(a["serial"]) == 8
    assert b["serial"].startswith("XB")
    assert verify(env, a["serial"], "store_a", a["sku"])["result"] == "VERIFIED"
    assert verify(env, b["serial"], "store_b", b["sku"])["result"] == "VERIFIED"
    # Store A stock at Store B is blocked.
    assert verify(env, a["serial"], "store_b", a["sku"])["reason_code"] == "NOT_IN_CHANNEL"


def test_demo_serial_never_hands_out_sold_stock(env):
    s = env["api"].get("/demo/serial", params={"store_id": "store_a"}).json()
    v = verify(env, s["serial"], "store_a", s["sku"])
    env["brand"].post(f"/v1/verify/{v['verification_id']}/confirm", json={"paypal_order_id": "MOCK-2"})
    assert verify(env, s["serial"], "store_a", s["sku"])["reason_code"] == "ALREADY_SOLD"
    for _ in range(20):
        assert env["api"].get("/demo/serial", params={"store_id": "store_a"}).json()["serial"] != s["serial"]


def test_demo_serial_off_and_unknown_store(env, monkeypatch):
    assert env["api"].get("/demo/serial", params={"store_id": "store_c"}).status_code == 404
    monkeypatch.setenv("DEMO_MODE", "0")
    assert env["api"].get("/demo/serial", params={"store_id": "store_a"}).status_code == 404


def test_demo_rename_keeps_aggregates(env):
    with db.connect("brand") as c:
        assert c.execute("SELECT count(*) AS n FROM serials WHERE serial LIKE 'X_0%' AND sold_store_id IS NOT NULL"
                         ).fetchone()["n"] == 0
        assert c.execute("SELECT count(*) AS n FROM serials WHERE serial = 'X123'").fetchone()["n"] == 1
