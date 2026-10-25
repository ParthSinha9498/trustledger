# How we used APIMatic

Full detail (which Context Plugin skill decided what, and which calls stay on plain REST): [`docs/APIMATIC.md`](../APIMATIC.md).

## What it does in TrustLedger
Authenticity is a condition of payment: the PayPal order is created only after the brand answers VERIFIED, and it
stores the verification ID in `custom_id`. Those PayPal Orders v2 calls (create, get, capture) go through the
APIMatic-generated **PayPal Server SDK** for Python (`paypal-server-sdk==2.4.0`, import package `paypalserversdk`).
We wrote that integration with APIMatic's **PayPal Context Plugin**, which gave the coding agent skills tied to this exact
SDK build (client setup, auth, calling endpoints, models, error handling, resilience, testing).

## Where
- Dependency pin: [`pyproject.toml:15`](../../pyproject.toml).
- SDK imports: [`backend/api/paypal_client.py:15-25`](../../backend/api/paypal_client.py).
- One long-lived `PaypalServersdkClient`, built on first use and never in mock mode, explicit sandbox/production
  environment, `max_retries=0` because create and capture are not idempotent: `paypal_client.py:79-92`.
- Typed order request (`OrderRequest`, `PurchaseUnitRequest(custom_id=...)`, `AmountWithBreakdown`, `ItemRequest`):
  `paypal_client.py:142-155`. Get and capture: lines 157-168.
- SDK errors (`ApiException`) wrapped into our own `PayPalError`: `paypal_client.py:95-101`.
- The checkout gate that calls `create_order` only after VERIFIED: [`backend/api/main.py:72-98`](../../backend/api/main.py).
- Offline tests that run the real SDK against a route-table HTTP adapter (no network) (serialized `custom_id`, SKU, amount,
  `intent: CAPTURE`, error mapping, mock mode never builds a client): [`tests/test_paypal_client.py`](../../tests/test_paypal_client.py).

## What we built on top
- A mock mode (`PAYPAL_MODE=mock`) with the same method signatures, so the app and the test suite run with no keys
  (`paypal_client.py:126-140, 158-167`).
- A token provider that surfaces a bad credential as `PayPalError(401)` with PayPal's body instead of a generic auth error
  (see the `python-error-handling` row in `docs/APIMATIC.md`).

- To exercise the SDK path end to end: set `PAYPAL_MODE=sandbox` with sandbox keys and run
  [`e2e/happy_path.py`](../../e2e/happy_path.py) (creates, approves and captures a sandbox order).

## What is not APIMatic
- Webhook signature verification and the browser client token use direct REST (httpx), because the SDK has no
  notifications controller and does not model the client-token fields (`paypal_client.py:170` onward, `backend/api/paypal_sdk.py`).
- We have not generated an SDK or a developer portal for TrustLedger's own API with APIMatic. Our OpenAPI spec is in
  [`openapi/`](../../openapi/).

## Screenshots
- [`docs/media/01_pos_verified.png`](../media/01_pos_verified.png): a verified checkout (taken in mock mode; in sandbox mode this is where
  the SDK creates the PayPal order with the verification ID in `custom_id`).
- [`docs/media/02_pos_blocked.png`](../media/02_pos_blocked.png): a blocked checkout; no SDK call is made and no order exists.
