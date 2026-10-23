"""Replay runner for finished or recorded case investigations."""
import json
from pathlib import Path

from backend import config
from backend.common import http

def load_replay(path_or_name: str) -> dict | None:
    p = Path(path_or_name)
    if not p.is_file():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def play_case_replay(case_id: str, reason: str, replay_name: str | None = None, write_steps: bool = False) -> dict:
    rep = load_replay(replay_name) if replay_name else None
    if rep and write_steps:
        with http.client(config.api_url()) as c:
            for s in rep.get("steps", []):
                c.post(f"/internal/cases/{case_id}/steps", json={"kind": s["kind"], "payload": s["payload"]})
    finish_payload = {
        "status": "waiting_capacity",
        "summary": "This case will be investigated live when capacity frees up.",
        "confidence": None,
        "agent_mode": "replay" if rep else "live",
        "agent_model": rep.get("model") if rep else None,
        "agent_reason": reason,
        "source_case_id": rep.get("source_case_id") if rep else None,
        "replay_recorded_at": rep.get("recorded_at") if rep else None,
    }
    with http.client(config.api_url()) as c:
        c.post(f"/internal/cases/{case_id}/finish", json=finish_payload)
    return finish_payload

