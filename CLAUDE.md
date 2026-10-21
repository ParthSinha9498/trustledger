# TrustLedger: notes for Claude Code

PayPal AI hackathon entry. **Product authenticity as a condition of payment.** Before a PayPal order is
created, the brand's verification API answers yes/no for a serialized product at this store. Yes: the
order is created with the verification ID in `custom_id`. No: no order exists, and an autonomous AI
investigator opens a case. It sees only differentially private aggregates from the brand and PayPal data.

Read first: `HANDOVER.md` (current state, what's left), `../PLAN.md` (milestones/specs), `../PITCH.md`,
`../STATUS.md` (last status, 2026-10-05), `../DP_RESEARCH.md` (privacy design), `../SPONSOR_SDKS.md`.

## Layout
- `backend/brand_node/`: brand-private service (port 8001). Holds serials and distributor data; `/v1/verify` returns yes/no only.
- `backend/paypal_node/`: PayPal-side data node (port 8002), DP aggregate queries only.
- `backend/api/`: public API (port 8000). Checkout gate, PayPal client/SDK, webhooks, cases, `console.py` (DP query console), supply chain.
- `backend/worker/`: investigation agent loop (`agent.py`), `mock_llm.py` for offline use, `astro.py` (Astropods, unverified).
- `backend/common/`: `privacy.py` (OpenDP zCDP), `query_spec.py`, `llm.py`, `notify.py`, `auth.py`, `http.py`.
- `backend/seed.py`: creates the 3 databases and loads fictional data (it drops tables).
- `web/`: Next.js 16 / React 19. Routes: `/` home, `/pos` checkout (camera scan), `/pay/[id]` (PayPal JS SDK v6),
  `/receipt/[id]`, `/cockpit` (AG Grid/Charts), `/cockpit/cases/[id]`, `/cockpit/console`, `/cockpit/supply-chain` (Bryntum Scheduler).
- `evals/`: `redteam.py`, `harness.py`, results in `evals/results/`. `tests/`: pytest.
- `openapi/`, `postman/`, `scripts/export_openapi.py`, `scripts/build_postman.py`: APIMatic/Postman artifacts.
- `docker/`, `docker-compose.yml`, `render.yaml`: containers and Render Blueprint.

## Commands
```bash
cp .env.example .env                 # mock modes need no keys
docker compose up -d postgres        # Postgres 17 on localhost:5433
uv sync
uv run python -m backend.seed
uv run uvicorn backend.brand_node.main:app --port 8001
uv run uvicorn backend.paypal_node.main:app --port 8002
uv run uvicorn backend.api.main:app --port 8000
uv run python -m backend.worker.main
uv run pytest -q                     # needs Postgres container; uses trustledger_test_* DBs
cd web && npm install && npm run dev # :3000   (npm run build to check types/build)
uv run --with playwright python e2e/happy_path.py  # sandbox e2e (stack running, .env sourced)
docker compose up --build            # full stack; ports overridable via PG_PORT/API_PORT/BRAND_PORT/PAYPAL_PORT/WEB_PORT
```

## Config (see `.env.example`)
- `PAYPAL_MODE=mock|sandbox` (+ `PAYPAL_CLIENT_ID/SECRET/WEBHOOK_ID`).
- `LLM_MODE=live|mock`. LLM is any OpenAI-compatible endpoint: Gemini by default (`LLM_BASE_URL`, `AGENT_MODEL`),
  Groq by changing those two vars. Don't hardwire a provider SDK.
- Each service gets only its own `*_DATABASE_URL`. The worker gets no DB URL at all. Only seed sees all three.
- `NEXT_PUBLIC_API_URL` is baked in at build time.
- AG Grid/Charts: **Community only** (decided 2026-10-20, no Enterprise trial). No map series or error bars; show ci95 in labels/tooltips.

## Hard constraints (don't break these)
- Verification is a deterministic yes/no from the brand. It is **not** AI. Brand logic and distributor data stay in the brand node.
- Blocked verification means no PayPal order is created. Never create the order first and cancel it later.
- Only privacy-guarded aggregates reach the LLM. Every query goes through `common/privacy.py`: zCDP Gaussian,
  per-buyer contribution cap (k=4 cells, clamp 1000), persistent per-brand rho budget (0.25), query cache, ci95 on every value.
  No raw rows, no per-buyer data in prompts.
- Service isolation: the api/worker never read another service's database directly.
- Cut from scope, don't re-add: QR/NFC tags, automated payments/refunds, smart contracts/blockchain.
- All data is fictional. Handle GDPR-type edge cases (minimisation, no PII to the LLM) as you implement.

## Conventions
- Python 3.12, uv, FastAPI, psycopg 3. Tests must pass offline (mock PayPal + mock LLM).
- Web: App Router, TypeScript, CSS modules / plain CSS, dark mode via `useDarkMode`.
- Sponsor integrations (AG Grid/Charts is the main prize bet, then Render, APIMatic, Postman, Bryntum, Zapier/Slack,
  Astropods) need to be visibly real in the demo. Don't add them as decoration only.
- Keep `openapi/` and `postman/` in sync by regenerating them with the scripts after API changes.

## Working with the user
- Give critique as a blunt numbered list with scores. Prefer one combined .md over many files.
- Parallel agents are fine. Claude writes the code and the demo; the user records the voice-over.
- Update `HANDOVER.md` / `../STATUS.md` at the end of a session or before a quota stop.

## Working with Antigravity
- The user runs Antigravity (a smaller model) in parallel. Claude leads: assigns tasks, sets file ownership, verifies its results.
- Coordination: `ANTIGRAVITY.md` (task, file ownership, Log). Check its Log regularly while both are working.
- Planned (not set up yet): `git init`, one branch per task, Antigravity reviews Claude's PRs; split inbox files
  (`AG_TO_CLAUDE.md` / `CLAUDE_TO_AG.md`) so writes can't interleave; file-watch instead of polling.

## Evening session plan (2026-10-20): finish everything in one go
The user will provide keys at the start: Render access (PayPal webhook ID is created after deploy).
LLM: the user won't pay. Gemini free tier is 5 req/min **per project** (~3 min/run). Development and evals: Groq free tier
(only `LLM_BASE_URL` + `AGENT_MODEL` change; watch its tokens-per-minute limit). The user can lend an OpenAI key **for the
video recording only** (`LLM_BASE_URL=https://api.openai.com/v1`); keep its usage to the demo runs. Done already: TODO #1–#3 (see HANDOVER.md). Order:
1. Set up git + branches (above). Give Antigravity TODO #6 (docs) with clear file ownership.
2. Live Gemini run of `evals/detection.py` (background). Its 100% result so far is from a scripted mock; report the live numbers honestly.
3. TODO #4: browser click-through of every page; fix issues; check Bryntum bars.
4. TODO #5: Render deploy → register the PayPal webhook → webhook e2e test. **Free plan only** (overrides PLAN.md's paid
   starter): fold the worker into the api service (no free background workers), expect sleep/cold starts, check the free
   Postgres expiry against judging (Dec 1–15). Needs a public GitHub repo (user creates it); `.env` is gitignored, so double-check no secrets get pushed.
   User checklist: `../SETUP_KEYS.md`.
5. Regenerate `openapi/` + `postman/` (API changed: case fields, capture 409).
6. TODO #7: captioned demo draft for the user's review → user voice-over → TODO #8 Devpost submission.
Open question: Gemini's OpenAI-compatible endpoint reported `cached: 0`. Verify caching before claiming savings in the pitch.

## Deadlines
Submissions close **2026-11-12 12:00 PM PT**. Internal target for all milestones: **Nov 5**. Judging Dec 1–15.
