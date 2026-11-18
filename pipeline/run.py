"""Daily run: write content for new products, pick today's products, render videos + pins,
rebuild the website and posting desk, optionally upload to YouTube, save state.

    python -m pipeline.run                # normal daily run
    python -m pipeline.run --count 1      # just one video
    python -m pipeline.run --regen ID     # rewrite the words for one product
"""
import argparse
import shutil
import time
from datetime import date, datetime, timezone

from . import content as content_mod
from . import pins, site, video, youtube
from .util import BUILD, load_config, load_products, load_state, save_state


def pick_today(products, state, n, repeat_days, today):
    """Never-posted first, then least-recently posted; rotate across niches."""
    def last(p):
        s = state["posted"].get(p["id"])
        return s["last"] if s else "0000-00-00"

    def fresh_enough(p):
        s = state["posted"].get(p["id"])
        if not s:
            return True
        return (date.fromisoformat(today) - date.fromisoformat(s["last"])).days >= repeat_days

    pool = sorted(products, key=last)
    eligible = [p for p in pool if fresh_enough(p)] or pool
    picked, niches_used = [], set()
    for p in eligible:                      # first pass: one per niche
        if len(picked) >= n:
            break
        if p["niche"] not in niches_used:
            picked.append(p)
            niches_used.add(p["niche"])
    for p in eligible:                      # fill the rest
        if len(picked) >= n:
            break
        if p not in picked:
            picked.append(p)
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int)
    ap.add_argument("--regen", help="product id to regenerate content for")
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    products = load_products()
    if not products:
        raise SystemExit("No active products in products.csv")
    state = load_state()
    today = datetime.now(timezone.utc).date().isoformat()
    print(f"== Affiliate pipeline {today}: {len(products)} active products ==")

    # 1. words (only new products hit the AI; ~13s gap keeps us inside the free rate limit)
    contents = {}
    for p in products:
        is_new = not (content_mod.CONTENT / f"{p['id']}.json").exists() or args.regen == p["id"]
        contents[p["id"]] = content_mod.get_content(p, cfg, force=(args.regen == p["id"]))
        if is_new and contents[p["id"]].get("_source") == "gemini":
            time.sleep(13)

    # 2. fresh build folder
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "today").mkdir(parents=True)

    # 3. pins for every product (cheap, keeps pin URLs stable)
    for p in products:
        pins.make_pins(p, contents[p["id"]], cfg, BUILD / "pins")

    # 4. today's videos
    n = args.count or cfg.get("videos_per_day", 3)
    picked = [] if args.no_video else pick_today(products, state, n, cfg.get("repeat_product_after_days", 14), today)
    today_items, yt_results = [], {}
    for p in picked:
        times = state["posted"].get(p["id"], {}).get("count", 0)
        fname = f"{today}-{p['id']}.mp4"
        t0 = time.time()
        info = video.render(p, contents[p["id"]], cfg, hook_index=times, out_path=BUILD / "today" / fname)
        print(f"[video] {fname} {info['duration']}s voice={'yes' if info['real_voice'] else 'SILENT'} ({time.time() - t0:.0f}s)")
        today_items.append({"id": p["id"], "file": fname, **info})
        if youtube.enabled():
            c = contents[p["id"]]
            tags = cfg["niches"].get(p["niche"], {}).get("hashtags", [])
            desc = (f"{c.get('youtube_description', '')}\n\nGet it here: {cfg['site_url']}/go/{p['id']}/\n\n"
                    f"{cfg['disclosure']}\n{' '.join(tags)}")
            try:
                yt_results[p["id"]] = youtube.upload(BUILD / "today" / fname, c.get("youtube_title", p["name"]), desc, tags)
                print(f"[youtube] {yt_results[p['id']]}")
            except Exception as e:
                print(f"[youtube] upload failed for {p['id']}: {e}")
        state["posted"][p["id"]] = {"last": today, "count": times + 1}
        state["history"].append({"date": today, "id": p["id"], "youtube": yt_results.get(p["id"], "")})
    state["history"] = state["history"][-500:]

    # 5. website, posting desk, Pinterest CSV
    site.build_site(products, contents, cfg, BUILD, today_items, today)
    site.pinterest_csv(products, contents, cfg, today_items, BUILD)
    site.today_page(cfg, today_items, contents, products, BUILD, today, yt_results)
    save_state(state)
    print(f"== Done. Posting desk: {cfg['site_url']}/today/ ==")


if __name__ == "__main__":
    main()
