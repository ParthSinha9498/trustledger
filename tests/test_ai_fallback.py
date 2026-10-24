import json
from pathlib import Path
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
    fixture_path = Path(__file__).parent / "fixtures" / "case_af739ac755.json"
    replay = load_replay(str(fixture_path))
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


def test_waiting_capacity_sets_retry_after_and_prevents_immediate_reclaim(env, monkeypatch):
    api = env["api"]
    events = []
    monkeypatch.setattr("backend.common.notify.case_event", lambda ev, c, s=None: events.append((ev, c["case_id"], s)))

    scan = api.post("/checkout/scan", json={"store_id": "store_b", "serial": "X999", "sku": "NMB-P8-128", "amount": 899.0}).json()
    case_id = scan.get("case_id")
    assert case_id is not None

    # Force 429 so it finishes as waiting_capacity
    def failing_llm():
        m = MagicMock()
        m.next_turn.side_effect = RuntimeError("429 Too Many Requests")
        return m

    monkeypatch.setattr("backend.worker.main.get_llm", failing_llm)
    worked = process_one()
    assert worked is True

    # Check case in DB has retry_after populated
    case = api.get(f"/cases/{case_id}").json()
    assert case["status"] == "waiting_capacity"
    assert case.get("retry_after") is not None
    assert any(ev[0] == "case_deferred" and ev[1] == case_id for ev in events)

    # Immediate reclaim must NOT return this case (backoff active)
    from backend import config
    claim_res = api.post("/internal/cases/claim", headers={"X-Node-Token": config.node_token()}).json()
    assert claim_res.get("case") is None


def test_agent_model_required_for_live_mode(monkeypatch):
    from backend.common import llm
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    monkeypatch.setenv("LLM_MODE", "live")
    import pytest
    with pytest.raises(RuntimeError, match="AGENT_MODEL"):
        llm.get_llm()


def test_export_replay_refuses_non_live_case(env, tmp_path):
    import pytest
    from backend import db
    from scripts.export_replay import export_case_replay

    with db.connect("platform") as pc:
        pc.execute(
            "INSERT INTO cases (case_id, status, agent_mode, agent_model, summary) VALUES (%s, %s, %s, %s, %s)",
            ("case_mock_test", "complete", "mock", "scripted-mock", "Mock summary")
        )

    with pytest.raises(ValueError, match="not a genuine live run"):
        export_case_replay("case_mock_test", tmp_path / "mock_replay.json")


def test_export_replay_refuses_legacy_mock_row(env, tmp_path):
    """Before #51, mock runs had mode='live', model='live', and LLM_MODE=mock summary."""
    import pytest
    from backend import db
    from scripts.export_replay import export_case_replay

    with db.connect("platform") as pc:
        pc.execute(
            "INSERT INTO cases (case_id, status, agent_mode, agent_model, summary) VALUES (%s, %s, %s, %s, %s)",
            ("case_legacy_mock", "complete", "live", "live", "Scripted mock investigation (LLM_MODE=mock).")
        )

    with pytest.raises(ValueError, match="not a genuine live run"):
        export_case_replay("case_legacy_mock", tmp_path / "legacy_replay.json")


def test_export_replay_refuses_disguised_mock_models(env, tmp_path):
    import pytest
    from backend import db
    from scripts.export_replay import export_case_replay

    cases = [
        ("case_empty_model", "live", "", "Investigated."),
        ("case_named_mock", "live", "my-mock-v2", "Investigated."),
        ("case_scripted_model", "live", "scripted_runner", "Investigated."),
    ]
    with db.connect("platform") as pc:
        for cid, mode, model, summary in cases:
            pc.execute(
                "INSERT INTO cases (case_id, status, agent_mode, agent_model, summary) VALUES (%s, %s, %s, %s, %s)",
                (cid, "complete", mode, model, summary)
            )

    for cid, _, _, _ in cases:
        with pytest.raises(ValueError, match="not a genuine live run"):
            export_case_replay(cid, tmp_path / f"{cid}.json")


def test_export_replay_allows_live_case(env, tmp_path):
    from backend import db
    from scripts.export_replay import export_case_replay

    with db.connect("platform") as pc:
        pc.execute(
            "INSERT INTO cases (case_id, status, agent_mode, agent_model, summary) VALUES (%s, %s, %s, %s, %s)",
            ("case_live_test", "complete", "live", "provider/real-model", "Live summary")
        )

    out = export_case_replay("case_live_test", tmp_path / "live_replay.json")
    assert out.exists()
    import json
    data = json.loads(out.read_text())
    assert data["source_case_id"] == "case_live_test"
    assert data["model"] == "provider/real-model"

