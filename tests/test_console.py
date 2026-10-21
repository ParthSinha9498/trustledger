"""Question console: plan -> run -> explain, in mock mode with in-process nodes."""
import json

from backend.api import console
from backend.common.llm import ToolCall, Turn


def test_mock_plan_is_deterministic_and_valid(env):
    api = env["api"]
    r = api.post("/console/plan", json={"question": "What is the age and gender of buyers at Store C in week 10?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rationale"]
    assert body == api.post("/console/plan", json={"question": "What is the age and gender of buyers at Store C in week 10?"}).json()
    s = body["specs"][0]
    assert s["node"] == "paypal"
    assert s["spec"]["metric"] == "buyers" and s["spec"]["group_by"] == ["age_band", "gender"]
    assert s["spec"]["filters"] == {"store_id": ["store_c"], "week_from": 10, "week_to": 10}


def test_mock_plan_keywords(env):
    api = env["api"]
    where = api.post("/console/plan", json={"question": "Where do verification checks fail?"}).json()["specs"]
    assert where[0]["node"] == "brand" and where[0]["spec"]["metric"] == "verification_failures"
    assert where[0]["spec"]["group_by"] == ["store_id", "reason_code"]
    dist = api.post("/console/plan", json={"question": "Which distributor's stock sells at which store?"}).json()["specs"]
    assert any(s["node"] == "brand" and s["spec"]["metric"] == "sold_units"
               and s["spec"]["group_by"] == ["store_id", "distributor_id"] for s in dist)


def test_run_brand_and_paypal_with_explanation(env):
    api = env["api"]
    specs = [
        {"node": "brand", "spec": {"metric": "verification_failures", "group_by": ["store_id"]}},
        {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["age_band"]}},
    ]
    r = api.post("/console/run", json={"specs": specs, "explain": True})
    assert r.status_code == 200, r.text
    body = r.json()
    brand, paypal = body["results"]
    assert brand["node"] == "brand" and brand["exact"] is True and brand["rows"]
    assert any(row["store_id"] == "store_b" for row in brand["rows"])
    assert paypal["node"] == "paypal" and "noise" in paypal and "suppressed_cells" in paypal
    assert all("ci95" in row for row in paypal["rows"])
    assert body["budget"]["spent"] > 0 and {"spent", "remaining", "daily"} <= set(body["budget"])
    assert isinstance(body["explanation"], str) and "PayPal-side" in body["explanation"]
    assert "payer_key" not in r.text


def test_run_refusals_keep_node_detail(env):
    api = env["api"]
    specs = [
        {"node": "brand", "spec": {"metric": "buyers"}},                                   # wrong node
        {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["distributor_id"]}},  # disallowed dim
        {"node": "paypal", "spec": {"metric": "buyers", "filters": {"payer_key": ["x"]}}},  # not in schema
    ]
    body = api.post("/console/run", json={"specs": specs, "explain": False}).json()
    codes = [r["refused"]["refused"] for r in body["results"]]
    assert codes == ["METRIC_NOT_ALLOWED", "DIMENSION_NOT_ALLOWED", "INVALID_SPEC"]
    assert body["explanation"] is None


def test_node_403_passed_through(env, monkeypatch):
    monkeypatch.setenv("PRIVACY_TOTAL_RHO", "0.01")
    api = env["api"]
    q = {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["store_id"]}}
    q2 = {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["sku"]}}
    body = api.post("/console/run", json={"specs": [q, q2]}).json()
    assert "rows" in body["results"][0]
    refused = body["results"][1]["refused"]
    assert refused["refused"] == "BUDGET_EXHAUSTED" and "budget" in refused
    assert body["budget"]["remaining"] == 0


def test_budget_passthrough(env):
    b = env["api"].get("/console/budget").json()
    node = env["paypal"].get("/v1/budget", params={"brand_id": "nimbus"}).json()
    assert b == node and {"spent", "remaining", "daily"} <= set(b)


class FakeLLM:
    """Stands in for the live provider: records every message it is sent."""

    def __init__(self):
        self.sent: list[list[dict]] = []

    def next_turn(self, messages, tools):
        self.sent.append(messages)
        return Turn("Look at failures by store, then buyers by age.", [
            ToolCall("1", "propose_brand_query", {"metric": "verification_failures", "group_by": ["store_id"]}),
            ToolCall("2", "propose_paypal_query", {"metric": "buyers", "group_by": ["distributor_id"]}),
            ToolCall("3", "propose_paypal_query", {"metric": "buyers", "group_by": ["age_band"]}),
        ])

    def complete(self, messages):
        self.sent.append(messages)
        return "Failures concentrate at one store."


def test_live_path_validates_and_explains_only_guarded_results(env, monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(console, "get_console_llm", lambda: console.LiveConsoleLLM(fake))
    api = env["api"]
    question = "secret question text about Store B"
    plan = api.post("/console/plan", json={"question": question}).json()
    assert [s["node"] for s in plan["specs"]] == ["brand", "paypal"]
    assert "Dropped 1 invalid" in plan["rationale"] and "DIMENSION_NOT_ALLOWED" in plan["rationale"]

    run = api.post("/console/run", json={"specs": plan["specs"], "explain": True}).json()
    assert run["explanation"] == "Failures concentrate at one store."
    explain_msgs = fake.sent[-1]
    payload = json.loads(explain_msgs[-1]["content"])
    assert question not in json.dumps(explain_msgs)
    assert [p["node"] for p in payload] == ["brand", "paypal"]
    allowed = {"node", "metric", "group_by", "filters", "rows", "rows_total", "suppressed_cells", "exact", "noise", "refused"}
    assert all(set(p) <= allowed for p in payload)
    assert "payer_key" not in json.dumps(fake.sent)
