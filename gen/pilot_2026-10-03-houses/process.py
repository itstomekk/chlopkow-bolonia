"""Iteration 2 compare: put the new house sprites into the real map strip around Chłopków 27A, 27, 26.

    python gen/pilot_2026-10-03-houses/process.py
Outputs: <name>.png sprites, compare_strip.png (old map / variant A: 27A front-on / variant B: 27A along the road),
sprites_x6.png. Not wired into the game.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A")); sys.path.insert(0, str(ROOT / "osm"))
from process import clean, pixelate, arek, SHADOW  # noqa: E402
from geo import P  # noqa: E402

PX_PER_M = 82 / 11.5            # Tomek picked 82 px for 27A (11.5 m long wall)
HOUSES = {  # name: (osm way, raw file, sprite width px)
    "27A": (909988193, ROOT / "gen/pilot_2026-10-03-house-27A/house_raw.png", 82),
    "27A_road": (909988193, D / "27A_road_raw.png", 86),
    "27": (909988189, D / "27_raw.png", round(10.3 * PX_PER_M)),
    "26": (909988213, D / "26_raw.png", round(9.6 * PX_PER_M)),
}
ZOOM = 3


def centroid(way):
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    g = next(e for e in osm["elements"] if e["id"] == way)["geometry"][:-1]
    return P(sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g))


def old_object(cx, cy, objs):
    hits = [o for o in objs if o.get("kind") != "tree" and o["x"] <= cx <= o["x"] + o["w"] and o["y"] <= cy <= o["base"] + 4]
    return min(hits, key=lambda o: o["w"] * o["h"])


def strip(variant, sprites, objs, box):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(box)
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box)
    placed = []
    if variant:
        for name in variant:
            way = HOUSES[name][0]; cx, cy = centroid(way); ob = old_object(cx, cy, objs)
            ImageDraw.Draw(o).rectangle([ob["x"] - box[0], ob["y"] - box[1], ob["x"] + ob["w"] - box[0],
                                         int(ob["base"]) + 2 - box[1]], fill=(0, 0, 0, 0))
            s = sprites[name]; x0 = int(cx - s.width / 2) - box[0]; y0 = int(ob["base"]) - s.height - box[1]
            sh = Image.new("RGBA", s.size, SHADOW + (255,)); sh.putalpha(s.getchannel("A"))
            g.alpha_composite(sh.crop((0, s.height // 2, s.width, s.height)), (x0 + 5, y0 + s.height // 2 + 3))
            placed.append((s, x0, y0))
    g.alpha_composite(o)
    for s, x0, y0 in placed:
        g.alpha_composite(s, (x0, y0))
    a = arek(); g.alpha_composite(a, (150, 175 - a.height))
    return g.resize((g.width * ZOOM, g.height * ZOOM), Image.Resampling.NEAREST)


def main():
    m = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))
    sprites = {}
    for name, (_, raw, w) in HOUSES.items():
        sprites[name] = pixelate(clean(raw), w); sprites[name].save(D / f"{name}.png")
    xs = [centroid(HOUSES[n][0]) for n in ("27A", "27", "26")]
    box = (int(min(x for x, _ in xs)) - 70, int(min(y for _, y in xs)) - 90,
           int(max(x for x, _ in xs)) + 70, int(max(y for _, y in xs)) + 60)
    panels = [("teraz w grze", strip(None, sprites, m["objects"], box)),
              ("A: 27A frontem (prawdziwy kat), 27, 26", strip(("27A", "27", "26"), sprites, m["objects"], box)),
              ("B: 27A rownolegle do drogi, 27, 26", strip(("27A_road", "27", "26"), sprites, m["objects"], box))]
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw, (ph + 26) * 3), (24, 24, 24)); d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        d.text((6, i * (ph + 26) + 7), t, fill=(255, 230, 80)); out.paste(p.convert("RGB"), (0, i * (ph + 26) + 26))
    out.save(D / "compare_strip.png")
    k = 6; row = Image.new("RGBA", (sum(s.width * k + 30 for s in sprites.values()), max(s.height for s in sprites.values()) * k), (40, 40, 40, 255))
    x = 0
    for s in sprites.values():
        row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (x, row.height - s.height * k)); x += s.width * k + 30
    row.save(D / "sprites_x6.png")
    print({n: s.size for n, s in sprites.items()}, "box", box)


if __name__ == "__main__":
    main()
