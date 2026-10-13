"""Place the swietlica sprite on the game map as a preview (not wired in).

    python gen/pilot_2026-10-03-swietlica/place_on_map.py
Outputs: place_compare.png (now vs with sprite, game zoom x3, Arek for scale).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gen"))

CX, BASE = 2302, 4619   # swietlica POI (items.json) - sprite bottom-centre anchors here
SCALE = 1.0            # sprite is already natively re-pixelated to size; do NOT fractional-scale
Y_DROP = 0.5           # Tomek 2026-10-03: 0.7 then moved 0.2 of height back up = 0.5 of length
SHADOW = (58, 84, 40)
ZOOM = 3
BOX = (CX - 150, BASE - 160, CX + 150, BASE + 90)


def arek():
    a = Image.open(ROOT / "docs/img/arek_sheet_8dir.png").convert("RGBA").crop((0, 0, 130, 170))
    a = a.crop(a.getbbox()); k = 40 / a.height
    return a.resize((max(1, round(a.width * k)), 40), Image.Resampling.NEAREST)


def scene(sprite):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    sc = g.crop(BOX); obj = o.crop(BOX)
    if sprite is not None:
        base = BASE + round(Y_DROP * sprite.height)
        x0, y0 = CX - sprite.width // 2 - BOX[0], base - sprite.height - BOX[1]
        sh = Image.new("RGBA", sprite.size, SHADOW + (255,)); sh.putalpha(sprite.getchannel("A"))
        foot = sh.crop((0, sprite.height // 2, sprite.width, sprite.height))
        sc.alpha_composite(foot, (x0 + 6, y0 + sprite.height // 2 + 4))
        sc.alpha_composite(obj)
        sc.alpha_composite(sprite, (x0, y0))
    else:
        sc.alpha_composite(obj)
    a = arek(); sc.alpha_composite(a, (CX + 70 - BOX[0], BASE + 34 - a.height - BOX[1]))
    return sc.resize((sc.width * ZOOM, sc.height * ZOOM), Image.Resampling.NEAREST)


def main():
    sprite = Image.open(D / "swietlica.png").convert("RGBA")
    sprite = sprite.resize((round(sprite.width * SCALE), round(sprite.height * SCALE)),
                           Image.Resampling.NEAREST)
    now = scene(None)
    with_sprite = scene(sprite)
    w, h = now.size
    out = Image.new("RGB", (w * 2 + 12, h + 34), (24, 24, 24))
    d = ImageDraw.Draw(out)
    d.text((6, 8), "teraz (tylko punkt POI)", fill=(255, 230, 80))
    d.text((w + 12 + 6, 8), f"ze sprite {sprite.size[0]}x{sprite.size[1]} px (native, drop 0.5)", fill=(255, 230, 80))
    out.paste(now.convert("RGB"), (0, 30)); out.paste(with_sprite.convert("RGB"), (w + 12, 30))
    out.save(D / "place_compare.png")
    print("wrote", D / "place_compare.png", out.size, "sprite", sprite.size)


if __name__ == "__main__":
    main()
