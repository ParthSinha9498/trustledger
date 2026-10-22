"""Settings read from environment variables at call time, so tests can override them."""
import os


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def node_token() -> str:
    return env("NODE_SHARED_TOKEN", "dev-token")


def payer_hash_key() -> bytes:
    """Secret for the keyed hash of payer IDs. Only the PayPal-side node holds it (docker/all_in_one.sh)."""
    return env("PAYER_HASH_KEY", "dev-payer-key").encode()


def brand_id() -> str:
    return env("BRAND_ID", "nimbus")


def current_week() -> int:
    """The demo's 'now' (week 42 is mid-October 2026). Seed history covers weeks 1..now."""
    return int(env("CURRENT_WEEK", "42"))


def demo_mode() -> bool:
    """Demo helpers (e.g. handing out an unsold demo serial). On by default; set DEMO_MODE=0 to turn off."""
    return env("DEMO_MODE", "1").lower() not in ("0", "false", "no")


def brand_node_url() -> str:
    return env("BRAND_NODE_URL", "http://localhost:8001")


def paypal_node_url() -> str:
    return env("PAYPAL_NODE_URL", "http://localhost:8002")


def api_url() -> str:
    return env("API_URL", "http://localhost:8000")
