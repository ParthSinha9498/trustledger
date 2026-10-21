"""Astropods entrypoint: the existing investigation agent behind the Astropods messaging protocol.

    python -m backend.worker.astro        # inside the Astropods container (docker/astro.Dockerfile)

Chat messages:
    next                    claim the oldest open case and investigate it (what the worker does)
    investigate case_ab12   re-run the investigation for one case (steps are appended)

Optional: `astropods-adapter-core` (and the OpenTelemetry packages) are NOT project dependencies. They
are installed only in docker/astro.Dockerfile. Importing this module never requires them; only main()
does. See docs/ASTROPODS.md.

Privacy: the agent runs in Astropods' cloud and its LLM calls go through their gateway. It only ever
receives what the nodes return, which is aggregates (exact brand-side counts about businesses, DP-noised
PayPal-side cells). As defense in depth, every tool result is scrubbed of buyer-level keys before the LLM
or a trace can see it, and prompt/completion text is kept off spans (TRACELOOP_TRACE_CONTENT=false).
"""
from __future__ import annotations

import asyncio
import os
import re
from typing import Any

# Never put prompt or completion text on spans. Forced, not defaulted: this must not be switched on by
# a stray deploy input.
os.environ["TRACELOOP_TRACE_CONTENT"] = "false"

from backend import config  # noqa: E402
from backend.common import http  # noqa: E402
from backend.common.llm import get_llm  # noqa: E402
from backend.worker.agent import SYSTEM_PROMPT, Investigation  # noqa: E402

# Keys that would identify a buyer or a single sale. Nodes never return them; if one ever did, it is
# dropped here before reaching the LLM provider, the chat, or a trace.
BLOCKED_KEYS = frozenset({
    "payer_ref", "payer_id", "buyer_id", "buyer", "email", "name", "phone", "address",
    "order_id", "paypal_order_id", "serial", "sold_order_id", "transaction_id",
})
CASE_ID = re.compile(r"\bcase_[0-9a-f]+\b")


def use_astro_gateway() -> None:
    """Point the OpenAI-compatible client at the Astro AI Gateway when it is injected (note the /v1)."""
    gw = os.environ.get("ASTRO_GATEWAY_URL")
    if not gw:
        return
    os.environ["LLM_BASE_URL"] = gw.rstrip("/") + "/v1"
    os.environ["LLM_API_KEY"] = os.environ.get("ASTRO_GATEWAY_API_KEY", "")
    os.environ["AGENT_MODEL"] = os.environ.get("MODEL_DEFAULT", "claude-haiku-4-5")
    os.environ.setdefault("LLM_MODE", "live")


def scrub(value: Any) -> Any:
    """Recursively drop buyer-level keys from a tool result."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if k.lower() not in BLOCKED_KEYS}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


class GuardedInvestigation(Investigation):
    """The unchanged agent loop, with scrubbed tool results, per-tool spans and a step callback."""

    def __init__(self, case: dict, llm, on_step=None) -> None:
        super().__init__(case, llm)
        self.on_step = on_step or (lambda kind, payload: None)

    def run_tool(self, name: str, args: dict) -> dict:
        tracer = _tracer()
        if tracer is None:
            return scrub(super().run_tool(name, args))
        with tracer.start_as_current_span(f"tool.{name}") as span:
            span.set_attribute("trustledger.case_id", self.case["case_id"])
            span.set_attribute("trustledger.tool", name)
            result = scrub(super().run_tool(name, args))
            # Metadata only, never the result itself.
            if isinstance(result, dict):
                span.set_attribute("trustledger.refused", bool(result.get("refused")))
                span.set_attribute("trustledger.rows", len(result.get("rows") or []))
            return result

    def log(self, kind: str, payload: dict) -> int:
        n = super().log(kind, payload)
        self.on_step(kind, payload)
        return n


def _tracer():
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    return trace.get_tracer("trustledger")


def setup_tracing() -> None:
    """OTLP export to Astropods. The endpoint is only injected for deployed agents."""
    ep = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not ep:
        return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.openai import OpenAIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    tp = TracerProvider(resource=Resource.create({
        "service.name": os.environ.get("ASTRO_AGENT_NAME", "trustledger-investigator"),
        "service.version": os.environ.get("ASTRO_AGENT_BUILD", "dev")}))
    tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=ep.rstrip("/") + "/v1/traces")))
    trace.set_tracer_provider(tp)
    OpenAIInstrumentor().instrument()  # one span per chat.completions call; content off (see top)


def _step_status(kind: str, payload: dict) -> str | None:
    """A short, data-free status line for the chat."""
    if kind == "tool_call":
        return f"Running {payload.get('tool', 'tool')}..."
    if kind == "finding":
        return "Recorded a finding."
    return None


def claim_case(prompt: str) -> dict | None:
    with http.client(config.api_url()) as c:
        m = CASE_ID.search(prompt or "")
        if m:
            r = c.get(f"/cases/{m.group(0)}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            case = r.json()
            case.pop("steps", None)
            return case
        return c.post("/internal/cases/claim").json()["case"]


class Investigator:
    """Astropods AgentAdapter (duck-typed protocol from astropods-adapter-core)."""

    name = "TrustLedger Investigator"

    async def stream(self, prompt: str, hooks, options) -> None:
        loop = asyncio.get_running_loop()

        def status(text: str) -> None:  # hooks are called on the event loop thread
            loop.call_soon_threadsafe(hooks.on_status_update, {"status": "CUSTOM", "custom_message": text})

        def on_step(kind: str, payload: dict) -> None:
            text = _step_status(kind, payload)
            if text:
                status(text)

        def run() -> tuple[dict | None, dict | None]:
            case = claim_case(prompt)
            if case is None:
                return None, None
            status(f"Investigating {case['case_id']} ({case.get('reason_code')} at {case.get('store_id')})")
            inv = GuardedInvestigation(case, get_llm(), on_step=on_step)
            try:
                return case, inv.run()
            except Exception as e:
                inv._finish("failed", {"summary": f"Investigation failed: {e}"})
                raise

        try:
            hooks.on_status_update({"status": "CUSTOM", "custom_message": "Claiming case..."})
            case, result = await asyncio.to_thread(run)
            if case is None:
                hooks.on_chunk("No open cases. Scan the demo serial at Store B to open one, or send "
                               "`investigate <case_id>`.")
            else:
                hooks.on_chunk(f"**{case['case_id']}**\n\n{result.get('summary', '')}\n\n"
                               f"Confidence: {result.get('confidence', '?')}\n\n"
                               f"Full steps: {config.env('PUBLIC_WEB_URL', '')}/cockpit/cases/{case['case_id']}")
            hooks.on_finish()
        except Exception as e:  # exactly one of on_finish / on_error
            hooks.on_error(e)

    def get_config(self) -> dict:
        return {"system_prompt": SYSTEM_PROMPT, "tools": []}


def main() -> None:
    try:
        from astropods_adapter_core import serve
    except ImportError as e:  # pragma: no cover
        raise SystemExit("astropods-adapter-core is not installed. It is only needed for the Astropods "
                         "deployment; see docs/ASTROPODS.md (docker/astro.Dockerfile installs it).") from e
    use_astro_gateway()
    setup_tracing()
    serve(Investigator())  # connects to GRPC_SERVER_ADDR (default localhost:9090)


if __name__ == "__main__":
    main()
