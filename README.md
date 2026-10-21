# TrustLedger

**TrustLedger makes product authenticity a condition of payment.** The brand verifies a serialized product
before the PayPal order is created. Verified: the buyer pays, and the verification ID is stored in the
order's `custom_id`. Not verified: no PayPal order is ever created, and an AI agent investigates the failure
using only privacy-protected aggregates.

> Status: skeleton. The full loop runs end to end in mock mode. See `../PLAN.md` for milestones and specs.

## Run it

**Backend (Python 3.12, uv)**

```bash
cp .env.example .env            # mock mode needs no keys
docker compose up -d postgres   # Postgres 17 on localhost:5433
uv sync
uv run python -m backend.seed   # creates the three databases and loads fictional data
uv run uvicorn backend.brand_node.main:app --port 8001 &
uv run uvicorn backend.paypal_node.main:app --port 8002 &
uv run uvicorn backend.api.main:app --port 8000 &
uv run python -m backend.worker.main   # investigation agent
```

**Web (Node 22)**

```bash
cd web && npm install && npm run dev   # http://localhost:3000
```

**Everything with Docker:** `docker compose up --build`

**Tests:** `uv run pytest` (needs the Postgres container; uses separate `trustledger_test_*` databases)

## Try the demo

1. Open **Store checkout**, pick **Store A**, serial **X123**, and scan. It verifies, a PayPal order is created, pay.
2. Pick **Store B**, same serial. It fails with "not in this store's supply chain". No PayPal order is created.
3. Open **Brand cockpit**. The case from step 2 appears; the agent's steps and findings fill in.

## Modes

| Variable | Values |
|---|---|
| `PAYPAL_MODE` | `mock` (offline) or `sandbox` (needs `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`) |
| `LLM_MODE` | `live` (any OpenAI-compatible provider) or `mock` (scripted stand-in, not the real agent) |
| `LLM_BASE_URL`, `AGENT_MODEL` | Gemini by default (`gemini-3.8-flash`); Groq works by changing these two |

## Layout

```
backend/
  api/           checkout gate, PayPal client, webhooks, cases
  brand_node/    mock brand: verification API + exact business aggregates
  paypal_node/   PayPal-side data behind differential privacy (OpenDP)
  worker/        investigation agent loop
  common/        query specs, privacy engine, LLM client, HTTP, auth
  seed.py        fictional data generator
web/             Next.js: store checkout, receipt, brand cockpit (AG Grid)
tests/           unit + end-to-end tests (mock mode)
```

## Real vs simulated

| Real | Simulated |
|---|---|
| PayPal Orders v2 create and capture (sandbox mode), `custom_id`, webhook verification | Buyer age and gender (PayPal's public API doesn't expose them) |
| Differential privacy with OpenDP, per-brand budget | Sales history, shipments, stores, buyers (all fictional) |
| | The brand's verification API (a mock brand) |

All brands, stores, cities and buyers in the seed data are fictional.

## License

MIT
