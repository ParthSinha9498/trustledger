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
