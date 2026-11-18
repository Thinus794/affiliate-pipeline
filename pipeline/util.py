"""Shared helpers: paths, config, product loading, downloads."""
import csv
import hashlib
import io
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
BUILD = ROOT / "build"          # regenerated every run, deployed to GitHub Pages
CACHE = ROOT / ".cache"         # downloaded product images

FONT_BOLD = None
FONT_REG = None
for cand in [
    ASSETS / "fonts" / "Montserrat-ExtraBold.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]:
    if cand.exists():
        FONT_BOLD = str(cand)
        break
for cand in [
    ASSETS / "fonts" / "Montserrat-Medium.ttf",
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]:
    if cand.exists():
        FONT_REG = str(cand)
        break


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    # Let a GitHub secret/variable override the site URL without editing the file
    if os.environ.get("SITE_URL"):
        cfg["site_url"] = os.environ["SITE_URL"].rstrip("/")
    cfg["site_url"] = cfg["site_url"].rstrip("/")
    return cfg


def _split(v):
    return [x.strip() for x in (v or "").split("|") if x.strip()]


def load_products():
    """Read products from a published Google Sheet (PRODUCTS_CSV_URL) or data/products.csv."""
    url = os.environ.get("PRODUCTS_CSV_URL", "").strip()
    text = None
    if url:
        try:
            text = fetch(url).decode("utf-8-sig")
            (DATA / "products.csv").write_text(text, encoding="utf-8")  # keep a copy in the repo
            print(f"[products] loaded from Google Sheet")
        except Exception as e:  # fall back to the local copy
            print(f"[products] sheet download failed ({e}); using local products.csv")
    if text is None:
        text = (DATA / "products.csv").read_text(encoding="utf-8-sig")
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
        if not r.get("id") or not r.get("affiliate_url"):
            continue
        if r.get("active", "yes").lower() in ("no", "n", "false", "0"):
            continue
        r["id"] = slugify(r["id"])
        r["images"] = _split(r.get("image_urls"))
        r["points"] = _split(r.get("key_points"))
        r["niche"] = r.get("niche") or "home"
        rows.append(r)
    return rows


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "item"


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (affiliate-pipeline)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def cached_image(url):
    """Download an image once and reuse it. Returns a local path or None."""
    if not url:
        return None
    if not url.startswith("http"):
        p = ROOT / url
        return str(p) if p.exists() else None
    CACHE.mkdir(exist_ok=True)
    name = hashlib.md5(url.encode()).hexdigest()
    path = CACHE / f"{name}.img"
    if path.exists() and path.stat().st_size > 0:
        return str(path)
    try:
        path.write_bytes(fetch(url))
        return str(path)
    except Exception as e:
        print(f"[image] could not download {url[:80]}: {e}")
        return None


def product_images(p):
    """Product image paths: explicit URLs, then any files in assets/images/<id>*."""
    out = [x for x in (cached_image(u) for u in p["images"]) if x]
    for f in sorted((ASSETS / "images").glob(f"{p['id']}*")):
        out.append(str(f))
    return out


def load_state():
    f = DATA / "state.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {"posted": {}, "history": []}


def save_state(state):
    (DATA / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
