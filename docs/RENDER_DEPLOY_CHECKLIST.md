# Render One-Click Deployment Checklist (Mon Oct 26)

This checklist walks through deploying TrustLedger on Render before judges and users access the live site.

---

### 1. Provisioning Order & Setup

1. **Sign in to Render**: Go to [dashboard.render.com](https://dashboard.render.com).
2. **Click "New +" > "Blueprint"**: Select repository `ParthSinha9498/trustledger` (branch `main`).
3. **Render provisions 3 resources in sequence**:
   - **`trustledger-db`** (Render Postgres Basic-256mb, Oregon)
   - **`trustledger-backend`** (Web Service, Docker, all-in-one container)
   - **`trustledger-web`** (Web Service, Next.js frontend)

---

### 2. Database Initialization (Run Once in Postgres Shell)

Before the backend container seeds tables, open **`trustledger-db` > "Connect" > "Web Shell"** (or local `psql` using the external connection string) and run:

```sql
CREATE DATABASE brand;
CREATE DATABASE paypal_side;
```

---

### 3. Environment Variables to Paste

Render Blueprint prompts for variables marked with `sync: false`. Paste the following values:

#### A. Under `trustledger-backend`:
| Key | Value / Source |
| :--- | :--- |
| `PLATFORM_DATABASE_URL` | *Auto-linked from `trustledger-db`* |
| `BRAND_DATABASE_URL` | Replace `/platform` with `/brand` in the `PLATFORM_DATABASE_URL` connection string |
| `PAYPAL_DATABASE_URL` | Replace `/platform` with `/paypal_side` in the `PLATFORM_DATABASE_URL` connection string |
| `PAYPAL_CLIENT_ID` | PayPal Sandbox Client ID (from [developer.paypal.com](https://developer.paypal.com)) |
| `PAYPAL_CLIENT_SECRET` | PayPal Sandbox Client Secret |
| `LLM_API_KEY` | Primary LLM Key: Groq (`gsk_...` from [console.groq.com](https://console.groq.com)) |
| `LLM_FALLBACK_API_KEY` | Fallback LLM Key: Google Gemini API Key |
| `SANDBOX_TEST_CARD_NUMBER` | PayPal 16-digit Sandbox Test Card |
| `SANDBOX_TEST_CARD_EXPIRY` | Card Expiration date (`MM/YY`) |
| `SANDBOX_TEST_CARD_CVV` | Card 3-digit CVV (`123`) |
| `PAYPAL_WEBHOOK_ID` | *Leave blank initially*; fill after backend URL is live (see Step 5) |

#### B. Under `trustledger-web`:
| Key | Value / Source |
| :--- | :--- |
| `API_PUBLIC_HOST` | *Auto-linked from `trustledger-backend` external hostname* |
| `NEXT_PUBLIC_PAYPAL_CLIENT_ID`| Same PayPal Sandbox Client ID as above |

---

### 4. Health Checks (Verify After Deploy)

Once builds turn green, curl or open the following endpoints in browser:

1. **Backend API Health**:
   ```bash
   curl -s https://<backend-slug>.onrender.com/health
   # Expected response: {"ok": true}
   ```
2. **Frontend Home**:
   `https://<web-slug>.onrender.com/` (loads without errors)
3. **Brand Onboarding Guide**:
   `https://<web-slug>.onrender.com/brands/onboard` (loads 5 steps, zero horizontal overflow)
4. **Brand Cockpit**:
   `https://<web-slug>.onrender.com/cockpit` (loads KPIs, cases, and release aggregates)

---

### 5. Configure PayPal Webhooks (One-Time)

1. In [developer.paypal.com](https://developer.paypal.com) Sandbox App settings:
   - Click **Add Webhook**.
   - URL: `https://<backend-slug>.onrender.com/paypal/webhooks`
   - Select event: `CHECKOUT.ORDER.APPROVED` and `PAYMENT.CAPTURE.COMPLETED`.
   - Copy the generated Webhook ID and paste it into `trustledger-backend` > **Environment** > `PAYPAL_WEBHOOK_ID`.

---

### 6. Post-Deploy Live Verification Scripts

Run from local terminal against the live deployed URLs:

```bash
# 1. Full Preflight UI & claims audit
uv run --with playwright python e2e/preflight.py \
  --base-url https://<web-slug>.onrender.com \
  --api https://<backend-slug>.onrender.com

# 2. Live end-to-end checkout & capture test
API="https://<backend-slug>.onrender.com" uv run --with playwright python e2e/happy_path.py
```
