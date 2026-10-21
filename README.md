# TrustLedger

**TrustLedger makes product authenticity a condition of payment.** The brand verifies a serialized product
before the PayPal order is created. Verified: the buyer pays, and the verification ID is stored in the
order's `custom_id`. Not verified: no PayPal order is ever created, and an AI agent investigates the failure
using only privacy-protected aggregates.

> **Status:** Complete implementation verified end-to-end. Checkout gate, PayPal sandbox integration, differential privacy engine (OpenDP zCDP), multi-turn investigation agent, and Next.js frontend (AG Grid, AG Charts, Bryntum Scheduler) are fully functional. Full offline test suite passing (49 tests).

## Run it

**Backend (Python 3.12, uv)**

```bash
cp .env.example .env            # mock mode needs no keys; sandbox credentials optional
docker compose up -d postgres   # Postgres 17 on localhost:5433
uv sync
uv run python -m backend.seed   # creates the three databases and loads fictional data
uv run --env-file .env uvicorn backend.brand_node.main:app --port 8001 &
uv run --env-file .env uvicorn backend.paypal_node.main:app --port 8002 &
uv run --env-file .env uvicorn backend.api.main:app --port 8000 &
uv run --env-file .env python -m backend.worker.main   # investigation agent
```

**Web (Node 22)**

```bash
cd web && npm install && npm run dev   # http://localhost:3000
```

**Everything with Docker:** `docker compose up --build`

**Tests:** `uv run pytest -q` (needs the Postgres container; uses separate `trustledger_test_*` databases)

## Try the demo

1. Open **Store checkout** (`/pos`), pick **Store A**, serial **X123**, and click verify. The brand verifies the unit, a PayPal order is created with the verification ID in `custom_id`, and customer pay options appear.
2. Pick **Store B**, same serial. It is deterministically blocked with "This product is not in this store's supply chain" (`NOT_IN_CHANNEL`). No PayPal order is ever created, and an investigation case is automatically opened.
3. Open **Brand cockpit** (`/cockpit`). The case appears in the AG Grid investigations table; the agent investigates using privacy-guarded aggregates and logs findings, citations, and steps.
4. Try the **Question console** (`/cockpit/console`) to plan or compose structured queries against the brand and PayPal nodes, observe differential privacy noise, and test cell-suppression guardrails.
5. Open **Supply chain** (`/cockpit/supply-chain`) to view batch movements, distributor holdings, store deliveries, and highlighted off-channel divergences in the Bryntum Scheduler.

## Modes

| Variable | Values | Description |
|---|---|---|
| `PAYPAL_MODE` | `mock` or `sandbox` | `mock` runs completely offline; `sandbox` calls real PayPal Orders v2 API with client credentials. |
| `LLM_MODE` | `live` or `mock` | `live` connects to an OpenAI-compatible endpoint (Gemini / Groq); `mock` runs a deterministic scripted stand-in. |
| `LLM_BASE_URL`, `AGENT_MODEL` | Provider URLs & models | Configured for Gemini (`gemini-3.5-flash`); switchable to Groq, OpenAI, or local gateways without code changes. |

## Real, Mock and Simulated Components

| Category | Component | Status | Details |
|---|---|---|---|
| **Real** | **PayPal Orders v2** | Real (Sandbox) | Server-side order creation (`intent: CAPTURE`), `custom_id` verification ID binding, client token exchange, PayPal JS SDK v6 button, capture API, and webhook signature verification. |
| **Real** | **Differential Privacy** | Real (OpenDP) | Zero-concentrated differential privacy (zCDP) Gaussian mechanism using OpenDP, per-buyer contribution bounding ($k=4$ cells, clamp 1000), persistent database budget ledger ($\rho=0.25$), query response caching (prevents noise averaging), and calculated 95% confidence intervals. |
| **Real** | **Investigation Loop** | Real / Agentic | Multi-turn agent loop with structured tool calling (`query_brand_node`, `query_paypal_node`, `record_finding`), dynamic step budgeting, and cited findings. |
| **Real** | **Web Frontend** | Real | Next.js 16 (Turbopack) & React 19 app with responsive light/dark mode, AG Grid Community investigations grid, AG Charts Community visualizations, and Bryntum Scheduler supply chain timeline. |
| **Mock** | **Brand Infrastructure** | Mock Service | In production, brands operate private serialization systems. Here, an isolated microservice (`backend/brand_node/`, port 8001) with its own database simulates the brand's private verification API and exact ERP aggregate queries. |
| **Simulated**| **Buyer Demographics** | Simulated Data | Public PayPal APIs do not expose customer demographics (age bands, gender). To demonstrate federated differential privacy on buyer data, synthetic demographic dimensions are populated in the PayPal data node. |
| **Simulated**| **Seed Data** | Simulated Dataset | All products (Nimbus P8/A5), serial numbers, distributor shipments, store sales (7,600 transactions), and planted supply chain leaks are generated fictional data. |
| **Mock** | **Offline Test Mode** | Fallback / CI | `PAYPAL_MODE=mock` and `LLM_MODE=mock` provide fully deterministic offline execution for the 49-test pytest suite without external network calls or API keys. |

All data, brands, stores, and individuals depicted are entirely fictional.

## License

MIT
