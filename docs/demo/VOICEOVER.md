# Demo voice-over script

Read at a calm ~150 words per minute (2.5 words per second). Each row is one scene. "Seconds" is the scene's planned
length: at least words ÷ 2.5 + 0.5 s, longer where the picture needs it (PayPal approval, the live agent). The cut
(`e2e/demo_cut.py`) fits each scene to its rendered audio. Total must stay under 3:00. Captions on screen stay short;
the voice carries the explanation. Every claim is backed in the product or by a row in the claims sheet.

The TTS script (`scripts/tts/make_voiceover.py`) reads the table below: one WAV per row, named by the `#` column.
Numbers are written as they should be spoken.

| # | Scene (seconds) | Narration |
|---|---|---|
| 1 | Problem (9) | Counterfeits are a four hundred and sixty seven billion dollar trade. In smartphones, one sale in eight is lost to fakes. |
| 2 | Gap (7) | Checking authenticity is optional and separate from paying, so most buyers skip it. |
| 3 | Product (17) | TrustLedger makes authenticity a condition of payment. The brand verifies the product before PayPal creates the order. If a check fails, an AI agent investigates where it came from, and brands get privacy-safe insights from verified purchases. |
| 4 | Teaser (5) | And it pays for itself. More on that later. |
| 5 | Genuine sale (14) | Store A scans serial X123. The brand confirms it, and only then does PayPal create the order, with the verification ID inside. The buyer approves, and the receipt is brand verified. |
| 6 | Blocked sale (13) | Now Store C scans the same serial. This phone was never shipped to Store C, so the checkout stops before any money moves. No PayPal order exists. |
| 7 | Investigation (15) | The brand gets a case. An AI agent investigates on its own, asking each side questions and never seeing a single record. Its findings show where the evidence diverges. |
| 8 | Supply chain (11) | The supply chain makes the leak visible: batches one distributor shipped to other stores, sold at Store C, a store it never supplies. |
| 9 | Business model (13) | Here's how it pays for itself. Brands spend over a hundred and fifty billion dollars a year on market insights. Surveys take weeks, and the answers are self-reported. |
| 10 | Brand insights (16) | With TrustLedger, a brand asks who buys its phones and gets an answer from verified purchases in seconds, with a ninety five percent interval on every value. The privacy budget is spent once; asking again costs nothing more. |
| 11 | AI analyst (8) | An AI analyst builds the charts, answering questions about buyers without ever seeing a buyer. |
| 12 | Privacy (13) | How is privacy ensured? Brand and PayPal data never leave their own systems, and every answer about buyers is protected with differential privacy, using OpenDP. No one is identifiable. |
| 13 | Onboarding (17) | Brands run one verification API, PayPal runs the gate, and a store adds one API call. AI shopping agents can call the same check. And for registered categories, PayPal can make it network policy, so a counterfeit seller can't opt out. |
| 14 | Close (10) | Brands pay for the insights, and the check is free for shoppers. Trust for buyers. Intelligence for brands. A stronger PayPal network. |

Planned total: 168 s + 1 s of silence before scene 1 = 2:49. Each scene in the cut = its audio + ≤ 1 s; waits sped up.

## Scene status

- **Scene 11** films the AG Studio analyst on `/cockpit/studio` (shipped in #79).
- **Scene 8** films the Bryntum supply-chain timeline (`/cockpit/supply-chain`) with stream B's "What you're looking at" strip.
- **Scene 6** needs stream A merged (blocked demo store = Store C). Before that, the screen still shows Store B.

## Accuracy notes (must stay true to the product)

- Scene 3 (product summary), "before PayPal creates the order": `/checkout/scan` creates the order only after VERIFIED
  (`tests/test_features.py::test_blocked_checkout_can_never_be_paid`).
- Scene 1: "four hundred and sixty seven billion" = OECD/EUIPO 2025, 2021 data; "one sale in eight" = 12.9% (EUIPO/ITU,
  2015 data). Sources and years are on the cards.
- Scene 6: the brand node checks the channel before the sold state (`backend/brand_node/main.py:62-64`), so X123 at
  Store C is NOT_IN_CHANNEL even after Store A sold it. Store C is supplied only by Distributor 2 (`backend/seed.py:46`).
- Scene 7 must not name a store or distributor: the live agent's finding varies by run.
- Scene 8 describes seeded, fictional data: Distributor 1 (Northline) supplies Stores A, D and F; some of its units are sold
  at Store C (`backend/seed.py:46,146-169,218-220`). Don't name Northline in the voice; the strip on screen does.
- Scene 9: "over a hundred and fifty billion dollars a year on market insights" = ESOMAR, 2024 data. It is the insights
  industry, not surveys alone: never say "on surveys". "Surveys take weeks" has no number on purpose.
- Scene 10: "in seconds" = the measured "Answered in N s" on the page. "Spent once; asking again costs nothing more" =
  the one-time private release (ρ 0.20 spent once; answers from it spend no further budget;
  `tests/test_privacy.py::test_private_release_queries_spend_zero_extra_rho`). "Costs nothing more" means privacy budget, not money.
- Scene 12: "protected with differential privacy, using OpenDP" (backend/common/privacy.py, OpenDP zCDP); "never leave their own systems" = separate brand/PayPal nodes; the numbers (lifetime ρ 0.25 ≈ ε 4.16,
  release ρ 0.20 ≈ ε 3.69, δ 1e-8) live on /privacy and in the README, not in the voice or on cards. "No one is identifiable"
  is the design goal the guarantee bounds; the card's footnote gives the red-team evidence.
- Scene 13: "a store adds one API call" until the APIMatic SDK exists; then "one SDK call, generated by APIMatic".
  "AI shopping agents can call the same check" = the MCP server in `mcp/`. "PayPal can make it network policy" is a
  proposal ("can"), not a shipped feature; never say PayPal does this today.
- Scene 14: "the check is free for shoppers" is the business model (brands pay for insights), not a price list.
