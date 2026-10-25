# TrustLedger Free-Plan Deployment Guide (Render + Neon)

This guide walks through deploying TrustLedger completely free of charge on [Render](https://render.com) and [Neon](https://neon.tech) using the free-tier Blueprint specification (`render.yaml`).

---

## 1. Free Architecture Overview

Render's Free plan offers web services but no background workers or private network services. TrustLedger accommodates this constraint via an all-in-one backend container (`docker/all_in_one.sh`):

```
                        ┌─────────────────────────┐
                        │   Internet / End Users  │
                        └────────────┬────────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                ▼                                         ▼
    ┌───────────────────────┐                 ┌───────────────────────┐
    │    trustledger-web    │                 │  trustledger-backend  │
    │   (Next.js Frontend)  ├────────────────►│ (All-in-One Container)│
    │      Plan: free       │                 │      Plan: free       │
    └───────────────────────┘                 └───────────┬───────────┘
                                                          │
                       ┌──────────────────────────────────┴──────────────────────────────────┐
                       │                   Container Localhost Isolation                     │
                       │                                                                     │
                       │   api (FastAPI)       0.0.0.0:$PORT    (PLATFORM_DATABASE_URL only) │
                       │   brand-node          127.0.0.1:8001   (BRAND_DATABASE_URL only)    │
                       │   paypal-node (DP)    127.0.0.1:8002   (PAYPAL_DATABASE_URL only)   │
                       │   worker (Agent)      HTTP to above    (No database credentials)    │
                       └──────────────┬───────────────────┬───────────────────┬──────────────┘
                                      │                   │                   │
                                      ▼                   ▼                   ▼
                               ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                               │    brand    │     │ paypal_side │     │  platform   │
                               │ (Postgres)  │     │ (Postgres)  │     │ (Postgres)  │
                               └─────────────┘     └─────────────┘     └─────────────┘
                                        External Managed Postgres (Neon Free Tier)
```

### Process Credential Isolation
Inside `trustledger-backend`, process supervision (`docker/all_in_one.sh`) launches each service with strict credential filtering using `env -u`:
- **API**: holds only `PLATFORM_DATABASE_URL`.
- **Brand Node**: bound to `127.0.0.1:8001` (never exposed externally); holds only `BRAND_DATABASE_URL`.
- **PayPal DP Node**: bound to `127.0.0.1:8002` (never exposed externally); holds only `PAYPAL_DATABASE_URL`.
- **Worker**: communicates purely over HTTP using `NODE_SHARED_TOKEN`; holds **no database credentials at all**.

---

## 2. Step 1: Create 3 Postgres Databases on Neon

A free Render Postgres instance expires automatically after 30 days. Because hackathon evaluation and judging runs from Dec 1–15, managed databases should be created outside Render to avoid data loss.

[Neon](https://neon.tech) provides a generous free tier with permanent Postgres databases:

1. Sign up for free at [neon.tech](https://neon.tech) and create a project (e.g. `trustledger`).
2. In the Neon Console, navigate to **Databases** and create 3 logical databases within the same project:
   - `trustledger_brand` (or `brand`)
   - `trustledger_paypal_side` (or `paypal_side`)
   - `trustledger_platform` (or `platform`)
3. Copy the **direct (non-pooled)** connection strings (e.g. `postgres://user:password@ep-...neon.tech/<dbname>?sslmode=require`) for each database:
   - `BRAND_DATABASE_URL`
   - `PAYPAL_DATABASE_URL`
   - `PLATFORM_DATABASE_URL`

> [!IMPORTANT]
> **Use Direct, Non-Pooled Connection Strings:** Do **not** use Neon's `-pooler` connection strings. TrustLedger uses `psycopg 3`, which automatically switches to server-side prepared statements after 5 executions. PgBouncer transaction pooling does not maintain prepared statements across connections, leading to `prepared statement "..." does not exist` errors. Keep `?sslmode=require`.

> [!NOTE]
> Neon's free compute automatically suspends after ~5 minutes of idle time. The first database query after compute sleep adds approximately 1–2 seconds of latency while the compute warms up.

---

## 3. Step 2: Deploy to Render via Blueprint

1. Sign in to [Render](https://dashboard.render.com).
2. Click **New +** > **Blueprint**.
3. Connect your GitHub repository (`trustledger`) and select the `main` branch.
4. Render parses `render.yaml` and provisions two free web services:
   - `trustledger-web`
   - `trustledger-backend`
5. Fill in the required environment variables marked with `sync: false`:

| Variable | Service | Value / Source |
|---|---|---|
| `BRAND_DATABASE_URL` | `trustledger-backend` | Direct connection string for brand database from Step 1 |
| `PAYPAL_DATABASE_URL` | `trustledger-backend` | Direct connection string for PayPal DP database from Step 1 |
| `PLATFORM_DATABASE_URL`| `trustledger-backend` | Direct connection string for platform database from Step 1 |
| `PAYPAL_CLIENT_ID` | `trustledger-backend` | PayPal REST App Client ID (developer.paypal.com sandbox) |
| `PAYPAL_CLIENT_SECRET`| `trustledger-backend` | PayPal REST App Secret |
| `PAYPAL_WEBHOOK_ID` | `trustledger-backend` | *(Leave blank initially; set after Step 4 below)* |
| `LLM_API_KEY` | `trustledger-backend` | Groq API Key (free at console.groq.com) or Gemini API Key |
| `NEXT_PUBLIC_PAYPAL_CLIENT_ID` | `trustledger-web` | PayPal Sandbox Client ID (loaded in browser SDK) |

Optional, for the one-click **Pay with test card (sandbox)** button on the pay page. These are not in `render.yaml`, so add
them by hand under `trustledger-backend` > **Environment**. Use a PayPal sandbox test card
(https://developer.paypal.com/tools/sandbox/card-testing/), never a real card. Without the first two the button is hidden
and judges pay with the sandbox buyer login.

| Variable | Service | Value / Source |
|---|---|---|
| `SANDBOX_TEST_CARD_NUMBER` | `trustledger-backend` | Sandbox test card number |
| `SANDBOX_TEST_CARD_EXPIRY` | `trustledger-backend` | Its expiry, `YYYY-MM` |
| `SANDBOX_TEST_CARD_CVV` | `trustledger-backend` | Its CVV (optional) |

6. Click **Apply**. Render will build and deploy both services.

---

## 4. Step 3: Automatic Database Seeding & Demo Reset

TrustLedger handles database initialization automatically on container boot:
- **`SEED_ON_START=auto`** (Default): On boot, `docker/all_in_one.sh` inspects `to_regclass('public.stores')` on `PLATFORM_DATABASE_URL`. If the database is empty, it runs `docker/seed.py`, creating all schemas and populating fictional demonstration data (Nimbus brand catalog, stores, distributors, and initial serials). If already seeded, it skips to preserve active state.
- **`SEED_ON_START=always`** (One-Off Demo Reset): Wipes and reseeds demo fixtures on boot.
  > [!WARNING]
  > Because Render Free web services spin down and restart on every cold start (after 15 minutes of inactivity), leaving `SEED_ON_START=always` permanently configured would wipe the database every time the service wakes up—including during evaluation! To reset the demo: change `SEED_ON_START` to `always`, let one deploy finish, and then immediately change it back to `auto`.
- **`SEED_ON_START=never`**: Bypasses any seed check.

---

## 5. Step 4: Configure PayPal Webhook

1. Open your [PayPal Developer Sandbox Dashboard](https://developer.paypal.com/dashboard/applications/sandbox).
2. Select your REST API application and navigate to **Webhooks** > **Add Webhook**.
3. Enter the webhook URL pointing to your deployed backend service:
   ```
   https://<trustledger-backend-host>.onrender.com/paypal/webhooks
   ```
4. Subscribe to the following event types:
   - `CHECKOUT.ORDER.APPROVED`
   - `PAYMENT.CAPTURE.COMPLETED`
5. Save the webhook and copy the generated **Webhook ID**.
6. In Render, edit environment variables for `trustledger-backend`:
   - Set `PAYPAL_WEBHOOK_ID` to the copied Webhook ID.
7. Click **Save Changes** (Render will automatically redeploy with the webhook secret active).

---

## 6. Cold Starts & Pre-Demo Warming

Render's Free tier spins down web services after 15 minutes of inactivity:
- **Cold start behavior:** If sleeping, the first incoming request takes approximately 50–70 seconds while the container initializes, checks the database seed, and spins up Uvicorn and Next.js. Subsequent requests respond instantly.
- **Pre-demo warming:** Before conducting a live demo or presentation, send a ping request to both services to warm them up:
  ```bash
  curl -I https://<trustledger-backend-host>.onrender.com/health
  curl -I https://<trustledger-web-host>.onrender.com/
  ```

---

## 7. LLM Provider Quotas & Judging Readiness

TrustLedger defaults to Groq's OpenAI-compatible endpoint (`openai/gpt-oss-120b` or `llama-3.3-70b-versatile`):
- **Free Tier Quota:** Groq allows approximately 200,000 tokens per day (sufficient for ~4 full multi-turn agent investigations).
- **Zero Cost for Case Browsing:** Completed investigations are stored with all citations and step timelines in the PostgreSQL database. Browsing cases, reviewing findings, and running console queries on cached cells consumes zero LLM tokens.
- **Deduplication:** Subsequent scans of known failed serials join existing cases without re-triggering the investigation agent.
- **Tip for Judging:** Trigger a Store C scan once prior to judging so that at least one complete investigation case is pre-seeded and immediately viewable.

---

## 8. Verification Checklist

1. **Backend Health Check:**
   - `https://<trustledger-backend-host>.onrender.com/health` returns `{"ok": true, "paypal_mode": "sandbox"}`.
2. **Store A Legitimate Checkout:**
   - Visit `https://<trustledger-web-host>.onrender.com/pos`.
   - Scan Store A with serial `X123`. Verify: brand verified badge, PayPal checkout button active.
   - To complete payment, sign in with a **PayPal sandbox buyer account** (create one at `developer.paypal.com` → Sandbox → Accounts).
3. **Store C Rejection & Case Creation:**
   - Scan Store C with serial `X123`. Verify: checkout blocked with `NOT_IN_CHANNEL`, PayPal order prevented, investigation opened.
4. **Brand Cockpit & Bryntum Timeline:**
   - Visit `/cockpit`: open case displayed in AG Grid with status and confidence score.
   - Click case detail: multi-turn agent tool executions, findings, and Bryntum supply timeline.
