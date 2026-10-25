"""Sandbox code path of the PayPal client, offline.

The real PayPal Server SDK runs (request building, JSON serialization, OAuth token fetch, error mapping),
but its transport is a requests.Session whose adapter answers from a route table. That's the seam the
APIMatic python-testing skill recommends: `http_client_instance` for the stub, `http_call_back` to see
what the SDK actually sent. No network is touched.
"""
import json

import pytest
import requests
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict

from backend.api import paypal_client
from backend.api.paypal_client import PayPalClient, PayPalError, paypal
from paypalserversdk.http.http_call_back import HttpCallBack

SANDBOX_HOST = "https://api-m.sandbox.paypal.com"
TOKEN = {"access_token": "TEST-ACCESS-TOKEN", "token_type": "Bearer", "expires_in": 32400}
ORDER_NOT_APPROVED = {
    "name": "UNPROCESSABLE_ENTITY", "message": "The requested action could not be performed.",
    "details": [{"issue": "ORDER_NOT_APPROVED", "description": "Payer has not yet approved the Order."}],
    "debug_id": "f00dbabe"}


class RouteAdapter(HTTPAdapter):
    """Answers (METHOD, path) from a table. The OAuth token path gets a 200 unless overridden."""

    def __init__(self, routes):
        super().__init__()
        self.routes = {("POST", "/v1/oauth2/token"): (200, TOKEN), **routes}

    def send(self, request, **kwargs):
        path = requests.utils.urlparse(request.url).path
        status, body = self.routes.get((request.method, path), (404, {"name": "RESOURCE_NOT_FOUND"}))
        resp = requests.Response()
        resp.status_code = status
        resp._content = json.dumps(body).encode()
        resp.headers = CaseInsensitiveDict({"Content-Type": "application/json"})
        resp.encoding = "utf-8"
        resp.url = request.url
        resp.request = request
        resp.reason = "stub"
        return resp


class Catcher(HttpCallBack):
    """Keeps every request the SDK sends (the token POST fires too, so select by path)."""

    def __init__(self):
        self.requests = []

    def on_before_request(self, request):
        self.requests.append(request)

    def on_after_response(self, response):
        pass

    def sent(self, path):
        return [r for r in self.requests if requests.utils.urlparse(r.query_url).path == path]


@pytest.fixture()
def sdk_stub(monkeypatch):
    """Route the SDK client that PayPalClient._sdk() builds through a stub session.

    Our own construction (environment, client-credentials auth, token provider, timeout) still runs;
    only the transport and an observer are added.
    """
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "test-client-secret")
    catcher = Catcher()
    adapter = RouteAdapter({})
    real = paypal_client.PaypalServersdkClient

    def build(**kwargs):
        session = requests.Session()
        session.mount("https://", adapter)
        return real(**kwargs, http_client_instance=session, http_call_back=catcher)

    monkeypatch.setattr(paypal_client, "PaypalServersdkClient", build)
    return adapter.routes, catcher


def sandbox_client(monkeypatch) -> PayPalClient:
    monkeypatch.setenv("PAYPAL_MODE", "sandbox")
    return PayPalClient()


def test_create_order_sends_typed_order_with_verification_id(monkeypatch, sdk_stub):
    routes, catcher = sdk_stub
    routes[("POST", "/v2/checkout/orders")] = (201, {"id": "5O190127TN364715T", "status": "CREATED"})
    client = sandbox_client(monkeypatch)

    order = client.create_order(amount=899, sku="NMB-P8-128", name="Nimbus P8", custom_id="ver_abc123")

    assert order == {"id": "5O190127TN364715T", "status": "CREATED"}  # plain dict, like the REST API
    [req] = catcher.sent("/v2/checkout/orders")
    assert req.query_url == f"{SANDBOX_HOST}/v2/checkout/orders"
    assert req.headers["Authorization"] == "Bearer TEST-ACCESS-TOKEN"
    body = json.loads(req.parameters)
    assert body["intent"] == "CAPTURE"
    [unit] = body["purchase_units"]
    assert unit["custom_id"] == "ver_abc123"
    assert unit["description"] == "Brand verified: Nimbus P8"
    assert unit["amount"] == {"currency_code": "USD", "value": "899.00",
                              "breakdown": {"item_total": {"currency_code": "USD", "value": "899.00"}}}
    assert unit["items"] == [{"name": "Nimbus P8", "sku": "NMB-P8-128", "quantity": "1",
                              "unit_amount": {"currency_code": "USD", "value": "899.00"}}]
    # Client credentials: the token was fetched once with Basic auth, then reused.
    [tok] = catcher.sent("/v1/oauth2/token")
    assert tok.headers["Authorization"].startswith("Basic ")


def test_get_and_capture_return_paypal_json(monkeypatch, sdk_stub):
    routes, catcher = sdk_stub
    order = {"id": "ORDER1", "status": "CREATED", "intent": "CAPTURE",
             "purchase_units": [{"reference_id": "default", "custom_id": "ver_abc123",
                                 "amount": {"currency_code": "USD", "value": "899.00"}}]}
    captured = {"id": "ORDER1", "status": "COMPLETED", "payer": {"payer_id": "QYR5Z8XDVJNXQ"}}
    routes[("GET", "/v2/checkout/orders/ORDER1")] = (200, order)
    routes[("POST", "/v2/checkout/orders/ORDER1/capture")] = (201, captured)
    client = sandbox_client(monkeypatch)

    assert client.get_order("ORDER1") == order
    result = client.capture_order("ORDER1")
    assert result["status"] == "COMPLETED" and result.get("payer", {}).get("payer_id") == "QYR5Z8XDVJNXQ"
    assert len(catcher.sent("/v1/oauth2/token")) == 1  # one SDK client, one token, reused


def test_capture_422_raises_paypal_error(monkeypatch, sdk_stub):
    routes, _ = sdk_stub
    routes[("POST", "/v2/checkout/orders/ORDER1/capture")] = (422, ORDER_NOT_APPROVED)
    client = sandbox_client(monkeypatch)

    with pytest.raises(PayPalError) as exc:
        client.capture_order("ORDER1")
    assert exc.value.status_code == 422
    assert exc.value.body["details"][0]["issue"] == "ORDER_NOT_APPROVED"
    assert str(exc.value) == ORDER_NOT_APPROVED["message"]


def test_token_failure_is_a_paypal_error_with_the_real_status(monkeypatch, sdk_stub):
    routes, _ = sdk_stub
    routes[("POST", "/v1/oauth2/token")] = (401, {"error": "invalid_client",
                                                   "error_description": "Client Authentication failed"})
    client = sandbox_client(monkeypatch)

    with pytest.raises(PayPalError) as exc:
        client.get_order("ORDER1")
    assert exc.value.status_code == 401 and exc.value.body["error"] == "invalid_client"


def test_capture_endpoint_maps_paypal_422_to_409(env, monkeypatch, sdk_stub):
    api = env["api"]
    chk = api.post("/checkout/scan", json={"serial": "X123", "sku": "NMB-P8-128", "amount": 899.0,
                                           "store_id": "store_a"}).json()
    assert chk["status"] == "VERIFIED"
    # The order was made in mock mode; the capture now goes through the SDK and PayPal says 422.
    routes, _ = sdk_stub
    routes[("POST", f"/v2/checkout/orders/{chk['paypal_order_id']}/capture")] = (422, ORDER_NOT_APPROVED)
    monkeypatch.setattr(paypal, "mode", "sandbox")
    monkeypatch.setattr(paypal, "_sdk_client", None)

    r = api.post(f"/checkout/{chk['checkout_id']}/capture")
    assert r.status_code == 409
    assert r.json()["detail"] == {"paypal_issue": "ORDER_NOT_APPROVED", "message": ORDER_NOT_APPROVED["message"]}

    routes[("POST", f"/v2/checkout/orders/{chk['paypal_order_id']}/capture")] = (
        500, {"name": "INTERNAL_SERVER_ERROR", "message": "An internal server error has occurred."})
    r = api.post(f"/checkout/{chk['checkout_id']}/capture")
    assert r.status_code == 502 and r.json()["detail"]["paypal_issue"] == "INTERNAL_SERVER_ERROR"


def test_mock_mode_never_touches_the_sdk(env, monkeypatch):
    def no_sdk(**kwargs):
        raise AssertionError("mock mode must not build a PayPal SDK client")

    monkeypatch.setattr(paypal_client, "PaypalServersdkClient", no_sdk)
    assert paypal.is_mock
    api = env["api"]
    chk = api.post("/checkout/scan", json={"serial": "X123", "sku": "NMB-P8-128", "amount": 899.0,
                                           "store_id": "store_a"}).json()
    assert chk["paypal_order_id"].startswith("MOCK-")
    assert paypal.get_order(chk["paypal_order_id"])["status"] == "CREATED"
    assert api.post(f"/checkout/{chk['checkout_id']}/capture").status_code == 200
    assert paypal._sdk_client is None


def test_create_and_capture_send_a_stable_paypal_request_id(monkeypatch, sdk_stub):
    """A resend with the same inputs carries the same PayPal-Request-Id, so PayPal answers it from the
    stored result for that key (one order, one capture) instead of creating or charging twice."""
    routes, catcher = sdk_stub
    routes[("POST", "/v2/checkout/orders")] = (201, {"id": "ORDER1", "status": "CREATED"})
    routes[("POST", "/v2/checkout/orders/ORDER1/capture")] = (201, {"id": "ORDER1", "status": "COMPLETED"})
    client = sandbox_client(monkeypatch)

    for _ in range(2):  # the second round is the retry
        client.create_order(amount=899, sku="NMB-P8-128", name="Nimbus P8", custom_id="ver_abc123")
        client.capture_order("ORDER1")

    creates = catcher.sent("/v2/checkout/orders")
    captures = catcher.sent("/v2/checkout/orders/ORDER1/capture")
    assert [r.headers["PayPal-Request-Id"] for r in creates] == ["create-ver_abc123"] * 2
    assert [r.headers["PayPal-Request-Id"] for r in captures] == ["capture-ORDER1"] * 2

    # A different verification gets a different key: it is a new order, not a replay.
    client.create_order(amount=899, sku="NMB-P8-128", name="Nimbus P8", custom_id="ver_def456")
    assert catcher.sent("/v2/checkout/orders")[-1].headers["PayPal-Request-Id"] == "create-ver_def456"


def test_get_order_sends_no_paypal_request_id(monkeypatch, sdk_stub):
    routes, catcher = sdk_stub
    routes[("GET", "/v2/checkout/orders/ORDER1")] = (200, {"id": "ORDER1", "status": "CREATED"})
    sandbox_client(monkeypatch).get_order("ORDER1")
    [req] = catcher.sent("/v2/checkout/orders/ORDER1")
    assert "PayPal-Request-Id" not in req.headers


def test_pay_with_test_card_confirms_with_the_card_then_captures(monkeypatch, sdk_stub):
    routes, catcher = sdk_stub
    routes[("POST", "/v2/checkout/orders/ORDER1/confirm-payment-source")] = (200, {"id": "ORDER1", "status": "APPROVED"})
    routes[("POST", "/v2/checkout/orders/ORDER1/capture")] = (201, {"id": "ORDER1", "status": "COMPLETED"})
    monkeypatch.setenv("SANDBOX_TEST_CARD_NUMBER", "4000000000000000")
    monkeypatch.setenv("SANDBOX_TEST_CARD_EXPIRY", "2030-01")
    monkeypatch.setenv("SANDBOX_TEST_CARD_CVV", "123")

    assert sandbox_client(monkeypatch).pay_with_test_card("ORDER1")["status"] == "COMPLETED"
    [confirm] = catcher.sent("/v2/checkout/orders/ORDER1/confirm-payment-source")
    assert json.loads(confirm.parameters) == {"payment_source": {"card": {
        "name": "TrustLedger Test", "number": "4000000000000000", "expiry": "2030-01", "security_code": "123"}}}
    [capture] = catcher.sent("/v2/checkout/orders/ORDER1/capture")
    assert capture.headers["PayPal-Request-Id"] == "capture-ORDER1"  # the same capture path and key


def test_pay_with_test_card_stops_when_the_card_is_not_approved(monkeypatch, sdk_stub):
    routes, catcher = sdk_stub
    routes[("POST", "/v2/checkout/orders/ORDER1/confirm-payment-source")] = (
        200, {"id": "ORDER1", "status": "PAYER_ACTION_REQUIRED"})
    monkeypatch.setenv("SANDBOX_TEST_CARD_NUMBER", "4000000000000000")
    monkeypatch.setenv("SANDBOX_TEST_CARD_EXPIRY", "2030-01")

    with pytest.raises(PayPalError) as exc:
        sandbox_client(monkeypatch).pay_with_test_card("ORDER1")
    assert exc.value.body["name"] == "TEST_CARD_NOT_APPROVED"
    assert catcher.sent("/v2/checkout/orders/ORDER1/capture") == []


def test_pay_with_test_card_needs_a_configured_card(monkeypatch, sdk_stub):
    monkeypatch.delenv("SANDBOX_TEST_CARD_NUMBER", raising=False)
    monkeypatch.delenv("SANDBOX_TEST_CARD_EXPIRY", raising=False)
    with pytest.raises(paypal_client.CardPaymentUnavailable):
        sandbox_client(monkeypatch).pay_with_test_card("ORDER1")
