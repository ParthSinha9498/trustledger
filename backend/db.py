"""Postgres access. Each service owns exactly one database and only gets its own URL.

    BRAND_DATABASE_URL     -> brand node
    PAYPAL_DATABASE_URL    -> PayPal-side node
    PLATFORM_DATABASE_URL  -> api (cases, checkouts)
"""
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend import config

ENV_VARS = {
    "brand": "BRAND_DATABASE_URL",
    "paypal_side": "PAYPAL_DATABASE_URL",
    "platform": "PLATFORM_DATABASE_URL",
}
LOCAL_DEFAULT = "postgresql://postgres:postgres@localhost:5433/trustledger_{name}"

_pools: dict[str, ConnectionPool] = {}


def url(name: str) -> str:
    return config.env(ENV_VARS[name]) or LOCAL_DEFAULT.format(name=name)


def _pool(name: str) -> ConnectionPool:
    u = url(name)
    if u not in _pools:
        _pools[u] = ConnectionPool(
            u, min_size=1, max_size=5, open=True,
            kwargs={"row_factory": dict_row, "autocommit": True},
        )
    return _pools[u]


@contextmanager
def connect(name: str) -> Iterator[psycopg.Connection]:
    with _pool(name).connection() as conn:
        yield conn


def ensure_database(name: str) -> None:
    """Create the database if it doesn't exist (local dev and tests; managed Postgres pre-creates it)."""
    target = conninfo_to_dict(url(name))
    dbname = target["dbname"]
    admin = make_conninfo(url(name), dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as c:
        exists = c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if not exists:
            c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
