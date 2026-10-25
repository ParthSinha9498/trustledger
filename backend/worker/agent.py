"""Investigation agent: plans queries across both nodes, never sees raw rows, cites its steps."""
import json

from backend import config
from backend.common import http
from backend.common.query_spec import tool_parameters

MAX_STEPS = int(config.env("AGENT_MAX_STEPS", "16"))
FINDINGS_BY = MAX_STEPS - 4  # nudge to record findings from this turn on

SYSTEM_PROMPT = """You investigate failed product verifications for a brand.

Facts you must respect:
- The brand already decided this product failed verification. You never declare a product counterfeit
  and never decide authenticity yourself.
- You only see aggregates. Brand-side results are exact counts about businesses. PayPal-side results
  are differentially private: each value has a ±ci95 interval, small cells are suppressed, and each
  new query spends privacy budget from a fixed total (about 25 count queries per brand). Repeating an
  identical query is free but returns the same answer.
- A difference smaller than the combined ci95 of the two values is not evidence. Prefer coarse
  groupings (store_id, region) first, then narrow down only where something stands out.
- Spend budget only when a PayPal-side answer would change your conclusion. Check get_budget if unsure.

How to work:
- You have a fixed number of turns; each tool result tells you how many are left.
- Start with get_case. A case groups every failed scan with the same store and reason, so get_case
  reports how many failures and which SKUs it covers. Then choose each next query based on what the last result showed.
- Use record_finding for each conclusion, citing the step numbers that support it.
- Describe suspicious links carefully: "earliest observed point of divergence in the available evidence".
  Never say "exactly", never claim intent or guilt, and never name anyone as responsible. Do name, by ID,
  the store, distributor_id, reason_code and weeks where the evidence diverges: that is what the brand needs.
- Trace the stock: for out-of-channel or already-sold failures, group the failures and the brand's sales by
  distributor_id to see whose shipments the failing serials came from.
- confidence: "high" only when brand-side and PayPal-side evidence independently point to the same store and
  link; "medium" when one side clearly does and the other doesn't contradict it; "low" when the failures are
  few or within normal noise. A single isolated failure is not a pattern: say so and use "low".
- Make at least one PayPal-side query before finishing: it is the independent view of the same stores.
- Record your findings before you run low on turns, then finish(summary, confidence, next_actions)
  when the evidence is sufficient or the budget is spent.
"""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_case", "description": "Facts about the failed verification that opened this case.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "query_brand_node",
        "description": "Exact aggregate counts from the brand's own data: shipments, sales by store and "
                       "distributor, verification failures by reason.",
        "parameters": tool_parameters("brand")}},
    {"type": "function", "function": {
        "name": "query_paypal_node",
        "description": "Differentially private aggregates of PayPal-side transactions (distinct buyers, or "
                       "spend with buyers and mean spend, by store, region, sku, week, age band, gender). "
                       "Each value has a ±ci95. Answered from the brand's one-time private release at no extra privacy "
                       "cost; questions the release cannot answer are refused (NOT_IN_RELEASE).",
        "parameters": tool_parameters("paypal")}},
    {"type": "function", "function": {
        "name": "get_budget", "description": "The brand's lifetime PayPal-side privacy budget (fixed, never resets).",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "record_finding", "description": "Record one finding with citations to step numbers.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
            "citations": {"type": "array", "items": {"type": "string"}}},
            "required": ["text", "citations"]}}},
    {"type": "function", "function": {
        "name": "finish", "description": "End the investigation with a summary.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "next_actions": {"type": "array", "items": {"type": "string"}}},
            "required": ["summary", "confidence"]}}},
]


class Investigation:
    def __init__(self, case: dict, llm) -> None:
        self.case = case
        self.llm = llm
        self.api = http.client(config.api_url())

    def log(self, kind: str, payload: dict) -> int:
        run = self.case.get("run_count") or 1
        r = self.api.post(f"/internal/cases/{self.case['case_id']}/steps", json={"kind": kind, "payload": payload, "run": run})
        r.raise_for_status()
        return r.json()["n"]

    def _query(self, node_url: str, args: dict) -> dict:
        with http.client(node_url) as c:
            r = c.post("/v1/query", json={"brand_id": self.case["brand_id"], "spec": args,
                                          "purpose": f"case:{self.case['case_id']}"})
            if r.status_code in (403, 422):
                return {"refused": r.json().get("detail")}
            r.raise_for_status()
            return r.json()

    def run_tool(self, name: str, args: dict) -> dict:
        if name == "get_case":
            c = self.case
            return {"store_id": c["store_id"], "sku": c["sku"], "reason_code": c["reason_code"],
                    "failure_count": c.get("failure_count", 1), "skus": c.get("skus") or [c["sku"]],
                    "investigation_run": c.get("run_count", 1), "current_week": config.current_week()}
        if name == "query_brand_node":
            return self._query(config.brand_node_url(), args)
        if name == "query_paypal_node":
            return self._query(config.paypal_node_url(), args)
        if name == "get_budget":
            with http.client(config.paypal_node_url()) as c:
                return c.get("/v1/budget", params={"brand_id": self.case["brand_id"]}).json()
        if name == "record_finding":
            n = self.log("finding", args)
            return {"recorded": True, "step": n}
        return {"error": f"unknown tool {name}"}

    def run(self) -> dict:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Investigate case {self.case['case_id']}."},
        ]
        usage = {"turns": 0, "prompt": 0, "cached": 0, "completion": 0}
        paypal_queried = has_findings = False
        try:
            for turn_no in range(1, MAX_STEPS + 1):
                left = MAX_STEPS - turn_no
                if left == 0:
                    messages.append({"role": "user", "content": "Last turn: call finish now with your summary."})
                elif turn_no == FINDINGS_BY and not has_findings:
                    messages.append({"role": "user", "content": "Record your findings with record_finding now; "
                                                                "only a few turns are left."})
                turn = self.llm.next_turn(messages, TOOLS)
                usage["turns"] += 1
                for k in ("prompt", "cached", "completion"):
                    usage[k] += turn.usage.get(k, 0)
                messages.append(turn.as_message())
                if turn.content:
                    self.log("thought", {"text": turn.content})
                if not turn.tool_calls:
                    if turn.content:
                        try:
                            data = json.loads(turn.content.strip())
                            if isinstance(data, dict) and "summary" in data:
                                self._finish("complete", data)
                                return data
                        except Exception:
                            pass
                    if left > 0:
                        messages.append({"role": "user", "content": "Please invoke a tool to continue or call finish."})
                        continue
                    break
                for call in turn.tool_calls:
                    if call.name == "finish":
                        if not paypal_queried and left > 0:
                            result = {"error": "Make at least one query_paypal_node call before finishing."}
                            messages.append({"role": "tool", "tool_call_id": call.id,
                                             "content": json.dumps({"result": result, "turns_left": left})})
                            continue
                        self._finish("complete", call.arguments)
                        return call.arguments
                    step = self.log("tool_call", {"tool": call.name, "args": call.arguments})
                    result = self.run_tool(call.name, call.arguments)
                    paypal_queried |= call.name == "query_paypal_node"
                    has_findings |= call.name == "record_finding"
                    if call.name != "record_finding":
                        self.log("tool_result", {"tool": call.name, "for_step": step, "result": result})
                    messages.append({"role": "tool", "tool_call_id": call.id,
                                     "content": json.dumps({"step": step, "result": result, "turns_left": left})})
            summary = {"summary": "Turn limit reached before the agent finished.", "confidence": "low"}
            self._finish("complete", summary)
            return summary
        finally:
            # Implicit prompt caching: the fixed prompt + tools prefix and earlier turns are billed at a discount.
            self.log("usage", usage)

    def _finish(self, status: str, args: dict, agent_reason: str | None = None) -> None:
        text = args.get("summary", "")
        if args.get("next_actions"):
            text += "\n\nNext actions:\n" + "\n".join(f"- {a}" for a in args["next_actions"])
        payload = {
            "status": status,
            "summary": text,
            "confidence": args.get("confidence"),
            # Record what actually ran: "mock" for the scripted stand-in, never a default "live".
            "agent_mode": agent_mode_of(self.llm),
            "agent_model": model_of(self.llm),
            "agent_reason": agent_reason,
        }
        if agent_reason is None and getattr(self.llm, "used_fallback", False) and getattr(self.llm, "is_smaller", False):
            payload["agent_reason"] = "Running on a smaller model due to free-tier limits"
        self.api.post(f"/internal/cases/{self.case['case_id']}/finish", json=payload).raise_for_status()


def agent_mode_of(llm) -> str:
    """"mock" for the scripted stand-in (or whenever LLM_MODE=mock), else "live"."""
    if getattr(llm, "mode", None) == "mock" or config.env("LLM_MODE", "live") == "mock":
        return "mock"
    return "live"


def model_of(llm) -> str | None:
    """The model name that actually answered (the fallback's, if the chain switched); None if unknown."""
    m = getattr(llm, "model", None)
    return m if isinstance(m, str) and m else None
