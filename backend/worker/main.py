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


def process_one() -> bool:
    with http.client(config.api_url()) as c:
        case = c.post("/internal/cases/claim").json()["case"]
    if case is None:
        return False
    inv = Investigation(case, get_llm())
    try:
        inv.run()
    except Exception as e:  # keep the worker alive; mark the case failed
        traceback.print_exc()
        inv._finish("failed", {"summary": f"Investigation failed: {e}"})
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
