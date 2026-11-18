"""Writes all the words for a product: video scripts, captions, pin text and a blog review.

Uses Google Gemini's free API tier when GEMINI_API_KEY is set; otherwise falls back to
built-in templates so the pipeline never stops.
Content is generated once per product and saved in content/<id>.json (edit it freely).
"""
import json
import os
import re
import urllib.request

from .util import CONTENT

PROMPT = """You write short-form affiliate marketing content for a faceless South African creator.
Product: {name}
Category: {niche_label}
Price: {price}
Key points: {points}
Affiliate program: {program}

Rules:
- Honest, specific, no fake claims, no fake personal experience ("I've used this for years" is NOT allowed). Speak as a reviewer who researched it.
- Plain conversational English a South African audience relates to. No emojis in the voiceover.
- Mention that the link is in the bio / description. Never invent discount codes.

Return ONLY JSON with exactly these keys:
{{
 "hooks": [3 different scroll-stopping first lines, max 12 words each],
 "body": "voiceover body, 45-65 words, explains who it is for and the 2-3 best points",
 "cta": "one closing line, max 12 words, pointing to the link in bio",
 "screen_title": "on-screen title, max 5 words",
 "tiktok_caption": "max 150 chars + 4 hashtags",
 "instagram_caption": "2-4 short lines + 6 hashtags",
 "youtube_title": "max 70 chars, ends with #shorts",
 "youtube_description": "2-3 sentences",
 "pins": [3 objects with "title" (max 90 chars) and "description" (max 400 chars, keyword-rich)],
 "blog_title": "SEO title, max 65 chars",
 "blog_meta": "meta description, max 155 chars",
 "blog_markdown": "a 500-700 word review in Markdown with ## headings: what it is, who it's for, best features, downsides to consider, verdict. Include a balanced downsides section.",
 "keywords": [6 search keywords]
}}"""


def _gemini(prompt, model):
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(text)
    except Exception as e:
        print(f"[content] Gemini failed ({e}); using templates")
        return None


def _template(p, niche_label, tags):
    name, price = p["name"], p.get("price") or "check the link"
    pts = p["points"] or [f"Popular pick in {niche_label}"]
    short = name.split(" ")[0] if len(name) > 28 else name
    body = (f"This is the {name}. " + " ".join(f"{x}." for x in pts[:3]) +
            f" It's ideal if you want something that just works without overthinking it. Price right now is {price}, but that changes, so check before you buy.")
    hashtags = " ".join(tags[:4])
    blog = [f"## What is the {name}?",
            f"The {name} is a {niche_label.lower()} pick that keeps coming up for good reason. Here's a quick, honest rundown.",
            "## Who it's for",
            f"It suits beginners and busy people who want results without a steep learning curve.",
            "## Best features"] + [f"- **{x}**" for x in pts] + [
            "## Downsides to consider",
            "- Prices and stock change often, so compare before buying.",
            "- Check shipping and import costs to South Africa.",
            "- Read the warranty terms for your country.",
            "## Verdict",
            f"If the points above match what you need, the {name} is worth a look. Use the button below to see the current price."]
    return {
        "hooks": [f"Stop scrolling if you've been eyeing a {short}.",
                  f"Three reasons people are buying the {short}.",
                  f"Is the {short} actually worth it? Quick answer."],
        "body": body,
        "cta": "Link's in my bio if you want to check the price.",
        "screen_title": short[:30],
        "tiktok_caption": f"{name} - worth it? {hashtags}",
        "instagram_caption": f"{name}\n" + "\n".join(f"- {x}" for x in pts[:3]) + f"\nLink in bio.\n{' '.join(tags[:6])}",
        "youtube_title": f"{name[:55]} - worth it? #shorts",
        "youtube_description": f"Quick look at the {name}. " + " ".join(pts[:2]),
        "pins": [{"title": f"{name}: is it worth it?", "description": f"{name} review. " + ". ".join(pts) + "."},
                 {"title": f"{len(pts)} reasons to get the {short}", "description": ". ".join(pts) + f". {niche_label} ideas."},
                 {"title": f"Best {niche_label.lower()} pick: {short}", "description": f"Looking for {niche_label.lower()}? The {name}: " + ". ".join(pts) + "."}],
        "blog_title": f"{name} Review: Is It Worth It?",
        "blog_meta": f"Honest look at the {name}: features, who it's for, downsides and verdict.",
        "blog_markdown": "\n\n".join(blog),
        "keywords": [name.lower(), f"{short.lower()} review", niche_label.lower()],
    }


def get_content(p, cfg, force=False):
    CONTENT.mkdir(exist_ok=True)
    path = CONTENT / f"{p['id']}.json"
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    niche = cfg["niches"].get(p["niche"], {"label": p["niche"].title(), "hashtags": []})
    prompt = PROMPT.format(name=p["name"], niche_label=niche["label"], price=p.get("price", ""),
                           points="; ".join(p["points"]), program=p.get("program", ""))
    data = _gemini(prompt, cfg.get("gemini_model", "gemini-2.5-flash"))
    source = "gemini"
    if not data or not data.get("hooks") or not data.get("body"):
        data, source = _template(p, niche["label"], niche.get("hashtags", [])), "template"
    data["_source"] = source
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[content] {p['id']}: written ({source})")
    return data
