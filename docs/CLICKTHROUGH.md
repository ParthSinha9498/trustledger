# Web App Browser Click-Through Audit

Comprehensive click-through audit of the TrustLedger web frontend running against local backend services and PayPal sandbox.

Audit run date: 2026-10-21  
Environment: Local stack (ports 8000–8002, 3000), Postgres on 5433, AG Grid Community, Bryntum Scheduler trial, PayPal Sandbox.

---

## Page Status Summary

| Page / State | Route | Status | Screenshot (`e2e/out/clickthrough/`) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Store Checkout (Initial)** | `/pos` | **works** | `01_pos_store_a_initial.png` | Store tiles, product selection, serial entry, camera scanner toggle. |
| **Store Checkout (Verified)** | `/pos` | **works** | `02_pos_store_a_verified.png` | Store A + Serial X123 verified; displays Verification ID, PayPal Order ID, customer pay box, and customer device link. |
| **Customer Pay Screen** | `/pay/[id]` | **works** | `03_pay_page.png` | Renders brand verification status, unit summary ($899.00), and gold PayPal SDK button for order capture. |
| **Receipt (Awaiting Payment)** | `/receipt/[id]` | **works** (fixed) | `04_receipt_page.png` | Shows verification ID, PayPal order ID, serial, and status. Fixed badge color to amber pending indicator. |
| **Store Checkout (Blocked)** | `/pos` | **works** | `05_pos_store_b_blocked.png` | Store B + Serial X123 blocked (`NOT_IN_CHANNEL`); displays reason, prevents payment, and links directly to opened case. |
| **Brand Cockpit (Cases List)** | `/cockpit` | **works** | `06_cockpit_cases_list.png` | AG Grid Community table showing cases, status pills, reason codes, opened dates, and live privacy budget meter. |
| **Case Detail Page** | `/cockpit/cases/[id]` | **works** (fixed) | `07_case_detail_page.png` | Case header, summary, cited findings, embedded supply chain panel, and full step timeline with AG Grid and AG Charts. Fixed column truncation. |
| **Question Console (Plan & Run)** | `/cockpit/console` | **works** (fixed) | `08_console_results.png` | Natural language planning, editable query specs, query execution returning exact brand tables and bar charts. Fixed manual query creation. |
| **Question Console (Refusal Guardrail)** | `/cockpit/console` | **works** | `09_console_refused_query.png` | Enforces privacy guardrails (`TOO_MANY_CELLS` refusal when combinations exceed 200 cells on PayPal node). |
| **Supply Chain Timeline** | `/cockpit/supply-chain` | **works** | `10_supply_chain_bryntum.png` | Bryntum Scheduler rendering brand batches, distributor storage, store deliveries, and red off-channel divergence highlights. |

---

## UI Fixes Applied (`web/**`)

1. **`web/app/cockpit/console/page.tsx`**:
   - *Issue:* Manual query creation was inaccessible on an initial page load because the "Planned queries" section and "Add query" button were conditionally hidden behind `specs.length > 0 || rationale || err`. If the LLM planner was busy or unavailable, the user was unable to "add queries by hand below" as stated in the instructions.
   - *Fix:* Added an "Add query by hand" action directly in the ask form card so users can immediately compose and run custom queries.

2. **`web/components/cockpit/SupplyTimeline.tsx`**:
   - *Issue:* In the Bryntum Scheduler resource table, the "Tier" column width of 100px truncated "Distributor" to "Distrib...".
   - *Fix:* Increased Tier column width to 115px to prevent truncation while preserving clean alignment.

3. **`web/app/receipt/[id]/page.tsx` & `web/components/checkout/checkout.module.css`**:
   - *Issue:* When a receipt was in `AWAITING_PAYMENT` state, the status circle displayed a harsh red error badge with dots (`…`) inside a verified card.
   - *Fix:* Added `.badgePending` with an amber background (`#d97706`) for the awaiting payment state.

4. **`web/app/cockpit/page.tsx` & `web/app/cockpit/cases/[id]/page.tsx` & `web/lib/api.ts`**:
   - *Enhancement:* Added support for the agent `confidence` field (low/medium/high). Added as a dedicated column in the AG Grid investigations list and displayed in the case detail header meta row, gracefully handling unassigned values as "–".
