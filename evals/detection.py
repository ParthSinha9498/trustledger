"""Detection evals: evaluate the investigation agent's ability to identify planted supply-chain issues.

Evaluates precision, recall, store/distributor attribution accuracy, false-blame rate on clean
control, step counts, and DP privacy budget expenditure.

    uv run python -m evals.detection --mock
    uv run python -m evals.detection            # live Gemini from .env
"""
import argparse
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys

from backend import config
from backend.common.llm import ToolCall, Turn
from backend.worker.agent import Investigation
from evals import harness
from evals.scenarios import SCENARIOS, Scenario


@dataclass
class ScenarioResult:
    scenario: str
    title: str
    is_problem: bool
    status: str
    confidence: str
    summary: str
    findings: list[str] = field(default_factory=list)
    steps_count: int = 0
    privacy_spent: float = 0.0
    queries_count: int = 0
    store_attributed: bool = False
    distributor_attributed: bool = False
    reason_attributed: bool = False
    correct: bool = False
    error: str | None = None
    trace: list[str] = field(default_factory=list)  # each tool call, for debugging misses


# ---------------------------------------------------------------- Offline Rule-Based Mock Agent

class ScenarioAwareMockLLM:
    """Offline mock that intelligently navigates tools based on scenario data."""

    def __init__(self):
        self.step = 0
        self.case_info = {}
        self.brand_failures = []
        self.distributor_findings = []

    def next_turn(self, messages: list[dict], tools: list[dict]) -> Turn:
        self.step += 1

        # Parse recent tool responses from messages
        for msg in reversed(messages):
            if msg.get("role") == "tool":
                try:
                    content = json.loads(msg.get("content", "{}"))
                    res = content.get("result", {})
                    if "reason_code" in res and "store_id" in res:
                        self.case_info = res
                    if "rows" in res:
                        rows = res.get("rows", [])
                        if rows and "reason_code" in rows[0]:
                            self.brand_failures = rows
                        if rows and "distributor_id" in rows[0]:
                            self.distributor_findings = rows
                except Exception:
                    pass

        # Turn 1: Get case trigger facts
        if self.step == 1:
            return Turn("Retrieve initial trigger facts for the case.",
                        [ToolCall("c1", "get_case", {})])

        # Turn 2: Query brand verification failures
        if self.step == 2:
            return Turn("Check verification failures by store and reason across the brand.",
                        [ToolCall("c2", "query_brand_node", {
                            "metric": "verification_failures",
                            "group_by": ["store_id", "reason_code"],
                        })])

        # Turn 3: Check distributor breakdown or clean path
        if self.step == 3:
            # Check if failures exist and exceed threshold
            max_fail = max((r.get("value", 0) for r in self.brand_failures), default=0)
            if max_fail <= 1:
                # Clean control path: check paypal node to satisfy validation
                return Turn("Check overall buyer volume across stores.",
                            [ToolCall("c3", "query_paypal_node", {
                                "metric": "buyers",
                                "group_by": ["store_id"],
                            })])
            else:
                return Turn("Break down verification failures by distributor.",
                            [ToolCall("c3", "query_brand_node", {
                                "metric": "verification_failures",
                                "group_by": ["store_id", "distributor_id"],
                            })])

        # Turn 4: PayPal verification
        if self.step == 4:
            max_fail = max((r.get("value", 0) for r in self.brand_failures), default=0)
            if max_fail <= 1:
                return Turn("Record conclusion for clean control.",
                            [ToolCall("c4", "record_finding", {
                                "text": "No systematic failure cluster or diversion pattern detected. Baseline noise.",
                                "citations": ["step:2", "step:3"],
                            })])
            else:
                return Turn("Corroborate buyer activity at trigger store on the PayPal side.",
                            [ToolCall("c4", "query_paypal_node", {
                                "metric": "buyers",
                                "group_by": ["store_id"],
                            })])

        # Turn 5: Record findings for problem scenarios
        if self.step == 5:
            max_fail = max((r.get("value", 0) for r in self.brand_failures), default=0)
            if max_fail <= 1:
                return Turn("Finish clean investigation.",
                            [ToolCall("c5", "finish", {
                                "summary": "No breach or anomaly identified across stores. Isolated operational anomaly.",
                                "confidence": "low",
                                "next_actions": ["Resume standard monitoring"],
                            })])

            # Problem scenarios
            store = self.case_info.get("store_id", "store_b")
            reason = self.case_info.get("reason_code", "UNKNOWN")
            dist = next((r["distributor_id"] for r in self.distributor_findings if r.get("distributor_id")), None)

            if reason == "NOT_IN_CHANNEL":
                dist_str = dist or "dist_1"
                text = f"Unauthorized inventory diversion: {dist_str} serials scanned at {store} under {reason}."
            elif reason == "ALREADY_SOLD":
                dist_str = dist or "dist_1"
                text = f"Cloned serials detected: Genuine {dist_str} serials re-scanned at {store} as {reason}."
            else:
                text = f"Counterfeit serials concentrated at rogue store {store} marked {reason}."

            return Turn("Record finding with supporting citations.",
                        [ToolCall("c5", "record_finding", {
                            "text": text,
                            "citations": ["step:2", "step:3", "step:4"],
                        })])

        # Turn 6: Finish problem investigation
        if self.step == 6:
            store = self.case_info.get("store_id", "store_b")
            reason = self.case_info.get("reason_code", "UNKNOWN")
            dist = next((r["distributor_id"] for r in self.distributor_findings if r.get("distributor_id")), None)
            dist_desc = f" linked to {dist}" if dist else ""
            summary = f"Root cause confirmed: {reason} anomaly concentrated at {store}{dist_desc}."

            return Turn("Conclude investigation with summary and actions.",
                        [ToolCall("c6", "finish", {
                            "summary": summary,
                            "confidence": "high",
                            "next_actions": [f"Inspect physical inventory at {store}", "Audit distributor shipment logs"],
                        })])

        return Turn("Conclude.", [ToolCall("c_end", "finish", {"summary": "Completed.", "confidence": "low"})])


# ---------------------------------------------------------------- Scoring

def _contains(haystack: str, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in haystack.lower()


def score_scenario(scenario: Scenario, case: dict, steps: list[dict], budget_spent: float) -> ScenarioResult:
    findings = [s["payload"].get("text", "") for s in steps if s.get("kind") == "finding"]
    summary = case.get("summary", "")
    all_text = " ".join(findings + [summary])

    gt = scenario.ground_truth
    tool_queries = sum(1 for s in steps if s.get("kind") == "tool_call")
    trace = [f'{s["payload"].get("tool")} {json.dumps(s["payload"].get("args"), sort_keys=True)}'
             for s in steps if s.get("kind") == "tool_call"]

    if not gt.is_problem:
        # Clean control: the agent will mention the trigger store (every case starts there), so mentions
        # aren't blame. A false alarm is any confidence above "low" (or none reported).
        correct = case.get("confidence") == "low"

        return ScenarioResult(
            scenario=scenario.name,
            title=scenario.title,
            is_problem=False,
            status=case.get("status", "unknown"),
            confidence=case.get("confidence") or "unknown",
            summary=summary,
            findings=findings,
            steps_count=len(steps),
            privacy_spent=round(budget_spent, 4),
            queries_count=tool_queries,
            store_attributed=True,
            distributor_attributed=True,
            reason_attributed=True,
            correct=correct,
            trace=trace,
        )

    # Problem scenario: check store, distributor, and reason attribution
    store_ok = _contains(all_text, gt.expected_store)
    dist_ok = _contains(all_text, gt.expected_distributor) if gt.expected_distributor else True
    reason_ok = _contains(all_text, gt.expected_reason)

    correct = store_ok and dist_ok and reason_ok

    return ScenarioResult(
        scenario=scenario.name,
        title=scenario.title,
        is_problem=True,
        status=case.get("status", "unknown"),
        confidence=case.get("confidence", "unknown"),
        summary=summary,
        findings=findings,
        steps_count=len(steps),
        privacy_spent=round(budget_spent, 4),
        queries_count=tool_queries,
        store_attributed=store_ok,
        distributor_attributed=dist_ok,
        reason_attributed=reason_ok,
        correct=correct,
        trace=trace,
    )


# ---------------------------------------------------------------- Runner

def run_scenario(name: str, mock: bool = True, tag_prefix: str = "det") -> ScenarioResult:
    scenario = SCENARIOS[name]
    tag = f"{tag_prefix}_{name}"
    harness.configure(tag, mock=mock)
    client_dict = harness.wire_services()
    api_client = client_dict["api"]

    try:
        scenario.build(tag)

        # Measure privacy budget spent
        from backend import db
        with db.connect("paypal_side") as c:
            row_before = c.execute("SELECT rho_spent FROM privacy_ledger WHERE brand_id=%s", (config.brand_id(),)).fetchone()
        spent_before = row_before["rho_spent"] if row_before else 0.0

        # Claim the trigger case
        claim_resp = api_client.post("/internal/cases/claim")
        assert claim_resp.status_code == 200, f"Claim failed: {claim_resp.text}"
        case = claim_resp.json().get("case")
        assert case is not None, f"No open case found for scenario {name}"

        # Run investigation
        if mock:
            llm = ScenarioAwareMockLLM()
        else:
            from backend.common.llm import OpenAICompatibleLLM
            llm = OpenAICompatibleLLM()  # always the real provider, regardless of LLM_MODE

        inv = Investigation(case, llm)
        inv.run()

        # Fetch finalized case
        case_resp = api_client.get(f"/cases/{case['case_id']}")
        assert case_resp.status_code == 200, f"Fetch case failed: {case_resp.text}"
        final_case = case_resp.json()

        # Fetch steps
        with db.connect("platform") as pc:
            steps = pc.execute(
                "SELECT * FROM case_steps WHERE case_id=%s ORDER BY n", (case["case_id"],)
            ).fetchall()

        with db.connect("paypal_side") as c:
            row_after = c.execute("SELECT rho_spent FROM privacy_ledger WHERE brand_id=%s", (config.brand_id(),)).fetchone()
        spent_after = row_after["rho_spent"] if row_after else 0.0

        result = score_scenario(scenario, final_case, steps, spent_after - spent_before)
        return result
    finally:
        from backend.common import http
        http.clear_overrides()
        harness.drop_databases(tag)


def run_all(mock: bool = True, scenario_names: list[str] | None = None, out_dir: Path | None = None,
            tag_prefix: str | None = None) -> dict:
    # Live runs get their own databases so a concurrent pytest run (which uses "det") can't drop them.
    tag_prefix = tag_prefix or ("det" if mock else "live")
    names = scenario_names or list(SCENARIOS.keys())
    results: list[ScenarioResult] = []

    for name in names:
        try:
            res = run_scenario(name, mock=mock, tag_prefix=tag_prefix)
        except Exception as e:  # e.g. provider quota: record it and keep going, never score it
            sc = SCENARIOS[name]
            res = ScenarioResult(scenario=name, title=sc.title, is_problem=sc.ground_truth.is_problem,
                                 status="error", confidence="unknown", summary="",
                                 error=f"{type(e).__name__}: {str(e)[:300]}")
        results.append(res)

    scored = [r for r in results if r.error is None]
    problem_scenarios = [r for r in scored if r.is_problem]
    clean_scenarios = [r for r in scored if not r.is_problem]

    detected_count = sum(1 for r in problem_scenarios if r.correct)
    clean_pass_count = sum(1 for r in clean_scenarios if r.correct)
    total_problems = len(problem_scenarios)
    total_clean = len(clean_scenarios)

    recall = (detected_count / total_problems) if total_problems else 1.0
    false_alarm_rate = (sum(1 for r in clean_scenarios if not r.correct) / total_clean) if total_clean else 0.0
    total_rho = sum(r.privacy_spent for r in results)

    data = {
        "mode": "mock (ScenarioAwareMockLLM)" if mock else f"live LLM ({os.environ.get('AGENT_MODEL', 'gemini')})",
        "scenarios_evaluated": len(scored),
        "scenarios_errored": [r.scenario for r in results if r.error],
        "recall": round(recall, 3),
        "false_alarm_rate": round(false_alarm_rate, 3),
        "total_rho_spent": round(total_rho, 4),
        "results": [asdict(r) for r in results],
    }

    md = markdown(data)
    harness.write_results("detection", data, md, out_dir=out_dir)
    return data


def markdown(d: dict) -> str:
    lines = [
        "# Agent Detection Evals (TODO #3)",
        "",
        f"**Mode:** {d['mode']}",
        f"- **Recall on planted issues:** {d['recall']:.0%}",
        f"- **False alarm rate on clean control:** {d['false_alarm_rate']:.0%}",
        f"- **Total DP budget spent (rho):** {d['total_rho_spent']}",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Type | Result | Store OK | Dist OK | Reason OK | Steps | Rho | Summary |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in d["results"]:
        type_str = "Problem" if r["is_problem"] else "Control"
        res_str = "**PASS**" if r["correct"] else "**FAIL**"
        s_ok = "✓" if r["store_attributed"] else "✗"
        d_ok = "✓" if r["distributor_attributed"] else "✗"
        r_ok = "✓" if r["reason_attributed"] else "✗"
        lines.append(
            f"| {r['scenario']} | {type_str} | {res_str} | {s_ok} | {d_ok} | {r_ok} | "
            f"{r['steps_count']} | {r['privacy_spent']:.4f} | {r['summary'][:60]}... |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evaluate investigation agent detection")
    ap.add_argument("--mock", action="store_true", default=True, help="Use mock agent")
    ap.add_argument("--live", dest="mock", action="store_false", help="Use live LLM from .env")
    ap.add_argument("--scenarios", nargs="+", help="Specific scenarios to evaluate")
    args = ap.parse_args(argv)

    data = run_all(mock=args.mock, scenario_names=args.scenarios)
    print(markdown(data))


if __name__ == "__main__":
    sys.exit(main())
