# APIMatic in TrustLedger

## PayPal Server SDK via Context Plugin

The backend's PayPal Orders v2 calls (`backend/api/paypal_client.py`) go through the APIMatic-generated
**PayPal Server SDK** (`paypal-server-sdk==2.4.0`, import package `paypalserversdk`). The integration was
written with APIMatic's **PayPal Context Plugin**, which gives the coding agent skills grounded in this
exact SDK build:

```bash
npx context-plugins install https://github.com/paypaldev/server-sdk-context-plugin-preview --targets claude
uv add "paypal-server-sdk==2.4.0"   # pinned, as the plugin asks
```

### Which skill guided what

| Skill | What it decided in our code |
|---|---|
| `python-getting-started` | Pin the exact version; import every name from its full module path (the package re-exports nothing); confirm each signature in the installed `site-packages/paypalserversdk/` source. |
| `python-client-initialization` | One long-lived `PaypalServersdkClient`, built lazily on the first sandbox/live call and reused (keeps the OAuth token). Pick `Environment.SANDBOX` / `Environment.PRODUCTION` explicitly instead of relying on the default. |
| `python-authentication` | `ClientCredentialsAuthCredentials(o_auth_client_id=..., o_auth_client_secret=...)` passed as `client_credentials_auth_credentials=`. We read our own `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` instead of `from_environment()`, which reads different variable names. The SDK stamps token expiry itself. |
| `python-calling-endpoints` | Orders operations take a single `options` dict: `orders.create_order({"body": OrderRequest(...)})`, `orders.get_order({"id": ...})`, `orders.capture_order({"id": ...})`. Responses are `ApiResponse` envelopes. The same `options` dict carries `paypal_request_id`, which the SDK sends as the `PayPal-Request-Id` header (see below). |
| `python-models` | The request is built from typed models: `OrderRequest`, `CheckoutPaymentIntent.CAPTURE`, `PurchaseUnitRequest(custom_id=<verification id>, ...)`, `AmountWithBreakdown` + `AmountBreakdown(item_total=Money(...))`, `ItemRequest`. Callers get PayPal's JSON as a plain dict (`json.loads(response.text)`), which avoids the "optional attribute is absent, not `None`" trap on response models. |
| `python-error-handling` | Errors arrive as `ApiException` (here the typed `ErrorException`), status on `.response_code`, raw body on `.response.text`. We wrap them in our own `PayPalError(status_code, body)`; the capture endpoint maps PayPal 422 to our 409 and other errors to 502. We never call `str()` on the typed exception (its `__str__` can fail on a non-JSON body). Token failures would normally surface as `AuthValidationException`, which is not an `ApiException` and hides the real status, so we pass an `o_auth_token_provider` that calls `fetch_token()` directly: a bad credential becomes `PayPalError(401)` with PayPal's body. |
| `python-configuration-resilience` | Defaults read from `Configuration.__init__`: `timeout=60`, `max_retries=0`, retries only for GET/PUT. We set `timeout=20` (what the old code used) and keep `max_retries=0` explicitly. See "What the plugin changed" below. |
| `python-testing` | `tests/test_paypal_client.py` runs the real SDK offline: a `requests.Session` with a route-table adapter is passed as `http_client_instance`, an `HttpCallBack` records every request (the OAuth token POST included, so we select by path), and the token path answers 200. Tests check the serialized order (`custom_id`, SKU, amount, `intent: CAPTURE`), 422 to `PayPalError` to our 409, token failure to `PayPalError(401)`, that mock mode never builds an SDK client, and that create and capture send a stable `PayPal-Request-Id` across a retry. |

### What the plugin changed in our client

Four concrete decisions, each checked against the code on this branch and the installed SDK 2.4.0 source
(`.venv/lib/python3.12/site-packages/paypalserversdk/`).

1. **Pinned SDK 2.4.0.** `pyproject.toml:15` has `"paypal-server-sdk==2.4.0"` (exact pin, also in `uv.lock`).
   The skills describe this exact build, so a floating version could silently change parameter names under us.
2. **20 s timeout instead of the SDK's 60 s default.** The SDK's `Configuration.__init__` defaults to
   `timeout=60` (`paypalserversdk/configuration.py:112`). We pass `timeout=TIMEOUT`
   (`backend/api/paypal_client.py:89`) with `TIMEOUT = 20` (`backend/api/paypal_client.py:31`), the same
   value the webhook and token httpx calls use (`:111`, `:192`). A checkout at a till should fail fast, not
   hang for a minute.
3. **No retries under the caller on create/capture.** `max_retries=0` is passed explicitly
   (`backend/api/paypal_client.py:90`). The SDK's default is already 0, and its default retry methods are
   only GET and PUT (`paypalserversdk/configuration.py:112,117-118`), so a POST create or capture would not be
   retried anyway; we pin it so a later change to the client config can't turn on silent POST retries.
4. **Idempotency keys on create and capture (PayPal-Request-Id).** Both operations take
   `paypal_request_id` in their `options` dict and send it as the `PayPal-Request-Id` header
   (`paypalserversdk/controllers/orders_controller.py:103-104` for create, `:624-625` for capture; the
   docstring says PayPal stores keys for 6 hours). We send:
   - create: `create-<verification id>` (`backend/api/paypal_client.py:159-160`). The verification ID is
     what we put in `custom_id`, and the checkout gate passes it in (`backend/api/main.py:93-94`). One brand
     verification can therefore produce at most one PayPal order, even if the create is resent.
   - capture: `capture-<order id>` (`backend/api/paypal_client.py:170-171`). A resent capture of the same
     order gets PayPal's stored result for that key instead of a second charge.

   `get_order` sends no key. Tests: `tests/test_paypal_client.py:191` (same key on both rounds of a
   create + capture retry, a different key for a different verification) and `:213` (no key on GET).
   Mock mode (`PAYPAL_MODE=mock`) is unchanged: it returns before any SDK call.

### What uses the SDK and what still uses httpx

| Call | Path | Why |
|---|---|---|
| Create order | SDK `orders.create_order` | Covered by the SDK. Only after the brand returns VERIFIED; blocked checkouts never create an order. |
| Get order | SDK `orders.get_order` | Covered by the SDK. |
| Capture order | SDK `orders.capture_order` | Covered by the SDK. |
| OAuth token for the above | SDK (`ClientCredentialsAuth`) | Fetched and refreshed by the SDK. |
| Webhook signature check (`POST /v1/notifications/verify-webhook-signature`) | httpx | The SDK has no Notifications/Webhooks controller (it covers Orders, Payments, Vault, Subscriptions, Transaction Search, OAuth). |
| Browser client token (`POST /v1/oauth2/token` with `response_type=client_token`, `domains[]`), in `backend/api/paypal_sdk.py` | httpx | The SDK's `o_auth_authorization.request_token` is the plain client-credentials token call. The client-token fields are not modelled; they would go through an untyped extra-form-params argument with a hand-built Basic auth header, which is no clearer than the direct call. |

`PAYPAL_MODE=mock` is unchanged: no network, no SDK client, orders kept in memory.
