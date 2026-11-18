"""Builds the free website hosted on GitHub Pages:
  /               link-in-bio hub + product grid (put this URL in every bio)
  /go/<id>/       short redirect to the affiliate link (swap links without re-posting)
  /posts/<id>/    SEO review article per product (Pinterest pins point here)
  /today/         private posting desk: today's videos, captions with copy buttons, Pinterest CSV
"""
import csv
import html
import json
import shutil
from datetime import datetime, timedelta, timezone

import markdown as md
from PIL import ImageOps

from . import graphics as g
from .util import product_images

CSS = """
:root{--bg:%(bg)s;--acc:%(accent)s;--txt:%(text)s;--mut:%(muted)s;--card:#1f2228}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--txt);line-height:1.55}
a{color:var(--acc)}.wrap{max-width:760px;margin:0 auto;padding:28px 18px 60px}
header{text-align:center;margin-bottom:26px}header h1{margin:.2em 0;font-size:2rem}header p{color:var(--mut);margin:0}
.btn{display:block;text-align:center;background:var(--acc);color:#141414;font-weight:700;text-decoration:none;padding:15px 18px;border-radius:12px;margin:10px 0}
.btn.ghost{background:transparent;color:var(--acc);border:2px solid var(--acc)}
h2.sec{margin:34px 0 12px;font-size:1.15rem;color:var(--acc);text-transform:uppercase;letter-spacing:.06em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}
.card{background:var(--card);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.card img{width:100%%;aspect-ratio:1;object-fit:cover;background:#fff}
.card .b{padding:12px;display:flex;flex-direction:column;gap:6px;flex:1}.card h3{margin:0;font-size:1rem}
.card .price{color:var(--mut);font-size:.9rem}.card .row{display:flex;gap:8px;margin-top:auto}
.card .row a{flex:1;text-align:center;padding:9px;border-radius:9px;font-weight:600;text-decoration:none;font-size:.9rem}
.card .row a.buy{background:var(--acc);color:#141414}.card .row a.read{border:1px solid var(--mut);color:var(--txt)}
.disc{color:var(--mut);font-size:.82rem;margin-top:40px;text-align:center}
article img{max-width:100%%;border-radius:12px}article h2{color:var(--acc)}
.item{background:var(--card);border-radius:14px;padding:16px;margin:16px 0}.item video{width:100%%;max-height:70vh;border-radius:10px;background:#000}
textarea{width:100%%;min-height:90px;background:#0e0f12;color:var(--txt);border:1px solid #333;border-radius:8px;padding:8px;font:inherit;font-size:.9rem}
.cap{margin:10px 0}.cap b{display:block;margin-bottom:4px}.small{font-size:.85rem;color:var(--mut)}
"""


def _page(cfg, title, body, desc="", noindex=False, extra_head=""):
    css = CSS % cfg["brand_colors"]
    robots = '<meta name="robots" content="noindex,nofollow">' if noindex else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><meta name="description" content="{html.escape(desc)}">{robots}
{extra_head}<style>{css}</style></head><body><div class="wrap">{body}
<p class="disc">{html.escape(cfg['disclosure'])} <a href="{cfg['site_url']}/disclosure/">Disclosure</a></p>
</div></body></html>"""


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _thumb(p, build):
    """Square product image for the site; falls back to the first pin."""
    out = build / "img" / f"{p['id']}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    imgs = product_images(p)
    im = g.open_image(imgs[0]) if imgs else None
    if im:
        ImageOps.fit(im, (600, 600)).save(out, quality=85)
    else:
        from .pins import _photo_or_card
        _photo_or_card(p, cfg_colors[0], (600, 600)).save(out, quality=85)
    return f"img/{p['id']}.jpg"


cfg_colors = [None]  # set by build_site so _thumb can draw a fallback card


def build_site(products, contents, cfg, build, today_items, run_date):
    url = cfg["site_url"]
    cfg_colors[0] = cfg["brand_colors"]
    by_niche = {}
    for p in products:
        by_niche.setdefault(p["niche"], []).append(p)
        thumb = _thumb(p, build)
        c = contents[p["id"]]
        # redirect page
        aff = html.escape(p["affiliate_url"], quote=True)
        _write(build / "go" / p["id"] / "index.html",
               f'<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex">'
               f'<meta http-equiv="refresh" content="0;url={aff}"><title>Redirecting…</title></head>'
               f'<body><p>Taking you to the store… <a href="{aff}" rel="sponsored nofollow">Continue</a></p>'
               f'<script>location.replace({json.dumps(p["affiliate_url"])})</script></body></html>')
        # review article
        art = md.markdown(c.get("blog_markdown", ""), extensions=["extra"])
        buy = f'<a class="btn" href="{url}/go/{p["id"]}/" rel="sponsored nofollow">Check the latest price →</a>'
        body = (f'<p><a href="{url}/">← All picks</a></p><article><h1>{html.escape(c.get("blog_title", p["name"]))}</h1>'
                f'<img src="{url}/{thumb}" alt="{html.escape(p["name"])}">'
                f'<p class="small">{html.escape(cfg["disclosure"])}</p>{buy}{art}{buy}'
                f'<p class="small">{html.escape(cfg["currency_note"])}</p></article>')
        ld = {"@context": "https://schema.org", "@type": "Article", "headline": c.get("blog_title", p["name"]),
              "image": f"{url}/{thumb}", "datePublished": run_date}
        _write(build / "posts" / p["id"] / "index.html",
               _page(cfg, c.get("blog_title", p["name"]), body, c.get("blog_meta", ""),
                     extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>'))

    # hub / link in bio
    featured_ids = [t["id"] for t in today_items]
    parts = [f'<header><h1>{html.escape(cfg["site_name"])}</h1><p>{html.escape(cfg["site_tagline"])}</p></header>']
    if featured_ids:
        parts.append('<h2 class="sec">From today\'s videos</h2>')
        for pid in featured_ids:
            p = next(x for x in products if x["id"] == pid)
            parts.append(f'<a class="btn" href="{url}/go/{pid}/" rel="sponsored nofollow">{html.escape(p["name"])}</a>')
    for key, items in by_niche.items():
        label = cfg["niches"].get(key, {}).get("label", key.title())
        parts.append(f'<h2 class="sec">{html.escape(label)}</h2><div class="grid">')
        for p in items:
            parts.append(f'<div class="card"><img loading="lazy" src="{url}/img/{p["id"]}.jpg" alt="{html.escape(p["name"])}">'
                         f'<div class="b"><h3>{html.escape(p["name"])}</h3><div class="price">{html.escape(p.get("price", ""))}</div>'
                         f'<div class="row"><a class="read" href="{url}/posts/{p["id"]}/">Review</a>'
                         f'<a class="buy" href="{url}/go/{p["id"]}/" rel="sponsored nofollow">Price</a></div></div></div>')
        parts.append("</div>")
    _write(build / "index.html", _page(cfg, cfg["site_name"], "".join(parts), cfg["site_tagline"]))

    _write(build / "disclosure" / "index.html", _page(cfg, "Affiliate disclosure",
           f'<p><a href="{url}/">← Home</a></p><h1>Affiliate disclosure</h1><p>{html.escape(cfg["disclosure"])}</p>'
           '<p>Recommendations are based on research of specs, features and public reviews. Prices and availability change; '
           'always confirm on the store page before buying.</p>'))
    # SEO plumbing
    urls = [f"{url}/"] + [f"{url}/posts/{p['id']}/" for p in products]
    _write(build / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(f"<url><loc>{u}</loc><lastmod>{run_date}</lastmod></url>" for u in urls) + "</urlset>")
    _write(build / "robots.txt", f"User-agent: *\nDisallow: /go/\nDisallow: /today/\nSitemap: {url}/sitemap.xml\n")
    (build / ".nojekyll").write_text("")


def pinterest_csv(products, contents, cfg, today_items, build, now=None):
    """Pinterest 'Bulk create Pins' CSV for today's products, scheduled through the day."""
    now = now or datetime.now(timezone.utc)
    url = cfg["site_url"]
    path = build / "today" / "pinterest.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    slot = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"])
        for t in today_items:
            p = next(x for x in products if x["id"] == t["id"])
            c = contents[p["id"]]
            board = cfg["niches"].get(p["niche"], {}).get("pinterest_board", "My Picks")
            for i, pin in enumerate((c.get("pins") or [])[:3]):
                slot += 1
                when = (now + timedelta(hours=2 + slot * 2)).strftime("%Y-%m-%dT%H:%M:%S")
                w.writerow([pin["title"][:100], f"{url}/pins/{p['id']}-{i + 1}.jpg", board, "",
                            pin.get("description", "")[:500], f"{url}/posts/{p['id']}/", when,
                            ", ".join(c.get("keywords", [])[:6])])
    return path


def today_page(cfg, today_items, contents, products, build, run_date, yt_results):
    url = cfg["site_url"]
    parts = [f'<header><h1>Posting desk</h1><p>{run_date} · open on your phone, save each video, copy the caption, post.</p></header>',
             f'<a class="btn ghost" href="{url}/today/pinterest.csv" download>Download today\'s Pinterest CSV</a>',
             '<p class="small">Pinterest → Create → Bulk create Pins → Upload .csv. Board names in the CSV must already exist on your account.</p>']
    for t in today_items:
        p = next(x for x in products if x["id"] == t["id"])
        c = contents[p["id"]]
        tags = " ".join(cfg["niches"].get(p["niche"], {}).get("hashtags", []))
        yt = yt_results.get(p["id"])
        yt_line = f'<p class="small">YouTube Shorts: uploaded automatically → <a href="{yt}">{yt}</a></p>' if yt else \
                  '<p class="small">YouTube Shorts: not auto-uploaded (no YouTube keys set) – post it with the YouTube caption below.</p>'
        caps = [("TikTok", f'{c.get("tiktok_caption", "")}\n{cfg["short_disclosure"]}'),
                ("Instagram Reels", f'{c.get("instagram_caption", "")}\n{cfg["short_disclosure"]}'),
                ("YouTube title", c.get("youtube_title", "")),
                ("YouTube description", f'{c.get("youtube_description", "")}\n\nGet it here: {url}/go/{p["id"]}/\n\n{cfg["disclosure"]}\n{tags}')]
        boxes = "".join(f'<div class="cap"><b>{n}</b><textarea readonly>{html.escape(v)}</textarea>'
                        f'<button onclick="navigator.clipboard.writeText(this.previousElementSibling.value);this.textContent=\'Copied ✓\'">Copy</button></div>'
                        for n, v in caps)
        parts.append(f'<div class="item"><h3>{html.escape(p["name"])}</h3>'
                     f'<video controls playsinline preload="metadata" src="{url}/today/{t["file"]}"></video>'
                     f'<a class="btn" href="{url}/today/{t["file"]}" download>Download video</a>{yt_line}{boxes}'
                     f'<p class="small">Link to put in bio: <b>{url}/</b> · Direct: {url}/go/{p["id"]}/</p></div>')
    if not today_items:
        parts.append("<p>No videos today.</p>")
    _write(build / "today" / "index.html", _page(cfg, "Posting desk", "".join(parts), noindex=True))
