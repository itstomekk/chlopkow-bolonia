"""Iteration 4 compare: thicker 28/26 + farm buildings in the strip, satellite-only house 29 separately.

    python gen/pilot_2026-10-03-houses/process4.py
Outputs: <name>.png sprites (fitted to the rule size), compare4.png, compare4_29.png, sprites4_x6.png.
Not wired into the game.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))
import process3 as p3  # noqa: E402
from process import clean, pixelate  # noqa: E402
from generate4 import JOBS, size  # noqa: E402

ZOOM = 3


FARM_PXM = 5.0       # farm buildings are exaggerated less than houses (7.5 px/m), so plots do not overflow
MAX_STRETCH = 1.15   # never stretch GPT's own proportions by more than 15% (a forced 4:1 box made towers)


def target(job):
    length, depth, storeys, kind = job[2], job[3], job[4], job[5]
    if kind == "farm":
        # receding buildings: the visible width is the gable end plus the leaning roof (~60% of the length)
        return round(max(length, depth * 0.6) * FARM_PXM), None
    return size(length, depth, storeys)


def fitted(raw, job):
    im = clean(raw)
    w, h_rule = target(job)
    h_nat = im.height * w / im.width
    h = h_nat if h_rule is None else min(max(h_rule, h_nat / MAX_STRETCH), h_nat * MAX_STRETCH)
    return pixelate(im.resize((w, round(h)), Image.Resampling.LANCZOS), w)


def panel(houses, box, sprites, osm, objs, coll=False):
    p3.HOUSES = houses
    return p3.build(sprites, osm, objs, box, coll)


def now(box):
    im = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(box)
    im.alpha_composite(Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box))
    return im.resize((im.width * ZOOM, im.height * ZOOM), Image.Resampling.NEAREST)


def stack(panels, path):
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw, (ph + 26) * len(panels)), (24, 24, 24)); d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        d.text((6, i * (ph + 26) + 7), t, fill=(255, 230, 80)); out.paste(p.convert("RGB"), (0, i * (ph + 26) + 26))
    out.save(path)


def main():
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    sprites = {"27A_road": Image.open(D / "27A_road.png").convert("RGBA"),
               "27_road": Image.open(D / "27_road.png").convert("RGBA")}
    for n, j in JOBS.items():
        sprites[n] = fitted(D / f"{n}_raw.png", j); sprites[n].save(D / f"{n}.png")
    strip = {"27A_road": (909988193, None, 0), "28_v2": (909988191, None, 0), "27_road": (909988189, None, 0),
             "26_v2": (909988213, None, 0), "farm_behind28": (909988763, None, 0),
             "farm_behind27A": (909989345, None, 0), "farm_behind27": (909988457, None, 0)}
    old = {"27A_road": (909988193, None, 0), "28_road": (909988191, None, 0), "27_road": (909988189, None, 0),
           "26_road": (909988213, None, 0)}
    sprites["28_road"] = Image.open(D / "28_road.png").convert("RGBA"); sprites["26_road"] = Image.open(D / "26_road.png").convert("RGBA")
    box = (301, 3790, 777, 4175)
    stack([("teraz w grze", now(box)),
           ("iteracja 3 (28 i 26 za plaskie)", panel(old, box, sprites, osm, objs)),
           ("iteracja 4: 28 i 26 grubsze + 3 budynki gospodarcze", panel(strip, box, sprites, osm, objs)),
           ("iteracja 4 + blokada z pikseli", panel(strip, box, sprites, osm, objs, True))], D / "compare4.png")
    x, y = p3.centroid(909988194, osm); box29 = (int(x) - 110, int(y) - 110, int(x) + 110, int(y) + 60)
    stack([("Chlopkow 29 teraz", now(box29)),
           ("Chlopkow 29 tylko z satelity", panel({"29_sat": (909988194, None, 0)}, box29, sprites, osm, objs))],
          D / "compare4_29.png")
    names = ["28_v2", "26_v2", "farm_behind28", "farm_behind27A", "farm_behind27", "29_sat"]
    k = 5; row = Image.new("RGBA", (sum(sprites[n].width * k + 24 for n in names), max(sprites[n].height for n in names) * k), (40, 40, 40, 255))
    xx = 0
    for n in names:
        s = sprites[n]; row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (xx, row.height - s.height * k)); xx += s.width * k + 24
    row.save(D / "sprites4_x6.png")
    print({n: sprites[n].size for n in names})


if __name__ == "__main__":
    main()
