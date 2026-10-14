"""Chlopkow 3 versions: pixelate each raw + composite on the game map (2026-10-03).

    python gen/pilot_2026-10-03-house-opposite-swietlica/process_versions.py
Outputs: <name>.png (game-grid sprite), versions_on_map.png (each on the map),
versions_raw.png (the GPT raws for reference).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_magenta_background  # noqa: E402

NAMES = ["photo", "cheerful", "plain", "warm"]
W = 58                # selected warm version, ~10% smaller than 65 px; repixelate from same raw
COLORS = 28
CX, BASE = 2220, 4665  # shifted 55 map px south so the house sits below the road
SHADOW = (58, 84, 40)
ZOOM = 3
BOX = (CX - 110, BASE - 110, CX + 110, BASE + 50)


def clean(raw):
    arr = np.array(remove_magenta_background(Image.open(raw)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        arr[(lab > 0) & (sizes[lab] < max(60, sizes.max() * 0.01)), 3] = 0
    arr[arr[..., 3] == 0, :3] = 0
    return Image.fromarray(arr).crop(Image.fromarray(arr).getbbox())


def pixelate(im, w):
    small = im.resize((w, round(im.height * w / im.width)), Image.Resampling.BOX)
    a = np.array(small.getchannel("A")) >= 128
    rgb = small.convert("RGB").quantize(colors=COLORS, dither=Image.Dither.NONE).convert("RGB")
    out = np.dstack([np.array(rgb), np.where(a, 255, 0).astype(np.uint8)]); out[~a, :3] = 0
    return Image.fromarray(out).crop(Image.fromarray(out).getbbox())


def arek():
    a = Image.open(ROOT / "docs/img/arek_sheet_8dir.png").convert("RGBA").crop((0, 0, 130, 170))
    a = a.crop(a.getbbox()); k = 40 / a.height
    return a.resize((max(1, round(a.width * k)), 40), Image.Resampling.NEAREST)


def scene(sprite):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    sc = g.crop(BOX); obj = o.crop(BOX)
    if sprite is not None:
        x0 = CX - sprite.width // 2 - BOX[0]
        y0 = BASE - sprite.height - BOX[1]
        sh = Image.new("RGBA", sprite.size, SHADOW + (255,)); sh.putalpha(sprite.getchannel("A"))
        foot = sh.crop((0, sprite.height // 2, sprite.width, sprite.height))
        sc.alpha_composite(foot, (x0 + 5, y0 + sprite.height // 2 + 3))
        sc.alpha_composite(obj)
        sc.alpha_composite(sprite, (x0, y0))
    else:
        sc.alpha_composite(obj)
    a = arek(); sc.alpha_composite(a, (CX + 70 - BOX[0], BASE + 40 - a.height - BOX[1]))
    return sc.resize((sc.width * ZOOM, sc.height * ZOOM), Image.Resampling.NEAREST)


def main():
    sprites = {}
    for name in NAMES:
        raw = clean(D / f"{name}_raw.png")
        sp = pixelate(raw, W)
        sp.save(D / f"{name}.png")
        sprites[name] = sp
        print(name, sp.size)

    panels = [("teraz (proceduralny)", scene(None))]
    for name in NAMES:
        panels.append((name, scene(sprites[name])))
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw * 3 + 20, (ph + 26) * 2 + 10), (24, 24, 24))
    d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        x, y = (i % 3) * (pw + 8), (i // 3) * (ph + 40)
        d.text((x + 4, y + 6), t + "   (Arek = 40 px, zoom x3)", fill=(255, 230, 80))
        out.paste(p.convert("RGB"), (x, y + 24))
    out.save(D / "versions_on_map.png")

    # raw thumbnails row
    raws = [Image.open(D / f"{n}_raw.png").convert("RGB") for n in NAMES]
    th = max(90, min(200, raws[0].width // 6))
    row = Image.new("RGB", (len(raws) * th + 20, th + 20), (24, 24, 24))
    for i, r in enumerate(raws):
        r = r.resize((th, th))
        row.paste(r, (10 + i * (th + 4), 10))
    row.save(D / "versions_raw.png")
    print("wrote", D / "versions_on_map.png", D / "versions_raw.png")


if __name__ == "__main__":
    main()
