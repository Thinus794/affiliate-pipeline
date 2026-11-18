"""Pillow helpers for slides (video) and Pinterest pins."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .util import FONT_BOLD, FONT_REG, hex_rgb


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    except Exception:
        return ImageFont.load_default()


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, max_w, max_h, start=96, min_size=36, bold=True, spacing=1.15):
    size = start
    while size >= min_size:
        f = font(size, bold)
        lines = wrap(draw, text, f, max_w)
        if len(lines) * size * spacing <= max_h and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines, size
        size -= 4
    f = font(min_size, bold)
    return f, wrap(draw, text, f, max_w), min_size


def draw_lines(draw, lines, f, size, x_center, y, fill, spacing=1.15, stroke=0, stroke_fill=None):
    for ln in lines:
        w = draw.textlength(ln, font=f)
        draw.text((x_center - w / 2, y), ln, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        y += int(size * spacing)
    return y


def fit_line(draw, text, max_w, start=40, min_size=18, bold=False):
    size = start
    while size > min_size and draw.textlength(text, font=font(size, bold)) > max_w:
        size -= 2
    return font(size, bold)


def gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c)
    return img


def open_image(path):
    try:
        im = Image.open(path)
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im)
            im = bg
        return im.convert("RGB")
    except Exception as e:
        print(f"[graphics] cannot open {path}: {e}")
        return None


def photo_slide(img, W=1080, H=1920):
    """Product photo centred on a blurred, darkened copy of itself."""
    bg = ImageOps.fit(img, (W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    fg = ImageOps.contain(img, (W - 80, 1150))
    card = Image.new("RGB", (fg.width + 24, fg.height + 24), (255, 255, 255))
    card.paste(fg, (12, 12))
    shadow = Image.new("RGBA", (card.width + 60, card.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([30, 40, card.width + 30, card.height + 40], 30, fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    x, y = (W - card.width) // 2, 330 + (1150 - card.height) // 2
    bg = bg.convert("RGBA")
    bg.alpha_composite(shadow, (x - 30, y - 30))
    bg.paste(card, (x, y))
    return bg.convert("RGB")


def text_slide(kicker, text, colors, idx=0, W=1080, H=1920):
    """Bold text card used when there are no product photos (or for key points)."""
    bgc = hex_rgb(colors["bg"])
    acc = hex_rgb(colors["accent"])
    img = gradient(W, H, tuple(min(255, c + 18) for c in bgc), bgc)
    d = ImageDraw.Draw(img)
    # decorative accent shapes
    d.ellipse([W - 420, -260, W + 260, 420], outline=acc, width=10)
    d.rectangle([90, 640, 110, 1260], fill=acc)
    kf = font(48, True)
    d.text((150, 640), kicker.upper(), font=kf, fill=acc)
    f, lines, size = fit_text(d, text, W - 260, 520, start=104, min_size=54)
    draw_lines_left(d, lines, f, size, 150, 730, hex_rgb(colors["text"]))
    return img


def draw_lines_left(draw, lines, f, size, x, y, fill, spacing=1.15):
    for ln in lines:
        draw.text((x, y), ln, font=f, fill=fill)
        y += int(size * spacing)
    return y


def cta_slide(name, price, site_host, colors, W=1080, H=1920):
    acc = hex_rgb(colors["accent"])
    img = gradient(W, H, hex_rgb(colors["bg"]), (0, 0, 0))
    d = ImageDraw.Draw(img)
    f, lines, size = fit_text(d, name, W - 160, 330, start=92, min_size=50)
    y = draw_lines(d, lines, f, size, W / 2, 420, hex_rgb(colors["text"]))
    if price:
        pf = font(54, True)
        pw = d.textlength(price, font=pf)
        d.rounded_rectangle([W / 2 - pw / 2 - 40, y + 40, W / 2 + pw / 2 + 40, y + 140], 50, fill=acc)
        d.text((W / 2 - pw / 2, y + 56), price, font=pf, fill=(20, 20, 20))
        y += 180
    bf = font(88, True)
    msg = "LINK IN BIO"
    bw = d.textlength(msg, font=bf)
    top = max(y + 50, 980)
    d.rounded_rectangle([W / 2 - bw / 2 - 60, top, W / 2 + bw / 2 + 60, top + 160], 30, outline=acc, width=8)
    d.text((W / 2 - bw / 2, top + 30), msg, font=bf, fill=acc)
    sf = fit_line(d, site_host, W - 120, start=40)
    sw = d.textlength(site_host, font=sf)
    d.text((W / 2 - sw / 2, top + 200), site_host, font=sf, fill=hex_rgb(colors["muted"]))
    return img
