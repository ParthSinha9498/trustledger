"""Settings read from environment variables at call time, so tests can override them."""
import os


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def node_token() -> str:
    return env("NODE_SHARED_TOKEN", "dev-token")


def brand_id() -> str:
    return env("BRAND_ID", "nimbus")


def current_week() -> int:
    """The demo's 'now' (week 42 is mid-October 2026). Seed history covers weeks 1..now."""
    return int(env("CURRENT_WEEK", "42"))


def brand_node_url() -> str:
    return env("BRAND_NODE_URL", "http://localhost:8001")


def paypal_node_url() -> str:
    return env("PAYPAL_NODE_URL", "http://localhost:8002")


def api_url() -> str:
    return env("API_URL", "http://localhost:8000")
