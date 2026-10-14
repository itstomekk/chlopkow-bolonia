"""Iteration 6 compare: yard 28 complete, farm 27A drawn rotated by GPT (no shear), 29 in natural projection,
and comparison for question 1: houses as GPT drew them vs. corrected to the exact road angle (23 deg) with a small
residual shear on top of GPT's own rotation.

    python gen/pilot_2026-10-03-houses/process6.py
Outputs: compare6.png, compare6_29.png, sprites6_x6.png. Not wired into the game.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))
import process3 as p3  # noqa: E402
from process import clean, pixelate  # noqa: E402
from process5 import render, stack, now  # noqa: E402

ROAD_DEG = 23   # road at 113 deg bearing -> 23 deg clockwise from east-west


def bottom_slope(im):
    a = np.array(im.getchannel("A")) > 0; W = a.shape[1]; xs = np.arange(int(W * .15), int(W * .85))
    bot = np.array([a.shape[0] - 1 - np.argmax(a[::-1, x]) for x in xs])
    return math.degrees(math.atan(np.polyfit(xs, bot, 1)[0]))


def to_angle(raw, w, target, k=1.0):
    im = clean(raw)
    if k != 1.0:
        im = im.resize((im.width, round(im.height * k)), Image.Resampling.LANCZOS)
    t = math.tan(math.radians(target)) - math.tan(math.radians(bottom_slope(im)))
    out_h = im.height + int(abs(t) * im.width) + 2
    sh = im.transform((im.width, out_h), Image.Transform.AFFINE, (1, 0, 0, -t, 1, 0 if t >= 0 else -t * im.width),
                      Image.Resampling.BICUBIC)
    sh = sh.crop(sh.getbbox())
    return pixelate(sh.resize((w, round(sh.height * w / sh.width)), Image.Resampling.LANCZOS), w)


def main():
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    L = lambda n: Image.open(D / f"{n}.png").convert("RGBA")  # noqa: E731
    S = {"27A_road": L("27A_road"), "28_v3": L("28_v3"), "27_road": L("27_road"), "26_v2": L("26_v2"),
         "farm_behind28": L("farm_behind28"), "farm_behind27": L("farm_behind27"),
         "farm_behind27A_gpt": pixelate(clean(D / "farm_behind27A_v2_raw.png"), 58),
         "yard28_L": pixelate(clean(D / "yard28_L_raw.png"), 64),
         "29_v3": pixelate(clean(D / "29_v3_raw.png"), 89)}
    # question 1: same drawings, corrected to exactly the road angle
    S["27A_23"] = to_angle(D / "27A_road_raw.png", 86, ROAD_DEG)
    S["28_23"] = to_angle(D / "28_road_raw.png", 86, ROAD_DEG, 1.15)
    S["27_23"] = to_angle(D / "27_road_raw.png", 77, ROAD_DEG)
    S["26_23"] = to_angle(D / "26_v2_raw.png", 72, ROAD_DEG, 1.12)
    for n in ("farm_behind27A_gpt", "yard28_L", "29_v3", "27A_23", "28_23", "27_23", "26_23"):
        S[n].save(D / f"{n}.png")
    print({n: (S[n].size, round(bottom_slope(S[n]), 1)) for n in S})
    yard = [("farm_behind28", 909988763), ("yard28_L", 909988358), ("farm_behind27A_gpt", 909989345),
            ("farm_behind27", 909988457)]
    A = [("27A_road", 909988193), ("28_v3", 909988191), ("27_road", 909988189), ("26_v2", 909988213)] + yard
    B = [("27A_23", 909988193), ("28_23", 909988191), ("27_23", 909988189), ("26_23", 909988213)] + yard
    box = (301, 3790, 777, 4175)
    stack([("teraz w grze", now(box)),
           ("A: katy domow jak narysowal GPT (8-18 st.); podworko 28 kompletne", render([(n, w, S[n]) for n, w in A], osm, objs, box)),
           ("B: te same rysunki, domy wyrownane do kata drogi 23 st.", render([(n, w, S[n]) for n, w in B], osm, objs, box))],
          D / "compare6.png")
    x, y = p3.centroid(909988194, osm); b29 = (int(x) - 110, int(y) - 110, int(x) + 110, int(y) + 60)
    stack([("Chlopkow 29 teraz", now(b29)), ("29: rzut jak inne domy, lekki obrot, tylko to co z satelity",
                                             render([("29_v3", 909988194, S["29_v3"])], osm, objs, b29))], D / "compare6_29.png")
    names = ["27A_road", "27A_23", "28_v3", "28_23", "27_road", "27_23", "26_v2", "26_23", "yard28_L", "farm_behind27A_gpt", "29_v3"]
    k = 4; row = Image.new("RGBA", (sum(S[n].width * k + 20 for n in names), max(S[n].height for n in names) * k), (40, 40, 40, 255))
    xx = 0
    for n in names:
        s = S[n]; row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (xx, row.height - s.height * k)); xx += s.width * k + 20
    row.save(D / "sprites6_x6.png")


if __name__ == "__main__":
    main()
