"""LLM client: a provider-side tool-call rejection is fed back to the model instead of crashing the case."""
from types import SimpleNamespace

import httpx
import pytest
from openai import BadRequestError

from backend.common.llm import OpenAICompatibleLLM

REJECTED = {"message": "parameters for tool query_brand_node did not match schema: `/group_by`: maxItems: got 3, want 2",
            "type": "invalid_request_error", "code": "tool_use_failed"}


def _bad_request(body):
    resp = httpx.Response(400, request=httpx.Request("POST", "https://llm.test/chat/completions"))
    return BadRequestError("Error code: 400", response=resp, body=body)


def _ok():
    msg = SimpleNamespace(content="done", tool_calls=None)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=2, prompt_tokens_details=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


def _llm(responses, seen):
    def create(**kw):
        seen.append(kw["messages"])
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    llm = OpenAICompatibleLLM.__new__(OpenAICompatibleLLM)
    llm.model = "test"
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return llm


def test_rejected_tool_call_is_retried_with_the_error():
    seen, history = [], [{"role": "user", "content": "investigate"}]
    turn = _llm([_bad_request(REJECTED), _ok()], seen).next_turn(history, tools=[])
    assert turn.content == "done"
    assert "maxItems" in seen[1][-1]["content"]  # the model is told what was wrong
    assert history == [{"role": "user", "content": "investigate"}]  # caller's history untouched


def test_gives_up_after_two_fixes_and_ignores_other_400s():
    with pytest.raises(BadRequestError):
        _llm([_bad_request(REJECTED)] * 3, []).next_turn([], tools=[])
    with pytest.raises(BadRequestError):
        _llm([_bad_request({"message": "bad model", "code": "model_not_found"})], []).next_turn([], tools=[])
