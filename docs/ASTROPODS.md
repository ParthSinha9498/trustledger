# Astropods Deployment & Integration Guide

TrustLedger packages its autonomous supply-chain divergence investigation agent as an [Astropods](https://astropods.com) blueprint (`astropods.yml`), allowing it to run as a hosted, monitored service with streaming chat interfaces, AI Gateway proxying, and distributed OpenTelemetry tracing.

---

## 1. Architecture Overview

The Astropods integration wraps TrustLedger's multi-step investigation loop using the `astropods-adapter-core` Python protocol:

```
┌────────────────────────────────────────────────────────┐
│                   Astropods Platform                   │
│                                                        │
│   Web / Messaging UI  ◄──►  Sidecar (gRPC :9090)       │
│                                    ▲                   │
│                                    │ streaming events  │
│                                    ▼                   │
│                        TrustLedger Investigator        │
│                        (backend.worker.astro)          │
│                                    │                   │
│     ┌──────────────────────────────┼─────────────────┐ │
│     ▼                              ▼                 ▼ │
│ AI Gateway                   OTLP Traces        Backend│
│ (Claude Haiku / Sonnet)      (Jaeger / OTEL)    Nodes  │
└────────────────────────────────────────────────────────┘
```

### Components
- **Blueprint Spec (`astropods.yml`)**: Declares `spec: blueprint/v1`, package metadata, models (`claude-haiku-4-5`, `claude-sonnet-4-6`), inputs (`API_URL`, `BRAND_NODE_URL`, `PAYPAL_NODE_URL`, `NODE_SHARED_TOKEN`), and web messaging adapter.
- **Worker Container (`docker/astro.Dockerfile`)**: Minimal Python 3.12 image packaging `backend/`, dependencies, and the `astropods-adapter-core` runtime with OpenTelemetry instrumentation.
- **Adapter Entrypoint (`backend/worker/astro.py`)**:
  - Implements `Investigator` adhering to the `AgentAdapter` duck-typed protocol (`stream(prompt, hooks, options)`).
  - Connects to the local Astropods messaging sidecar (`GRPC_SERVER_ADDR`, default `localhost:9090`).
  - Claims cases via TrustLedger Platform API (`POST /internal/cases/claim` or `GET /cases/{id}`).
  - Maps investigation lifecycle events to streaming status updates (`hooks.on_status_update`) and markdown response chunks (`hooks.on_chunk`).

---

## 2. Privacy & Data Protection Safeguards

Because the agent runs in Astropods' managed cloud and sends requests through the AI Gateway, TrustLedger implements multi-layered privacy guardrails:

1. **Buyer-Level Field Scrubbing (`BLOCKED_KEYS`)**:
   - Keys identifying buyers or specific transactions (`payer_ref`, `payer_id`, `buyer_id`, `email`, `phone`, `name`, `address`, `order_id`, `serial`, `transaction_id`) are recursively scrubbed by `scrub()` before tool results reach the LLM or chat stream.
2. **Span Content Masking (`TRACELOOP_TRACE_CONTENT=false`)**:
   - OpenTelemetry span payloads never contain prompt or completion text.
   - Per-tool spans (`tool.<name>`) only record operational metadata (e.g., `trustledger.case_id`, `trustledger.refused`, `trustledger.rows`), never raw cell values.
3. **Differential Privacy Preserved**:
   - The agent only queries brand aggregate endpoints and PayPal Differential Privacy query endpoints (`/v1/query`), consuming noisy counts within the configured epsilon budget ($\varepsilon$).

---

## 3. Local Development (`ast project start`)

You can run and test the Astropods agent locally alongside the local TrustLedger stack.

### Prerequisites
- Docker running locally.
- Astropods CLI installed:
  ```bash
  curl -fsSL https://astropods.com/install | sh
  ast --version
  ```

### Running Locally
1. Start the TrustLedger backend services (`api` on 8000, `brand_node` on 8001, `paypal_node` on 8002).
2. Launch the Astropods project environment:
  ```bash
  ast project start
  ```
3. Open the local chat adapter interface at **http://localhost:3100**.

### Chat Commands
- **`next`**: Claims the oldest pending case in the queue, runs the autonomous investigation loop, logs step-by-step tool executions, and returns the final divergence verdict.
- **`investigate <case_id>`** (e.g. `investigate case_demo01`): Re-runs the investigation on an existing case.

---

## 4. Cloud Deployment

### Step 1: Authentication
Authenticate the CLI with your Astropods account:
```bash
ast login
ast whoami
```

### Step 2: Push Blueprint
Push the blueprint to your Astropods blueprint registry:
```bash
ast blueprint push trustledger-investigator
```

### Step 3: Configure Environment & Secrets
Store secrets in the Astropods vault or provide them during deployment:
- `API_URL`: Public or tunneled URL for TrustLedger Platform API.
- `BRAND_NODE_URL`: Internal or tunneled URL for Brand Node.
- `PAYPAL_NODE_URL`: Internal or tunneled URL for PayPal DP Node.
- `NODE_SHARED_TOKEN`: Shared bearer authentication token (`secret: true`).

### Step 4: Deploy Agent
Deploy the container instance:
```bash
ast blueprint deploy trustledger-investigator
```

Verify deployment status:
```bash
ast agent list
```

---

## 5. Observability & Tracing

When deployed, Astropods injects `OTEL_EXPORTER_OTLP_ENDPOINT` and `ASTRO_GATEWAY_URL`:
- **AI Gateway**: Directs OpenAI-compatible completions to `https://api.astropods.com/v1`, tracking token counts, latency, and costs per investigation.
- **OTLP Traces**: Pushes hierarchical spans for `tool.query_brand_timeline`, `tool.query_paypal_sales`, `tool.query_brand_shipments`, etc.
- **Insights Dashboard**: Inspect live execution graphs, tool refusal rates, and agent reasoning step-by-step in the Astropods Web Console.
