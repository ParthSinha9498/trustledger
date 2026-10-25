"""AG Studio backend: release cells (read-only, no budget) and the /ai/turn LLM proxy (offline)."""
import json

import httpx
import pytest

from backend.api import studio
from backend.common import privacy

DIM_FIELDS = {"store_id", "sku", "week", "age_band", "gender", "distributor_id", "reason_code"}
MARGINAL_FIELDS = {"value", "ci95", "var", "suppressed"}
SPEND_FIELDS = {"spend", "spend_ci95", "spend_var"}


def _budget(api):
    r = api.get("/console/budget")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture()
def cells(env):
    before = _budget(env["api"])
    r = env["api"].get("/console/release/cells")
    assert r.status_code == 200, r.text
    return r.json(), before


def test_release_cells_shape_and_allowlisted_fields(env, cells):
    body, _ = cells
    assert {"marginals", "brand_counts", "epsilon", "rho_spent"} <= set(body)
    assert body["epsilon"] == pytest.approx(3.69, abs=0.01) and body["rho_spent"] == pytest.approx(privacy.RELEASE_RHO)
    assert [m["id"] for m in body["marginals"]] == [m["id"] for m in privacy.WORKLOAD]
    for m, w in zip(body["marginals"], privacy.WORKLOAD):
        assert m["dims"] == w["dims"] and m["title"] and m["rows"]
        allowed = set(m["dims"]) | MARGINAL_FIELDS | (SPEND_FIELDS if w["metric"] == "both" else set())
        for row in m["rows"]:
            assert set(row) == allowed, (m["id"], row)
        # Full public domain: one row per cell, suppressed ones included.
        assert len({tuple(r[d] for d in m["dims"]) for r in m["rows"]}) == len(m["rows"])
    for t in body["brand_counts"]:
        assert t["id"] and t["title"] and t["rows"]
        for row in t["rows"]:
            assert set(row) == set(t["dims"]) | {"value"} and isinstance(row["value"], int)
            assert set(t["dims"]) <= DIM_FIELDS
    assert not studio.find_buyer_fields(body)
    assert "payer" not in json.dumps(body)


def test_release_cells_spend_no_budget(env, cells):
    _, before = cells
    assert _budget(env["api"]) == before
    env["api"].get("/console/release/cells")
    assert _budget(env["api"]) == before


def test_release_cells_values_match_console_run_and_var(env, cells):
    body, _ = cells
    m4 = next(m for m in body["marginals"] if m["id"] == "M4")
    run = env["api"].post("/console/run", json={"specs": [
        {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["store_id"]}}]}).json()["results"][0]
    assert run["noise"]["marginal_id"] == "M4"
    by_store = {r["store_id"]: r for r in run["rows"]}
    for row in m4["rows"]:
        if row["store_id"] in by_store:
            assert row["value"] == by_store[row["store_id"]]["value"] and row["ci95"] == by_store[row["store_id"]]["ci95"]
    for m in body["marginals"]:
        for row in m["rows"]:
            if row["suppressed"]:
                assert row["value"] is None and row["ci95"] is None and row["var"] is None
            else:
                assert row["var"] == pytest.approx((row["ci95"] / 1.96) ** 2)
    m1 = next(m for m in body["marginals"] if m["id"] == "M1")
    assert any(r["suppressed"] for r in m1["rows"]) and any(not r["suppressed"] for r in m1["rows"])


def test_release_cells_three_dim_marginals_come_from_their_own_table(env, monkeypatch):
    seen = []
    real = studio._paypal

    def spy(metric, dims, filters=None):
        rows, mid = real(metric, dims, filters)
        seen.append(mid)
        return rows, mid

    monkeypatch.setattr(studio, "_paypal", spy)
    studio._cells_cache.clear()
    assert env["api"].get("/console/release/cells").status_code == 200
    assert set(seen) == {m["id"] for m in privacy.WORKLOAD}


def test_studio_domains_match_paypal_node():
    from backend.paypal_node import main as node

    assert studio.AGE_BANDS == node.AGE_BANDS and studio.GENDERS == node.GENDERS


# ---------------------------------------------------------------- /ai/turn

TURN = {
    "model": "gpt-client-choice",
    "messages": [{"role": "system", "content": "You are the Insights analyst."},
                 {"role": "user", "content": "Which store sells the most P8 128GB?"}],
    "tools": [{"type": "function", "function": {"name": "query_release", "description": "Read release cells",
                                                "parameters": {"type": "object", "properties": {}}}}],
    "stream": True,
    "max_tokens": 999999,
}


def _events(text: str) -> list:
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"]


def test_ai_turn_mock_stream(env):
    r = env["api"].post("/ai/turn", json=TURN)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream") and r.headers["x-trustledger-llm"] == "mock"
    assert r.text.rstrip().endswith("data: [DONE]")
    events = _events(r.text)
    text = "".join(e["choices"][0]["delta"].get("content", "") for e in events)
    assert text.startswith("Mock mode") and "not a recorded run" in text and "replay" not in text.lower()
    assert events[-1]["choices"][0]["finish_reason"] == "stop"


@pytest.mark.parametrize("bad", [
    {"role": "user", "content": "group by payer_key please"},
    {"role": "tool", "tool_call_id": "c1", "content": json.dumps([{"store_id": "store_c", "txn_id": "T1"}])},
    {"role": "user", "content": "contact buyer jane.doe@example.com"},
    {"role": "user", "content": "show ORDER_ID per sale"},
])
def test_ai_turn_rejects_buyer_fields(env, bad):
    n = len(studio.FORWARDED_BODIES)
    r = env["api"].post("/ai/turn", json=TURN | {"messages": TURN["messages"] + [bad]})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["refused"] == "BUYER_FIELDS"
    assert len(studio.FORWARDED_BODIES) == n
    assert studio.TURN_LOG[-1]["status"] == "refused"
    assert "jane.doe" not in json.dumps(list(studio.TURN_LOG))


def test_buyer_fields_derived_from_paypal_schema():
    assert {"payer_key", "txn_id", "order_id", "payer_ref"} <= set(studio.BUYER_FIELDS)
    assert not ({"store_id", "sku", "week", "age_band", "gender", "region"} & set(studio.BUYER_FIELDS))


def _live(monkeypatch, handler, fallback=True):
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("AGENT_MODEL", "primary-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://primary.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-primary-secret")
    if fallback:
        monkeypatch.setenv("LLM_FALLBACK_MODEL", "fallback-model")
        monkeypatch.setenv("LLM_FALLBACK_BASE_URL", "https://fallback.test/v1")
        monkeypatch.setenv("LLM_FALLBACK_API_KEY", "sk-fallback-secret")
    else:
        monkeypatch.delenv("LLM_FALLBACK_MODEL", raising=False)
    monkeypatch.setattr(studio, "_provider_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))


SSE_OK = (b'data: {"choices":[{"index":0,"delta":{"content":"Store A"},"finish_reason":null}]}\n\n'
          b'data: {"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')


def test_ai_turn_ignores_client_model_caps_tokens_injects_key(env, monkeypatch):
    sent = []

    def handler(req: httpx.Request):
        sent.append((str(req.url), req.headers["authorization"], json.loads(req.content)))
        return httpx.Response(200, content=SSE_OK, headers={"content-type": "text/event-stream"})

    _live(monkeypatch, handler)
    r = env["api"].post("/ai/turn", json=TURN | {"user": "x", "extra_body": {"a": 1}})
    assert r.status_code == 200, r.text
    assert r.content == SSE_OK  # provider SSE relayed unchanged
    url, auth, body = sent[0]
    assert url == "https://primary.test/v1/chat/completions" and auth == "Bearer sk-primary-secret"
    assert body["model"] == "primary-model" and body["stream"] is True and body["max_tokens"] == 4096
    assert "user" not in body and "extra_body" not in body
    assert "sk-" not in json.dumps(list(studio.TURN_LOG)) + json.dumps(list(studio.FORWARDED_BODIES))
    assert studio.TURN_LOG[-1]["client_model_ignored"] == "gpt-client-choice"


def test_ai_turn_falls_back_on_429_then_reports_capacity(env, monkeypatch):
    calls = []

    def handler(req: httpx.Request):
        calls.append(json.loads(req.content)["model"])
        if "primary" in str(req.url):
            return httpx.Response(429, json={"error": {"message": "Rate limit. Please try again in 12s"}})
        return httpx.Response(200, content=SSE_OK, headers={"content-type": "text/event-stream"})

    _live(monkeypatch, handler)
    r = env["api"].post("/ai/turn", json=TURN)
    assert r.status_code == 200 and calls == ["primary-model", "fallback-model"]
    assert r.headers["x-trustledger-model-role"] == "fallback"

    _live(monkeypatch, lambda req: httpx.Response(503, text="overloaded, retry in 7s"), fallback=False)
    r = env["api"].post("/ai/turn", json=TURN)
    assert r.status_code == 503 and r.json()["error"]["code"] == "waiting_capacity"
    assert r.json()["error"]["retry_after"] == 8


def test_agent_never_sends_buyer_fields_to_llm(env, monkeypatch):
    """A Studio turn built from what the Studio sources hold (release cells + brand counts) passes the guard,
    and nothing forwarded to the provider names a buyer-level field."""
    studio.FORWARDED_BODIES.clear()
    cells = env["api"].get("/console/release/cells").json()
    forwarded = []

    def handler(req: httpx.Request):
        forwarded.append(req.content.decode())
        return httpx.Response(200, content=SSE_OK, headers={"content-type": "text/event-stream"})

    _live(monkeypatch, handler)
    table = cells["marginals"][3]
    tool_output = "\n".join(json.dumps(r) for r in table["rows"][:50])
    turn = TURN | {"messages": TURN["messages"] + [
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "query_release", "arguments": '{"id":"M4"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": tool_output},
        {"role": "user", "content": json.dumps(cells["brand_counts"][:2])},
    ]}
    r = env["api"].post("/ai/turn", json=turn)
    assert r.status_code == 200, r.text
    assert forwarded and studio.FORWARDED_BODIES
    for text in forwarded + [json.dumps(b) for b in studio.FORWARDED_BODIES]:
        assert not studio.find_buyer_fields(json.loads(text))
        for f in studio.BUYER_FIELDS:
            assert f not in text.lower()
