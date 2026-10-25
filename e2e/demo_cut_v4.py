"""demo_cut_v4.py: Full v4 cut with exact scene-to-picture remapping, USD card clip, and /privacy."""
import json, os, subprocess, wave, shutil
import imageio_ffmpeg

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "demo")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
VO_DIR = "/home/parth.sinha/Downloads/paypal/videos/vo"
FINAL_OUT = "/home/parth.sinha/Downloads/paypal/videos/dryrun-2026-10-25-v4.mp4"

meta = json.load(open(os.path.join(OUT_DIR, "marks.json")))
main_video = meta["video"]
marks = meta["marks"]

# Inputs:
# 0: main_video
# 1: popup_video
# 2: privacy_video
# 3: card_usd_video

popups = [m["label"] for m in marks if m["kind"] == "popup_close" and m.get("label")]
popup_video = popups[0] if popups else None

privacy_video = os.path.join(CLIPS_DIR, "page@3344527d9a3b7740084b86675fe527fc.webm")
card_usd_video = os.path.join(CLIPS_DIR, "page@0c56c495787e13db32d277e031edd5f6.webm")

audio_durs = json.load(open(os.path.join(VO_DIR, "durations.json")))
audio_durs = {int(k): float(v) for k, v in audio_durs.items()}

# Target per-scene durations matching v5 narration:
target_scene_durs = {
    1: 8.13,   # Problem (audio 7.13s)
    2: 5.69,   # Gap (audio 4.69s)
    3: 16.08,  # Product (audio 15.08s: 6.0s idea + 10.08s how)
    4: 3.39,   # Teaser (audio 2.39s: why brands pay)
    5: 16.76,  # Genuine sale (audio 12.76s: checkout + USD card + popup + receipt)
    6: 10.22,  # Blocked sale (audio 9.22s: Store C block & compare)
    7: 14.67,  # Investigation (audio 10.67s: Store C case & agent findings)
    8: 8.68,   # Supply chain (audio 7.68s: Bryntum timeline)
    9: 10.54,  # Business model (audio 9.54s: $150B market & survey pain)
    10: 14.76, # Brand insights (audio 13.76s: console queries & charts)
    11: 6.57,  # AI analyst (audio 5.57s: AG Studio analyst)
    12: 13.57, # Privacy (audio 12.57s: /privacy data boundary & OpenDP)
    13: 16.55, # Onboarding (audio 15.55s: network policy & 3 tiers)
    14: 9.64,  # Close (audio 7.64s: closing CTA)
}

LEAD_IN = 1.0

# Segments definition: (input_idx, start, end, speed_factor, scene_num, desc)
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
    (3, 1.00, 5.50, 1.0, 5, "Card payment form in USD ($899.00)"),
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
    (0, 427.74, 438.28, 1.0, 9, "Business model arrow chain"),
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
# Inputs count:
# 0: main_video
# 1: popup_video
# 2: privacy_video
# 3: card_usd_video
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
    # find segments for this scene
    sc_descs = [seg[5] for seg in segments if seg[4] == sc]
    desc_str = " -> ".join(sc_descs)
    print(f"{sc:<6} | {a_dur:5.2f}s  | {s_time:6.2f}s - {e_time:6.2f}s  | {v_dur:6.2f}s    | {pad:4.2f}s | {desc_str}")
print("-" * 95)
print(f"Total Video Duration: {curr_time:.2f}s ({int(curr_time // 60)}m {curr_time % 60:04.1f}s)")
