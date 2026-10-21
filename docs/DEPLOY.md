# TrustLedger Deployment Guide (Render Blueprint)

This guide documents deploying TrustLedger to [Render](https://render.com) using Infrastructure as Code via `render.yaml` (Render Blueprint specification).

---

## 1. Blueprint Architecture

The TrustLedger platform deploys as an isolated multi-service cluster defined in `render.yaml`:

```
                       ┌─────────────────────────┐
                       │   Internet / End Users  │
                       └────────────┬────────────┘
                                    │
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
   ┌───────────────────────┐                 ┌───────────────────────┐
   │    trustledger-web    │                 │    trustledger-api    │
   │   (Public Web App)    ├────────────────►│ (FastAPI Platform API)│
   │        Next.js        │                 │ (Public + Webhooks)   │
   └───────────────────────┘                 └───────────┬───────────┘
                                                         │ Private Network
                       ┌─────────────────────────────────┼─────────────────────────┐
                       ▼                                 ▼                         ▼
           ┌───────────────────────┐         ┌───────────────────────┐ ┌───────────────────────┐
           │trustledger-brand-node │         │trustledger-paypal-node│ │  trustledger-worker   │
           │(Private Brand Service)│         │ (Private DP Service)  │ │ (Investigation Agent) │
           └───────────┬───────────┘         └───────────┬───────────┘ └───────────┬───────────┘
                       │                                 │                         │
                       ▼                                 ▼                         │
           ┌───────────────────────┐         ┌───────────────────────┐             │
           │  trustledger-brand-db │         │ trustledger-paypal-db │             │
           │      (Postgres)       │         │      (Postgres)       │             │
           └───────────────────────┘         └───────────────────────┘             │
                       ▲                                                           │
                       │             ┌───────────────────────┐                     │
                       └─────────────┤   trustledger-seed    │◄────────────────────┘
                                     │  (Admin Cron / Init)  │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │trustledger-platform-db│
                                     │      (Postgres)       │
                                     └───────────────────────┘
```

### Services & Resources

| Service / Resource | Type | Exposure | Description |
|---|---|---|---|
| `trustledger-web` | Web Service | Public | Next.js frontend UI (`/pos`, `/cockpit`, `/cockpit/console`, `/receipt/[id]`) |
| `trustledger-api` | Web Service | Public | Platform API, case management, and PayPal webhook listener (`/paypal/webhooks`) |
| `trustledger-brand-node` | Private Service | Private | Mock brand endpoint for serial authentication and internal brand aggregates |
| `trustledger-paypal-node` | Private Service | Private | Differential privacy query engine backed by OpenDP |
| `trustledger-worker` | Background Worker | Private | Autonomous multi-step case investigation agent |
| `trustledger-seed` | Cron / Job | Admin | Database migration and seeding job (`docker/seed.py`) |
| `3 x Render Postgres` | Database | Private | Three isolated database instances (`brand`, `paypal_side`, `platform`) |

---

## 2. Prerequisites & Setup

### Step 1: Connect Repository to Render
1. Sign in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** > **Blueprint**.
3. Connect your GitHub repository (`trustledger`) and select the branch to deploy (`main`).
4. Render automatically parses `render.yaml` and lists the 6 services and 3 databases.

---

## 3. Environment Variables Configuration

`render.yaml` automatically generates internal credentials (such as `NODE_SHARED_TOKEN`) and injects cross-service hostnames via Render's service discovery. You only need to populate external credentials (`sync: false`):

### `trustledger-api`
- `PAYPAL_MODE`: Set to `sandbox` (default) or `live`.
- `PAYPAL_CLIENT_ID`: PayPal REST App Client ID from developer.paypal.com.
- `PAYPAL_CLIENT_SECRET`: PayPal REST App Secret.
- `PAYPAL_WEBHOOK_ID`: *(Leave blank initially; set after registering webhook below)*.
- `LLM_MODE`: Set to `live` (for live Gemini/Groq model) or `mock` (deterministic test fixtures).
- `LLM_API_KEY`: Google Gemini API key or Groq API key.
- `LLM_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/` (default for Gemini OpenAI compatibility).
- `AGENT_MODEL`: `gemini-3.5-flash` or `gemini-1.5-flash`.
- `NOTIFY_WEBHOOK_URL`: Optional Slack incoming webhook or Zapier catch hook for instant alerts.

### `trustledger-worker`
- Inherits `LLM_API_KEY`, `LLM_BASE_URL`, and `AGENT_MODEL` matching the API configuration.

### `trustledger-web`
- `NEXT_PUBLIC_PAYPAL_CLIENT_ID`: Your PayPal sandbox client ID (loaded in browser by PayPal JS SDK v6).
- `NEXT_PUBLIC_AG_GRID_LICENSE`: Optional AG Grid Enterprise key (or evaluation).

---

## 4. Database Seeding & Initialization

Render does not run database seeding on every deploy. Once the initial build finishes:

1. In the Render Dashboard, navigate to the `trustledger-seed` cron job service.
2. Click **Manual Trigger** > **Trigger Run**.
3. The job runs `python docker/seed.py`:
   - Connects to `trustledger-brand-db`, `trustledger-paypal-db`, and `trustledger-platform-db`.
   - Creates all necessary schemas and tables.
   - Populates realistic multi-tier supply chain data (Nimbus Brand, distributors, retail store accounts, test serials like `X123`).
4. You can re-trigger this job at any time to reset demo data back to clean state.

---

## 5. PayPal Webhook Configuration

To receive live payment verification and capture notifications:

1. Open your [PayPal Developer Dashboard](https://developer.paypal.com/dashboard/applications/sandbox).
2. Open your REST API application and scroll to **Webhooks**.
3. Click **Add Webhook** and configure:
   - **Webhook URL**: `https://<trustledger-api-hostname>.onrender.com/paypal/webhooks`
   - **Event types to subscribe**:
     - `CHECKOUT.ORDER.APPROVED`
     - `PAYMENT.CAPTURE.COMPLETED`
4. Save the webhook and copy the generated **Webhook ID**.
5. Back in Render, edit `trustledger-api` environment variables:
   - Set `PAYPAL_WEBHOOK_ID=<your-webhook-id>`.
6. Click **Save Changes** (Render will trigger a zero-downtime redeploy).

---

## 6. Verifying the Deployment

1. **Health Check**:
   - Visit `https://<trustledger-api-hostname>.onrender.com/health` (should return `{"status": "ok"}`).
2. **Web Portal Click-Through**:
   - Navigate to `https://<trustledger-web-hostname>.onrender.com/pos`.
   - Scan serial `X123` at Store A: verify legitimate checkout flow.
   - Scan serial `X123` at Store B: verify counterfeit refusal, case creation, and notification trigger.
3. **Investigation Cockpit**:
   - Navigate to `/cockpit` to view cases.
   - Click case detail to observe autonomous agent execution, findings, and Bryntum supply timeline.

---

## 7. Planned for Free Plan

`render.yaml` currently specifies Render paid resource tiers (`0.5c-512mb` compute and `0.1c-256mb` databases) because the hackathon evaluation window (Dec 1–15) requires persistent databases and background workers.

For developers seeking a zero-cost deployment on Render's Free tier, the following optimizations are planned:

1. **Folding the Worker into the API Service**:
   - Render's Free plan does not offer background worker instances.
   - Planned architecture will embed the `Investigation` worker loop directly inside the `trustledger-api` process using FastAPI background tasks or an `asyncio` task runner, removing `trustledger-worker` as a separate container.
2. **Single Postgres Instance Consolidation**:
   - Rather than 3 independent database instances, consolidate `trustledger_brand`, `trustledger_paypal_side`, and `trustledger_platform` onto a single managed Postgres server with 3 logical schemas.
   - Logical isolation is maintained while fitting within the free tier single-database allowance.
3. **Managing Cold Starts & 30-Day Database Expiry**:
   - Render Free web services spin down after 15 minutes of inactivity (50s cold start). Keep-alive pings can prevent spin-down during active evaluation.
   - Free Postgres databases expire after 30 days. To maintain continuous availability, use the `trustledger-seed` manual trigger to re-seed demo fixtures if a database rotates.
