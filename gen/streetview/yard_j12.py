"""Yards in map sector J12 (Tomek 2026-10-04: "zrób podwórko w J12 z satellite view"). Reuses the iteration-9
pipeline of yard_strip.py (asset-style-guide rule 25) with J12 settings; houses here have no accepted drawings, so
they are drawn from the satellite too (rule 21: plain walls, nothing invented).

    python gen/streetview/yard_j12.py shift       # global OSM -> satellite offset for this box
    python gen/streetview/yard_j12.py plan        # gen/yards/j12/plan.json + plan.png
    python gen/streetview/yard_j12.py houses      # Codex: one satellite-only drawing per house (skips existing raws)
    python gen/streetview/yard_j12.py gen [yard]  # Codex: all outbuildings of a yard in one image
    python gen/streetview/yard_j12.py cut         # split yard images into buildings
    python gen/streetview/yard_j12.py render      # sprites + placement -> gen/yards/final (+ compare9.png here)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
import yard_strip as ys  # noqa: E402

ROOT = ys.ROOT
OUT = ROOT / "gen/yards/j12"
ys.OUT = OUT
ys.HOUSES_DIR = OUT                       # compare9.png / pos_check9c.png / sprites9_x4.png land here
ys.BOX = (4608, 5560, 5143, 6180)         # sector J12 (x 4608-5120, y 5632-6144) + the yards' overhang
ys.ROAD = 236865227                       # unpaved village road east of both yards
ys.SHIFT = tuple(json.loads((OUT / "shift.json").read_text())) if (OUT / "shift.json").exists() else (0, 0)
STYLE_ANCHOR = ROOT / "gen/yards/strip/anchor_27A.png"   # accepted house: camera / pixel size / shading
# houses of J12 (way id -> yard). 993157804 (Chlopkow 14) lies in J11 and is left as it is.
HOUSE_IDS = {993157803: "15", 993157801: "18"}
ys.HOUSES = {h: (y, OUT / f"house_{h}_raw.png", 1.0) for h, y in HOUSE_IDS.items()}
ys.YARD_OVERRIDE = {}                     # filled from plan.png review (YARDS below)
YARDS = {
    # yard 15 (north): long barn west, big barn south, sheds north
    993157840: "15", 993157830: "15", 993157836: "15", 993157839: "15", 993157841: "15", 993157869: "15",
    # yard 18 (south): second dwelling 993157862 is drawn as a farm building (no address, satellite only)
    993157862: "18", 993157863: "18", 993157864: "18", 993157867: "18", 993157866: "18",
}
ys.YARD_OVERRIDE.update(YARDS)
_buildings = ys.buildings
ys.buildings = lambda o: list({b["id"]: b for b in _buildings(o) if b["id"] in YARDS or b["id"] in HOUSE_IDS}.values())


def _old_map():
    """building id -> old procedural objects, one-to-one (Hungarian on ground-centre distance). Leftover boxes that
    contain a building centre within 25 px (duplicate OSM way 993157866 was drawn twice) go to that building."""
    from scipy.optimize import linear_sum_assignment
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    cen = {b["id"]: (b["c"][0] - ys.SHIFT[0], b["c"][1] - ys.SHIFT[1]) for b in P_}
    inside = lambda o, c: o["x"] <= c[0] <= o["x"] + o["w"] and o["y"] <= c[1] <= o["base"] + 4  # noqa: E731
    gc = lambda o: (o["x"] + o["w"] / 2, o["base"] - o["h"] * .225)  # noqa: E731
    cand = [i for i, o in enumerate(objs) if o.get("kind") != "tree" and any(inside(o, c) for c in cen.values())]
    ids = list(cen)
    cost = np.full((len(ids), len(cand)), 1e6)
    for r, bid in enumerate(ids):
        for c, i in enumerate(cand):
            if inside(objs[i], cen[bid]): cost[r, c] = np.hypot(*np.subtract(gc(objs[i]), cen[bid]))
    rr, cc = linear_sum_assignment(cost)
    out = {bid: [] for bid in ids}; used = set()
    for r, c in zip(rr, cc):
        if cost[r, c] < 1e6: out[ids[r]].append(cand[c]); used.add(cand[c])
    for i in cand:
        if i in used: continue
        d, bid = min((np.hypot(*np.subtract(gc(objs[i]), cen[b])), b) for b in ids if inside(objs[i], cen[b]))
        if d < 25: out[bid].append(i); print("  extra old object", objs[i]["x"], objs[i]["y"], "->", bid, round(d))
    return {cen[b]: [(o["x"], o["y"], o["w"], o["h"]) for o in (objs[i] for i in v)] for b, v in out.items()}


def old_objects(cx, cy, objs, taken):
    keys = _OLD.get((cx, cy))
    if not keys: raise ValueError("no old object")
    return [o for k in keys for o in objs if (o["x"], o["y"], o["w"], o["h"]) == k and o.get("kind") != "tree"]


_OLD = {}


def shift():
    """Edge-alignment search: one offset for all OSM outlines in the box (like the strip's +5,+3)."""
    o = ys.osm(); old = ys.SHIFT; ys.SHIFT = (0, 0)
    B = ys.buildings(o)
    ys.SHIFT = old
    x0, y0, x1, y1 = ys.BOX; k = 2
    from sat_strip import strip
    sat = strip(ys.BOX, k, outlines=False)
    g = np.array(sat.convert("L"), float); mag = np.hypot(ndimage.sobel(g, 0), ndimage.sobel(g, 1))

    def score(dx, dy):
        m = Image.new("L", sat.size); d = ImageDraw.Draw(m)
        for b in B:
            pp = [((x + dx - x0) * k, (y + dy - y0) * k) for x, y in b["pts"]]
            d.line(pp + pp[:1], fill=1, width=3)
        return mag[np.array(m, bool)].mean()
    res = sorted(((score(dx, dy), dx, dy) for dx in range(-14, 15) for dy in range(-14, 15)), reverse=True)
    s0 = score(0, 0)
    print("no shift", round(s0, 1), "best", [(round(s, 1), dx, dy) for s, dx, dy in res[:5]])
    (OUT / "shift.json").write_text(json.dumps([res[0][1], res[0][2]]))


def house_prompt(b):
    w = round(b["ew_m"] * ys.A * ys.HOUSE_F)
    if b["tilt"] <= 12:
        orient = ("Its walls run exactly north-south and east-west on the satellite: draw it perfectly straight, front "
                  "wall facing the viewer horizontally, no diagonal turn. ")
    else:
        orient = f"It is turned about {b['tilt']} degrees from north-south/east-west, keep that turn as in image 1. "
    return (
        "Image 1: north-up satellite photo of ONE house in the Polish village Chlopkow, outlined in magenta (the "
        "outline is from a map and can be a few metres off: draw the real roof under or next to it). Image 2: wider "
        "satellite view of its farm yard, same house outlined in magenta. Image 3: style reference. Image 4: a house "
        "already made for the same game: copy EXACTLY its camera (oblique top-down 3/4 view from the south, roof "
        "mostly seen from above, the south wall visible below it with real depth), pixel size, outline and shading, "
        "light from the left.\nDraw ONLY the magenta-outlined house as one game sprite, exactly as it looks on the "
        "satellite: the same roof shape (hip or gable, ridge direction, annexes, chimneys), roof colour and material, "
        f"the same proportions: {b['ew_m']} m wide (left-right) and {b['ns_m']} m deep (front-back). The roof is "
        "deep, do not flatten it. " + orient + "Only the satellite is known: walls plain plaster in a colour that "
        "fits, NO windows, NO doors, NO stairs, NO balcony, NO plants, no invented details. "
        f"It must fit about {w} pixels wide. " + ys.STYLE)


def houses():
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    for b in P_:
        if b["id"] not in HOUSE_IDS: continue
        raw = OUT / f"house_{b['id']}_raw.png"
        if raw.exists(): print(b["id"], "raw exists"); continue
        d = OUT / f"h{b['id']}"; d.mkdir(exist_ok=True)
        r = max(b["ew_m"], b["ns_m"]) * 0.5 + 6
        ys.sat_crop(*b["c"], r, b["pts"]).save(d / "sat_tight.png")
        mates = [q["pts"] for q in P_ if q.get("yard") == b["yard"] and q["id"] != b["id"]]
        ys.sat_crop(*b["c"], 40, b["pts"], others=mates).save(d / "sat_yard.png")
        text = house_prompt(b); (d / "prompt.txt").write_text(text, encoding="utf-8")
        args = [ys.CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", text, "--out", str(raw)]
        for p in (d / "sat_tight.png", d / "sat_yard.png", ys.SHRINE, STYLE_ANCHOR):
            args += ["--ref", str(p)]
        res = ""
        for _ in range(3):
            res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if '"ok": true' in res: break
        print(b["id"], res[-120:])


def anchor_for(yard):
    """House sprite of the yard as Codex anchor (x8), from the satellite-only house raw."""
    hid = next(k for k, v in ys.HOUSES.items() if v[0] == yard)
    p = OUT / f"anchor_{yard}.png"
    if not p.exists():
        from process import clean, pixelate
        s = ys.house_sprite(hid, clean, pixelate)
        s.resize((s.width * 8, s.height * 8), Image.Resampling.NEAREST).save(p)
    return p, hid


ys.anchor_for = anchor_for


def render():
    _OLD.update(_old_map()); ys.OLD_OBJECTS = old_objects
    ys.render()


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"shift": shift, "plan": ys.plan, "houses": houses, "cut": ys.cut_yards, "render": render,
     "single": lambda: ys.gen_single(sys.argv[2:])}.get(cmd, lambda: ys.gen(sys.argv[2:]))()
