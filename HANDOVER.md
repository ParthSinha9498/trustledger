# TrustLedger handover (2026-10-19)

Written so a fresh session can pick up without the earlier chat. Last work session ended 2026-10-05 on a
token-quota stop. Nothing has changed in the code since then (all file mtimes are 2026-10-05 or earlier).

## The idea (settled)
- **Authenticity as a condition of payment.** At checkout the platform calls the brand's verification API
  *before* creating the PayPal order. The answer is a deterministic yes/no, not AI. The brand's logic and
  distributor data never leave the brand node.
- **Federated analytics with differential privacy.** The brand node and the PayPal node each answer only
  aggregate queries, through OpenDP zCDP with per-buyer caps, a stored budget, a query cache and CIs.
- **The AI part:** an autonomous investigator agent opens a case when verification fails. It queries the
  DP aggregates (the only data it can see) and writes up its findings. Alerts go to Zapier/Slack.
- **Cut, with reasons:** QR/NFC (hardware, and not needed for the story), automated payments/refunds (risk and
  scope), smart contracts (adds nothing judges reward and costs time).

## Done and verified (as of 2026-10-05)
- Backend on Postgres 17 (compose service, host port 5433). 3 databases: brand, paypal_side, platform.
- Checkout gate: verify, then create the PayPal order with the verification ID in `custom_id`. If blocked, no order.
  Webhook reconciliation. Case alerts via `NOTIFY_WEBHOOK_URL`.
- Privacy engine (`backend/common/privacy.py`), built per `../DP_RESEARCH.md`: zCDP Gaussian, k=4 cells per buyer,
  clamp 1000, persistent rho 0.25 per brand, query cache, ci95 on every value.
- Investigation agent: Gemini by default through an OpenAI-compatible client (Groq by switching env vars). Mock mode runs offline.
- Web (Next.js 16) builds cleanly: `/pos` checkout with camera scan, `/pay/[id]` PayPal JS SDK v6, receipt,
  cockpit (AG Grid/Charts), cases, case detail, console, Bryntum supply chain. **Not yet opened in a browser.**
- Tests: 38 test functions across 8 files (`uv run pytest -q`, needs Postgres). 38 passed last time they were run.

## Partial work from stopped agents. Verify before you rely on it.
- **Console + evals agent.** `backend/api/console.py` (353 lines) and `tests/test_console.py` (7 tests) both exist.
  `../STATUS.md` says the test file was missing, so it was written at the very end; confirm it passes.
  `evals/redteam.py` and `evals/harness.py` exist. `evals/results/redteam.md` shows a **mock** run: 10 of 11 attacks
  blocked (suppression 5, noise 3, budget 1, refusal 1). **One attack succeeded.** Investigate it before claiming
  the system is privacy-safe. Still missing: `evals/detection.py`, `evals/scenarios.py`, `tests/test_evals.py`.
- **Deploy agent.** These exist but are unverified: `render.yaml` (web + api + 2 pserv nodes + worker + seed cron +
  3 Postgres 17 DBs), `openapi/{brand-verification,platform}.yaml`, `postman/trustledger.postman_collection.json`,
  `scripts/export_openapi.py`, `scripts/build_postman.py`, `backend/worker/astro.py`.
  Compose port variables are **already done**: `../STATUS.md` lists them as missing, but that is out of date.
  Still missing: `e2e/` (Playwright), `docs/DEPLOY.md`, `docs/ASTROPODS.md`, `astropods.yml`.

## Remaining (about 40%), in order
1. Run `uv run pytest -q`, review `console.py` and its tests, and write the detection eval (`evals/detection.py`, `scenarios.py`, tests).
2. Look into the successful red-team attack. Then run the red-team with the live LLM, not only the mock.
3. Check `render.yaml` against Render's Blueprint docs (plan names, `fromService` hostport, the pserv/worker
   networking). Finish e2e, `docs/`, `astropods.yml`.
4. Run the full stack and open every page in a browser. Check that the Bryntum bars render and the AG Grid cockpit works.
5. Real runs: PayPal sandbox end to end (order, `custom_id`, webhook) and the Gemini agent. Tune the agent prompt.
6. Render deploy. (AG Grid: Community only, decided 2026-10-20; no licence key needed.)
7. Demo video (Claude writes the script and drives the demo; the user records the voice-over) and the Devpost write-up.

**Needed from the user:** PayPal sandbox client ID/secret and webhook ID, a Gemini API key, an AG Grid trial key, and Render account access.

## Decisions and why
- Verification is yes/no and not AI. That makes it auditable, and the brand keeps its data. AI goes where judgement is needed, in the investigation.
- DP: zCDP rather than pure epsilon, because composition across many agent queries is tighter. The budget is persisted
  so restarts can't reset it. The cache means repeated queries cost nothing and can't be averaged to remove the noise. CIs let the agent reason about the noise.
- One database per service, with no shared DB URL. Isolation can be shown at the infra level, not just claimed. The worker has no DB access.
- OpenAI-compatible LLM client, so the provider can change (Gemini for cost and quota, Groq for speed) without code changes.
- Sponsor plan: AG Grid/Charts is the main prize bet (cockpit + console). Render (hosting), APIMatic (OpenAPI; PayPal Server SDK for Orders v2, see docs/APIMATIC.md),
  Postman (collection), Bryntum (supply-chain timeline), Zapier/Slack (alerts), Astropods (agent) are side prizes.

## Gotchas
- Tests and seed need the Postgres container up. Seed **drops and recreates** every table.
- Local Postgres is on **5433**, not 5432. `.env` holds host-side DB URLs; compose blanks them inside containers on purpose.
- `NEXT_PUBLIC_API_URL` is fixed at web build time. Rebuild after changing it.
- `.env.example` sets `LLM_MODE=live`, but compose defaults to `mock`. With no key, use mock.
- `AGENT_MODEL=gemini-3.8-flash` is set in `.env.example` and `render.yaml`. Confirm the model name is valid when you add the key.
- Bryntum is the `scheduler-trial` package, which shows a trial watermark. AG Grid shows a watermark until the licence key is set.
- The README says "Status: skeleton", which is out of date. Fix it before submission.
- On Render the seed is a manual cron job ("Trigger Run" after the first deploy).

## Deadlines
Submissions close 2026-11-12 12:00 PM PT (target: all milestones by Nov 5). Judging Dec 1–15.

## Update 2026-10-19 (live run, task 1)
- `.env` set up: PayPal sandbox creds (OAuth OK), Gemini key, `AGENT_MODEL=gemini-3.5-flash` (3.8 doesn't exist), sandbox buyer login.
- Real sandbox order created by `/checkout/scan` for a genuine serial; fake serial blocked with no order + case opened.
- Fixed `common/llm.py`: echo tool-call `extra_content` back (Gemini 3 thought_signature requirement, 400 otherwise).
- Live agent runs, but hits the step limit before concluding (spends turns re-querying). Next: prompt/step-limit tuning.
- Suspicious: `get_budget` reported `spent: 0.0` after 6 brand queries. Check budget accounting.
- Not yet tested: buyer approve + `/capture` (needs the browser/PayPal popup), webhooks, India-region seller with USD.

## Decisions 2026-10-19 (case design + agent)
- **Case = one open problem, not one failed scan.** On failure, attach to an open case with same (brand, store, reason_code); else open a new case. No time-window grouping.
- **One agentic run per case.** Re-run only on material change (failure count doubles, new distributor/SKU appears).
- Why: per-scan agents would burn the per-brand DP budget (~25 PayPal-side queries/day) in a handful of cases and spam duplicate findings.
- **Agent fixes:** MAX_STEPS 10 → 16, show remaining steps each turn, record findings by step 12, forced finish on last step, require ≥1 PayPal-side query.
- **Cost story for pitch:** no AI on checkout path; dedup into open cases; Gemini implicit caching (stable prompt prefix, log `cached_content_token_count`); optional nightly trend sweep via Gemini Batch API (~50% cheaper, 24h SLA).
- `get_budget spent: 0.0` was correct: only brand-side (free, exact) queries had run. Confirm once a PayPal-side query happens.

## Happy-path run 2026-10-19
- Scan → sandbox order OK. Buyer approval (headless Playwright, now `e2e/happy_path.py`) fails at PayPal with
  `UNSUPPORTED_PAYEE_CURRENCY`: the India-region sandbox seller can't receive USD. Fix: create a **US-region sandbox
  business account**, create a new sandbox app linked to it, swap CLIENT_ID/SECRET in `.env`.
- `/checkout/{id}/capture` returns a bare 500 when the order isn't approved. Should return a clean 4xx.
- Receipt shows `brand_verified: false` for a VERIFIED checkout in AWAITING_PAYMENT. Check whether that's intended pre-capture.

## Seller-side changes (to document in PLAN/PITCH)
- Store/mall POS: scan the brand serial (existing barcode scanner or the /pos camera page) and route payment through the
  TrustLedger checkout (sends store_id, serial, sku, amount). No other data reporting. Store needs its own PayPal business account.
- Brand: expose `/v1/verify` and keep serial → batch → distributor → store shipment records (from ERP/serialization it already runs).
  Products must carry a unique serial label.
- Distributors and malls: no changes, no reporting (by design).
- **Resolved:** switched `.env` to a US-region sandbox app ("Hackathon"). Full happy path passes: scan → order → buyer
  approves (headless, `e2e/happy_path.py`) → `/capture` → status CAPTURED, `brand_verified: true`. Receipt flag is just false until capture.

## TODO (as of 2026-10-19, ordered)
1. Agent: open-case dedup (brand, store, reason_code) + re-run on material change; MAX_STEPS 16, remaining-steps hint, forced finish, ≥1 PayPal-side query; log cached tokens.
2. `/checkout/{id}/capture`: clean 4xx when order not approved (currently bare 500).
3. Detection evals (`evals/detection.py`, `evals/scenarios.py`, `tests/test_evals.py`) + red-team 10/11 fix.
4. Web app: browser click-through on sandbox, fix issues; AG Grid licence key (user).
5. Render deploy (needs user's Render access) → PayPal webhook ID → webhook test.
6. Docs: README status, `docs/DEPLOY.md`, Astropods (`astropods.yml`, `docs/ASTROPODS.md`), seller-side changes into PLAN/PITCH, refresh `../STATUS.md`.
7. Demo: silent captioned draft (Playwright skill) → optional ElevenLabs voice.
8. Devpost submission (user). Deadline 2026-11-12 12:00 PM PT; target Nov 5.

## Update 2026-10-20 (TODO #1 + #2 done)
- Case dedup live: failures join the non-closed case with same (brand, store, reason_code); `record_failure()` in `api/main.py`,
  new `case_failures` table, run snapshot columns on `cases`. Re-queue on material change (failures ≥2× last run, or new SKU).
- Agent: 16 turns, `turns_left` in every tool result, findings nudge at turn 12, `finish` rejected until ≥1 PayPal-side query,
  `usage` step logged per run. Tests: `tests/test_cases.py`.
- Live Gemini run: 14 turns, 2 PayPal queries, 4 findings, finished cleanly. ~53k prompt tokens per run.
  **`cached` reported 0**: Gemini's OpenAI-compatible endpoint may not return `prompt_tokens_details.cached_tokens`. Check the
  native API or the usage dashboard before claiming caching numbers in the pitch.
- Free tier = 5 req/min: `common/llm.py` now waits out 429s using the provider's retry delay (a run takes ~3 min on the free tier).
- `/checkout/{id}/capture`: PayPal 422 (e.g. ORDER_NOT_APPROVED) → 409 `{paypal_issue, message}`; other PayPal errors → 502.
- TODO #3 is being done by Antigravity in parallel (see `ANTIGRAVITY.md`).
