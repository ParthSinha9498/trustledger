import json
from unittest.mock import MagicMock

from backend.common.llm import ChainedLLM, Turn, ToolCall
from backend.worker.main import process_one
from backend.worker.replay import play_case_replay, load_replay


def test_chained_llm_falls_back_on_error():
    # Primary fails with 429 / error
    primary = MagicMock()
    primary.model = "primary-model"
    primary.next_turn.side_effect = RuntimeError("Rate limit exceeded 429")

    # Fallback succeeds
    fallback = MagicMock()
    fallback.model = "fallback-8b"
    fallback.next_turn.return_value = Turn(content="Fallback investigation thought", tool_calls=[])

    chain = ChainedLLM(primary, fallback, is_smaller=True)
    res = chain.next_turn([{"role": "user", "content": "hi"}], [])

    assert res.content == "Fallback investigation thought"
    assert chain.used_fallback is True
    assert chain.model == "fallback-8b"
    assert chain.is_smaller is True

    # Second turn stays on fallback (sticky per run)
    fallback.next_turn.return_value = Turn(content="Second turn", tool_calls=[])
    res2 = chain.next_turn([{"role": "user", "content": "next"}], [])
    assert res2.content == "Second turn"
    assert primary.next_turn.call_count == 1  # Not called again


def test_replay_loader_loads_test_fixture():
    replay = load_replay("case_replay_TEST_ONLY.json")
    assert "replay_id" in replay
    assert "steps" in replay
    assert len(replay["steps"]) > 0
    assert replay["model"] == "openai/gpt-oss-120b"


def test_play_case_replay(env):
    api = env["api"]
    # Open a test case
    scan = api.post("/checkout/scan", json={"store_id": "store_b", "serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}).json()
    case_id = scan.get("case_id")
    assert case_id is not None

    # Play replay (defers to waiting_capacity, no grafted foreign steps)
    res = play_case_replay(case_id, "Demo AI free-tier quota reached")
    assert res["status"] == "waiting_capacity"
    assert res["agent_reason"] == "Demo AI free-tier quota reached"

    # Verify through API
    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "waiting_capacity"
    assert case["agent_reason"] == "Demo AI free-tier quota reached"
    assert len(case["steps"]) == 0


def test_worker_falls_back_to_replay_when_llm_fails(env, monkeypatch):
    api = env["api"]
    scan = api.post("/checkout/scan", json={"store_id": "store_b", "serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}).json()
    case_id = scan.get("case_id")
    assert case_id is not None

    # Mock get_llm to raise 429
    def failing_llm():
        m = MagicMock()
        m.next_turn.side_effect = RuntimeError("429 Too Many Requests")
        return m

    monkeypatch.setattr("backend.worker.main.get_llm", failing_llm)

    # Run worker process_one
    worked = process_one()
    assert worked is True

    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "waiting_capacity"
    assert case["agent_reason"] == "Demo AI free-tier quota reached"
    # Only the runner's own partial steps (e.g. usage), no foreign replay steps grafted
    assert not any(s.get("payload", {}).get("tool") == "get_case" for s in case["steps"])


def test_worker_falls_back_to_replay_when_budget_exhausted(env, monkeypatch):
    api = env["api"]
    scan = api.post("/checkout/scan", json={"store_id": "store_b", "serial": "X123", "sku": "NMB-P8-128", "amount": 899.0}).json()
    case_id = scan.get("case_id")
    assert case_id is not None

    # Mock budget check to return exhausted
    monkeypatch.setattr("backend.worker.main._is_budget_exhausted", lambda brand: True)

    worked = process_one()
    assert worked is True

    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "waiting_capacity"
    assert case["agent_reason"] == "Privacy budget used up: that's the guarantee working"
    assert len(case["steps"]) == 0
