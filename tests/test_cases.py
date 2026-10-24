"""Case design: one case per open problem (brand, store, reason), agent re-runs only on material change."""

from backend.api.paypal_client import PayPalError, paypal
from backend.common.llm import ToolCall, Turn
from backend.worker import agent
from backend.worker.main import process_one


def scan(api, serial, store="store_b", sku="NMB-P8-128"):
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
    assert scan(api, "FAKE-005", store="store_c")["case_id"] != first["case_id"]
    assert scan(api, "X123")["case_id"] != first["case_id"]  # NOT_IN_CHANNEL at store_b


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
