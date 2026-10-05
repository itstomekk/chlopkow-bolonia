"""Iteration 3 compare (2026-10-03): all four houses along the road at the road angle (variant B for everyone),
old procedural shadow removed, new shadow and collision derived automatically from the sprite pixels.

    python gen/pilot_2026-10-03-houses/process3.py
Outputs: <name>.png sprites, compare3.png (now / new / new + collision overlay), sprites3_x6.png.
Not wired into the game.

Automatic rules shown here (proposed for the real pipeline):
  shadow    = sprite silhouette, lower half only, offset (+5, +3), colour of the procedural ground shadow
  collision = sprite silhouette shifted DOWN by the wall height, clipped at the base line: the ground the house
              really stands on in this oblique view; the roof above it stays walk-behind (y-sorted)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A")); sys.path.insert(0, str(ROOT / "osm"))
from process import clean, pixelate, arek, SHADOW  # noqa: E402
from geo import P  # noqa: E402

PX_PER_M = 82 / 11.5
TILT_PAD = 86 / 82               # the road-angle sprite of 27A came out 86 px wide for an 82 px house
HOUSES = {  # name: (osm way, raw, sprite width px)
    "27A_road": (909988193, D / "27A_road_raw.png", 86),
    "28_road": (909988191, D / "28_road_raw.png", round(11.5 * PX_PER_M * TILT_PAD)),
    "27_road": (909988189, D / "27_road_raw.png", round(10.3 * PX_PER_M * TILT_PAD)),
    "26_road": (909988213, D / "26_road_raw.png", round(9.6 * PX_PER_M * TILT_PAD)),
}
WALL_FRAC = 0.38                 # wall band height as a share of sprite height (1-2 storey houses)
ZOOM = 3


def centroid(way, osm):
    g = next(e for e in osm["elements"] if e["id"] == way)["geometry"][:-1]
    return P(sum(p["lat"] for p in g) / len(g), sum(p["lon"] for p in g) / len(g))


def old_object(cx, cy, objs):
    hits = [o for o in objs if o.get("kind") != "tree" and o["x"] <= cx <= o["x"] + o["w"] and o["y"] <= cy <= o["base"] + 4]
    return min(hits, key=lambda o: o["w"] * o["h"])


def remove_old_shadow(ground, ob):
    """Inpaint the flat procedural shadow colour around the old house with the nearest real ground pixel."""
    g = np.array(ground)
    x0, y0, x1, y1 = ob["x"] - 4, ob["y"] - 4, ob["x"] + ob["w"] + 12, int(ob["base"]) + 12
    sub = g[y0:y1, x0:x1]
    mask = np.all(sub[..., :3] == SHADOW, axis=-1)
    if mask.any():
        _, (iy, ix) = ndimage.distance_transform_edt(mask, return_indices=True)
        sub[mask] = sub[iy[mask], ix[mask]]
    return Image.fromarray(g)


def collision(s):
    a = np.array(s.getchannel("A")) > 0
    wall = round(s.height * WALL_FRAC)
    foot = np.zeros_like(a); foot[wall:] = a[:-wall]          # silhouette pushed down by the wall height
    foot &= np.arange(a.shape[0])[:, None] < a.shape[0]       # clipped at the base line (sprite bottom)
    return foot


def build(sprites, osm, objs, box, show_coll):
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box)
    places = []
    for name, (way, _, _) in HOUSES.items():
        cx, cy = centroid(way, osm); ob = old_object(cx, cy, objs)
        g = remove_old_shadow(g, ob)
        ImageDraw.Draw(o).rectangle([ob["x"] - box[0], ob["y"] - box[1], ob["x"] + ob["w"] - box[0],
                                     int(ob["base"]) + 2 - box[1]], fill=(0, 0, 0, 0))
        s = sprites[name]; places.append((s, int(cx - s.width / 2) - box[0], int(ob["base"]) - s.height - box[1]))
    g = g.crop(box)
    for s, x0, y0 in places:
        sh = Image.new("RGBA", s.size, SHADOW + (255,)); sh.putalpha(s.getchannel("A"))
        g.alpha_composite(sh.crop((0, s.height // 2, s.width, s.height)), (x0 + 5, y0 + s.height // 2 + 3))
    g.alpha_composite(o)
    for s, x0, y0 in places:
        g.alpha_composite(s, (x0, y0))
        if show_coll:
            c = collision(s); ov = np.zeros((*c.shape, 4), np.uint8); ov[c] = (255, 0, 0, 120)
            g.alpha_composite(Image.fromarray(ov), (x0, y0 + 0))
    a = arek(); g.alpha_composite(a, (150, 175 - a.height))
    return g.resize((g.width * ZOOM, g.height * ZOOM), Image.Resampling.NEAREST)


def main():
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    m = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))
    sprites = {n: pixelate(clean(raw), w) for n, (_, raw, w) in HOUSES.items()}
    for n, s in sprites.items():
        s.save(D / f"{n}.png")
    xy = [centroid(w, osm) for w, _, _ in HOUSES.values()]
    box = (int(min(x for x, _ in xy)) - 70, int(min(y for _, y in xy)) - 95,
           int(max(x for x, _ in xy)) + 70, int(max(y for _, y in xy)) + 55)
    now = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(box)
    now.alpha_composite(Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(box))
    now = now.resize((now.width * ZOOM, now.height * ZOOM), Image.Resampling.NEAREST)
    panels = [("teraz w grze", now), ("nowe: wszystkie wzdluz drogi, stary cien usuniety", build(sprites, osm, m["objects"], box, False)),
              ("to samo + blokada liczona z pikseli (czerwone)", build(sprites, osm, m["objects"], box, True))]
    pw, ph = panels[0][1].size
    out = Image.new("RGB", (pw, (ph + 26) * 3), (24, 24, 24)); d = ImageDraw.Draw(out)
    for i, (t, p) in enumerate(panels):
        d.text((6, i * (ph + 26) + 7), t, fill=(255, 230, 80)); out.paste(p.convert("RGB"), (0, i * (ph + 26) + 26))
    out.save(D / "compare3.png")
    k = 6; row = Image.new("RGBA", (sum(s.width * k + 30 for s in sprites.values()), max(s.height for s in sprites.values()) * k), (40, 40, 40, 255))
    x = 0
    for s in sprites.values():
        row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (x, row.height - s.height * k)); x += s.width * k + 30
    row.save(D / "sprites3_x6.png")
    print({n: s.size for n, s in sprites.items()}, box)


if __name__ == "__main__":
    main()
