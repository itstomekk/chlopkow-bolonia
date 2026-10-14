"""Iteration 8: size fix. The map is 2 px per metre; sprites were 7.5 px/m (3.6x real), old procedural houses ~2.4x.
Same GPT raws (no regeneration, no rotation), re-pixelated so the sprite width = OSM footprint width on the map x F.
Compares F = 3.6 (iteration 7), 2.6 and 2.2 for houses (farm buildings x 0.75 of that).

    python gen/pilot_2026-10-03-houses/process8.py   -> compare8.png
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
Y = ROOT / "gen/yards"
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A")); sys.path.insert(0, str(ROOT / "osm"))
from geo import P  # noqa: E402
from process import clean, pixelate  # noqa: E402
from process5 import render, stack, now  # noqa: E402

DEEP = {"28_road_raw.png": 1.15, "26_v2_raw.png": 1.12}   # Tomek's "thicker" for 28 / 26, kept


def items():
    out = [("27A", D / "27A_road_raw.png", 909988193, "house"), ("28", D / "28_road_raw.png", 909988191, "house"),
           ("27", D / "27_road_raw.png", 909988189, "house"), ("26", D / "26_v2_raw.png", 909988213, "house"),
           ("f28", D / "farm_behind28_raw.png", 909988763, "farm"), ("f28L", D / "yard28_L_raw.png", 909988358, "farm"),
           ("f27A", D / "farm_behind27A_v2_raw.png", 909989345, "farm"), ("f27", D / "farm_behind27_raw.png", 909988457, "farm")]
    for yard in ("yard26", "yard25", "yard24"):
        for j in json.loads((Y / yard / "jobs.json").read_text(encoding="utf-8")):
            raw = Y / yard / f"{j['name']}_raw.png"
            if raw.exists(): out.append((j["name"], raw, j["way"], j["kind"]))
    return out


def sprite(raw, way, kind, F, E):
    pts = [P(p["lat"], p["lon"]) for p in E[way]["geometry"][:-1]]
    w = round((max(p[0] for p in pts) - min(p[0] for p in pts)) * F * (1 if kind == "house" else 0.75))
    im = clean(raw); k = DEEP.get(raw.name, 1.0)
    return pixelate(im.resize((w, round(im.height * w / im.width * k)), Image.Resampling.LANCZOS), w)


def main():
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8")); E = {e["id"]: e for e in osm["elements"]}
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    box = (330, 3960, 1000, 4240); panels = [("teraz w grze", now(box))]
    for F in (3.6, 2.6, 2.2):
        its = [(n, w, sprite(r, w, k, F, E)) for n, r, w, k in items()]
        if F == 2.6:
            for n, _, s in its: s.save(D / f"s8_{n}.png")
        print(F, {n: s.size for n, _, s in its})
        panels.append((f"budynki x{F} rzeczywistej wielkosci" + (" (iteracja 7)" if F == 3.6 else ""), render(its, osm, objs, box)))
    stack(panels, D / "compare8.png")


if __name__ == "__main__":
    main()
