"""Browser SDK endpoints: mock mode is fake and obvious; sandbox mode asks PayPal for a client token."""
import httpx

from backend.api import paypal_sdk
from backend.api.paypal_client import paypal


def test_config_mock(env):
    body = env["api"].get("/paypal/sdk/config").json()
    assert body == {"mode": "mock", "client_id": None, "currency": "USD", "sdk_url": None, "test_card": True}


def test_client_token_mock(env):
    body = env["api"].get("/paypal/sdk/client-token").json()
    assert body["mode"] == "mock"
    assert body["client_token"].startswith("MOCK-")


def test_client_token_sandbox_requests_browser_safe_token(env, monkeypatch):
    monkeypatch.setattr(paypal, "mode", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "pub-id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "s3cret")
    monkeypatch.setenv("PAYPAL_SDK_DOMAINS", "trustledger.example")
    paypal_sdk._cache.clear()
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return httpx.Response(200, json={"access_token": "CT-123", "expires_in": 900, "token_type": "Bearer"},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(paypal_sdk.httpx, "post", fake_post)
    api = env["api"]

    cfg = api.get("/paypal/sdk/config").json()
    assert cfg["mode"] == "sandbox" and cfg["client_id"] == "pub-id"
    assert cfg["sdk_url"] == "https://www.sandbox.paypal.com/web-sdk/v6/core"
    assert "s3cret" not in str(cfg)

    body = api.get("/paypal/sdk/client-token").json()
    assert body["client_token"] == "CT-123" and body["mode"] == "sandbox"
    url, kw = calls[0]
    assert url.endswith("/v1/oauth2/token")
    assert kw["data"] == {"grant_type": "client_credentials", "response_type": "client_token",
                          "domains[]": "trustledger.example"}
    assert kw["auth"] == ("pub-id", "s3cret")

    api.get("/paypal/sdk/client-token")
    assert len(calls) == 1  # cached until near expiry
    paypal_sdk._cache.clear()


def test_client_token_sandbox_without_credentials(env, monkeypatch):
    monkeypatch.setattr(paypal, "mode", "sandbox")
    monkeypatch.delenv("PAYPAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("PAYPAL_CLIENT_SECRET", raising=False)
    paypal_sdk._cache.clear()
    assert env["api"].get("/paypal/sdk/client-token").status_code == 503
