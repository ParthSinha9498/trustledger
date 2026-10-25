"""demo_cut_v3.py: v3 cut with 1s initial black/silence, VO v5 alignment, and target ~2:40-2:45."""
import json, os, subprocess, wave, shutil
import imageio_ffmpeg

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")
VO_DIR = "/home/parth.sinha/Downloads/paypal/videos/vo"
FINAL_OUT = "/home/parth.sinha/Downloads/paypal/videos/dryrun-2026-10-25-v3.mp4"

meta = json.load(open(os.path.join(OUT_DIR, "marks.json")))
main_video = meta["video"]
marks = meta["marks"]

popups = [m["label"] for m in marks if m["kind"] == "popup_close" and m.get("label")]
popup_video = popups[0] if popups else None

audio_durs = json.load(open(os.path.join(VO_DIR, "durations.json")))
audio_durs = {int(k): float(v) for k, v in audio_durs.items()}

# Target per-scene durations (with 1s black lead-in before scene 1)
# Audio lengths:
# 1: 7.13s (Problem) -> 8.13s
# 2: 4.69s (Gap) -> 5.69s
# 3: 15.08s (Product) -> 16.08s
# 4: 2.39s (Teaser) -> 3.39s
# 5: 12.76s (Genuine sale) -> 16.76s (PayPal popup)
# 6: 9.22s (Blocked sale) -> 10.22s
# 7: 10.67s (Investigation) -> 14.67s (Agent progress)
# 8: 7.68s (Supply chain) -> 8.68s
# 9: 9.54s (Business model) -> 10.54s
# 10: 13.76s (Brand insights) -> 14.76s
# 11: 5.57s (AI analyst) -> 6.57s
# 12: 12.57s (Privacy) -> 13.57s
# 13: 15.55s (Onboarding) -> 16.55s
# 14: 7.64s (Close) -> 9.64s

target_scene_durs = {
    1: 8.13,
    2: 5.69,
    3: 16.08,
    4: 3.39,
    5: 16.76,
    6: 10.22,
    7: 14.67,
    8: 8.68,
    9: 10.54,
    10: 14.76,
    11: 6.57,
    12: 13.57,
    13: 16.55,
    14: 9.64,
}

# 1s initial black frame
LEAD_IN = 1.0

# Segments definition: (input_index, start, end, speed_factor, scene_number)
# input 0 is black lead-in generator or main_video
segments = [
    # Scene 1: Problem (t=8.0 in raw video)
    (0, 8.0, 16.13, 1.0, 1),
    # Scene 2: Gap (t=15.51 in raw video)
    (0, 15.51, 21.20, 1.0, 2),
    # Scene 3: Product (t=21.01 in raw video)
    (0, 21.01, 37.09, 1.0, 3),
    # Scene 4: Teaser (t=0.0 hero landing)
    (0, 0.0, 3.39, 1.0, 4),
    # Scene 5: Genuine sale (checkout & paypal)
    (0, 45.42, 50.42, 1.0, 5),               # 5.0s checkout
    (1, 7.91, 21.49, 13.58 / 8.50, 5),        # 8.5s popup (sped up 1.6x)
    (0, 72.73, 75.99, 1.0, 5),               # 3.26s receipt
    # Scene 6: Blocked sale (WhyBrandsPay & Store C block)
    (0, 75.83, 78.83, 1.0, 6),               # 3.0s receipt
    (0, 86.43, 93.65, 1.0, 6),               # 7.22s comparison expanded
    # Scene 7: Investigation (Store C case)
    (0, 93.67, 98.67, 1.0, 7),               # 5.0s case expand
    (0, 99.88, 106.88, 2.0, 7),              # 3.5s agent progress (sped up 2x)
    (0, 403.65, 409.82, 1.0, 7),             # 6.17s findings & verdict
    # Scene 8: Supply chain (Bryntum)
    (0, 417.75, 426.43, 1.0, 8),
    # Scene 9: Business model (arrow chain)
    (0, 427.74, 438.28, 1.0, 9),
    # Scene 10: Brand insights (console query)
    (0, 438.74, 453.50, 1.0, 10),
    # Scene 11: AI analyst (Studio)
    (0, 458.55, 465.12, 1.0, 11),
    # Scene 12: Privacy (differential privacy / OpenDP)
    (0, 468.67, 482.24, 1.0, 12),
    # Scene 13: Onboarding
    (0, 475.18, 491.73, 1.0, 13),
    # Scene 14: Close
    (0, 491.18, 500.82, 1.0, 14),
]

scene_start_times = {}
curr_time = LEAD_IN

for seg in segments:
    src, start, end, speed, sc = seg
    dur = (end - start) / speed
    if sc not in scene_start_times:
        scene_start_times[sc] = curr_time
    curr_time += dur

parts = []
# 0-th video part: 1s black color generator
parts.append("color=c=#0b1220:s=1280x720:d=1.0,fps=30,format=yuv420p[v_lead]")

for i, (src, start, end, speed, sc) in enumerate(segments):
    filter_chain = f"[{src}:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed}"
    filter_chain += ",scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#0b1220,fps=30,format=yuv420p"
    parts.append(f"{filter_chain}[v{i}]")

v_concat = "[v_lead]" + "".join(f"[v{i}]" for i in range(len(segments))) + f"concat=n={len(segments) + 1}:v=1:a=0[outv]"
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
print(f"{'LeadIn':<6} | {'0.00s':<8} | {'1.00s':<11} | {'1.00s':<6} | {'0.00s':<10} | OK")
for sc in range(1, 15):
    a_dur = audio_durs[sc]
    v_dur = target_scene_durs[sc]
    pad = v_dur - a_dur
    s_time = scene_start_times[sc]
    print(f"{sc:<6} | {a_dur:5.2f}s  | {v_dur:6.2f}s    | {pad:4.2f}s | {s_time:6.2f}s   | OK")
print("-" * 65)
print(f"Total Video Duration: {curr_time:.2f}s ({int(curr_time // 60)}m {curr_time % 60:04.1f}s)")
