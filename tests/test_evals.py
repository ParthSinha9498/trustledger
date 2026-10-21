"""Test evals: detection on planted scenarios and redteam privacy battery.

Runs completely offline (mock LLM, mock PayPal).
"""
import os

import pytest

from evals import detection, redteam
from evals.scenarios import SCENARIOS

PID = os.getpid()  # unique DB names so parallel pytest runs (e.g. two agents) don't collide


@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
def test_detection_single_scenario(scenario_name: str):
    res = detection.run_scenario(scenario_name, mock=True, tag_prefix=f"test{PID}_{scenario_name}")
    assert res.correct, (
        f"Scenario {scenario_name} failed attribution or clean check: "
        f"store={res.store_attributed}, dist={res.distributor_attributed}, reason={res.reason_attributed}, "
        f"summary='{res.summary}', findings={res.findings}"
    )
    if res.is_problem:
        assert res.store_attributed
        assert res.reason_attributed
    else:
        assert res.confidence != "high"


def test_detection_run_all_metrics(tmp_path):
    summary = detection.run_all(mock=True, out_dir=tmp_path, tag_prefix=f"det{PID}")  # never overwrite committed results
    assert summary["scenarios_evaluated"] == len(SCENARIOS)
    assert summary["recall"] == 1.0, f"Expected 100% recall, got {summary['recall']}"
    assert summary["false_alarm_rate"] == 0.0, f"Expected 0% false alarms, got {summary['false_alarm_rate']}"
    assert summary["total_rho_spent"] > 0, "DP budget should have been spent for queries"


def test_redteam_all_attacks_blocked(tmp_path):
    """Assert that 0 attacks succeed in the scripted red-team privacy battery."""
    # Run a full battery of all 11 attacks with fast membership trials
    res = redteam.run(
        attempts=11,
        mock=True,
        small=True,
        tag=f"test_rt{PID}",
        membership_trials=40,
        keep_db=False,
        out_dir=tmp_path,
    )
    assert res["succeeded"] == 0, f"Expected 0 successful attacks, but {res['succeeded']} succeeded"
    assert res["blocked"] == 11, f"Expected all 11 attacks blocked, got {res['blocked']}"
    for check in res["checks"]:
        assert check["passed"], f"Privacy check failed: {check}"
