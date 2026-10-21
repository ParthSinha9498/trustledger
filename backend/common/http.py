"""HTTP clients between services. Tests register in-process clients by base URL."""
from typing import Callable

import httpx

from backend import config

_overrides: dict[str, Callable[[], httpx.Client]] = {}


def register_override(base_url: str, factory: Callable[[], httpx.Client]) -> None:
    _overrides[base_url] = factory


def clear_overrides() -> None:
    _overrides.clear()


def client(base_url: str) -> httpx.Client:
    if base_url in _overrides:
        c = _overrides[base_url]()
        c.headers["X-Node-Token"] = config.node_token()
        return c
    return httpx.Client(
        base_url=base_url, timeout=20, headers={"X-Node-Token": config.node_token()}
    )
