"""Build the pitch video from one recording, with every scene cut at the recording's own marks.

Inputs (written by e2e/demo_record.py):
    e2e/out/demo/marks.json     main video path + timed marks (story cards, popup window, agent wait)
    $VO_DIR/<n>.wav             one voice-over WAV per scene (default: videos/vo next to the repo)
    $VO_DIR/durations.json      optional: VO lengths; read with ffmpeg when missing

Each VO scene is a list of visual parts cut from the recording. A part starts at a mark, so no
number is typed in by hand. The scene's visual is conformed to its audio + PAD: parts are cut
proportionally when too long, and the last frame is held when too short. Audio is laid end to end
with the same lengths, so every scene starts at the same time in both tracks.

Gate (exit 1 on failure), written to e2e/out/video_report.json:
    1. output video and audio durations agree within 0.10 s;
    2. the frame count is exactly FPS per second (a wrong frame rate shows up here);
    3. every scene boundary has a visible change (frame-difference cut detection) within 0.10 s.
Frozen frames in live-UI scenes are reported, not gated: a page that holds still while narration plays is expected.

Usage:
    uv run --with imageio-ffmpeg python e2e/build_video.py --out <path>.mp4
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.join(HERE, "out", "demo")
REPORT = os.path.join(HERE, "out", "video_report.json")
VO_DIR = os.environ.get("VO_DIR", "/home/parth.sinha/Downloads/paypal/videos/vo")

PAD = 0.6          # seconds of visual hold after each scene's narration
SNAP = 1.0         # seconds: a recorder mark moves to the strongest visible change within this window
FPS = 30
TOL = 0.10         # sync tolerance, seconds
MAX_FREEZE = 2.0   # seconds (reported)
CUT_LUMA = 1.0     # mean luma change that counts as a visible cut
WINDOW = 0.5       # seconds around each audio cue searched for the cut
FF = imageio_ffmpeg.get_ffmpeg_exe()

# Scene plan: VO scene -> visual parts (source, from_mark, to_mark). source "main" = the recording,
# "popup" = the PayPal approval window on its own clock (main time minus popup_open).
# "name+x" adds x seconds to a mark; "end" is the end of the recording.
# Card scenes are story cards (kind "scene" marks); live scenes show the running app.
PLAN = [
    (1, "Problem", [("main", "problem", "gap")], "card"),
    (2, "Gap", [("main", "gap", "how")], "card"),
    (3, "Product", [("main", "idea+0.6", "problem"), ("main", "how", "s1")], "card"),  # +0.6: first frames are a blank page load
    (4, "Teaser", [("main", "business", "business+2.4")], "card"),
    (5, "Genuine sale", [("main", "popup_open+-5", "popup_open"), ("popup", "popup_cut_end", "popup_keep_until"),
                         ("main", "receipt", "s2")], "live"),  # the Brand Verified receipt is narrated in scene 5
    (6, "Blocked sale", [("main", "s2", "s3")], "live"),
    (7, "Investigation", [("main", "s3", "cut_start"), ("main", "cut_end", "supply-chain")], "live"),
    (8, "Supply chain", [("main", "supply-chain", "studio-supply")], "live"),
    (9, "Studio supply chain", [("main", "studio-supply", "business")], "live"),  # AG Studio supply-chain page, recorded live
    (10, "Business model", [("main", "business+2.4", "s4")], "card"),
    (11, "Brand insights", [("main", "s4", "analyst")], "live"),
    (12, "AI analyst", [("main", "analyst", "guarantee")], "live"),  # AG Studio page, recorded live
    (13, "Privacy", [("main", "guarantee", "levels")], "card"),
    (14, "Onboarding", [("main", "levels", "close")], "card"),
    (15, "Close", [("main", "close", "end")], "card"),
]


def mark_time(marks, key):
    """A mark's time on its clock. 'name+x' adds x seconds."""
    base, _, plus = key.partition("+")
    off = float(plus) if plus else 0.0
    if base.startswith("popup_"):
        hits = [m for m in marks if m["kind"] == base]
    else:
        hits = [m for m in marks if m["kind"] == "scene" and m["label"] == base]
        if not hits:
            hits = [m for m in marks if m["kind"] == base]  # agent wait marks are keyed by kind: cut_start, cut_end
    if not hits:
        raise SystemExit(f"mark not found in marks.json: {base}")
    return hits[0]["t"] + off


def popup_time(marks, t_main):
    """Main-clock time to the popup clip's clock, which starts when the popup opened."""
    opened = next(m["t"] for m in marks if m["kind"] == "popup_open")
    return t_main - opened


def ffmpeg_duration(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out)
    if not m:
        raise SystemExit(f"cannot read duration: {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def visible_changes(path):
    """(time, mean luma change) for every frame of a video, from the frame-to-frame difference."""
    diff = subprocess.run([FF, "-i", path, "-vf",
                           "tblend=all_mode=difference,signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG:file=-",
                           "-f", "null", "-"], capture_output=True, text=True).stdout
    luma, t_now = [], None
    for line in diff.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t_now = float(m.group(1))
        m = re.search(r"YAVG=([\d.]+)", line)
        if m and t_now is not None:
            luma.append((t_now, float(m.group(1))))
    return luma


def cut_change(t, changes, window):
    """The visible cut nearest to t: the strong frame change (>= CUT_LUMA) closest in time within +/-window.
    The same rule places each cut (snap) and checks it (gate). Taking the biggest change instead picks the
    peak of a card's fade-in, which lands up to 0.4 s after the hard cut."""
    near = [(abs(c - t), c) for c, v in changes if abs(c - t) <= window and v >= CUT_LUMA]
    return min(near)[1] if near else None


def snap(t, changes):
    """Move a mark to the nearest visible cut within SNAP seconds. A mark with no visible change nearby
    (a live page that is still) keeps its recorded time."""
    c = cut_change(t, changes, SNAP)
    return t if c is None else c


def vo_duration(n):
    dur_file = os.path.join(VO_DIR, "durations.json")
    if os.path.exists(dur_file):
        d = json.load(open(dur_file))
        if str(n) in d:
            return float(d[str(n)])
    return ffmpeg_duration(os.path.join(VO_DIR, f"{n}.wav"))


def resolve_parts(parts, marks, main_len, changes):
    """Plan keys to (input index, start, end) in seconds on each source's clock. Main-clock cuts snap to the picture."""
    out = []
    for src, a, b in parts:
        if src == "popup":
            out.append((1, popup_time(marks, mark_time(marks, a)), popup_time(marks, mark_time(marks, b))))
        else:
            start = snap(mark_time(marks, a), changes)
            end = main_len if b == "end" else snap(mark_time(marks, b), changes)
            out.append((0, start, end))
    return out


def conform(parts, target):
    """Fit parts to target frames: cut proportionally when too long; the last frame is held when short."""
    natural = sum(e - s for _, s, e in parts)
    if natural <= 0:
        raise SystemExit("empty visual part")
    if natural <= target:
        # Too short: play the parts as recorded and hold the last frame (tpad). Never borrow frames
        # past a part's end, since those belong to the next card.
        frames = [max(1, round((e - s) * FPS)) for _, s, e in parts]
    else:
        f = target / natural
        frames = [max(1, round((e - s) * f * FPS)) for _, s, e in parts]
        frames[-1] += round(target * FPS) - sum(frames)  # absorb rounding in the last part
        if frames[-1] < 1:
            raise SystemExit("scene too short for its parts")
    # End half a frame early: a trim ending exactly on a frame boundary can yield one extra frame.
    return [(i, s, s + (n - 0.5) / FPS) for (i, s, _), n in zip(parts, frames)], natural


def build(out_path):
    meta = json.load(open(os.path.join(DEMO, "marks.json")))
    marks = meta["marks"]
    main_video = meta["video"]
    popup_video = next((m["label"] for m in marks if m["kind"] == "popup_close" and m["label"]), None)
    main_len = ffmpeg_duration(main_video)
    changes = visible_changes(main_video)

    scenes = []
    for n, name, parts, kind in PLAN:
        vo = vo_duration(n)
        target = math.ceil((vo + PAD) * FPS) / FPS  # whole frames, so video and audio never drift
        conformed, natural = conform(resolve_parts(parts, marks, main_len, changes), target)
        scenes.append({"n": n, "name": name, "kind": kind, "vo": vo, "target": target,
                       "natural": natural, "parts": conformed})

    inputs = ["-i", main_video]
    if popup_video:
        inputs += ["-i", popup_video]
    lines, v_labels, a_labels = [], [], []
    for k, sc in enumerate(scenes):
        labels = []
        for j, (src, s, e) in enumerate(sc["parts"]):
            lab = f"p{k}_{j}"
            lines.append(f"[{src}:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
                         f"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#0b1220,"
                         f"fps={FPS},format=yuv420p[{lab}]")
            labels.append(f"[{lab}]")
        frames_k = round(sc["target"] * FPS)  # exact frame count per scene
        lines.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=120,"
                     f"trim=end_frame={frames_k},setpts=PTS-STARTPTS[v{k}]")
        v_labels.append(f"[v{k}]")
        ai = len(inputs) // 2
        inputs += ["-i", os.path.join(VO_DIR, f"{sc['n']}.wav")]
        lines.append(f"[{ai}:a]apad=pad_dur={max(0.0, sc['target'] - sc['vo']):.3f},"
                     f"atrim=duration={sc['target']:.3f},asetpts=PTS-STARTPTS[a{k}]")
        a_labels.append(f"[a{k}]")

    lines.append(f"{''.join(v_labels)}concat=n={len(scenes)}:v=1:a=0,fps={FPS}[outv]")
    lines.append(f"{''.join(a_labels)}concat=n={len(scenes)}:v=0:a=1[outa]")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [FF, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(lines),
           "-map", "[outv]", "-map", "[outa]", "-r", str(FPS), "-fps_mode", "cfr",
           "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", out_path]
    subprocess.run(cmd, check=True)

    report = gate(out_path, scenes)
    report["scenes"] = [{k: v for k, v in s.items() if k != "parts"} | {
        "parts": [{"input": i, "from": round(a, 2), "to": round(b, 2)} for i, a, b in s["parts"]]}
        for s in scenes]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(report, open(REPORT, "w"), indent=1)
    print(json.dumps({k: report[k] for k in ("video_s", "audio_s", "vo_total_s", "passed")}, indent=1))
    return report


def gate(out_path, scenes):
    video_s = ffmpeg_duration(out_path)
    audio_total = sum(s["target"] for s in scenes)
    checks = {}

    checks["duration_match"] = {"ok": abs(video_s - audio_total) <= TOL,
                                "video_s": round(video_s, 3), "audio_s": round(audio_total, 3)}

    framemd5 = subprocess.run([FF, "-i", out_path, "-map", "0:v:0", "-f", "framemd5", "-"],
                              capture_output=True, text=True).stdout
    frames = sum(1 for line in framemd5.splitlines() if line and not line.startswith("#"))
    expected = round(audio_total * FPS)
    checks["frame_count"] = {"ok": frames == expected, "frames": frames, "expected": expected}

    boundaries, t = [], 0.0
    for s in scenes:
        boundaries.append((s["n"], t))
        t += s["target"]
    # Per boundary: the largest frame-to-frame luma change within +/-WINDOW of the audio cue must sit within TOL of it
    # and reach CUT_LUMA. Animations elsewhere cannot satisfy the check; only the real cut at the boundary can.
    luma = visible_changes(out_path)
    misses = []
    for n, b in boundaries[1:]:
        peak_t = cut_change(b, luma, WINDOW)
        if peak_t is None or abs(peak_t - b) > TOL:
            vals = dict(luma)
            misses.append({"scene": n, "boundary_s": round(b, 3),
                           "peak_s": None if peak_t is None else round(peak_t, 3),
                           "peak_luma": None if peak_t is None else round(vals[peak_t], 2)})
    checks["scene_boundaries"] = {"ok": not misses, "checked": len(boundaries) - 1, "missed": misses}

    frozen = subprocess.run([FF, "-i", out_path, "-vf", f"freezedetect=n=0.003:d={MAX_FREEZE}",
                             "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True).stderr
    freezes = [(float(a), float(b)) for a, b in re.findall(r"freeze_start: ([\d.]+).*?freeze_end: ([\d.]+)", frozen, re.S)]
    live_ranges, t = [], 0.0
    for s in scenes:
        if s["kind"] == "live":
            live_ranges.append((t, t + s["target"]))
        t += s["target"]
    over = [(round(a, 2), round(b, 2)) for a, b in freezes
            if b - a > MAX_FREEZE and any(a < r1 and b > r0 for r0, r1 in live_ranges)]
    checks["frozen_live_frames"] = {"ok": True, "gated": False, "over_limit_count": len(over), "over_limit": over}

    passed = all(c["ok"] for c in checks.values())
    return {"video": out_path, "video_s": round(video_s, 3), "audio_s": round(audio_total, 3),
            "vo_total_s": round(sum(s["vo"] for s in scenes), 3), "checks": checks, "passed": passed}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rep = build(args.out)
    if not rep["passed"]:
        print(json.dumps(rep["checks"], indent=1), file=sys.stderr)
        sys.exit(1)
