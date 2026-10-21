"""Endpoints the browser PayPal JS SDK v6 needs.

The v6 SDK is loaded from https://www.sandbox.paypal.com/web-sdk/v6/core (production:
https://www.paypal.com/web-sdk/v6/core) and initialised with `window.paypal.createInstance(...)` using
either the public client ID (PayPal's recommended path) or a browser-safe client token.
Docs: https://developer.paypal.com/sdk/js/set-up/
      https://docs.paypal.ai/reference/sdk/js/v6/reference

The client token comes from the same OAuth endpoint as the server token, with two extra form fields:
    POST /v1/oauth2/token  (basic auth client_id:secret, x-www-form-urlencoded)
      grant_type=client_credentials
      response_type=client_token
      domains[]=<root domains the page runs on, no protocol/subdomain/wildcard>
The response's `access_token` is the client token (`expires_in` seconds). The secret never leaves the server.

The order itself is created server-side by /checkout/scan, only after the brand says VERIFIED. The browser
never creates orders; it only starts a payment session for the order ID we already have.

Owned by the web work stream. Router is included in backend/api/main.py.
"""
import time

import httpx
from fastapi import APIRouter, HTTPException

from backend import config
from backend.api.paypal_client import paypal

router = APIRouter(prefix="/paypal/sdk", tags=["paypal-sdk"])

SDK_URLS = {
    "sandbox": "https://www.sandbox.paypal.com/web-sdk/v6/core",
    "live": "https://www.paypal.com/web-sdk/v6/core",
}
MOCK_CLIENT_TOKEN = "MOCK-CLIENT-TOKEN-not-a-real-paypal-token"

_cache: dict[str, float | str] = {}


def _mode() -> str:
    return "mock" if paypal.is_mock else paypal.mode


def _sdk_url() -> str | None:
    if paypal.is_mock:
        return None
    return SDK_URLS["live"] if paypal.mode == "live" else SDK_URLS["sandbox"]


def _domains() -> str:
    """Root domains for the client token, from PAYPAL_SDK_DOMAINS (comma separated)."""
    return config.env("PAYPAL_SDK_DOMAINS", "localhost") or "localhost"


@router.get("/config")
def sdk_config():
    """Public, browser-safe settings. Never includes the secret."""
    return {
        "mode": _mode(),
        "client_id": None if paypal.is_mock else (config.env("PAYPAL_CLIENT_ID", "") or None),
        "currency": config.env("PAYPAL_CURRENCY", "USD"),
        "sdk_url": _sdk_url(),
    }


@router.get("/client-token")
def client_token():
    """Browser-safe client token for `createInstance({clientToken})`. Mock mode returns a clearly fake one."""
    if paypal.is_mock:
        return {"mode": "mock", "client_token": MOCK_CLIENT_TOKEN, "expires_in": 900}

    now = time.time()
    if _cache.get("token") and now < float(_cache.get("expiry", 0)) - 60:
        return {"mode": _mode(), "client_token": _cache["token"],
                "expires_in": int(float(_cache["expiry"]) - now)}

    client_id = config.env("PAYPAL_CLIENT_ID", "")
    secret = config.env("PAYPAL_CLIENT_SECRET", "")
    if not client_id or not secret:
        raise HTTPException(503, "PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not set")
    try:
        r = httpx.post(
            f"{paypal.base}/v1/oauth2/token",
            auth=(client_id, secret),
            data={"grant_type": "client_credentials", "response_type": "client_token",
                  "domains[]": _domains()},
            timeout=20,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"PayPal client token request failed: {e}") from e
    body = r.json()
    token = body["access_token"]
    expires_in = int(body.get("expires_in", 900))
    _cache.update(token=token, expiry=now + expires_in)
    return {"mode": _mode(), "client_token": token, "expires_in": expires_in}
