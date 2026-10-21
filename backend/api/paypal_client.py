"""PayPal Orders v2 client. PAYPAL_MODE=mock runs offline; anything else calls the sandbox."""
import time
import uuid

import httpx

from backend import config

SANDBOX = "https://api-m.sandbox.paypal.com"


class PayPalClient:
    def __init__(self) -> None:
        self.mode = config.env("PAYPAL_MODE", "mock")
        self.base = config.env("PAYPAL_BASE_URL", SANDBOX)
        self._token: str | None = None
        self._token_expiry = 0.0
        self._mock_orders: dict[str, dict] = {}

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    # ---------------------------------------------------------------- auth
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = httpx.post(
            f"{self.base}/v1/oauth2/token",
            auth=(config.env("PAYPAL_CLIENT_ID", ""), config.env("PAYPAL_CLIENT_SECRET", "")),
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        r.raise_for_status()
        body = r.json()
        self._token = body["access_token"]
        self._token_expiry = time.time() + body.get("expires_in", 300)
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}

    # ---------------------------------------------------------------- orders
    def create_order(self, *, amount: float, sku: str, name: str, custom_id: str, currency: str = "USD") -> dict:
        """Create an order with the verification ID in custom_id. Called only after VERIFIED."""
        value = f"{amount:.2f}"
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "custom_id": custom_id,
                "description": f"Brand verified: {name}",
                "amount": {"currency_code": currency, "value": value,
                           "breakdown": {"item_total": {"currency_code": currency, "value": value}}},
                "items": [{"name": name, "sku": sku, "quantity": "1",
                           "unit_amount": {"currency_code": currency, "value": value}}],
            }],
        }
        if self.is_mock:
            oid = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            self._mock_orders[oid] = {"id": oid, "status": "CREATED", "body": body}
            return {"id": oid, "status": "CREATED"}
        r = httpx.post(f"{self.base}/v2/checkout/orders", json=body, headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def capture_order(self, order_id: str) -> dict:
        if self.is_mock:
            order = self._mock_orders.get(order_id, {"id": order_id})
            order["status"] = "COMPLETED"
            return {"id": order_id, "status": "COMPLETED",
                    "payer": {"payer_id": f"MOCKPAYER{uuid.uuid4().hex[:6]}"}}
        r = httpx.post(f"{self.base}/v2/checkout/orders/{order_id}/capture", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def get_order(self, order_id: str) -> dict:
        if self.is_mock:
            return self._mock_orders.get(order_id, {"id": order_id, "status": "UNKNOWN"})
        r = httpx.get(f"{self.base}/v2/checkout/orders/{order_id}", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    # ---------------------------------------------------------------- webhooks
    def verify_webhook(self, headers: dict, event: dict) -> bool:
        if self.is_mock:
            return True
        body = {
            "auth_algo": headers.get("paypal-auth-algo"),
            "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": config.env("PAYPAL_WEBHOOK_ID", ""),
            "webhook_event": event,
        }
        r = httpx.post(f"{self.base}/v1/notifications/verify-webhook-signature",
                       json=body, headers=self._headers(), timeout=20)
        return r.status_code == 200 and r.json().get("verification_status") == "SUCCESS"


paypal = PayPalClient()
