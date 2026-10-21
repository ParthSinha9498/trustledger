"""Seed wrapper for managed Postgres (Render): same as `python -m backend.seed`, except that a failure
to reach the `postgres` maintenance database (used only to CREATE DATABASE locally) is not fatal,
because the managed databases already exist."""
import sys

from backend import db, seed

_ensure = db.ensure_database


def _ensure_or_skip(name: str) -> None:
    try:
        _ensure(name)
    except Exception as e:  # noqa: BLE001
        print(f"ensure_database({name}) skipped: {e}", file=sys.stderr)


db.ensure_database = _ensure_or_skip
seed.build(small="--small" in sys.argv[1:])
