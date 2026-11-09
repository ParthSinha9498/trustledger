# Demo voice-over script

Read at a calm ~150 words per minute (2.5 words per second). Each row is one scene. "Seconds" is the scene's budget
from the latest take (`e2e/out/demo/marks.json`, recorded 2026-11-07): the narration must fit inside it. The cut
(`e2e/demo_cut.py`) fits each scene to its rendered audio. Total must stay under 3:00. Captions on screen stay short;
the voice carries the explanation. Every claim is backed in the product or by a row in the claims sheet.

The TTS script (`scripts/tts/make_voiceover.py`) reads the table below: one WAV per row, named by the `#` column.
Numbers are written as they should be spoken.

| # | Scene (seconds) | Narration |
|---|---|---|
| 1 | Problem (7.5) | Counterfeits: a four hundred and sixty seven billion dollar trade. Smartphones: one in eight sales lost to fakes. |
| 2 | Gap (5.5) | Checking authenticity is optional and separate from paying, so most buyers skip it. |
| 3 | Product (8) | TrustLedger makes authenticity a condition of payment. The brand verifies the product before PayPal creates the order. |
| 4 | Teaser (10.5) | And it pays for itself, more on that later. Data never moves: questions go to the brand and PayPal nodes, and only private aggregates come back. |
| 5 | Genuine sale (19) | Store A enters serial X123 at checkout. The brand confirms it, and only then does PayPal create the order, with the verification ID inside. The buyer approves, and the receipt is brand verified. |
| 6 | Blocked sale (18) | Now Store C enters the same serial. This serial is not in Store C's channel, so checkout stops before any money moves. No PayPal order exists. |
| 7 | Investigation (23) | The brand gets a case. An investigator asks each side questions and sees only aggregates, never a single record. Its findings show where the evidence diverges. |
| 8 | Supply chain (10.5) | The supply chain makes the leak visible: batches one distributor shipped to other stores, sold at Store C, a store it never supplies. |
| 9 | Business model (11) | Brands spend over a hundred and fifty billion dollars a year on market insights. TrustLedger answers from verified purchases in seconds, and brand budgets fund the free check. |
| 10 | Brand insights (20) | With TrustLedger, a brand asks which age bands buy its phones and gets an answer from verified purchases in seconds, with a ninety five percent interval on every value. PayPal-side answers spend the privacy budget once; asking again costs no more budget. |
| 11 | Analyst (6) | An analyst answers questions about buyers, without seeing a single buyer record. |
| 12 | Privacy (6.5) | Buyers stay anonymous. One fixed privacy limit per brand, for life, protected with OpenDP differential privacy. |
| 13 | Onboarding (16) | Brands run one verification API, PayPal runs the checkout gate, and a store adds one API call. AI shopping agents can call the same check. For registered categories, PayPal could make it network policy. This prototype runs locally. |
| 14 | Close (8) | Brands pay for insights. The check is free for shoppers. Trust for buyers. Intelligence for brands. A stronger PayPal network. |

Planned total: about 2:22 of narration (14 rows, words ÷ 2.5 + 0.5 s each) plus 1 s of silence before scene 1. Each scene in the cut = its audio + ≤ 1 s.
Scene 5 also carries the PayPal approval window (login cut out, about 17 s kept), and scene 7 carries the agent wait,
which the cut removes; both sit outside the narration budget.

## Recording map (take of 2026-11-07, `e2e/out/demo/marks.json`)

| # | Marks (seconds into the take) | What is on screen |
|---|---|---|
| 1 | problem 8.0 to 15.5 | Problem card |
| 2 | gap 15.5 to 21.0 | Gap card |
| 3 | idea 0.0 to 8.0 | Idea card. **Plays before the problem card; see mismatch below.** |
| 4 | how 21.0 to 31.5 | "Data never moves" card |
| 5 | s1 31.5 to 50.7, popup 50.7 to 90.6, receipt 90.7 to 93.7 | Store A at POS, PayPal approval (login cut), Brand Verified receipt |
| 6 | s2 93.7 to 107.7, compare 107.7 to 111.8 | Store C at POS, "Never created", side-by-side compare |
| 7 | s3 111.8 to 119.3; agent cut 119.3 to 301.5; findings and boundary to 316.8 | Case page, agent wait cut, findings and data boundary. Scripted run, see status |
| 8 | supply-chain 316.8 to 327.3 | Supply-chain timeline |
| 9 | business 327.3 to 338.3 | Business case card |
| 10 | s4 338.3 to 358.5 | Cockpit console: "Which age bands buy", comparison, "Answered in N s", PayPal-side label |
| 11 | analyst 358.5 to 364.5 | AG Studio analyst page (`/cockpit/studio`), recorded live in take 14 |
| 12 | guarantee 364.5 to 371.0 | Privacy card |
| 13 | levels 371.0 to 387.0 | Levels card |
| 14 | close 387.0 to 395.0 | Close card |

**Mismatch:** the recording plays the idea card (scene 3) before the problem card (scene 1), but the narration plays
problem, gap, product. Either move the idea card after the gap card in `e2e/demo_record.py`, or swap rows 1 and 3 here.
Until one is done, the voice and the picture are out of step by about 8 s on scenes 1 to 3.

## Scene status

- **Scene 5 and 6** show Store A and Store C (the recorder's current stores). Store C is the blocked store.
- **Scene 7** is a scripted investigator run. Do not describe it as a live model. The cut hides the wait.
- **Scene 8** films the Bryntum supply-chain timeline (`/cockpit/supply-chain`) with its "What you're looking at" strip.
- **Scene 11** films the AG Studio page (`/cockpit/studio`) live. The narration may name "AG Studio".
- **Sponsor tools on screen:** AG Grid and AG Charts Community run in the cockpit. AG Studio is the prize target
  (`/cockpit/studio`), running on an evaluation licence valid to 10 Dec 2026.
- **Hosted demo:** none. Render is not deployed. The video says the prototype runs locally (scene 13).

## Accuracy notes (must stay true to the product)

- Scene 3 (product summary), "before PayPal creates the order": `/checkout/scan` creates the order only after VERIFIED
  (`tests/test_features.py::test_blocked_checkout_can_never_be_paid`).
- Scene 1: "four hundred and sixty seven billion" = OECD/EUIPO 2025, 2021 data; "one sale in eight" = 12.9% (EUIPO/ITU,
  2015 data). Sources and years are on the cards.
- Scene 5: the checkout is typed in the demo ("enters serial"), not camera-scanned. Do not say "scans" for the checkout.
  In production the store's POS would send the scanned serial through the TrustLedger API; that line is a caption or a
  hint, not a claim about this build.
- Scene 6: the brand node checks the channel before the sold state (`backend/brand_node/main.py:62-64`), so X123 at
  Store C is NOT_IN_CHANNEL even after Store A sold it. Store C is supplied only by Distributor 2 (`backend/seed.py:46`).
- Scene 7 must not name a store or distributor: the investigator's finding varies by run. The run is scripted in this
  take, so the narration says "investigator" and makes no claim about a live AI model. Do not say "autonomous".
- Scene 8 describes seeded, fictional data: Distributor 1 (Northline) supplies Stores A, D and F; some of its units are sold
  at Store C (`backend/seed.py:46,146-169,218-220`). Don't name Northline in the voice; the strip on screen does.
- Scene 9: "over a hundred and fifty billion dollars a year on market insights" = ESOMAR, 2024 data. It is the insights
  industry, not surveys alone: never say "on surveys". The "surveys take weeks" line was cut to fit the 11 s card.
- Scene 10: "in seconds" = the measured "Answered in N s" on the page. "Spent once" = the one-time private release
  (ρ 0.20 spent once; answers from it spend no further budget;
  `tests/test_privacy.py::test_private_release_queries_spend_zero_extra_rho`). The line says "privacy budget", not money,
  and applies to PayPal-side answers only.
- Scene 12: "protected with differential privacy, using OpenDP" (backend/common/privacy.py, OpenDP zCDP); the numbers
  (lifetime ρ 0.25 ≈ ε 4.16, release ρ 0.20 ≈ ε 3.69, δ 1e-8) live on /privacy and in the README, not in the voice or on
  cards. "No one is identifiable" is no longer in the voice: it is a design goal, and the red-team footnote gives the evidence.
- Scene 13: "a store adds one API call". "AI shopping agents can call the same check" = the MCP server in `mcp/`.
  "PayPal could make it network policy" is a proposal, not a shipped feature; never say PayPal does this today.
  "This prototype runs locally" matches the state on 2026-11-07 (no hosted demo).
- Scene 14: "the check is free for shoppers" is the business model (brands pay for insights), not a price list.
