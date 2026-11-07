# TrustLedger Deployment Guide (Render)

**Status:** not live yet. `render.yaml` is written; the first Render deploy is planned. Until a hosted URL is published, run the stack locally with Docker Compose (see the README).

This guide uses the Render Blueprint in `render.yaml`.

---

## 1. Hosting Today

| Service | Type | Plan today | Contents |
|---|---|---|---|
| `trustledger-web` | web (Docker, `docker/web.Dockerfile`) | Render free | Next.js app |
| `trustledger-backend` | web (Docker, `docker/backend.Dockerfile`) | Render free | One container, four processes (`docker/all_in_one.sh`) |
| `trustledger-db` | Render Postgres | `plan: free` in `render.yaml` | One instance, three logical databases |

- **Database plan:** `render.yaml` currently sets `plan: free` on `trustledger-db`. Its header comment says Basic-256mb. A paid Postgres Basic-256mb is **planned for 9 Nov** and is not in place yet.
- **Sleep:** Render free web services spin down after inactivity. The web app shows **"Waking the demo (~1 min)"** while the backend starts (`web/components/ColdStartNotice.tsx`).

### Process layout inside `trustledger-backend`

`docker/all_in_one.sh` runs four processes. Each gets only the credentials it needs (`env -u`):

| Process | Listens on | Database access |
|---|---|---|
| api (FastAPI) | `0.0.0.0:$PORT` (public) | `PLATFORM_DATABASE_URL` only |
| brand-node | `127.0.0.1:8001` (not public) | `BRAND_DATABASE_URL` only |
| paypal-node (DP) | `127.0.0.1:8002` (not public) | `PAYPAL_DATABASE_URL` and `PAYER_HASH_KEY` only |
| worker (agent) | no listener; calls the three above over HTTP | none |

If any process exits, the container exits and Render restarts it.

---

## 2. Databases

The one Postgres instance holds three logical databases: `platform`, `brand`, `paypal_side`.

1. Create the two extra databases on the instance (Render dashboard, `psql`, or the instance shell):
   ```sql
   CREATE DATABASE brand;
   CREATE DATABASE paypal_side;
   ```
2. Connection strings:
   - `PLATFORM_DATABASE_URL`: linked from `trustledger-db` by `render.yaml`.
   - `BRAND_DATABASE_URL`: the same URL with the database name changed to `brand`.
   - `PAYPAL_DATABASE_URL`: the same URL with the database name changed to `paypal_side`.

---

## 3. Deploy with the Blueprint

1. In the Render dashboard, click **New +** > **Blueprint**.
2. Connect the GitHub repository and select the branch to deploy.
3. Render reads `render.yaml` and creates `trustledger-db`, `trustledger-web` and `trustledger-backend`.
4. Fill in the variables marked `sync: false` (Render prompts for them, or set them under **Environment**):

| Variable | Service | Value / source |
|---|---|---|
| `PLATFORM_DATABASE_URL` | `trustledger-backend` | Linked automatically from `trustledger-db` |
| `BRAND_DATABASE_URL` | `trustledger-backend` | Connection string for `brand` (section 2) |
| `PAYPAL_DATABASE_URL` | `trustledger-backend` | Connection string for `paypal_side` (section 2) |
| `PAYPAL_CLIENT_ID` | `trustledger-backend` | PayPal sandbox REST app client ID |
| `PAYPAL_CLIENT_SECRET` | `trustledger-backend` | PayPal sandbox REST app secret |
| `PAYPAL_WEBHOOK_ID` | `trustledger-backend` | Leave blank first; set in section 5 |
| `LLM_API_KEY` | `trustledger-backend` | Key for the provider set in `LLM_BASE_URL` (section 4) |
| `LLM_FALLBACK_API_KEY` | `trustledger-backend` | Key for the fallback provider |
| `SANDBOX_TEST_CARD_NUMBER` | `trustledger-backend` | Sandbox test card number (optional, see below) |
| `SANDBOX_TEST_CARD_EXPIRY` | `trustledger-backend` | Its expiry, `YYYY-MM` (optional) |
| `SANDBOX_TEST_CARD_CVV` | `trustledger-backend` | Its CVV (optional) |
| `NOTIFY_WEBHOOK_URL` | `trustledger-backend` | Optional Zapier or Slack hook; blank disables alerts |
| `NEXT_PUBLIC_PAYPAL_CLIENT_ID` | `trustledger-web` | PayPal sandbox client ID for the browser SDK |

The generated values (`NODE_SHARED_TOKEN`, `PAYER_HASH_KEY`) are created by Render from `render.yaml`.

**Pay with test card (sandbox):** the one-click button on the pay page appears only when both `SANDBOX_TEST_CARD_NUMBER` and `SANDBOX_TEST_CARD_EXPIRY` are set. Use a PayPal sandbox test card from https://developer.paypal.com/tools/sandbox/card-testing/, never a real card. Without them, the pay page still offers the PayPal button, and you pay with a PayPal sandbox buyer login.

5. Click **Apply**. Render builds and deploys both services.

---

## 4. LLM Provider

- **Default in `.env.example`:** any OpenAI-compatible endpoint; the default is Google's Gemini endpoint (`LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`, `AGENT_MODEL=gemini-3.5-flash`).
- **Current `render.yaml`:** sets `LLM_BASE_URL` to Groq (`https://api.groq.com/openai/v1`, `AGENT_MODEL=openai/gpt-oss-120b`) with Gemini as the fallback (`LLM_FALLBACK_*`). A Render deploy uses these values unless you change them in the dashboard.
- **Capacity:** if the provider has no capacity, the case shows a waiting-for-capacity state with the reason and is retried later.

---

## 5. Seeding

On boot, `docker/all_in_one.sh` reads `SEED_ON_START`:

- **`auto`** (value set in `render.yaml`): seeds only if the platform database is empty (it checks for the `stores` table). Otherwise it leaves the data alone.
- **`always`**: reseeds on every container start. Use it for one deploy to reset the demo, then set it back to `auto`. Left on permanently, every cold start would wipe the data.
- **`never`**: never seeds.

To reset the demo before submission or judging: set `SEED_ON_START=always` on `trustledger-backend`, let it deploy, then set `auto` again.

Reseed before each demo: the demo serial `X123` is used up by a completed Store A sale, and the walkthrough depends on the seeded state.

---

## 6. PayPal Webhook

1. In the PayPal Developer Dashboard (sandbox), open your REST app and choose **Webhooks** > **Add Webhook**.
2. URL: `https://<trustledger-backend-host>.onrender.com/paypal/webhooks`
3. Subscribe to `CHECKOUT.ORDER.APPROVED` and `PAYMENT.CAPTURE.COMPLETED` (the two events the handler in `backend/api/main.py` processes).
4. Copy the Webhook ID into `PAYPAL_WEBHOOK_ID` on `trustledger-backend` and save. Render redeploys.

---

## 7. Checks After Deploy

1. **Health:** `https://<trustledger-backend-host>.onrender.com/health` returns `{"ok": true, "paypal_mode": "sandbox"}` (`backend/api/main.py`).
2. **Store A checkout:** open `/pos`, select Store A, scan `X123` (or fill an unsold unit). Verification succeeds and the pay page opens.
3. **Store C block:** on `/pos`, select Store C and scan `X123`. The check returns `NOT_IN_CHANNEL`, no PayPal order is created, and an investigation case opens.
4. **Cockpit:** `/cockpit` lists the case; `/cockpit/cases/<id>` shows the agent steps and the supply-chain timeline.

Warm both services before a live demo:

```bash
curl -I https://<trustledger-backend-host>.onrender.com/health
curl -I https://<trustledger-web-host>.onrender.com/
```
