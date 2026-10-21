"""Edit a demo recording: cut the waits, splice in PayPal's approval window, export an MP4.

    uv run --with imageio-ffmpeg python e2e/demo_cut.py [--keep 1.5]

Reads e2e/out/demo/marks.json (written by demo_record.py):
  * each cut_start/cut_end pair is removed, keeping --keep seconds on each side so the viewer sees the work
    start and the result arrive;
  * popup_open/popup_close: Playwright records PayPal's approval window as its own video, so the main video
    only shows the waiting pay page then. That stretch is replaced by the popup's recording, minus the
    popup_cut_start/popup_cut_end stretch (the sandbox login, so no account details are shown).
Writes e2e/out/demo/demo.mp4.
"""
import argparse, json, os, subprocess

import imageio_ffmpeg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")


def plan(marks: list[dict], keep: float) -> list[tuple[int, float, float | None]]:
    """Segments as (input index, start, end): input 0 is the main video, 1.. are spliced popup videos."""
    segs: list[tuple[int, float, float | None]] = []
    pos, cut_from, popup_from, inputs, pop_cut, pop_end = 0.0, None, None, 0, [], None
    for m in marks:
        if m["kind"] == "cut_start":
            cut_from = m["t"] + keep
        elif m["kind"] == "cut_end" and cut_from is not None:
            cut_to = max(m["t"] - keep, cut_from)
            if cut_to > cut_from:
                segs.append((0, pos, cut_from))
                pos = cut_to
            cut_from = None
        elif m["kind"] == "popup_open":
            popup_from, pop_cut, pop_end = m["t"], [], None
        elif m["kind"] in ("popup_cut_start", "popup_cut_end") and popup_from is not None:
            pop_cut.append(m["t"] - popup_from)  # times inside the popup's own recording
        elif m["kind"] == "popup_keep_until" and popup_from is not None:
            pop_end = m["t"] - popup_from + 3.0  # a beat of "Thanks for using PayPal", not the whole spinner
        elif m["kind"] == "popup_close" and popup_from is not None and m.get("label"):
            inputs += 1
            segs.append((0, pos, popup_from))
            if len(pop_cut) == 2:  # drop the login stretch (account details stay off screen)
                segs.append((inputs, 0.0, pop_cut[0]))
                segs.append((inputs, pop_cut[1], pop_end))
            else:
                segs.append((inputs, 0.0, pop_end))
            pos, popup_from = m["t"], None
    segs.append((0, pos, None))
    return segs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=float, default=1.5, help="seconds kept on each side of a cut")
    args = ap.parse_args()
    meta = json.load(open(os.path.join(OUT, "marks.json")))
    marks = meta["marks"]
    popups = [m["label"] for m in marks if m["kind"] == "popup_close" and m.get("label")]
    segs = plan(marks, args.keep)
    parts = []
    for i, (src, a, b) in enumerate(segs):
        end = f":end={b}" if b is not None else ""
        parts.append(f"[{src}:v]trim=start={a}{end},setpts=PTS-STARTPTS,"
                     f"scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#0b1220,"
                     f"fps=30,format=yuv420p[v{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[out]"
    dst = os.path.join(OUT, "demo.mp4")
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", meta["video"]]
    for p in popups:
        cmd += ["-i", p]
    cmd += ["-filter_complex", graph, "-map", "[out]", "-c:v", "libx264", "-crf", "18", dst]
    subprocess.run(cmd, check=True)
    cuts = sum(1 for m in marks if m["kind"] == "cut_end")
    print(f"{cuts} cut(s), {len(popups)} popup splice(s) → {dst}")


if __name__ == "__main__":
    main()
