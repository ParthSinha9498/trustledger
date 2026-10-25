"""demo_cut_v2.py: Exact per-scene trimming and assembly to 2:30-2:45 target."""
import json, os, subprocess, wave, shutil
import imageio_ffmpeg

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")
VO_DIR = "/home/parth.sinha/Downloads/paypal/videos/vo"
FINAL_OUT = "/home/parth.sinha/Downloads/paypal/videos/dryrun-2026-10-25-v2.mp4"

meta = json.load(open(os.path.join(OUT_DIR, "marks.json")))
main_video = meta["video"]
marks = meta["marks"]

popups = [m["label"] for m in marks if m["kind"] == "popup_close" and m.get("label")]
popup_video = popups[0] if popups else None

audio_durs = {}
for i in range(1, 15):
    with wave.open(os.path.join(VO_DIR, f"{i}.wav"), "rb") as w:
        audio_durs[i] = w.getnframes() / float(w.getframerate())

target_scene_durs = {
    1: 8.98,
    2: 8.13,
    3: 6.03,
    4: 11.28,
    5: 16.76,
    6: 10.72,
    7: 14.67,
    8: 8.68,
    9: 10.54,
    10: 14.76,
    11: 6.57,
    12: 7.04,
    13: 16.55,
    14: 9.64,
}

total_dur = sum(target_scene_durs.values())
print(f"Total target video duration: {total_dur:.2f}s ({int(total_dur // 60)}:{total_dur % 60:04.1f})")

segments = [
    # Scene 1 (8.98s)
    (0, 0.0, 8.98, 1.0, 1),
    # Scene 2 (8.13s)
    (0, 8.0, 16.13, 1.0, 2),
    # Scene 3 (6.03s)
    (0, 15.51, 21.54, 1.0, 3),
    # Scene 4 (11.28s)
    (0, 21.01, 32.29, 1.0, 4),
    # Scene 5 (16.76s)
    (0, 45.42, 50.42, 1.0, 5),               # 5.0s checkout
    (1, 7.91, 21.49, 13.58 / 8.50, 5),        # 8.5s popup (sped up 1.6x)
    (0, 72.73, 75.99, 1.0, 5),               # 3.26s receipt
    # Scene 6 (10.72s)
    (0, 75.83, 78.83, 1.0, 6),               # 3.0s receipt
    (0, 85.93, 93.65, 1.0, 6),               # 7.72s comparison expanded
    # Scene 7 (14.67s)
    (0, 93.67, 98.67, 1.0, 7),               # 5.0s case expand
    (0, 99.88, 106.88, 2.0, 7),              # 3.5s agent progress (sped up 2x)
    (0, 403.65, 409.82, 1.0, 7),             # 6.17s findings & verdict
    # Scene 8 (8.68s)
    (0, 417.75, 426.43, 1.0, 8),
    # Scene 9 (10.54s)
    (0, 427.74, 438.28, 1.0, 9),
    # Scene 10 (14.76s)
    (0, 438.74, 453.50, 1.0, 10),
    # Scene 11 (6.57s)
    (0, 458.55, 465.12, 1.0, 11),
    # Scene 12 (7.04s)
    (0, 468.67, 475.71, 1.0, 12),
    # Scene 13 (16.55s)
    (0, 475.18, 491.73, 1.0, 13),
    # Scene 14 (9.64s)
    (0, 491.18, 500.82, 1.0, 14),
]

scene_start_times = {}
curr_time = 0.0

for seg in segments:
    src, start, end, speed, sc = seg
    dur = (end - start) / speed
    if sc not in scene_start_times:
        scene_start_times[sc] = curr_time
    curr_time += dur

parts = []
for i, (src, start, end, speed, sc) in enumerate(segments):
    filter_chain = f"[{src}:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed}"
    filter_chain += ",scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#0b1220,fps=30,format=yuv420p"
    parts.append(f"{filter_chain}[v{i}]")

v_concat = "".join(f"[v{i}]" for i in range(len(segments))) + f"concat=n={len(segments)}:v=1:a=0[outv]"
v_graph = ";".join(parts) + ";" + v_concat

wavs = [os.path.join(VO_DIR, f"{i}.wav") for i in range(1, 15)]
audio_inputs = []
a_parts = []
offset_inputs = 1 + (1 if popup_video else 0)

for i in range(14):
    sc_num = i + 1
    audio_inputs.extend(["-i", wavs[i]])
    t_start = scene_start_times[sc_num]
    delay_ms = max(0, int(round(t_start * 1000)))
    input_idx = offset_inputs + i
    a_parts.append(f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}[a{i}]")

mix_inputs = "".join(f"[a{i}]" for i in range(14))
a_graph = ";".join(a_parts) + f";{mix_inputs}amix=inputs=14:dropout_transition=0:normalize=0[outa]"

full_graph = v_graph + ";" + a_graph

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [ffmpeg, "-v", "error", "-y", "-i", main_video]
if popup_video:
    cmd += ["-i", popup_video]
cmd += audio_inputs
cmd += [
    "-filter_complex", full_graph,
    "-map", "[outv]", "-map", "[outa]",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast",
    "-c:a", "aac", "-b:a", "192k",
    "-t", f"{curr_time:.2f}",
    FINAL_OUT
]

print(f"Executing ffmpeg assemble to {FINAL_OUT}...")
subprocess.run(cmd, check=True)

sz = os.path.getsize(FINAL_OUT)
print(f"Successfully generated {FINAL_OUT} ({sz / (1024*1024):.2f} MB)")

print("\n=== Per-Scene Report Table ===")
print(f"{'Scene':<6} | {'Audio':<8} | {'Visual Dur':<11} | {'Pad':<6} | {'Start Time':<10} | {'Status'}")
print("-" * 65)
for sc in range(1, 15):
    a_dur = audio_durs[sc]
    v_dur = target_scene_durs[sc]
    pad = v_dur - a_dur
    s_time = scene_start_times[sc]
    print(f"{sc:<6} | {a_dur:5.2f}s  | {v_dur:6.2f}s    | {pad:4.2f}s | {s_time:6.2f}s   | OK")
print("-" * 65)
print(f"Total Video Duration: {curr_time:.2f}s ({int(curr_time // 60)}m {curr_time % 60:04.1f}s)")
