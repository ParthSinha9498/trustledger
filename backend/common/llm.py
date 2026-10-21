"""Provider-neutral LLM client over the OpenAI-compatible chat API.

Gemini (default):  LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
Groq:              LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODE=mock uses a scripted stand-in so tests and offline dev run without a key.
"""
import json
import re
import time
from dataclasses import dataclass, field

from backend import config

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    # Provider extras echoed back verbatim (Gemini 3 needs extra_content.google.thought_signature).
    extra: dict = field(default_factory=dict)


@dataclass
class Turn:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Token usage for this turn: prompt, cached (implicit prompt cache hits), completion.
    usage: dict = field(default_factory=dict)

    def as_message(self) -> dict:
        msg: dict = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": t.id, "type": "function",
                 "function": {"name": t.name, "arguments": json.dumps(t.arguments)}, **t.extra}
                for t in self.tool_calls
            ]
        return msg


class OpenAICompatibleLLM:
    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.model = model or config.env("AGENT_MODEL", "gemini-3.5-flash")
        self.client = OpenAI(
            api_key=config.env("LLM_API_KEY", ""),
            base_url=config.env("LLM_BASE_URL", GEMINI_BASE),
            max_retries=2,  # transient errors; 429s are paced in next_turn
        )

    def next_turn(self, messages: list[dict], tools: list[dict]) -> Turn:
        from openai import BadRequestError, RateLimitError

        sent, fixes = list(messages), 0
        for attempt in range(6):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, messages=sent, tools=tools, tool_choice="auto"
                )
                break
            except BadRequestError as e:
                # Groq validates tool calls server-side and rejects the whole turn (bad arguments, or output it
                # couldn't parse). Tell the model and let it try again; the caller's history is left untouched.
                code = _error_code(e)
                if code not in ("tool_use_failed", "output_parse_failed") or fixes == 2 or attempt == 5:
                    raise
                fixes += 1
                hint = (f"Your last tool call was rejected: {_error_message(e)} "
                        "Fix the arguments to match the tool schema and call it again."
                        if code == "tool_use_failed" else
                        "Your last reply could not be parsed. Reply with one valid tool call.")
                sent = sent + [{"role": "user", "content": hint}]
            except RateLimitError as e:
                # Free tiers allow a few requests per minute; wait as long as the provider asks.
                if attempt == 5:
                    raise
                wait = _retry_after(str(e)) or 15 * (attempt + 1)
                if wait > 300:  # a daily quota, not a per-minute limit: fail now rather than stall the case
                    raise
                time.sleep(wait)
        m = resp.choices[0].message
        calls = [
            ToolCall(id=c.id, name=c.function.name, arguments=json.loads(c.function.arguments or "{}"),
                     extra=dict(c.model_extra or {}))
            for c in (m.tool_calls or [])
        ]
        u = resp.usage
        details = getattr(u, "prompt_tokens_details", None) if u else None
        usage = {"prompt": u.prompt_tokens, "completion": u.completion_tokens,
                 "cached": (getattr(details, "cached_tokens", None) or 0)} if u else {}
        return Turn(content=m.content or "", tool_calls=calls, usage=usage)


def _retry_after(msg: str) -> float | None:
    """Seconds to wait from a 429 message: Gemini says "retry in 12.3s", Groq "try again in 1m29.8s" or "520ms"."""
    m = re.search(r"(?:retry|try again) in ((?:[\d.]+(?:ms|h|m|s))+)", msg, re.IGNORECASE)
    if not m:
        return None
    scale = {"ms": 0.001, "h": 3600, "m": 60, "s": 1}
    return sum(float(n) * scale[u.lower()] for n, u in re.findall(r"([\d.]+)(ms|h|m|s)", m.group(1), re.I)) + 1


def _error_body(e) -> dict:
    body = getattr(e, "body", None)
    return (body.get("error", body) if isinstance(body, dict) else {}) or {}


def _error_code(e) -> str | None:
    return _error_body(e).get("code")


def _error_message(e) -> str:
    return str(_error_body(e).get("message") or e)[:500]


def get_llm():
    if config.env("LLM_MODE", "live") == "mock":
        from backend.worker.mock_llm import ScriptedLLM

        return ScriptedLLM()
    return OpenAICompatibleLLM()
