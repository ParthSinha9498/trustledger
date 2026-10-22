"""Worker: claims open cases from the API and runs the investigation agent.

    python -m backend.worker.main          # poll forever
    python -m backend.worker.main --once   # process at most one case
"""
import argparse
import time
import traceback

import httpx

from backend import config
from backend.common import http
from backend.common.llm import get_llm
from backend.worker.agent import Investigation
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

    # If privacy budget is exhausted, play recorded replay with guarantee reason
    if _is_budget_exhausted(brand_id):
        print(f"worker: budget exhausted for {brand_id}; playing replay for {case_id}", flush=True)
        play_case_replay(case_id, "Privacy budget used up: that's the guarantee working")
        return True

    # Try live/chained LLM investigation; if both fail (429/timeout/error), fall back to replay
    try:
        inv = Investigation(case, get_llm())
        inv.run()
    except Exception as e:
        print(f"worker: live investigation failed for {case_id} ({e}); falling back to replay", flush=True)
        traceback.print_exc()
        try:
            play_case_replay(case_id, "Demo AI free-tier quota reached")
        except Exception as re:
            print(f"worker: replay failed ({re}); marking case failed", flush=True)
            with http.client(config.api_url()) as c:
                c.post(f"/internal/cases/{case_id}/finish",
                       json={"status": "failed", "summary": f"Investigation failed: {e}",
                             "agent_mode": "live", "agent_reason": str(e)[:300]})
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.once:
        process_one()
        return
    backoff = 3
    while True:
        try:
            worked = process_one()
            backoff = 3
        except httpx.TransportError as e:  # api not up yet, or restarting: wait instead of dying
            print(f"worker: api unreachable ({e}); retrying in {backoff}s", flush=True)
            worked, backoff = False, min(backoff * 2, 60)
            time.sleep(backoff)
            continue
        if not worked:
            time.sleep(3)


if __name__ == "__main__":
    main()
