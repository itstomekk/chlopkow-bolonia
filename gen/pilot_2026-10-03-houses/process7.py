"""Compare yards 28-24 (iteration 7): GPT angles as drawn, no rotation/shear (rule 20).

    python gen/pilot_2026-10-03-houses/process7.py   -> compare7.png, sprites7_x4.png
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
Y = ROOT / "gen/yards"
sys.path.insert(0, str(D)); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))
from process5 import render, stack, now  # noqa: E402


def main():
    subprocess_free = None  # noqa: F841
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    L = lambda p: Image.open(p).convert("RGBA")  # noqa: E731
    items = [("28_v3", 909988191, L(D / "28_v3.png")), ("farm_behind28", 909988763, L(D / "farm_behind28.png")),
             ("yard28_L", 909988358, L(D / "yard28_L.png")), ("26_v2", 909988213, L(D / "26_v2.png")),
             ("27_road", 909988189, L(D / "27_road.png")), ("farm_behind27", 909988457, L(D / "farm_behind27.png"))]
    for yard in ("yard26", "yard25", "yard24"):
        for j in json.loads((Y / yard / "jobs.json").read_text(encoding="utf-8")):
            p = Y / yard / f"{j['name']}.png"
            if p.exists(): items.append((j["name"], j["way"], L(p)))
    box = (560, 3960, 1000, 4240)
    stack([("teraz w grze", now(box)), ("podworka 27, 26, 25, 24 (katy jak narysowal GPT, bez obracania)",
                                        render(items, osm, objs, box)),
           ("to samo + blokada", render(items, osm, objs, box, True))], D / "compare7.png")
    new = [i for i in items if i[0].startswith(("house_", "farm1_", "farm2_", "farm3_"))]
    k = 4; row = Image.new("RGBA", (sum(s.width * k + 20 for _, _, s in new), max(s.height for _, _, s in new) * k), (40, 40, 40, 255))
    x = 0
    for _, _, s in new:
        row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (x, row.height - s.height * k)); x += s.width * k + 20
    row.save(D / "sprites7_x4.png")
    print([n for n, _, _ in new])


if __name__ == "__main__":
    main()
