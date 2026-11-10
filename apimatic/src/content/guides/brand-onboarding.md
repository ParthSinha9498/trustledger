# Brand onboarding

TrustLedger makes product authenticity a condition of payment. When a cashier, a web shop or an AI
shopping agent is about to sell a serialized product, the checkout platform first asks **the brand**:
may this unit be sold at this store? Only a `VERIFIED` answer leads to a PayPal order. Anything else
means no order is created.

To take part, a brand runs one small service that implements two endpoints.

## What you implement

| Endpoint | When it is called | What you do |
| --- | --- | --- |
| `POST /v1/verify` | A product is scanned, before any payment exists | Answer `VERIFIED` or `NOT_VERIFIED` with a reason code |
| `POST /v1/verify/{verification_id}/confirm` | After the PayPal capture completes | Mark the serial sold. Must be idempotent |

How you decide is your own business logic, run against your own serial and distribution data. That data
never leaves your service: the platform only ever sees the verdict.

## Reason codes

Always answer `200` for a well-formed request, including for serials you never issued.

| `reason_code` | Meaning |
| --- | --- |
| `null` | `VERIFIED`: you stand behind this unit being sold at this store |
| `UNKNOWN_SERIAL` | You never issued this serial |
| `SKU_MISMATCH` | The serial belongs to a different product |
| `NOT_IN_CHANNEL` | This store is not in the serial's supply chain. Check this before `ALREADY_SOLD`, so a clone at the wrong store fails even before the genuine unit sells |
| `ALREADY_SOLD` | The serial was already sold |

Reason codes must never reveal which store a serial belongs to.

## Authentication

TrustLedger sends a shared secret in the `X-Node-Token` header on every call. Reject a missing or wrong
token with `401`.

## Try it

Against the reference brand (Nimbus, fictional) running locally on port 8001:

```bash
curl -s http://localhost:8001/v1/verify \
  -H "X-Node-Token: $NODE_SHARED_TOKEN" -H "Content-Type: application/json" \
  -d '{"serial":"X123","sku":"NMB-P8-128","store_id":"store_b"}'
# {"verification_id":"ver_…","result":"NOT_VERIFIED","reason_code":"NOT_IN_CHANNEL"}
```

The same API is available to AI agents through an MCP server, and through the SDKs on this portal.
