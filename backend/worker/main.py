"""Worker: claims open cases from the API and runs the investigation agent.

    python -m backend.worker.main          # poll forever
    python -m backend.worker.main --once   # process at most one case
"""
import argparse
import os
import time
import traceback

import httpx

from backend import config
from backend.common import http
from backend.common.llm import get_llm
from backend.worker.agent import Investigation, agent_mode_of, model_of
from backend.worker.replay import play_case_replay


def _is_budget_exhausted(brand_id: str) -> bool:
    try:
        with http.client(config.paypal_node_url()) as c:
            r = c.get("/v1/budget", params={"brand_id": brand_id})
            if r.status_code == 200:
                return r.json().get("remaining", 1) <= 0
    except Exception:
        pass
    return False


def process_one() -> bool:
    with http.client(config.api_url()) as c:
        case = c.post("/internal/cases/claim").json()["case"]
    if case is None:
        return False

    case_id = case["case_id"]
    brand_id = case.get("brand_id", config.brand_id())

    # If privacy budget is exhausted, defer with guarantee reason
    if _is_budget_exhausted(brand_id):
        reason = "Privacy budget used up: that's the guarantee working"
        print(f"worker: budget exhausted for {brand_id}; deferring {case_id} ({reason})", flush=True)
        play_case_replay(case_id, reason)
        return True

    # Try live/chained LLM investigation; if both fail (429/timeout/error), defer with honest reason
    llm = None
    try:
        llm = get_llm()
        inv = Investigation(case, llm)
        inv.run()
    except Exception as e:
        err_str = str(e).lower()
        err_cls = type(e).__name__.lower()
        if "429" in err_str or "rate limit" in err_str or "ratelimit" in err_cls or "quota" in err_str:
            reason = "Demo AI free-tier quota reached"
        elif "timeout" in err_str or "timeout" in err_cls or "timed out" in err_str:
            reason = "AI provider timed out"
        else:
            reason = "AI unavailable right now"

        print(f"worker: live investigation failed for {case_id} ({e}); deferring with reason: {reason}", flush=True)
        traceback.print_exc()
        try:
            play_case_replay(case_id, reason)
        except Exception as re:
            print(f"worker: deferral failed ({re}); marking case failed", flush=True)
            with http.client(config.api_url()) as c:
                c.post(f"/internal/cases/{case_id}/finish",
                       json={"status": "failed", "summary": f"Investigation failed: {e}",
                             "agent_mode": agent_mode_of(llm), "agent_model": model_of(llm),
                             "agent_reason": str(e)[:300]})
    return True


def next_idle_sleep(current: float, max_idle: float = 300.0) -> float:
    """Exponential backoff when idle: doubles sleep time up to max_idle."""
    return min(current * 2.0, max_idle)


def main() -> None:
    if config.env("LLM_MODE", "live") != "mock" and not config.env("AGENT_MODEL"):
        raise RuntimeError("AGENT_MODEL environment variable must be set when LLM_MODE is not 'mock'")
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.once:
        process_one()
        return
    backoff = 3
    idle_sleep = 3.0  # WORKER_MAX_IDLE_S > 3 enables idle backoff (off by default: a judge's case must start within seconds)
    max_idle = float(os.environ.get("WORKER_MAX_IDLE_S", "3"))
    while True:
        try:
            worked = process_one()
            backoff = 3
        except httpx.TransportError as e:  # api not up yet, or restarting: wait instead of dying
            print(f"worker: api unreachable ({e}); retrying in {backoff}s", flush=True)
            worked, backoff = False, min(backoff * 2, 60)
            time.sleep(backoff)
            continue
        if worked:
            idle_sleep = 3.0
        else:
            time.sleep(idle_sleep)
            idle_sleep = next_idle_sleep(idle_sleep, max_idle)


if __name__ == "__main__":
    main()
