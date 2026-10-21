import os

os.environ.setdefault("PAYPAL_MODE", "mock")
os.environ.setdefault("LLM_MODE", "mock")

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.common import http


TEST_PG = os.environ.get("TEST_PG_URL", "postgresql://postgres:postgres@localhost:5433")
# Unique per process so parallel test runs never share databases.
TEST_SUFFIX = os.environ.get("TEST_DB_SUFFIX") or str(os.getpid())
TEST_DBS = {name: f"trustledger_test_{TEST_SUFFIX}_{name}" for name in ("brand", "paypal_side", "platform")}


@pytest.fixture(scope="session", autouse=True)
def _drop_test_databases():
    yield
    import psycopg
    from backend import db as dbmod

    for pool in dbmod._pools.values():
        pool.close()
    dbmod._pools.clear()
    with psycopg.connect(f"{TEST_PG}/postgres", autocommit=True) as c:
        for name in TEST_DBS.values():
            c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture()
def env(monkeypatch):
    # Separate test databases; seed drops and recreates every table, so each test starts clean.
    for name, var in (("brand", "BRAND_DATABASE_URL"), ("paypal_side", "PAYPAL_DATABASE_URL"),
                      ("platform", "PLATFORM_DATABASE_URL")):
        monkeypatch.setenv(var, f"{TEST_PG}/{TEST_DBS[name]}")
    monkeypatch.setenv("CURRENT_WEEK", "42")  # the demo's "now"; eval harnesses may set 12 process-wide
    from backend import seed
    seed.build(small=True)

    from backend.api.main import app as api_app
    from backend.brand_node.main import app as brand_app
    from backend.paypal_node.main import app as paypal_app

    http.clear_overrides()
    http.register_override(config.brand_node_url(), lambda: TestClient(brand_app, base_url=config.brand_node_url()))
    http.register_override(config.paypal_node_url(), lambda: TestClient(paypal_app, base_url=config.paypal_node_url()))
    http.register_override(config.api_url(), lambda: TestClient(api_app, base_url=config.api_url()))
    yield {
        "api": TestClient(api_app),
        "brand": TestClient(brand_app, headers={"X-Node-Token": config.node_token()}),
        "paypal": TestClient(paypal_app, headers={"X-Node-Token": config.node_token()}),
    }
    http.clear_overrides()
