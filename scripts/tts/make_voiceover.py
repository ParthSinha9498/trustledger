#!/usr/bin/env python3
"""Generates TTS voiceover files for each scene in docs/demo/VOICEOVER.md using Kokoro-ONNX."""

import argparse
import json
import os
import re
import sys
import soundfile as sf
from kokoro_onnx import Kokoro

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT_MD = os.path.join(REPO_ROOT, "docs", "demo", "VOICEOVER.md")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(MODELS_DIR, "voices-v1.0.bin")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "videos", "vo")


def parse_vo_table(md_path: str):
    """Parses markdown table into list of dicts: {'num': str, 'name': str, 'text': str}."""
    scenes = []
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_table = False
    for line in lines:
        line = line.strip()
        if line.startswith("| # |") or line.startswith("|---|"):
            in_table = True
            continue
        if in_table and line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                num = parts[0]
                name = parts[1]
                text = parts[2]
                if num.isdigit():
                    scenes.append({"num": num, "scene": name, "text": text})
        elif in_table and not line.startswith("|"):
            if scenes:
                break
    return scenes


def main():
    parser = argparse.ArgumentParser(description="Render voiceover WAV files using Kokoro")
    parser.add_argument("--voice", default="af_heart", help="Voice id (e.g. af_heart, am_adam, am_michael)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="Output directory for WAVs and durations.json")
    parser.add_argument("--scene", type=str, help="Render only a specific scene number")
    args = parser.parse_args()

    if not os.path.exists(MODEL_PATH) or not os.path.exists(VOICES_PATH):
        print(f"Error: Kokoro model files missing in {MODELS_DIR}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    scenes = parse_vo_table(SCRIPT_MD)
    if not scenes:
        print(f"Error: No scenes found in {SCRIPT_MD}", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(scenes)} scenes from {SCRIPT_MD}")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)

    durations = {}
    for sc in scenes:
        if args.scene and sc["num"] != args.scene:
            continue
        num = sc["num"]
        text = sc["text"]
        print(f"Rendering scene {num}: {sc['scene']} ({len(text.split())} words)...")
        samples, sample_rate = kokoro.create(text, voice=args.voice, speed=args.speed, lang="en-us")
        wav_path = os.path.join(args.out, f"{num}.wav")
        sf.write(wav_path, samples, sample_rate)
        duration = len(samples) / sample_rate
        durations[num] = round(duration, 2)
        print(f"  -> {wav_path} ({duration:.2f}s)")

    durations_json_path = os.path.join(args.out, "durations.json")
    # Read existing if partial update
    existing_durations = {}
    if os.path.exists(durations_json_path):
        try:
            with open(durations_json_path) as f:
                existing_durations = json.load(f)
        except Exception:
            pass
    existing_durations.update(durations)

    with open(durations_json_path, "w", encoding="utf-8") as f:
        json.dump(existing_durations, f, indent=2)
    print(f"Wrote durations to {durations_json_path}")


if __name__ == "__main__":
    main()
