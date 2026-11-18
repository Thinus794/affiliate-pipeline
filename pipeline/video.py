"""Renders a 1080x1920 faceless short (TikTok / Reels / YouTube Shorts) with voiceover,
animated slides, burned-in captions and optional background music."""
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import graphics as g
from .util import ASSETS, product_images, hex_rgb
from .voice import synthesize

FPS = 30


def _ass_time(t):
    h, rem = divmod(max(0, t), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _ass_color(hexstr):
    r, g_, b = hex_rgb(hexstr)
    return f"&H00{b:02X}{g_:02X}{r:02X}"


def _subtitles(words, title, dur, colors, path):
    accent = _ass_color(colors["accent"])
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,86,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,330,1
Style: Title,DejaVu Sans,62,&H00141414,&H00141414,{accent},{accent},-1,0,0,0,100,100,0,0,3,22,0,8,80,80,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    if title:
        lines.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(dur - 2.6)},Title,,0,0,0,,{title.upper()}\n")
    # 3-word caption chunks, current word highlighted in the accent colour
    chunk = []
    groups = []
    for w in words:
        chunk.append(w)
        if len(chunk) == 3 or w["word"].endswith((".", "!", "?", ",")):
            groups.append(chunk)
            chunk = []
    if chunk:
        groups.append(chunk)
    for gi, grp in enumerate(groups):
        g_end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else grp[-1]["end"] + 0.3
        for wi, w in enumerate(grp):
            s = w["start"]
            e = grp[wi + 1]["start"] if wi + 1 < len(grp) else g_end
            txt = " ".join(
                (f"{{\\c{accent}}}{x['word'].upper()}{{\\c&H00FFFFFF&}}" if j == wi else x["word"].upper())
                for j, x in enumerate(grp))
            lines.append(f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Cap,,0,0,0,,{txt}\n")
    Path(path).write_text("".join(lines), encoding="utf-8")


def _clip(img_path, seconds, out, zoom_in=True):
    frames = max(1, int(seconds * FPS))
    z = "min(zoom+0.0009,1.14)" if zoom_in else "if(eq(on,0),1.14,max(zoom-0.0009,1.0))"
    vf = (f"scale=2160:3840,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s=1080x1920:fps={FPS},format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img_path, "-vf", vf,
                    "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out], check=True)


def render(p, c, cfg, hook_index, out_path):
    """Build one short. Returns dict with duration and whether a real voice was used."""
    colors = cfg["brand_colors"]
    tmp = Path(tempfile.mkdtemp(prefix="vid_"))
    try:
        hook = c["hooks"][hook_index % len(c["hooks"])]
        script = f"{hook} {c['body']} {c['cta']}"
        audio, words, dur, real = synthesize(script, cfg["voice"], cfg.get("voice_rate", "+0%"),
                                             str(tmp / "voice.mp3"))
        dur = max(dur + 0.6, 8)

        # --- slides ---
        slides = []
        for i, ip in enumerate(product_images(p)[:5]):
            im = g.open_image(ip)
            if im:
                slides.append(g.photo_slide(im))
        niche_label = cfg["niches"].get(p["niche"], {}).get("label", "")
        if len(slides) < 2:  # pad with text cards built from the key points
            slides.insert(0, g.text_slide(niche_label or "Worth a look", p["name"], colors))
            for i, pt in enumerate(p["points"][:4]):
                slides.append(g.text_slide(f"Reason {i + 1}", pt, colors, i))
        host = cfg["site_url"].split("//")[-1]
        slides.append(g.cta_slide(p["name"], p.get("price", ""), host, colors))

        cta_len = 2.6
        body_len = (dur - cta_len) / max(1, len(slides) - 1)
        clips = []
        for i, s in enumerate(slides):
            ip = tmp / f"s{i}.png"
            s.save(ip)
            secs = cta_len if i == len(slides) - 1 else body_len
            cp = tmp / f"c{i}.mp4"
            _clip(str(ip), secs, str(cp), zoom_in=(i % 2 == 0))
            clips.append(cp)
        (tmp / "list.txt").write_text("".join(f"file '{x}'\n" for x in clips))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                        str(tmp / "list.txt"), "-c", "copy", str(tmp / "slides.mp4")], check=True)

        _subtitles(words, c.get("screen_title", ""), dur, colors, tmp / "subs.ass")

        music = sorted((ASSETS / "music").glob("*.mp3"))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "slides.mp4"), "-i", audio]
        if music:
            cmd += ["-stream_loop", "-1", "-i", str(random.choice(music))]
            af = (f"[1:a]volume=1.0[v];[2:a]volume=0.12,afade=t=out:st={dur - 1.5:.2f}:d=1.5[m];"
                  f"[v][m]amix=inputs=2:duration=first:dropout_transition=0[a]")
        else:
            af = "[1:a]anull[a]"
        subs = str(tmp / "subs.ass").replace(":", "\\:")
        cmd += ["-filter_complex", f"[0:v]ass='{subs}'[vo];{af}", "-map", "[vo]", "-map", "[a]",
                "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out_path)]
        subprocess.run(cmd, check=True)
        return {"duration": round(dur, 1), "real_voice": real, "script": script}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
