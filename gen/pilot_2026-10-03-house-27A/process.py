"""Process the 27A raw into game-grid pixel art and compare sizes in map context (2026-10-03).

    python gen/pilot_2026-10-03-house-27A/process.py
Outputs: house_<w>.png for each width, compare_sizes.png (game zoom x3), compare.html. Not wired into the game.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_magenta_background  # noqa: E402

WIDTHS = (53, 72, 82, 90)          # 53 = current in-game width of this house (map.json object), 90 = house_generic
COLORS = 28
CX, BASE = 371, 3975           # footprint centre x and south (base) y in world px
OLD_BOX = (340, 3905, 409, 3980)  # old procedural house in the object layer (map.json object + margin)
SHADOW = (58, 84, 40)          # render_map.py ground-shadow colour, offset (+5, +3)
ZOOM = 3


def clean(raw):
    arr = np.array(remove_magenta_background(Image.open(raw)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        arr[(lab > 0) & (sizes[lab] < max(60, sizes.max() * 0.01)), 3] = 0
    arr[arr[..., 3] == 0, :3] = 0
    im = Image.fromarray(arr)
    return im.crop(im.getbbox())


def pixelate(im, w):
    size = (w, round(im.height * w / im.width))
    small = im.resize(size, Image.Resampling.BOX)
    a = np.array(small.getchannel("A")) >= 128
    rgb = small.convert("RGB").quantize(colors=COLORS, dither=Image.Dither.NONE).convert("RGB")
    out = np.dstack([np.array(rgb), np.where(a, 255, 0).astype(np.uint8)]); out[~a, :3] = 0
    out = Image.fromarray(out)
    return out.crop(out.getbbox())


def arek():
    a = Image.open(ROOT / "docs/img/arek_sheet_8dir.png").convert("RGBA").crop((0, 0, 130, 170))
    a = a.crop(a.getbbox()); k = 40 / a.height
    return a.resize((max(1, round(a.width * k)), 40), Image.Resampling.NEAREST)


def scene(sprite):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    box = (CX - 100, BASE - 120, CX + 100, BASE + 40)
    sc = g.crop(box); obj = o.crop(box)
    if sprite is not None:
        ImageDraw.Draw(obj).rectangle([OLD_BOX[0] - box[0], OLD_BOX[1] - box[1], OLD_BOX[2] - box[0], OLD_BOX[3] - box[1]],
                                      fill=(0, 0, 0, 0))
        x0, y0 = CX - sprite.width // 2 - box[0], BASE - sprite.height - box[1]
        sh = Image.new("RGBA", sprite.size, SHADOW + (255,)); sh.putalpha(sprite.getchannel("A"))
        foot = sh.crop((0, sprite.height // 2, sprite.width, sprite.height))   # shadow only from the lower half
        sc.alpha_composite(foot, (x0 + 5, y0 + sprite.height // 2 + 3))
        sc.alpha_composite(obj)
        sc.alpha_composite(sprite, (x0, y0))
    else:
        sc.alpha_composite(obj)
    a = arek(); sc.alpha_composite(a, (CX + 60 - box[0], BASE + 30 - a.height - box[1]))
    return sc.resize((sc.width * ZOOM, sc.height * ZOOM), Image.Resampling.NEAREST)


def main():
    raw = clean(D / "house_raw.png")
    panels = [("teraz (proceduralny)", scene(None))]
    for w in WIDTHS:
        s = pixelate(raw, w); s.save(D / f"house_{w}.png")
        panels.append((f"{w} px" + (" = obecny rozmiar" if w == 53 else " = jak house_generic" if w == 90 else ""), scene(s)))
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw * 2 + 10, (ph + 30) * 2 + 10), (24, 24, 24)); d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        x, y = (i % 2) * (pw + 10), (i // 2) * (ph + 40)
        d.text((x + 6, y + 8), t + "   (Arek = 40 px, zoom x3)", fill=(255, 230, 80)); out.paste(p.convert("RGB"), (x, y + 30))
    out.save(D / "compare_sizes.png")
    big = pixelate(raw, 82); big.resize((big.width * 6, big.height * 6), Image.Resampling.NEAREST).save(D / "house_82_x6.png")
    print(json.dumps({w: Image.open(D / f"house_{w}.png").size for w in WIDTHS}))


if __name__ == "__main__":
    main()
