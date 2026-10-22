"""Shared plumbing for evals: dedicated databases, in-process services, direct DB access.

Evals are the only code allowed to read the PayPal-side database directly (for ground truth)
and to reset the privacy ledger between attempts. They never touch dev data: every database is
named trustledger_eval_<tag>_<name>.
"""
import json
import os
from pathlib import Path

PG = os.environ.get("EVAL_PG_URL", "postgresql://postgres:postgres@localhost:5433")
DB_VARS = {"brand": "BRAND_DATABASE_URL", "paypal_side": "PAYPAL_DATABASE_URL", "platform": "PLATFORM_DATABASE_URL"}
RESULTS_DIR = Path(__file__).parent / "results"


def db_names(tag: str) -> dict[str, str]:
    return {name: f"trustledger_eval_{tag}_{name}" for name in DB_VARS}


def configure(tag: str, mock: bool) -> None:
    """Point every service at the eval databases. Call before importing backend apps."""
    for name, dbname in db_names(tag).items():
        os.environ[DB_VARS[name]] = f"{PG}/{dbname}"
    os.environ["PAYPAL_MODE"] = "mock"      # evals never create real PayPal orders
    os.environ["CURRENT_WEEK"] = "12"       # scenarios are built on a 12-week world (evals/scenarios.py)
    os.environ.pop("NOTIFY_WEBHOOK_URL", None)
    if mock:
        os.environ["LLM_MODE"] = "mock"


def wire_services() -> dict:
    """Route inter-service HTTP in-process (same as tests/conftest.py). Returns clients."""
    from fastapi.testclient import TestClient

    from backend import config
    from backend.api.main import app as api_app
    from backend.brand_node.main import app as brand_app
    from backend.common import http
    from backend.paypal_node.main import app as paypal_app

    http.clear_overrides()
    http.register_override(config.brand_node_url(), lambda: TestClient(brand_app, base_url=config.brand_node_url()))
    http.register_override(config.paypal_node_url(), lambda: TestClient(paypal_app, base_url=config.paypal_node_url()))
    http.register_override(config.api_url(), lambda: TestClient(api_app, base_url=config.api_url()))
    return {"api": TestClient(api_app, headers={"X-Node-Token": config.node_token()})}


def reset_privacy_state(brand: str = "nimbus") -> None:
    """Fresh budget and empty release cache (a labelled 'dataset reset' between eval attempts)."""
    from backend import db
    from backend.common import privacy

    with db.connect("paypal_side") as c:
        c.execute("UPDATE privacy_ledger SET rho_spent = 0")
        c.execute("DELETE FROM query_cache")
        c.execute("DELETE FROM private_release_marginals")
        c.execute("DELETE FROM private_releases")
    privacy.build_release(brand)


def bump_data_version() -> None:
    """Call after modifying PayPal-side data so cached releases are not reused."""
    from backend import db

    with db.connect("paypal_side") as c:
        c.execute("UPDATE meta SET value = (value::int + 1)::text WHERE key='data_version'")


def close_pools() -> None:
    from backend import db

    for pool in db._pools.values():
        pool.close()
    db._pools.clear()


def drop_databases(tag: str) -> None:
    import psycopg

    close_pools()
    with psycopg.connect(f"{PG}/postgres", autocommit=True) as c:
        for dbname in db_names(tag).values():
            c.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')


def write_results(name: str, data: dict, markdown: str, out_dir: Path | None = None) -> tuple[Path, Path]:
    out = out_dir or RESULTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    jp, mp = out / f"{name}.json", out / f"{name}.md"
    jp.write_text(json.dumps(data, indent=2, default=str))
    mp.write_text(markdown)
    return jp, mp
