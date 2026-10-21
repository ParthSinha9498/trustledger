"""Brand supply chain view (Bryntum Scheduler data): brand node endpoint and api proxy."""


def get(env, **params):
    return env["brand"].get("/v1/supply-chain", params={"brand_id": "nimbus", **params})


def test_requires_node_token(env):
    from fastapi.testclient import TestClient
    from backend.brand_node.main import app

    assert TestClient(app).get("/v1/supply-chain").status_code == 401


def test_wrong_brand_refused(env):
    r = env["brand"].get("/v1/supply-chain", params={"brand_id": "other"})
    assert r.status_code == 403


def test_shape_resources_events_dependencies(env):
    r = get(env)
    assert r.status_code == 200
    d = r.json()
    tiers = [res["tier"] for res in d["resources"]]
    assert tiers[0] == "brand" and "distributor" in tiers and "store" in tiers
    # Brand first, then distributors, then stores.
    assert tiers == sorted(tiers, key=["brand", "distributor", "store"].index)
    assert all(res["region"] for res in d["resources"] if res["tier"] == "store")

    ids = {e["id"] for e in d["events"]}
    res_ids = {res["id"] for res in d["resources"]}
    assert all(e["resource_id"] in res_ids for e in d["events"])
    assert all(dep["from"] in ids and dep["to"] in ids for dep in d["dependencies"])
    assert all(e["end_week"] > e["start_week"] for e in d["events"])
    # Seed small: 12 batches, each dispatch -> distributor -> store.
    assert d["totals"]["batches"] == 12
    kinds = [e["kind"] for e in d["events"]]
    assert kinds.count("dispatch") == kinds.count("distributor") == 12


def test_aggregates_only_no_serials(env):
    d = get(env).json()
    text = str(d)
    assert "X123" not in text and "NMB1" not in text
    allowed = {"id", "resource_id", "batch_id", "sku", "kind", "name", "start_week", "end_week",
               "units", "sold", "highlight"}
    assert all(set(e) <= allowed for e in d["events"])


def test_planted_diversion_highlighted(env):
    d = get(env).json()
    off = [e for e in d["events"] if e["highlight"]]
    assert off, "seed plants Distributor 1 stock sold at Store C"
    assert all(e["kind"] == "off_channel" for e in off)
    assert any(e["resource_id"] == "store_c" for e in off)
    for o in d["off_channel"]:
        assert o["distributor_id"] == "dist_1"
        assert o["sold_store_id"] == "store_c"
        assert "store_c" not in o["channel_store_ids"]
    assert d["totals"]["off_channel_units"] == sum(o["units"] for o in d["off_channel"]) > 0
    # Off-channel bars hang off the distributor bar (earliest observed point of divergence).
    by_id = {e["id"]: e for e in d["events"]}
    hl_deps = [dep for dep in d["dependencies"] if dep.get("highlight")]
    assert hl_deps and all(by_id[dep["from"]]["kind"] == "distributor" for dep in hl_deps)


def test_in_channel_sales_not_highlighted(env):
    d = get(env).json()
    assert not any(e["highlight"] for e in d["events"] if e["kind"] != "off_channel")


def test_filters(env):
    d = get(env, sku="NMB-P8-128").json()
    assert d["events"] and all(e["sku"] == "NMB-P8-128" for e in d["events"])
    s = get(env, store_id="store_c").json()
    batches = {e["batch_id"] for e in s["events"]}
    # Every kept batch either ships to store_c or was sold there off-channel.
    for b in batches:
        assert any(e["batch_id"] == b and e["resource_id"] == "store_c" for e in s["events"])
    assert any(e["highlight"] for e in s["events"])
    none = get(env, sku="NOPE").json()
    assert none["events"] == [] and none["totals"]["batches"] == 0


def test_api_proxy(env):
    r = env["api"].get("/supply-chain", params={"sku": "NMB-P8-128"})
    assert r.status_code == 200
    d = r.json()
    assert d["brand_id"] == "nimbus" and d["exact"] is True
    assert all(e["sku"] == "NMB-P8-128" for e in d["events"])
