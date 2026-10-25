"""Edit a demo recording: cut the waits, splice in PayPal's approval window, export an MP4 with voiceover.

    uv run --with imageio-ffmpeg python e2e/demo_cut.py [--keep 1.5] [--audio-dir DIR] [--out OUT_MP4]

Reads e2e/out/demo/marks.json (written by demo_record.py):
  * each cut_start/cut_end pair is removed, keeping --keep seconds on each side;
  * popup_open/popup_close is spliced in without the login stretch;
  * synchronizes the 14 scene voiceover WAVs with the cut video.
Writes e2e/out/demo/demo.mp4 and optional --out.
"""
import argparse, json, os, subprocess, shutil
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
            pop_cut.append(m["t"] - popup_from)
        elif m["kind"] == "popup_keep_until" and popup_from is not None:
            pop_end = m["t"] - popup_from + 3.0
        elif m["kind"] == "popup_close" and popup_from is not None and m.get("label"):
            inputs += 1
            segs.append((0, pos, popup_from))
            if len(pop_cut) == 2:
                segs.append((inputs, 0.0, pop_cut[0]))
                segs.append((inputs, pop_cut[1], pop_end))
            else:
                segs.append((inputs, 0.0, pop_end))
            pos, popup_from = m["t"], None
    segs.append((0, pos, None))
    return segs


def to_cut_time(t: float, segs: list[tuple[int, float, float | None]]) -> float:
    acc = 0.0
    for src, a, b in segs:
        dur = (b - a) if b is not None else 999999.0
        if src == 0:
            if a <= t < (b if b is not None else 999999.0):
                return acc + (t - a)
            acc += dur
        else:
            acc += dur
    return acc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=float, default=1.5, help="seconds kept on each side of a cut")
    ap.add_argument("--audio-dir", default="/home/parth.sinha/Downloads/paypal/videos/vo", help="directory with 1.wav..14.wav")
    ap.add_argument("--out", default="/home/parth.sinha/Downloads/paypal/videos/dryrun-2026-10-25.mp4", help="destination MP4")
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
    v_graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0[out]"

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    dst = os.path.join(OUT, "demo.mp4")

    # Check for audio files
    scene_marks = [m for m in marks if m["kind"] == "scene" and m["label"] != "compare"]
    wavs = [os.path.join(args.audio_dir, f"{i}.wav") for i in range(1, 15)]
    has_audio = os.path.isdir(args.audio_dir) and all(os.path.exists(w) for w in wavs)

    if has_audio and len(scene_marks) >= 14:
        print(f"Found all 14 voiceover WAVs. Mapping to {len(scene_marks)} scenes...")
        # Build audio filter graph
        audio_inputs = []
        a_parts = []
        for i in range(14):
            wav_path = wavs[i]
            audio_inputs.extend(["-i", wav_path])
            m_t = scene_marks[i]["t"]
            cut_t = to_cut_time(m_t, segs)
            delay_ms = max(0, int(round(cut_t * 1000)))
            input_idx = 1 + len(popups) + i
            a_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
        
        mix_inputs = "".join(f"[a{i}]" for i in range(14))
        a_graph = ";".join(a_parts) + f";{mix_inputs}amix=inputs=14:dropout_transition=0:normalize=0[aout]"
        full_graph = v_graph + ";" + a_graph

        cmd = [ffmpeg, "-v", "error", "-y", "-i", meta["video"]]
        for p in popups:
            cmd += ["-i", p]
        cmd += audio_inputs
        cmd += ["-filter_complex", full_graph, "-map", "[out]", "-map", "[aout]",
                "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", dst]
    else:
        cmd = [ffmpeg, "-v", "error", "-y", "-i", meta["video"]]
        for p in popups:
            cmd += ["-i", p]
        cmd += ["-filter_complex", v_graph, "-map", "[out]", "-c:v", "libx264", "-crf", "18", dst]

    print("Running ffmpeg assemble...")
    subprocess.run(cmd, check=True)
    cuts = sum(1 for m in marks if m["kind"] == "cut_end")
    print(f"{cuts} cut(s), {len(popups)} popup splice(s) -> {dst}")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        shutil.copyfile(dst, args.out)
        print(f"Copied export to {args.out}")


if __name__ == "__main__":
    main()
