"""Pixelate the świetlica annex variants exactly like the approved pilot (43 px wide, 24 colours, hard alpha).

    python gen/pilot_2026-10-03-swietlica/process_annex.py
Writes annex_<v>.png and annex_review.png (old vs variants, x4, plus map context at x3).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen"))
from generate import clean, pixelate, W_WORLD  # noqa: E402

X0, Y0 = 2281, 4583   # top-left of the approved sprite on the map; the north end stays, the annex grows south


def build(v):
    im = clean(D / f"annex_{v}_raw.png")
    im = im.crop(im.getbbox())
    out = pixelate(im, (W_WORLD, round(im.height * W_WORLD / im.width)))
    out = out.crop(out.getbbox())
    out.save(D / f"annex_{v}.png")
    return out


def context(sprite):
    Image.MAX_IMAGE_PIXELS = None
    box = (2180, 4520, 2400, 4730)
    sc = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(box)
    obj = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box)
    sc.alpha_composite(obj)
    if sprite is not None:
        old = Image.open(ROOT / "gen/lm_swietlica.png").convert("RGBA")
        # erase the currently baked old hall by repainting it from a clean neighbour column is not possible here,
        # so the preview just draws the variant on top (the old one is fully covered: same x, same top, longer).
        sc.alpha_composite(sprite, (X0 - box[0] + (old.width - sprite.width) // 2, Y0 - box[1]))
    return sc.resize((sc.width * 3, sc.height * 3), Image.Resampling.NEAREST)


def main():
    vs = [v for v in ("v1", "v2") if (D / f"annex_{v}_raw.png").exists()]
    sprites = {"old": Image.open(ROOT / "gen/lm_swietlica.png").convert("RGBA")}
    for v in vs:
        sprites[v] = build(v); print(v, sprites[v].size)
    z = 4; pad = 20
    w = sum(s.width * z + pad for s in sprites.values()) + pad; h = max(s.height for s in sprites.values()) * z + 40
    sheet = Image.new("RGB", (w, h), (226, 224, 214)); d = ImageDraw.Draw(sheet); x = pad
    for k, s in sprites.items():
        d.text((x, 6), f"{k} {s.width}x{s.height}", fill=(0, 0, 0))
        sheet.paste(s.resize((s.width * z, s.height * z), Image.Resampling.NEAREST), (x, 30), s.resize((s.width * z, s.height * z), Image.Resampling.NEAREST))
        x += s.width * z + pad
    sheet.save(D / "annex_review.png")
    ctx = [context(sprites[v]) for v in vs]
    cw, ch = ctx[0].size
    out = Image.new("RGB", (cw * len(ctx) + 12 * (len(ctx) - 1), ch + 26), (20, 20, 20)); d = ImageDraw.Draw(out)
    for i, (v, c) in enumerate(zip(vs, ctx)):
        out.paste(c.convert("RGB"), (i * (cw + 12), 26)); d.text((i * (cw + 12) + 6, 6), v, fill=(255, 230, 80))
    out.save(D / "annex_on_map.png")
    print("wrote", D / "annex_review.png", D / "annex_on_map.png")


if __name__ == "__main__":
    main()
