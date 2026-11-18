"""Pinterest pin images (1000x1500) - three designs per product."""
from PIL import Image, ImageDraw, ImageOps

from . import graphics as g
from .util import hex_rgb, product_images

W, H = 1000, 1500


def _photo_or_card(p, colors, size):
    imgs = product_images(p)
    if imgs:
        im = g.open_image(imgs[0])
        if im:
            bg = Image.new("RGB", size, (255, 255, 255))
            fg = ImageOps.contain(im, (size[0] - 60, size[1] - 60))
            bg.paste(fg, ((size[0] - fg.width) // 2, (size[1] - fg.height) // 2))
            return bg
    card = g.gradient(size[0], size[1], hex_rgb(colors["accent"]), tuple(int(c * 0.7) for c in hex_rgb(colors["accent"])))
    d = ImageDraw.Draw(card)
    f, lines, s = g.fit_text(d, p["name"], size[0] - 140, size[1] - 200, start=110, min_size=60)
    y = (size[1] - len(lines) * s * 1.15) / 2
    g.draw_lines(d, lines, f, s, size[0] / 2, y, (20, 20, 20))
    return card


def make_pins(p, c, cfg, out_dir):
    colors = cfg["brand_colors"]
    bg, acc, txt = hex_rgb(colors["bg"]), hex_rgb(colors["accent"]), hex_rgb(colors["text"])
    host = cfg["site_url"].split("//")[-1]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    pins = c.get("pins") or [{"title": p["name"]}]
    for i in range(3):
        title = pins[i % len(pins)]["title"]
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        if i == 0:      # photo top, title panel bottom
            img.paste(_photo_or_card(p, colors, (W, 930)), (0, 0))
            d.rectangle([0, 930, W, H], fill=bg)
            f, lines, s = g.fit_text(d, title, W - 120, 380, start=78, min_size=44)
            g.draw_lines(d, lines, f, s, W / 2, 990, txt)
        elif i == 1:    # big headline top, photo below
            d.rectangle([0, 0, W, 520], fill=acc)
            f, lines, s = g.fit_text(d, title, W - 120, 400, start=86, min_size=46)
            g.draw_lines(d, lines, f, s, W / 2, 60 + (400 - len(lines) * s * 1.15) / 2, (20, 20, 20))
            img.paste(_photo_or_card(p, colors, (W, 860)), (0, 520))
        else:           # checklist of key points
            d.rectangle([0, 0, W, 300], fill=acc)
            f, lines, s = g.fit_text(d, title, W - 100, 230, start=70, min_size=40)
            g.draw_lines(d, lines, f, s, W / 2, 35 + (230 - len(lines) * s * 1.15) / 2, (20, 20, 20))
            pts = (p["points"] or [p["name"]])[:5]
            pf, lh = g.font(56, False), 70
            blocks = [g.wrap(d, pt, pf, W - 220) for pt in pts]
            total = sum(len(b) * lh for b in blocks) + 60 * (len(blocks) - 1)
            y = 300 + max(40, (H - 110 - 300 - total) // 2)
            for lines in blocks:
                d.ellipse([60, y + 10, 110, y + 60], fill=acc)
                d.text((70, y + 6), "✓", font=g.font(42), fill=(20, 20, 20))
                for ln in lines:
                    d.text((140, y), ln, font=pf, fill=txt)
                    y += lh
                y += 60
        # footer
        d.rectangle([0, H - 110, W, H], fill=(0, 0, 0))
        label = f"{host}"
        ff = g.fit_line(d, label, W - 80, start=34, bold=True)
        d.text(((W - d.textlength(label, font=ff)) / 2, H - 78), label, font=ff, fill=acc)
        path = out_dir / f"{p['id']}-{i + 1}.jpg"
        img.save(path, quality=88)
        paths.append(path)
    return paths
