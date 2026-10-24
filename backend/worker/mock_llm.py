"""Scripted stand-in for offline dev and tests. NOT the real agent: it always runs the same plan."""
from backend.common.llm import ToolCall, Turn


class ScriptedLLM:
    mode = "mock"           # recorded on the case as agent_mode, so a mock run is never badged as live AI
    model = "scripted-mock"

    def __init__(self) -> None:
        self.i = 0

    def next_turn(self, messages: list[dict], tools: list[dict]) -> Turn:
        self.i += 1
        plan = [
            Turn("Start from the trigger facts.", [ToolCall("c1", "get_case", {})]),
            Turn("Where are verification failures concentrated?",
                 [ToolCall("c2", "query_brand_node",
                           {"metric": "verification_failures", "group_by": ["store_id", "reason_code"]})]),
            Turn("Which distributors' stock is selling where?",
                 [ToolCall("c3", "query_brand_node",
                           {"metric": "sold_units", "group_by": ["store_id", "distributor_id"]})]),
            Turn("Compare buyer volume by store on the PayPal side.",
                 [ToolCall("c4", "query_paypal_node", {"metric": "buyers", "group_by": ["store_id"]})]),
            Turn("Record what the evidence shows.",
                 [ToolCall("c5", "record_finding",
                           {"text": "Verification failures cluster at the trigger store.",
                            "citations": ["step:6"]})]),
            Turn("Done.", [ToolCall("c6", "finish",
                                    {"summary": "Scripted mock investigation (LLM_MODE=mock).",
                                     "confidence": "low"})]),
        ]
        return plan[min(self.i, len(plan)) - 1]
