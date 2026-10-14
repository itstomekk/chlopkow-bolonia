"""Iteration 5 compare: 28 = iteration-3 drawing made 15% deeper, farm 27A at satellite angle, 29 conservative with
the satellite angle applied by shear, and an automatic placement solver so no building stands on another one.

    python gen/pilot_2026-10-03-houses/process5.py
Outputs: compare5.png, compare5_29.png, sprites5_x6.png, <name>.png. Not wired into the game.

Placement solver: each new sprite starts centred on its OSM footprint with its base on the old object's base.
Its ground collision (process3.collision) must not touch the ground of any other building (other new sprites and
old buildings not replaced yet: their lower 45%). If it does, try shifts up to +-16 px, then scale 0.9 / 0.8,
and keep the smallest change. The chosen move is printed so it can be reviewed.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))
import process3 as p3  # noqa: E402
from process import clean, pixelate, arek, SHADOW  # noqa: E402

ZOOM = 3


def deeper(raw, w, k=1.15):
    im = clean(raw); h = im.height * w / im.width * k
    return pixelate(im.resize((w, round(h)), Image.Resampling.LANCZOS), w)


def sheared(raw, w, deg):
    """Apply a real-world clockwise rotation of `deg` as a vertical shear (verticals stay vertical, east end lower)."""
    im = clean(raw); t = math.tan(math.radians(deg))
    out_h = im.height + int(im.width * t) + 2
    sh = im.transform((im.width, out_h), Image.Transform.AFFINE, (1, 0, 0, -t, 1, 0), Image.Resampling.BICUBIC)
    sh = sh.crop(sh.getbbox())
    return pixelate(sh.resize((w, round(sh.height * w / sh.width)), Image.Resampling.LANCZOS), w)


def ground_rects(objs, replaced):
    m = []
    for o in objs:
        if o.get("kind") == "tree" or id(o) in replaced: continue
        m.append((o["x"], int(o["base"] - o["h"] * 0.45), o["x"] + o["w"], int(o["base"])))
    return m


def solve(name, s, cx, base, blockers, taken):
    best = None
    for scale in (1.0, 0.9, 0.8):
        sp = s if scale == 1 else pixelate(s, max(8, round(s.width * scale)))
        c = p3.collision(sp)
        ys, xs = np.nonzero(c)
        for dy in range(-8, 13, 2):
            for dx in range(-16, 17, 2):
                x0 = int(cx - sp.width / 2) + dx; y0 = int(base) - sp.height + dy
                gx, gy = xs + x0, ys + y0
                hit = sum(((gx >= a) & (gx < b) & (gy >= t) & (gy < u)).sum() for a, t, b, u in blockers)
                hit += sum(len(set(zip(gx.tolist(), gy.tolist())) & tk) for tk in taken)
                cost = hit * 1000 + abs(dx) + abs(dy) + (1 - scale) * 60
                if best is None or cost < best[0]:
                    best = (cost, sp, x0, y0, dx, dy, scale, hit)
    _, sp, x0, y0, dx, dy, scale, hit = best
    print(f"{name:20s} shift ({dx:+d},{dy:+d}) scale {scale} overlap {hit}")
    c = p3.collision(sp); ys, xs = np.nonzero(c)
    return sp, x0, y0, set(zip((xs + x0).tolist(), (ys + y0).tolist()))


def render(items, osm, objs, box, coll=False):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box)
    replaced, starts = set(), []
    for name, way, s in items:
        cx, cy = p3.centroid(way, osm); ob = p3.old_object(cx, cy, objs)
        replaced.add(id(ob)); g = p3.remove_old_shadow(g, ob)
        ImageDraw.Draw(o).rectangle([ob["x"] - box[0], ob["y"] - box[1], ob["x"] + ob["w"] - box[0],
                                     int(ob["base"]) + 2 - box[1]], fill=(0, 0, 0, 0))
        starts.append((name, s, cx, ob["base"]))
    blockers = ground_rects(objs, replaced); taken, placed = [], []
    for name, s, cx, base in sorted(starts, key=lambda t: -t[1].width * t[1].height):   # big ones first
        sp, x0, y0, tk = solve(name, s, cx, base, blockers, taken); taken.append(tk); placed.append((sp, x0, y0))
    g = g.crop(box)
    for sp, x0, y0 in placed:
        sh = Image.new("RGBA", sp.size, SHADOW + (255,)); sh.putalpha(sp.getchannel("A"))
        g.alpha_composite(sh.crop((0, sp.height // 2, sp.width, sp.height)), (x0 - box[0] + 5, y0 - box[1] + sp.height // 2 + 3))
    g.alpha_composite(o)
    for sp, x0, y0 in sorted(placed, key=lambda t: t[2] + t[0].height):           # y-sort by base
        g.alpha_composite(sp, (x0 - box[0], y0 - box[1]))
        if coll:
            c = p3.collision(sp); ov = np.zeros((*c.shape, 4), np.uint8); ov[c] = (255, 0, 0, 120)
            g.alpha_composite(Image.fromarray(ov), (x0 - box[0], y0 - box[1]))
    a = arek(); g.alpha_composite(a, (150, 175 - a.height))
    return g.resize((g.width * ZOOM, g.height * ZOOM), Image.Resampling.NEAREST)


def stack(panels, path):
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw, (ph + 26) * len(panels)), (24, 24, 24)); d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        d.text((6, i * (ph + 26) + 7), t, fill=(255, 230, 80)); out.paste(p.convert("RGB"), (0, i * (ph + 26) + 26))
    out.save(path)


def now(box):
    im = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(box)
    im.alpha_composite(Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box))
    return im.resize((im.width * ZOOM, im.height * ZOOM), Image.Resampling.NEAREST)


def main():
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    L = lambda n: Image.open(D / f"{n}.png").convert("RGBA")  # noqa: E731
    S = {"27A_road": L("27A_road"), "27_road": L("27_road"), "26_v2": L("26_v2"),
         "28_v3": deeper(D / "28_road_raw.png", 86),
         "farm_behind28": L("farm_behind28"), "farm_behind27": L("farm_behind27"),
         "farm_behind27A_v2": sheared(D / "farm_behind27A_front_raw.png", 58, 27),
         "29_sat_v2": sheared(D / "29_sat_v2_raw.png", 89, 11)}
    for n in ("28_v3", "farm_behind27A_v2", "29_sat_v2"):
        S[n].save(D / f"{n}.png")
    items = [("27A_road", 909988193, S["27A_road"]), ("28_v3", 909988191, S["28_v3"]),
             ("27_road", 909988189, S["27_road"]), ("26_v2", 909988213, S["26_v2"]),
             ("farm_behind28", 909988763, S["farm_behind28"]), ("farm_behind27A_v2", 909989345, S["farm_behind27A_v2"]),
             ("farm_behind27", 909988457, S["farm_behind27"])]
    box = (301, 3790, 777, 4175)
    stack([("teraz w grze", now(box)), ("iteracja 5 (solver: nic nie stoi na innym budynku)", render(items, osm, objs, box)),
           ("iteracja 5 + blokada", render(items, osm, objs, box, True))], D / "compare5.png")
    x, y = p3.centroid(909988194, osm); b29 = (int(x) - 110, int(y) - 110, int(x) + 110, int(y) + 60)
    stack([("Chlopkow 29 teraz", now(b29)),
           ("29: tylko to, co widac z satelity; kat 11 st. z satelity", render([("29_sat_v2", 909988194, S["29_sat_v2"])], osm, objs, b29))],
          D / "compare5_29.png")
    names = ["28_road", "28_v3", "farm_behind27A_v2", "29_sat_v2"]
    S["28_road"] = L("28_road")
    k = 5; row = Image.new("RGBA", (sum(S[n].width * k + 24 for n in names), max(S[n].height for n in names) * k), (40, 40, 40, 255))
    xx = 0
    for n in names:
        s = S[n]; row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (xx, row.height - s.height * k)); xx += s.width * k + 24
    row.save(D / "sprites5_x6.png")


if __name__ == "__main__":
    main()
