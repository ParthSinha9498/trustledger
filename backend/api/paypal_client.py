"""PayPal Orders v2 client.

PAYPAL_MODE=mock runs offline and never touches the network or the SDK. sandbox (default for anything
that isn't mock) and live call PayPal through the APIMatic-generated PayPal Server SDK
(`paypal-server-sdk`, import package `paypalserversdk`) for Orders v2: create, get, capture.

The SDK covers Orders, Payments, Vault, Subscriptions, Transaction Search and the OAuth token endpoint.
It has no webhook-signature verification, so `verify_webhook` stays on httpx with its own token.
"""
import json
import time
import uuid

import httpx
from paypalserversdk.configuration import Environment
from paypalserversdk.exceptions.api_exception import ApiException
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.models.amount_breakdown import AmountBreakdown
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.item_request import ItemRequest
from paypalserversdk.models.money import Money
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

from backend import config

SANDBOX = "https://api-m.sandbox.paypal.com"
LIVE = "https://api-m.paypal.com"
TIMEOUT = 20  # seconds per request, same as the old httpx calls (the SDK default is 60)


class PayPalError(Exception):
    """A non-2xx answer from PayPal. `body` is PayPal's JSON error ({} if it wasn't JSON)."""

    def __init__(self, status_code: int, body: dict, message: str | None = None) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message or body.get("message") or f"PayPal returned HTTP {status_code}")

    @classmethod
    def from_api_exception(cls, e: ApiException) -> "PayPalError":
        try:
            body = json.loads(e.response.text or "")
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        # Not str(e): the SDK's typed ErrorException.__str__ reads unboxed fields that may be unset.
        return cls(e.response_code, body, body.get("message") or f"PayPal {e.response_code}: {e.reason}")


def _fetch_token(last_token, auth_manager):
    """OAuth token provider for the SDK: fetch a new token and let failures raise.

    Without a provider the SDK swallows a failed token request and raises AuthValidationException with a
    fixed message (not an ApiException). Fetching here surfaces PayPal's real status and body as an
    ApiException (OAuthProviderException), which becomes a PayPalError like any other PayPal failure.
    The SDK stamps the token's expiry itself and calls this again when it expires.
    """
    return auth_manager.fetch_token()


class PayPalClient:
    def __init__(self) -> None:
        self.mode = config.env("PAYPAL_MODE", "mock")
        self.base = config.env("PAYPAL_BASE_URL", LIVE if self.mode == "live" else SANDBOX)
        self._token: str | None = None
        self._token_expiry = 0.0
        self._mock_orders: dict[str, dict] = {}
        self._sdk_client: PaypalServersdkClient | None = None

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"

    # ---------------------------------------------------------------- SDK client
    def _sdk(self) -> PaypalServersdkClient:
        """One SDK client per process, built on first use (never in mock mode)."""
        if self._sdk_client is None:
            self._sdk_client = PaypalServersdkClient(
                environment=Environment.PRODUCTION if self.mode == "live" else Environment.SANDBOX,
                client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
                    o_auth_client_id=config.env("PAYPAL_CLIENT_ID", ""),
                    o_auth_client_secret=config.env("PAYPAL_CLIENT_SECRET", ""),
                    o_auth_token_provider=_fetch_token,
                ),
                timeout=TIMEOUT,
                max_retries=0,  # no silent retries of create/capture; a resend reuses its PayPal-Request-Id
            )
        return self._sdk_client

    @staticmethod
    def _call(operation, options: dict) -> dict:
        """Run one SDK operation and return PayPal's JSON as a plain dict, like the REST API."""
        try:
            response = operation(options)
        except ApiException as e:
            raise PayPalError.from_api_exception(e) from e
        return json.loads(response.text) if response.text else {}

    # ---------------------------------------------------------------- httpx auth (webhook verification only)
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        r = httpx.post(
            f"{self.base}/v1/oauth2/token",
            auth=(config.env("PAYPAL_CLIENT_ID", ""), config.env("PAYPAL_CLIENT_SECRET", "")),
            data={"grant_type": "client_credentials"},
            timeout=TIMEOUT,
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
        """Create an order with the verification ID in custom_id. Called only after VERIFIED.

        PayPal-Request-Id is `create-<verification id>`: a resend of the same create (a retry after a
        timeout) gets PayPal's stored answer for that key (kept 6 hours) instead of a second order.
        """
        value = f"{amount:.2f}"
        if self.is_mock:
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
            oid = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
            self._mock_orders[oid] = {"id": oid, "status": "CREATED", "body": body}
            return {"id": oid, "status": "CREATED"}

        order = OrderRequest(
            intent=CheckoutPaymentIntent.CAPTURE,
            purchase_units=[PurchaseUnitRequest(
                custom_id=custom_id,
                description=f"Brand verified: {name}",
                amount=AmountWithBreakdown(
                    currency_code=currency, value=value,
                    breakdown=AmountBreakdown(item_total=Money(currency_code=currency, value=value)),
                ),
                items=[ItemRequest(name=name, sku=sku, quantity="1",
                                   unit_amount=Money(currency_code=currency, value=value))],
            )],
        )
        return self._call(self._sdk().orders.create_order,
                          {"body": order, "paypal_request_id": f"create-{custom_id}"})

    def capture_order(self, order_id: str) -> dict:
        """Capture an approved order. PayPal-Request-Id is `capture-<order id>`, so a resent capture
        returns the stored result for that key instead of charging the buyer twice."""
        if self.is_mock:
            order = self._mock_orders.get(order_id, {"id": order_id})
            order["status"] = "COMPLETED"
            return {"id": order_id, "status": "COMPLETED",
                    "payer": {"payer_id": f"MOCKPAYER{uuid.uuid4().hex[:6]}"}}
        return self._call(self._sdk().orders.capture_order,
                          {"id": order_id, "paypal_request_id": f"capture-{order_id}"})

    def get_order(self, order_id: str) -> dict:
        if self.is_mock:
            return self._mock_orders.get(order_id, {"id": order_id, "status": "UNKNOWN"})
        return self._call(self._sdk().orders.get_order, {"id": order_id})

    # ---------------------------------------------------------------- webhooks (not in the SDK: httpx)
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
                       json=body, headers=self._headers(), timeout=TIMEOUT)
        return r.status_code == 200 and r.json().get("verification_status") == "SUCCESS"


paypal = PayPalClient()
