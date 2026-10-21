"""Cut the waits out of a demo recording and export an MP4.

    uv run --with imageio-ffmpeg python e2e/demo_cut.py [--keep 1.5]

Reads e2e/out/demo/marks.json (written by demo_record.py). Each cut_start/cut_end pair is removed, keeping
--keep seconds on each side so the viewer sees the work start and the result arrive. Writes e2e/out/demo/demo.mp4.
"""
import argparse, json, os, subprocess

import imageio_ffmpeg

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")


def keep_segments(marks: list[dict], keep: float) -> list[tuple[float, float | None]]:
    segs, start, cut_from = [], 0.0, None
    for m in marks:
        if m["kind"] == "cut_start":
            cut_from = m["t"] + keep
        elif m["kind"] == "cut_end" and cut_from is not None:
            cut_to = max(m["t"] - keep, cut_from)
            if cut_to > cut_from:
                segs.append((start, cut_from))
                start = cut_to
            cut_from = None
    segs.append((start, None))
    return segs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=float, default=1.5, help="seconds kept on each side of a cut")
    args = ap.parse_args()
    meta = json.load(open(os.path.join(OUT, "marks.json")))
    segs = keep_segments(meta["marks"], args.keep)
    parts = []
    for i, (a, b) in enumerate(segs):
        end = f":end={b}" if b is not None else ""
        parts.append(f"[0:v]trim=start={a}{end},setpts=PTS-STARTPTS[v{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[out]"
    dst = os.path.join(OUT, "demo.mp4")
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-i", meta["video"], "-filter_complex", graph,
                    "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", "30", dst], check=True)
    print(f"{len(segs) - 1} cut(s) → {dst}")


if __name__ == "__main__":
    main()
