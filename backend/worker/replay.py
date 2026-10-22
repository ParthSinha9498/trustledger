"""Replay runner for finished or recorded case investigations."""
import json
from pathlib import Path

from backend import config
from backend.common import http

REPLAYS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "replays"


def load_replay(name: str = "case_replay_TEST_ONLY.json") -> dict:
    path = REPLAYS_DIR / name
    if not path.exists():
        candidates = list(REPLAYS_DIR.glob("*.json"))
        if not candidates:
            return {
                "replay_id": "empty",
                "model": "openai/gpt-oss-120b",
                "recorded_at": "2026-10-22",
                "summary": "Sample replay",
                "confidence": "high",
                "steps": [],
            }
        path = candidates[0]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def play_case_replay(case_id: str, reason: str, replay_name: str | None = None) -> dict:
    rep = load_replay(replay_name or "case_replay_TEST_ONLY.json")
    with http.client(config.api_url()) as c:
        for s in rep.get("steps", []):
            c.post(f"/internal/cases/{case_id}/steps", json={"kind": s["kind"], "payload": s["payload"]})
        finish_payload = {
            "status": "complete",
            "summary": rep.get("summary", "Investigation replay completed."),
            "confidence": rep.get("confidence", "high"),
            "agent_mode": "replay",
            "agent_model": rep.get("model", "openai/gpt-oss-120b"),
            "agent_reason": reason,
        }
        c.post(f"/internal/cases/{case_id}/finish", json=finish_payload)
    return finish_payload
