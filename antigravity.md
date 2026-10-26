# TrustLedger — Project Context & State

> **Handover Document for Antigravity Session**  
> **Last Updated:** October 26, 2026  
> **Repository:** `trustledger` (`/home/parth.sinha/Downloads/paypal/trustledger`)  
> **Comms Hub:** `/home/parth.sinha/Downloads/paypal/comms`

---

## 1. Executive Summary & Core Value Proposition

**TrustLedger: Verify the product. Then pay.**
TrustLedger creates a pre-payment verification network for registered high-value retail categories (e.g. luxury electronics, smartphones, pharmaceuticals). 

1. **Pre-Payment Verification Gate**: Before a PayPal payment order is created, the store's POS scanner sends the product serial to TrustLedger.
2. **Deterministic Brand Registry**: The brand's private node executes a deterministic registry check (verifying channel authorization and supply-chain custody—never AI).
3. **Two Strict Transaction Outcomes**:
   - **Verified**: Brand confirms serial in authorized stock → PayPal creates payment order → Verification ID permanently attached to payment record.
   - **Blocked**: Serial unrecognized, assigned to another depot, or previously checked → No PayPal order created → Autonomous AI investigation opens immediately with cited evidence.
4. **Business Model**: **Brands pay for privacy-safe insights; shoppers get free authenticity checks.** Brands access aggregated checkout intelligence via OpenDP (Differential Privacy); shoppers get instant, free authenticity verification at checkout.

---

## 2. Live Cloud Deployment & Infrastructure

The entire stack is deployed live on **Render (Free Tier)**:

| Component | Service Name | Endpoint / Resource | Status |
| :--- | :--- | :--- | :--- |
| **Frontend Web** | `trustledger-web` | `https://trustledger-web.onrender.com` | `Live` |
| **Backend API** | `trustledger-backend` | `https://trustledger-backend-0abs.onrender.com` | `Live` (`{"ok": true, "paypal_mode": "sandbox"}`) |
| **PostgreSQL Database** | `trustledger-db` | `dpg-dbffi7i9lscs739va7vg-a` (Postgres 16) | `Available` (Seeded: 42 weeks, 17,755 txns, 21,001 serials, 40 clone attempts) |

### Key Automation Scripts:
- **`scripts/render_env_sync.py`**: Zero copy-pasting. Syncs 27 production environment variables directly to Render services via Render REST API (`--live`).
- **`e2e/preflight.py`**: Rigorous pre-PR audit validating build, banned claims, responsive layouts (390px, 1440px), color schemes (light, dark), console errors, hydration warnings, and horizontal overflow. Live run passed **145/145 checks**.
- **Live Genuine Checkout Verified**: Real transaction successfully completed against PayPal Sandbox creating order `8JP97654EE881554L`.

---

## 3. Communication Protocols & Partner Integrations

### Comms Protocol (AG ↔ Claude)
- **AG to Claude**: `/home/parth.sinha/Downloads/paypal/comms/AG_TO_CLAUDE.md` (append-only progress logs, PR notices).
- **Claude to AG**: `/home/parth.sinha/Downloads/paypal/comms/CLAUDE_TO_AG.md` (instructions, reviews).
- **Background Watcher**: `bash /home/parth.sinha/Downloads/paypal/comms/watch_inbox.sh` continuously runs in background (`task-1231`).
- **Rule**: All major milestones and PR notifications are logged to `AG_TO_CLAUDE.md`.

### Partner Status:
1. **APIMatic**:
   - DM sent to Sohaib requesting hackathon trial keys to generate SDKs and developer portal documentation from `/openapi/platform.yaml`.
2. **AG Studio / Enterprise Grid**:
   - Evaluation key requested to remove evaluation watermark. License wiring is already committed in `web/components/studio/StudioInsights.tsx` via `NEXT_PUBLIC_AG_GRID_LICENSE`.

---

## 4. Current Task & Active Branch

**Active Branch**: `ag/ui-polish`  
**Task**: Implementing comprehensive UX/UI overhaul specified by User/Claude (`# TrustLedger — UI Changes to Make`).

### Key UI Deliverables:
1. **Hero Section**:
   - Split layout: headline ("Verify the product. Then pay."), subhead, scope badge, and CTAs on left.
   - Interactive checkout verification gate preview on right with toggleable **Verified** vs **Blocked** outcomes (`HeroCheckoutPreview.tsx`).
   - Primary CTA: "Try the checkout demo" (`/pos`); secondary: "Explore the brand cockpit" (`/cockpit`).
2. **Header & Navigation (`Nav.tsx`)**:
   - Clean hierarchy: Landing, Brand Tools (Investigations, Insights, Supply chain, Studio), Privacy.
   - Prominent primary action button for "Store checkout" (`/pos`).
   - Mobile navigation drawer optimized with zero overflow and clean Escape key handling.
3. **How It Works**:
   - 3-step visual branching: Scan → Brand Check → Verified (PayPal Order) vs Blocked (No order; Investigation).
4. **Features (5 cards)**:
   - Elevated Checkout Gate and AI Investigations with concrete product previews.
   - Compact UI previews inside Brand Insights (mini chart), Supply-chain Timeline, and Privacy Diagram.
5. **Business Model Consolidation**:
   - Single cohesive section leading with sample Brand Insights question (`"What age group buys the P8 in Riverton?"` -> `25–34: 48% (±3.2%)`).
   - Formula: "Brands pay for privacy-safe insights; shoppers get free authenticity checks."
   - Compact citation: Pew Research Center (Nov 2024 survey of 11,114 US adults, published 2026: 18% flagged as bogus). Removed unapproved 2023 statistic.
   - USD 150B+ associated with the market-insights industry (ESOMAR, 2024 data).
6. **Privacy Section**:
   - Two balanced columns: (1) Data never leaves its owner; (2) No buyer is identifiable.
   - Architecture diagram showing Brand node and PayPal node separation.
7. **Factual & Copy Integrity**:
   - Brand system makes authenticity decisions (deterministic, not AI).
   - Blocked check triggers investigation (does not prove every blocked check is a leak).
   - 95% DP intervals apply strictly to buyer estimates; brand-side counts are exact.
   - Replaced "moats" with "design commitments" on Privacy page.
   - Story hook corrected so verification does not overclaim conclusive counterfeit proof.
   - Prohibited terms avoided: "prevents counterfeits", "guarantees authenticity", "zero-knowledge".

---

## 5. Directory Structure Quick Reference

- `web/`: Next.js 14 App Router (Vanilla CSS design system, zero Tailwind).
  - `web/app/page.tsx`: Landing page.
  - `web/app/pos/`: Interactive checkout demo.
  - `web/app/cockpit/`: Brand investigation cases, query console, supply-chain timeline, AG Studio.
  - `web/app/privacy/`: Privacy architecture documentation.
  - `web/app/story/`: 13-card guided pitch presentation.
  - `web/components/cockpit/Nav.tsx`: Navigation bar.
  - `web/components/home/copy.ts`: Landing page copy definitions.
- `backend/`: FastAPI application.
  - `backend/api/`: Verification and checkout endpoints (`/checkout/scan`, `/checkout/verify`).
  - `backend/brand_node/`: Brand registry and authorization logic.
  - `backend/paypal_node/`: PayPal order creation and differential privacy query engine.
  - `backend/worker/`: AI investigation agent (cited evidence workflow).
- `e2e/`: Automated test suite and preflight checker (`e2e/preflight.py`).
- `docker/`: Production Dockerfiles for web and backend.
