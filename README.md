# Affiliate Pipeline (free)

Every morning at 06:17 (SA time) GitHub runs this for free and:

1. **Writes the words** for any new product in your list (Gemini free API): 3 video hooks, voiceover script, TikTok / Instagram / YouTube captions, 3 Pinterest pin texts and a 500-700 word review article.
2. **Picks today's products**: new ones first, then whatever has gone longest without a video, spread across your niches. Each repeat uses a different hook.
3. **Makes the videos**: 1080x1920 faceless shorts with a free South African AI voice (edge-tts, `en-ZA-LukeNeural`), moving product slides, word-by-word captions and an end card that says "link in bio".
4. **Makes the Pinterest pins**: 3 designs per product, plus a ready-to-upload bulk CSV.
5. **Updates your free website** on GitHub Pages: a link-in-bio hub, a review page per product, short `/go/` redirect links, a sitemap for Google.
6. **Uploads to YouTube Shorts** automatically (optional, once you add the keys).
7. **Builds your posting desk** at `/today/`: open it on your phone, download each video, copy the caption, post to TikTok and Instagram.

## Your daily routine (about 10 minutes)
1. Open `https://thinus794.github.io/affiliate-pipeline/today/` on your phone.
2. For each video, tap **Download video**, then post it to TikTok and Instagram Reels and paste the matching caption.
3. Once a week: tap **Download today's Pinterest CSV** and upload it in Pinterest → Create → Bulk create Pins.

## Adding products
Edit `data/products.csv`, or point the pipeline at a Google Sheet (see the setup guide). Columns:

| column | example |
|---|---|
| id | `xtool-f1` (short, unique, no spaces) |
| niche | `tools`, `tech` or `home` (set up in config.json) |
| name | xTool F1 Portable Laser Engraver |
| price | From about $400 |
| program | xTool affiliate |
| affiliate_url | your tracking link |
| image_urls | product photo links separated by a vertical bar (or put files in `assets/images/<id>-1.jpg`) |
| key_points | 3-4 selling points separated by a vertical bar |
| active | yes / no |

The words for a product are saved in `content/<id>.json`; edit that file to change any script or caption. To have them rewritten, delete the file, or start a manual run with `--regen <id>`.

## Settings
`config.json`: site name, videos per day, voice, brand colours, hashtags and Pinterest board names per niche, disclosure text.
Background music: drop royalty-free `.mp3` files into `assets/music/` (for example from the YouTube Audio Library).

## Run on your own PC (optional)
```
pip install -r requirements.txt   # plus ffmpeg installed
python -m pipeline.run --count 1
```
Output lands in `build/`.
