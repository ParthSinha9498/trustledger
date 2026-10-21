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
| `python-calling-endpoints` | Orders operations take a single `options` dict: `orders.create_order({"body": OrderRequest(...)})`, `orders.get_order({"id": ...})`, `orders.capture_order({"id": ...})`. Responses are `ApiResponse` envelopes. |
| `python-models` | The request is built from typed models: `OrderRequest`, `CheckoutPaymentIntent.CAPTURE`, `PurchaseUnitRequest(custom_id=<verification id>, ...)`, `AmountWithBreakdown` + `AmountBreakdown(item_total=Money(...))`, `ItemRequest`. Callers get PayPal's JSON as a plain dict (`json.loads(response.text)`), which avoids the "optional attribute is absent, not `None`" trap on response models. |
| `python-error-handling` | Errors arrive as `ApiException` (here the typed `ErrorException`), status on `.response_code`, raw body on `.response.text`. We wrap them in our own `PayPalError(status_code, body)`; the capture endpoint maps PayPal 422 to our 409 and other errors to 502. We never call `str()` on the typed exception (its `__str__` can fail on a non-JSON body). Token failures would normally surface as `AuthValidationException`, which is not an `ApiException` and hides the real status, so we pass an `o_auth_token_provider` that calls `fetch_token()` directly: a bad credential becomes `PayPalError(401)` with PayPal's body. |
| `python-configuration-resilience` | Defaults read from `Configuration.__init__`: `timeout=60`, `max_retries=0`, retries only for GET/PUT. We set `timeout=20` (what the old code used) and keep `max_retries=0`, because creating and capturing an order are not idempotent. |
| `python-testing` | `tests/test_paypal_client.py` runs the real SDK offline: a `requests.Session` with a route-table adapter is passed as `http_client_instance`, an `HttpCallBack` records every request (the OAuth token POST included, so we select by path), and the token path answers 200. Tests check the serialized order (`custom_id`, SKU, amount, `intent: CAPTURE`), 422 to `PayPalError` to our 409, token failure to `PayPalError(401)`, and that mock mode never builds an SDK client. |

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
