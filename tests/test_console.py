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
    assert any(row["store_id"] == "store_c" for row in brand["rows"])
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


def test_node_403_passed_through(env):
    api = env["api"]
    q = {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["store_id"]}}
    # Spec refused by paypal node because filter/group is not covered in release
    q2 = {"node": "paypal", "spec": {"metric": "buyers", "group_by": ["age_band", "gender"], "filters": {"week_from": 30, "week_to": 35}}}
    body = api.post("/console/run", json={"specs": [q, q2]}).json()
    assert "rows" in body["results"][0]
    refused = body["results"][1]["refused"]
    assert refused["refused"] == "NOT_IN_RELEASE"


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
    assert "The current week is 42" in fake.sent[0][0]["content"]  # planner gets the calendar, never data


# The Brand Insights example questions (keep in sync with EXAMPLES in web/app/cockpit/console/page.tsx).
INSIGHT_QUESTIONS = {
    "Where did the P8 128GB sell, by region, in the last 8 weeks?":
        ("brand", "sold_units", ["region"], {"sku": ["NMB-P8-128"], "week_from": 35, "week_to": 42}),
    "Which age bands buy the P8 128GB vs the A5?":
        ("paypal", "buyers", ["age_band", "sku"], {"sku": ["NMB-A5-64", "NMB-P8-128"]}),
    "How did weekly buyers change at Store C over the last 12 weeks?":
        ("paypal", "buyers", ["week"], {"store_id": ["store_c"], "week_from": 31, "week_to": 42}),
    "What is the spend per buyer by region?":
        ("paypal", "sum_amount", ["region"], {}),
}


def test_insight_questions_plan_and_answer(env):
    api = env["api"]
    for question, (node, metric, group_by, filters) in INSIGHT_QUESTIONS.items():
        plan = api.post("/console/plan", json={"question": question}).json()
        assert plan["specs"] == [{"node": node, "spec": {"metric": metric, "group_by": group_by, "filters": filters}}], question
        assert "Dropped" not in plan["rationale"]
        result = api.post("/console/run", json={"specs": plan["specs"]}).json()["results"][0]
        assert "refused" not in result, (question, result)
        if node == "brand":
            assert result["rows"], question  # exact business counts: always present
        else:
            # A private release: on the small test seed some or all cells can fall under the noise-scaled display
            # floor, so require a release (rows or hidden cells), not visible rows.
            assert result["rows"] or result.get("suppressed_cells", 0) > 0, (question, result)
            assert all("ci95" in row for row in result["rows"])
        if metric == "sum_amount":  # spend per buyer: each released cell has a noisy buyer count and the mean
            assert all({"buyers", "mean_spend"} <= set(row) for row in result["rows"])


def test_model_names_and_relative_weeks(monkeypatch):
    monkeypatch.setenv("CURRENT_WEEK", "20")
    f = console._filters_from("the P8 vs the A5 64GB in the past 4 weeks")
    assert f == {"sku": ["NMB-A5-64", "NMB-P8-128", "NMB-P8-256"], "week_from": 17, "week_to": 20}
    assert console._filters_from("weeks 3 to 5, not the last 4 weeks")["week_from"] == 3  # explicit weeks win
    assert console._filters_from("the last 40 weeks")["week_from"] == 1
