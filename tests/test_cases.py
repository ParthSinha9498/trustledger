"""Case design: one case per open problem (brand, store, reason), agent re-runs only on material change."""

import json

from backend.api.paypal_client import PayPalError, paypal
from backend.common.llm import ToolCall, Turn
from backend.worker import agent
from backend.worker.main import process_one


def scan(api, serial, store="store_c", sku="NMB-P8-128"):
    return api.post("/checkout/scan", json={"serial": serial, "sku": sku, "amount": 899.0, "store_id": store}).json()


def test_failures_join_one_open_case(env):
    api = env["api"]
    first = scan(api, "FAKE-001")
    assert first["reason_code"] == "UNKNOWN_SERIAL"
    ids = {scan(api, f"FAKE-00{i}")["case_id"] for i in range(2, 5)}
    assert ids == {first["case_id"]}
    case = api.get(f"/cases/{first['case_id']}").json()
    assert case["failure_count"] == 4
    # Another store or reason is another problem.
    assert scan(api, "FAKE-005", store="store_b")["case_id"] != first["case_id"]
    assert scan(api, "X123")["case_id"] != first["case_id"]  # NOT_IN_CHANNEL at store_c


def test_rerun_only_on_material_change(env):
    api = env["api"]
    case_id = scan(api, "FAKE-001")["case_id"]
    assert process_one() is True
    assert api.get(f"/cases/{case_id}").json()["status"] == "complete"

    # Last run saw 1 failure, so a second one doubles it and re-queues the case.
    scan(api, "FAKE-002")
    assert api.get(f"/cases/{case_id}").json()["status"] == "open"
    assert process_one() is True
    scan(api, "FAKE-003")  # 3 < 2 * 2: no re-run
    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "complete" and case["failure_count"] == 3
    assert process_one() is False

    # A new SKU is a material change even without doubling.
    scan(api, "FAKE-004", sku="NMB-A5-64")
    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "open" and set(case["skus"]) == {"NMB-P8-128", "NMB-A5-64"}
    assert process_one() is True
    assert api.get(f"/cases/{case_id}").json()["run_count"] == 3


class EagerLLM:
    """Tries to finish without any PayPal-side query, then complies."""

    def __init__(self):
        self.turns = 0

    def next_turn(self, messages, tools):
        self.turns += 1
        if self.turns == 1:
            return Turn("", [ToolCall("f1", "finish", {"summary": "too early"})], {"prompt": 100, "cached": 0})
        if self.turns == 2:
            return Turn("", [ToolCall("q1", "query_paypal_node", {"metric": "buyers", "group_by": ["store_id"]})],
                        {"prompt": 200, "cached": 90})
        return Turn("", [ToolCall("f2", "finish", {"summary": "done"})], {"prompt": 300, "cached": 180})


class StubbornLLM:
    """Never finishes; the loop must stop at the turn limit."""

    def next_turn(self, messages, tools):
        return Turn("", [ToolCall("b", "get_budget", {})])


def claimed_case(env):
    api = env["api"]
    case_id = scan(api, "FAKE-001")["case_id"]
    return api.post("/internal/cases/claim", headers=env["brand"].headers).json()["case"], case_id


def test_finish_requires_paypal_query_and_logs_usage(env):
    case, case_id = claimed_case(env)
    result = agent.Investigation(case, EagerLLM()).run()
    assert result["summary"] == "done"
    steps = env["api"].get(f"/cases/{case_id}").json()["steps"]
    assert any(s["payload"].get("tool") == "query_paypal_node" for s in steps)
    usage = [s["payload"] for s in steps if s["kind"] == "usage"]
    assert usage == [{"turns": 3, "prompt": 600, "cached": 270, "completion": 0}]


def test_turn_limit_forces_finish(env):
    case, case_id = claimed_case(env)
    agent.Investigation(case, StubbornLLM()).run()
    c = env["api"].get(f"/cases/{case_id}").json()
    assert c["status"] == "complete" and "Turn limit" in c["summary"]
    assert sum(s["kind"] == "tool_call" for s in c["steps"]) == agent.MAX_STEPS


def test_mock_run_is_recorded_as_mock_not_live(env):
    """Hard rule: a scripted mock run must never be stored (and so never badged) as a live AI run."""
    case_id = scan(env["api"], "FAKE-001")["case_id"]
    assert process_one() is True
    c = env["api"].get(f"/cases/{case_id}").json()
    assert c["status"] == "complete"
    assert c["agent_mode"] == "mock" and c["agent_model"] == "scripted-mock"


class NamedLiveLLM(EagerLLM):
    model = "provider/real-model"


def test_live_run_records_real_model(env, monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    case, case_id = claimed_case(env)
    agent.Investigation(case, NamedLiveLLM()).run()
    c = env["api"].get(f"/cases/{case_id}").json()
    assert c["agent_mode"] == "live" and c["agent_model"] == "provider/real-model"


class FailingPrimaryLLM:
    model = "provider/primary-model"

    def next_turn(self, messages, tools):
        raise RuntimeError("429 Too Many Requests")


def test_fallback_run_records_fallback_model(env, monkeypatch):
    from backend.common.llm import ChainedLLM

    monkeypatch.setenv("LLM_MODE", "live")
    fallback = NamedLiveLLM()
    fallback.model = "provider/fallback-model"
    case, case_id = claimed_case(env)
    agent.Investigation(case, ChainedLLM(FailingPrimaryLLM(), fallback, is_smaller=True)).run()
    c = env["api"].get(f"/cases/{case_id}").json()
    assert c["status"] == "complete"
    assert c["agent_mode"] == "live" and c["agent_model"] == "provider/fallback-model"
    assert c["agent_reason"] == "Running on a smaller model due to free-tier limits"


def test_capture_unapproved_order_is_clean_409(env, monkeypatch):
    api = env["api"]
    chk = scan(api, "X123", store="store_a")

    def boom(order_id):
        raise PayPalError(422, {
            "name": "UNPROCESSABLE_ENTITY", "message": "The requested action could not be performed.",
            "details": [{"issue": "ORDER_NOT_APPROVED"}]})

    monkeypatch.setattr(paypal, "capture_order", boom)
    r = api.post(f"/checkout/{chk['checkout_id']}/capture")
    assert r.status_code == 409 and r.json()["detail"]["paypal_issue"] == "ORDER_NOT_APPROVED"


def test_case_rerun_returns_latest_run_and_earlier_runs(env):
    """Reproduces case_487ef88d9f's shape: 2 runs with identical findings -> API returns 1 latest set and lists 1 earlier run."""
    api = env["api"]
    case_id = scan(api, "FAKE-001")["case_id"]
    # Run 1
    assert process_one() is True
    c1 = api.get(f"/cases/{case_id}").json()
    assert c1["status"] == "complete"
    assert c1["run_count"] == 1
    assert c1["earlier_runs"] == []
    steps_1 = c1["steps"]
    findings_1 = [s for s in steps_1 if s["kind"] == "finding"]
    assert len(findings_1) == 1
    assert all(s.get("run") == 1 for s in steps_1)

    # Trigger rerun on material change (second failure)
    scan(api, "FAKE-002")
    c_open = api.get(f"/cases/{case_id}").json()
    assert c_open["status"] == "open"
    # Run 2
    assert process_one() is True
    c2 = api.get(f"/cases/{case_id}").json()
    assert c2["status"] == "complete"
    assert c2["run_count"] == 2

    # Earlier runs listed with step counts
    assert len(c2["earlier_runs"]) == 1
    assert c2["earlier_runs"][0]["run"] == 1
    assert c2["earlier_runs"][0]["step_count"] == len(steps_1)

    # c2["steps"] only contains run 2's steps, so only ONE finding is returned (no duplicate finding!)
    steps_2 = c2["steps"]
    assert all(s.get("run") == 2 for s in steps_2)
    findings_2 = [s for s in steps_2 if s["kind"] == "finding"]
    assert len(findings_2) == 1

    # list_cases also reports findings count for the latest run only
    cases_list = api.get("/cases").json()
    case_row = next(x for x in cases_list if x["case_id"] == case_id)
    assert case_row["findings"] == 1
    assert case_row["step_count"] == len(steps_2)

    # Query param ?run=1 retrieves run 1's steps
    run_1_resp = api.get(f"/cases/{case_id}?run=1").json()
    assert len(run_1_resp["steps"]) == len(steps_1)
    assert all(s.get("run") == 1 for s in run_1_resp["steps"])

    # Query param ?include_earlier_steps=true embeds earlier steps in earlier_runs
    embed_resp = api.get(f"/cases/{case_id}?include_earlier_steps=true").json()
    assert len(embed_resp["earlier_runs"][0]["steps"]) == len(steps_1)


class PlainTextThenSummaryLLM:
    def __init__(self):
        self.turns = 0

    def next_turn(self, messages, tools):
        self.turns += 1
        if self.turns == 1:
            # Plain text turn without tool calls: MUST NOT end the run
            return Turn("I am reviewing the case data.", [])
        if self.turns == 2:
            return Turn("", [ToolCall("q1", "query_paypal_node", {"metric": "buyers", "group_by": ["store_id"]})])
        # Turn 3: JSON summary in content without tool calls: MUST finish the run
        return Turn(json.dumps({"summary": "Root cause identified.", "confidence": "high"}), [])


def test_plain_text_turn_continues_and_json_summary_finishes(env):
    case, case_id = claimed_case(env)
    llm = PlainTextThenSummaryLLM()
    res = agent.Investigation(case, llm).run()
    assert res["summary"] == "Root cause identified."
    assert llm.turns == 3
    c = env["api"].get(f"/cases/{case_id}").json()
    assert c["status"] == "complete"
    assert c["summary"] == "Root cause identified."

