"""AG Studio Insights backend: release cells for Studio's data sources, and the LLM proxy for its agent turns.

    GET  /console/release/cells  -> the six private-release marginals as cells (+ exact brand counts)
    POST /ai/turn                -> one Studio agent turn, an OpenAI Chat Completions request, streamed back as SSE
    GET  /ai/log                 -> redacted metadata of recent /ai/turn requests (no bodies, no secrets)

Privacy rules kept here:
  * Release cells come from the PayPal node's existing one-time private release through /v1/query, exactly
    like /console/run. Nothing here spends privacy budget, and no buyer-level field is ever returned.
  * /ai/turn is the only path from Studio to a model. The server picks the model (AGENT_MODEL, then
    LLM_FALLBACK_MODEL; the client's model is ignored), injects the key, caps output tokens and refuses any
    request that names a buyer-level field of the PayPal node's schema or carries an email address.
  * LLM_MODE=mock returns a scripted stream that says it is a mock. It is not a replay of a recorded run.
"""
import collections
import hashlib
import itertools
import json
import logging
import re
import threading
import time
import uuid

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend import config, db
from backend.api.console import run_one
from backend.common import http, privacy
from backend.common.llm import GEMINI_BASE, _retry_after
from backend.common.query_spec import NODE_RULES

log = logging.getLogger("trustledger.studio")

router = APIRouter(tags=["studio"])

# ---------------------------------------------------------------- release cells

# Public domains (the PayPal node uses the same lists; tests check they match).
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["female", "male", "other"]

MARGINAL_TITLES = {
    "M1": "Buyers by store, product and week",
    "M2": "Buyers by store, product and age band",
    "M3": "Buyers by store, age band and gender",
    "M4": "Buyers and spend by store",
    "M5": "Buyers by product and week (all stores)",
    "M6": "Buyers and spend by store and product",
}

BRAND_TABLES = [
    {"id": "B1", "title": "Verified units sold by store and week", "metric": "sold_units", "dims": ["store_id", "week"]},
    {"id": "B2", "title": "Verified units sold by product", "metric": "sold_units", "dims": ["sku"]},
    {"id": "B3", "title": "Units sold by store and supplying distributor", "metric": "sold_units",
     "dims": ["store_id", "distributor_id"]},
    {"id": "B4", "title": "Verification failures by store and reason", "metric": "verification_failures",
     "dims": ["store_id", "reason_code"]},
    {"id": "B5", "title": "Units shipped by store and product", "metric": "shipped_units", "dims": ["store_id", "sku"]},
]

_cells_lock = threading.Lock()
_cells_cache: dict = {}  # (release_id, created_at) -> marginals payload (the release is static until a reseed)


def _var(ci95: float | None) -> float | None:
    return None if ci95 is None else (ci95 / 1.96) ** 2


def _release_status() -> dict:
    try:
        with http.client(config.paypal_node_url()) as c:
            r = c.get("/v1/release/status", params={"brand_id": config.brand_id()})
    except httpx.HTTPError as e:
        raise HTTPException(502, f"PayPal node unavailable: {e}")
    if r.status_code == 404:
        raise HTTPException(404, "No private release yet for this brand")
    if r.status_code != 200:
        raise HTTPException(502, {"node_status": r.status_code})
    return r.json()


def _stores() -> list[str]:
    # The platform's own store directory (public catalog), not another service's database.
    with db.connect("platform") as c:
        rows = c.execute("SELECT store_id FROM stores WHERE brand_id=%s ORDER BY store_id",
                         (config.brand_id(),)).fetchall()
    return [r["store_id"] for r in rows]


def _brand(metric: str, dims: list[str]) -> list[dict]:
    res = run_one("brand", {"metric": metric, "group_by": dims})
    if "refused" in res:
        raise HTTPException(502, {"brand_node": res["refused"]})
    return res["rows"]


def _paypal(metric: str, dims: list[str], filters: dict | None = None) -> tuple[list[dict], str | None]:
    res = run_one("paypal", {"metric": metric, "group_by": dims, "filters": filters or {}})
    if "refused" in res:
        raise HTTPException(502, {"paypal_node": res["refused"]})
    return res["rows"], (res.get("noise") or {}).get("marginal_id")


def _cell(dims: list[str], key: tuple, row: dict | None) -> dict:
    out = {d: str(v) for d, v in zip(dims, key)}
    if row is None:
        out.update(value=None, ci95=None, var=None, suppressed=True)
    else:
        out.update(value=float(row["value"]), ci95=float(row["ci95"]), var=_var(float(row["ci95"])), suppressed=False)
    return out


def _marginal(m: dict, stores: list[str], skus: list[str]) -> dict:
    """One release marginal as a full table: every public cell, suppressed ones with null values.

    The node answers at most two group-by dimensions per query, so a three-dimension marginal is read one
    store at a time (a store filter keeps the router on this marginal). Each answer is a stored release cell:
    no new noise and no budget.
    """
    dims = m["dims"]
    domains = {"store_id": stores, "sku": skus, "week": list(range(1, config.current_week() + 1)),
               "age_band": AGE_BANDS, "gender": GENDERS}
    found: dict[tuple, dict] = {}
    used: set = set()
    if len(dims) == 3:
        rest = dims[1:]
        assert dims[0] == "store_id"
        for s in stores:
            rows, mid = _paypal("buyers", rest, {"store_id": [s]})
            used.add(mid)
            for r in rows:
                found[(s, *(r[d] for d in rest))] = r
    else:
        rows, mid = _paypal("buyers", dims)
        used.add(mid)
        for r in rows:
            found[tuple(r[d] for d in dims)] = r
    if used - {m["id"]}:
        # The router chose a different marginal; never label one table as another.
        raise HTTPException(500, f"release router answered {m['id']} from {sorted(used)}")

    spend: dict[tuple, dict] = {}
    if m["metric"] == "both":
        rows, _ = _paypal("sum_amount", dims)
        spend = {tuple(r[d] for d in dims): r for r in rows}

    out_rows = []
    for key in itertools.product(*(domains[d] for d in dims)):
        cell = _cell(dims, key, found.get(key))
        if m["metric"] == "both":
            s = spend.get(key)
            cell.update(spend=float(s["value"]) if s else None, spend_ci95=float(s["ci95"]) if s else None,
                        spend_var=_var(float(s["ci95"])) if s else None)
        out_rows.append(cell)
    return {"id": m["id"], "title": MARGINAL_TITLES.get(m["id"], m["id"]), "dims": dims,
            "metric": "buyers" + ("+spend" if m["metric"] == "both" else ""), "rows": out_rows}


def _brand_counts() -> list[dict]:
    out = []
    for t in BRAND_TABLES:
        rows = [{**{d: str(r[d]) for d in t["dims"]}, "value": int(r["value"])} for r in _brand(t["metric"], t["dims"])]
        rows.sort(key=lambda r: [r[d] for d in t["dims"]])
        out.append({"id": t["id"], "title": t["title"], "dims": t["dims"], "rows": rows})
    return out


@router.get("/console/release/cells")
def release_cells():
    """The private release as cells for AG Studio. Read-only: spends no privacy budget.

    Marginal rows: dims + value, ci95 (95% half-width), var = (ci95/1.96)^2, suppressed (values null when
    suppressed). M4 and M6 also carry spend, spend_ci95, spend_var. Brand counts are exact business counts.
    """
    status = _release_status()
    rel = status["release_id"]
    cache_key = (rel, status.get("created_at"))  # a reseed reuses the id but makes a new release
    with _cells_lock:
        marginals = _cells_cache.get(cache_key)
        if marginals is None:
            stores = _stores()
            skus = sorted({r["sku"] for r in _brand("shipped_units", ["sku"])})
            marginals = [_marginal(m, stores, skus) for m in privacy.WORKLOAD]
            _cells_cache.clear()
            _cells_cache[cache_key] = marginals
    return {
        "marginals": marginals,
        "brand_counts": _brand_counts(),  # exact and live (sales change them), so not cached
        "epsilon": status["eps_equivalent"],
        "rho_spent": status["rho_spent"],
        "delta": status.get("delta"),
        "release_id": rel,
    }


# ---------------------------------------------------------------- LLM proxy guard

def _schema_columns(table: str) -> set[str]:
    from backend.seed import PAYPAL_SCHEMA

    m = re.search(rf"CREATE TABLE {table} \((.*?)\);", PAYPAL_SCHEMA, re.S)
    return {part.split()[0] for part in m.group(1).replace("\n", " ").split(",") if part.strip()}


# Buyer-level fields: columns of the PayPal node's transaction table that are not a public, aggregatable
# dimension (query_spec) or the brand key; plus the ingest payload's payer reference and the usual
# person-identifying field names. `amount` and `source` are excluded: neither identifies a buyer, and
# "amount" is an everyday word.
_PUBLIC = set(NODE_RULES["paypal"]["dims"]) | {"brand_id", "amount", "source"}
BUYER_FIELDS = sorted((_schema_columns("transactions") - _PUBLIC) | {
    "payer_ref", "payer_id", "buyer_id", "customer_id", "payer_email", "buyer_email", "email_address",
    "given_name", "surname", "full_name", "first_name", "last_name", "phone_number", "date_of_birth",
    "birth_date", "shipping_address", "address_line_1",
})
_BUYER_RE = re.compile(r"\b(" + "|".join(map(re.escape, BUYER_FIELDS)) + r")\b", re.I)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

MAX_BODY_BYTES = 1_500_000
ALLOWED_KEYS = {"messages", "tools", "tool_choice", "response_format", "temperature", "top_p",
                "parallel_tool_calls", "stop", "seed"}


def find_buyer_fields(body) -> list[str]:
    """Buyer-level field names (and email addresses) anywhere in a request, keys or values."""
    hits: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            hits.update(h.lower() for h in _BUYER_RE.findall(x))
            if _EMAIL_RE.search(x):
                hits.add("<email address>")

    walk(body)
    return sorted(hits)


def check_no_bare_numbers(text: str) -> None:
    """Verifies that numeric estimates in an analyst response carry their 95% confidence interval

    (e.g., '1,420 ± 18.2 units') or an '(exact)' annotation, rejecting bare quantities without intervals.
    """
    pattern = re.compile(r'\b(\d+(?:,\d+)?)\s*(?:units|buyers|sales)\b', re.I)
    for m in pattern.finditer(text):
        snippet = text[max(0, m.start() - 25):min(len(text), m.end() + 25)]
        if "±" not in snippet and "+/-" not in snippet and "ci95" not in snippet.lower() and "exact" not in snippet.lower():
            raise ValueError(f"Bare number without confidence interval: '{m.group(0)}' in context '{snippet}'")


# Redacted in-memory log. Metadata for every turn; the forwarded body (long strings cut) is kept only for
# the last few forwarded turns so tests and reviewers can check what left the server. No keys ever.
TURN_LOG: collections.deque = collections.deque(maxlen=200)
FORWARDED_BODIES: collections.deque = collections.deque(maxlen=20)
_rate: collections.deque = collections.deque()
_rate_lock = threading.Lock()


def _trim(x, limit: int = 4000):
    if isinstance(x, dict):
        return {k: _trim(v, limit) for k, v in x.items()}
    if isinstance(x, list):
        return [_trim(v, limit) for v in x]
    if isinstance(x, str) and len(x) > limit:
        return x[:limit] + f"...[{len(x) - limit} chars cut]"
    return x


def _record(entry: dict) -> None:
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **entry}
    TURN_LOG.append(entry)
    log.info("ai_turn %s", json.dumps(entry))


def _rate_ok() -> bool:
    limit = int(config.env("STUDIO_TURNS_PER_MIN", "40"))
    now = time.monotonic()
    with _rate_lock:
        while _rate and now - _rate[0] > 60:
            _rate.popleft()
        if len(_rate) >= limit:
            return False
        _rate.append(now)
        return True


def _models() -> list[dict]:
    """The server's allowlist, in order: primary then fallback. Nothing the client sends can add to it."""
    out = []
    primary = config.env("AGENT_MODEL")
    if primary:
        out.append({"model": primary, "base_url": config.env("LLM_BASE_URL", GEMINI_BASE),
                    "api_key": config.env("LLM_API_KEY", ""), "role": "primary"})
    fb = config.env("LLM_FALLBACK_MODEL")
    if fb:
        out.append({"model": fb,
                    "base_url": config.env("LLM_FALLBACK_BASE_URL") or config.env("LLM_BASE_URL", GEMINI_BASE),
                    "api_key": config.env("LLM_FALLBACK_API_KEY") or config.env("LLM_API_KEY", ""),
                    "role": "fallback"})
    return out


def _provider_client() -> httpx.Client:
    # Tests replace this with an httpx.MockTransport client.
    return httpx.Client(timeout=httpx.Timeout(120, connect=10))


def _sse(obj: dict) -> bytes:
    return f"data: {json.dumps(obj)}\n\n".encode()


MOCK_TEXT = ("Mock mode (`LLM_MODE=mock`): no model was called. This is a scripted placeholder answer, "
             "not a recorded run. Set `LLM_MODE=live` with `AGENT_MODEL` to ask the Insights analyst.")


def _mock_stream():
    cid = f"chatcmpl-mock-{uuid.uuid4().hex[:8]}"
    base = {"id": cid, "object": "chat.completion.chunk", "created": int(time.time()), "model": "mock"}
    yield _sse(base | {"choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})
    for word in re.findall(r"\S+\s*", MOCK_TEXT):
        yield _sse(base | {"choices": [{"index": 0, "delta": {"content": word}, "finish_reason": None}]})
    yield _sse(base | {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
    yield b"data: [DONE]\n\n"


@router.post("/ai/turn")
async def ai_turn(request: Request):
    """One AG Studio agent turn: an OpenAI Chat Completions request, answered as an SSE stream.

    The model is chosen here (AGENT_MODEL, then LLM_FALLBACK_MODEL on 429/5xx), the key is injected here,
    max_tokens is capped, and a request naming any buyer-level field is refused with 400.
    """
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(413, "request too large")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(400, "body must be JSON")
    if not isinstance(body, dict) or not isinstance(body.get("messages"), list) or not body["messages"]:
        raise HTTPException(400, "body must be a Chat Completions request with messages")

    digest = hashlib.sha256(raw).hexdigest()[:16]
    meta = {"sha256": digest, "bytes": len(raw), "messages": len(body["messages"]),
            "tools": [t.get("function", {}).get("name") for t in body.get("tools") or [] if isinstance(t, dict)],
            "client_model_ignored": body.get("model")}
    found = find_buyer_fields(body)
    if found:
        _record(meta | {"status": "refused", "buyer_fields": found})  # the body itself is not kept
        raise HTTPException(400, {"refused": "BUYER_FIELDS", "fields": found,
                                  "detail": "Only privacy-guarded aggregates may reach the model."})
    if not _rate_ok():
        _record(meta | {"status": "rate_limited"})
        return JSONResponse({"error": {"code": "rate_limited", "message": "Too many AI turns; try again in a minute."}},
                            status_code=429, headers={"Retry-After": "60"})

    cap = int(config.env("STUDIO_MAX_TOKENS", "4096"))
    asked = body.get("max_tokens") or body.get("max_completion_tokens") or cap
    out = {k: v for k, v in body.items() if k in ALLOWED_KEYS}
    out["max_tokens"] = max(1, min(int(asked), cap))
    out["stream"] = True

    if config.env("LLM_MODE", "live") == "mock":
        FORWARDED_BODIES.append(_trim(out | {"model": "mock"}))
        _record(meta | {"status": "mock", "model": "mock"})
        return StreamingResponse(_mock_stream(), media_type="text/event-stream",
                                 headers={"X-TrustLedger-LLM": "mock", "Cache-Control": "no-cache"})

    models = _models()
    if not models:
        raise HTTPException(503, "AGENT_MODEL is not set")
    return _forward(out, models, meta)


def _forward(out: dict, models: list[dict], meta: dict):
    client = _provider_client()
    last_status, last_text = None, ""
    for m in models:
        payload = out | {"model": m["model"]}
        try:
            req = client.build_request("POST", m["base_url"].rstrip("/") + "/chat/completions", json=payload,
                                       headers={"Authorization": f"Bearer {m['api_key']}",
                                                "Accept": "text/event-stream"})
            resp = client.send(req, stream=True)
        except httpx.HTTPError as e:
            last_status, last_text = 503, str(e)[:300]
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            last_status = resp.status_code
            last_text = resp.read().decode(errors="replace")[:1000]
            resp.close()
            continue
        if resp.status_code >= 400:
            text = resp.read().decode(errors="replace")[:2000]
            resp.close()
            client.close()
            _record(meta | {"status": f"provider_{resp.status_code}", "model": m["model"]})
            try:
                err = json.loads(text)
            except ValueError:
                err = {"error": {"message": text}}
            return JSONResponse(err, status_code=resp.status_code)

        FORWARDED_BODIES.append(_trim(payload))
        _record(meta | {"status": "ok", "model": m["model"], "role": m["role"]})

        def relay(resp=resp):
            accumulated = []
            try:
                for chunk in resp.iter_bytes():  # decoded (we set our own headers)
                    accumulated.append(chunk)
                    yield chunk
            finally:
                resp.close()
                client.close()
                raw_sse = b"".join(accumulated).decode(errors="replace")
                full_content = []
                for line in raw_sse.splitlines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            d = json.loads(line[6:])
                            delta = d.get("choices", [{}])[0].get("delta", {})
                            c = delta.get("content")
                            if c:
                                full_content.append(c)
                        except Exception:
                            pass
                if full_content:
                    combined = "".join(full_content)
                    try:
                        check_no_bare_numbers(combined)
                    except ValueError as e:
                        log.warning("Analyst reply contained bare numbers: %s", e)
                        _record(meta | {"status": "bare_numbers_rejected", "warning": str(e)})
                        raise

        return StreamingResponse(relay(), media_type="text/event-stream",
                                 headers={"X-TrustLedger-Model": m["model"], "X-TrustLedger-Model-Role": m["role"],
                                          "Cache-Control": "no-cache"})
    client.close()
    wait = _retry_after(last_text) or 30
    _record(meta | {"status": "waiting_capacity", "provider_status": last_status})
    return JSONResponse({"error": {"code": "waiting_capacity", "retry_after": round(wait),
                                   "message": f"Every configured model is busy or unavailable (last status "
                                              f"{last_status}). Try again in about {round(wait)} s."}},
                        status_code=503, headers={"Retry-After": str(round(wait))})


@router.get("/ai/log")
def ai_log(limit: int = 50):
    """Redacted metadata of recent /ai/turn requests: sizes, hashes, tool names, status. No bodies, no keys."""
    return list(TURN_LOG)[-max(1, min(limit, 200)):]
