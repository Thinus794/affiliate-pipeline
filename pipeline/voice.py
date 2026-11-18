"""Free AI voiceover with Microsoft Edge neural voices (edge-tts), plus word timings for captions.

If the voice service can't be reached, a silent track with estimated timings is used so the
video still renders (you'd add a voiceover in CapCut instead).
"""
import asyncio
import subprocess


async def _edge(text, voice, rate, out_mp3):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append({"word": chunk["text"], "start": start, "end": start + chunk["duration"] / 1e7})
    return words


def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", path], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def synthesize(text, voice, rate, out_mp3):
    """Returns (audio_path, words[{word,start,end}], duration_seconds, used_real_voice)."""
    try:
        words = asyncio.run(_edge(text, voice, rate, out_mp3))
        dur = _duration(out_mp3)
        if dur > 1 and words:
            return out_mp3, words, dur, True
        raise RuntimeError("empty audio")
    except Exception as e:
        print(f"[voice] edge-tts unavailable ({str(e)[:90]}); using silent track with estimated timing")
    tokens = text.split()
    per = 0.36  # ~165 words per minute
    words, t = [], 0.3
    for w in tokens:
        d = per + (0.25 if w.endswith((".", "!", "?")) else 0)
        words.append({"word": w, "start": t, "end": t + per})
        t += d
    dur = t + 0.5
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", f"{dur:.2f}", "-q:a", "9", out_mp3], check=True)
    return out_mp3, words, dur, False
