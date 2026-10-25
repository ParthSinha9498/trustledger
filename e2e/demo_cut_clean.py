"""demo_cut_clean.py: Rebuild demo-2026-10-25-clean.mp4 with updated scene 9 VO and verified A/V alignment."""
import json
import os
import subprocess
import imageio_ffmpeg

OUT_DIR = "/home/parth.sinha/Downloads/paypal/ag-wt/f-video-pipeline/e2e/out/demo"
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
VO_DIR = "/home/parth.sinha/Downloads/paypal/videos/vo"
FINAL_OUT = "/home/parth.sinha/Downloads/paypal/videos/demo-2026-10-25-clean.mp4"

meta = json.load(open(os.path.join(OUT_DIR, "marks.json")))
main_video = meta["video"]
marks = meta["marks"]

popups = [m["label"] for m in marks if m["kind"] == "popup_close" and m.get("label")]
popup_video = popups[0] if popups else None

privacy_video = os.path.join(CLIPS_DIR, "page@3344527d9a3b7740084b86675fe527fc.webm")
card_usd_video = os.path.join(CLIPS_DIR, "page@0c56c495787e13db32d277e031edd5f6.webm")

audio_durs = json.load(open(os.path.join(VO_DIR, "durations.json")))
audio_durs = {int(k): float(v) for k, v in audio_durs.items()}

# Each scene = its audio + <= 1.0s pad (scene 5 and 7 have up to 4s for payment / agent steps)
target_scene_durs = {
    1: 8.13,
    2: 5.69,
    3: 16.08,
    4: 3.39,
    5: 16.76,
    6: 10.22,
    7: 14.67,
    8: 8.68,
    9: round(audio_durs[9] + 1.0, 2),  # 15.55s audio + 1.0s pad = 16.55s
    10: 14.76,
    11: 6.57,
    12: 13.57,
    13: 16.55,
    14: 9.64,
}

LEAD_IN = 1.0

sc9_dur = target_scene_durs[9]

segments = [
    # Scene 1: Problem (v5 audio: 467B / 1 in 8 fakes -> old scene 2 problem card)
    (0, 8.0, 16.13, 1.0, 1, "Problem card (467B / 1 in 8)"),
    # Scene 2: Gap (v5 audio: checking is optional -> old scene 3 gap card)
    (0, 15.51, 21.20, 1.0, 2, "Gap card (checking optional)"),
    # Scene 3: Product (v5 audio: authenticity as condition -> old scene 1 idea (6s) + old scene 4 how it works (10.08s))
    (0, 0.0, 6.00, 1.0, 3, "Idea card (condition of payment)"),
    (0, 21.01, 31.09, 1.0, 3, "How it works card (3 steps)"),
    # Scene 4: Teaser (v5 audio: pays for itself teaser -> landing why brands pay)
    (0, 86.43, 89.82, 1.0, 4, "Landing Why Brands Pay teaser"),
    # Scene 5: Genuine sale (v5 audio: Store A X123 genuine sale)
    (0, 45.42, 49.92, 1.0, 5, "Store A checkout scan"),
    (3, 1.00, 5.50, 1.0, 5, "Store A Nimbus P8 128GB card payment form ($899.00)"),
    (1, 7.91, 21.49, 13.58 / 4.50, 5, "PayPal sandbox popup approval"),
    (0, 72.73, 75.99, 1.0, 5, "Verified customer receipt"),
    # Scene 6: Blocked sale (v5 audio: Store C blocked checkout)
    (0, 75.83, 78.83, 1.0, 6, "Store C receipt transition"),
    (0, 86.43, 93.65, 1.0, 6, "Store C out-of-channel block & compare"),
    # Scene 7: Investigation (v5 audio: brand gets a case, AI agent investigates)
    (0, 93.67, 98.67, 1.0, 7, "Store C case expansion"),
    (0, 99.88, 106.88, 2.0, 7, "Agent investigation steps (2x)"),
    (0, 403.65, 409.82, 1.0, 7, "Agent findings & verdict"),
    # Scene 8: Supply chain (v5 audio: supply chain leak visible)
    (0, 417.75, 426.43, 1.0, 8, "Bryntum supply chain timeline"),
    # Scene 9: Business model (v5 audio: brands spend >$150B on market insights)
    (0, 427.74, 427.74 + sc9_dur, 1.0, 9, "Business model arrow chain"),
    # Scene 10: Brand insights (v5 audio: answers from verified purchases in seconds)
    (0, 438.74, 453.50, 1.0, 10, "Console Insights query & 95% interval"),
    # Scene 11: AI analyst (v5 audio: AI analyst builds charts)
    (0, 458.55, 465.12, 1.0, 11, "AG Studio autonomous analyst"),
    # Scene 12: Privacy (v5 audio: data boundary & differential privacy with OpenDP)
    (2, 1.00, 14.57, 1.0, 12, "/privacy page boundary & OpenDP"),
    # Scene 13: Onboarding (v5 audio: verification API & network policy)
    (0, 475.18, 491.73, 1.0, 13, "Onboarding security levels"),
    # Scene 14: Close (v5 audio: closing CTA)
    (0, 491.18, 500.82, 1.0, 14, "Closing CTA & logo"),
]

scene_start_times = {}
curr_time = LEAD_IN

for seg in segments:
    src, start, end, speed, sc, desc = seg
    dur = (end - start) / speed
    if sc not in scene_start_times:
        scene_start_times[sc] = curr_time
    curr_time += dur

parts = []
parts.append("color=c=#0b1220:s=1280x720:d=1.0,fps=30,format=yuv420p[v_lead]")

for i, (src, start, end, speed, sc, desc) in enumerate(segments):
    filter_chain = f"[{src}:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed}"
    filter_chain += ",scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#0b1220,fps=30,format=yuv420p"
    parts.append(f"{filter_chain}[v{i}]")

v_concat = "[v_lead]" + "".join(f"[v{i}]" for i in range(len(segments))) + f"concat=n={len(segments) + 1}:v=1:a=0[outv]"
v_graph = ";".join(parts) + ";" + v_concat

wavs = [os.path.join(VO_DIR, f"{i}.wav") for i in range(1, 15)]
audio_inputs = []
a_parts = []
offset_inputs = 4

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
cmd = [
    ffmpeg, "-v", "error", "-y",
    "-i", main_video,
    "-i", popup_video,
    "-i", privacy_video,
    "-i", card_usd_video,
]
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

print("\n=== Per-Scene Synchronization Report Table ===")
print(f"{'Scene':<6} | {'Audio':<8} | {'Audio Start-End':<17} | {'Visual Dur':<10} | {'Pad':<6} | {'Visual Source & Description'}")
print("-" * 95)
print(f"{'LeadIn':<6} | {'0.00s':<8} | {'0.00s - 1.00s':<17} | {'1.00s':<10} | {'1.00s':<6} | Black slate lead-in (#0b1220)")
for sc in range(1, 15):
    a_dur = audio_durs[sc]
    v_dur = target_scene_durs[sc]
    pad = v_dur - a_dur
    s_time = scene_start_times[sc]
    e_time = s_time + a_dur
    sc_descs = [seg[5] for seg in segments if seg[4] == sc]
    desc_str = " -> ".join(sc_descs)
    print(f"{sc:<6} | {a_dur:5.2f}s  | {s_time:6.2f}s - {e_time:6.2f}s  | {v_dur:6.2f}s    | {pad:4.2f}s | {desc_str}")
print("-" * 95)
print(f"Total Video Duration: {curr_time:.2f}s ({int(curr_time // 60)}m {curr_time % 60:04.1f}s)")
