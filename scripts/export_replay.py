#!/usr/bin/env python3
"""Export a finished case from the platform DB as a replay fixture JSON.

Direct database access is used intentionally here: this is an administrative
ops/export script, not runtime application code.

Usage:
    python scripts/export_replay.py <case_id> [output_path]
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db


def export_case_replay(case_id: str, out_path: str | Path | None = None) -> Path:
    with db.connect("platform") as pc:
        case = pc.execute("SELECT * FROM cases WHERE case_id=%s", (case_id,)).fetchone()
        if not case:
            raise ValueError(f"Case {case_id} not found")
        steps = pc.execute("SELECT * FROM case_steps WHERE case_id=%s ORDER BY n", (case_id,)).fetchall()

    recorded_at = case.get("updated_at") or case.get("created_at") or datetime.utcnow()
    if hasattr(recorded_at, "isoformat"):
        recorded_at = recorded_at.date().isoformat()
    else:
        recorded_at = str(recorded_at)[:10]

    # Convert timestamps in steps to ISO strings
    clean_steps = []
    for s in steps:
        step_dict = dict(s)
        if "at" in step_dict and hasattr(step_dict["at"], "isoformat"):
            step_dict["at"] = step_dict["at"].isoformat()
        clean_steps.append(step_dict)

    replay = {
        "replay_id": f"replay-{case_id}",
        "kind": "case",
        "source_case_id": case_id,
        "model": case.get("agent_model") or "",
        "recorded_at": recorded_at,
        "summary": case.get("summary") or "Investigation completed.",
        "confidence": case.get("confidence") or "high",
        "steps": clean_steps,
    }

    if out_path is None:
        target_dir = Path("tests/fixtures/replays")
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{case_id}.json"
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(replay, f, indent=2, default=str)
    print(f"Exported replay for {case_id} ({len(clean_steps)} steps) to {out_path}")
    return out_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/export_replay.py <case_id> [output_path]")
        sys.exit(1)
    case_id = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    export_case_replay(case_id, out_path)


if __name__ == "__main__":
    main()
