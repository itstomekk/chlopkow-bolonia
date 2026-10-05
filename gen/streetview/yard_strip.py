"""Yard rebuild for the main-road strip (iteration 9, Tomek: scale x2.6 is right, but redo the yards so the gaps
between buildings are sensible and the barns look like the real ones on the satellite).

    python gen/streetview/yard_strip.py plan      # assign outbuildings to yards, write gen/yards/strip/plan.json + plan.png
    python gen/streetview/yard_strip.py refs      # satellite crops per outbuilding (tight + yard), target outlined
    python gen/streetview/yard_strip.py gen [id]  # Codex: one sprite per outbuilding, skips existing raws
    python gen/streetview/yard_strip.py render    # sprites + layout solver -> compare9.png (+ sat strip)

Rules used (plans/asset-style-guide.md): houses keep their accepted GPT drawings at F=2.6 x footprint width; no
rotation or shear of any GPT drawing (20); outbuildings are drawn from the satellite only (21), straight when they
are axis-aligned on the satellite (19), at FARM_F; positions: OSM footprints + global satellite offset, then the
layout solver pushes outbuildings away from the road (along their plot) until every ground footprint keeps GAP px
from every other building, the road and tree trunks.
"""
import io
import json
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
import os  # noqa: E402
STRIP = os.environ.get("STRIP", "west")          # which stretch of the main road (see STRIPS below)
OUT = ROOT / ("gen/yards/strip" if STRIP == "west" else f"gen/yards/strip_{STRIP}")
TAG = "9" if STRIP == "west" else f"_{STRIP}"    # output name suffix: compare9.png / compare_east1.png
HOUSES_DIR = ROOT / "gen/pilot_2026-10-03-houses"
sys.path.insert(0, str(HOUSES_DIR)); sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "osm")); sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))   # its process.py wins
from geo import A, BBOX, MX, MY, P  # noqa: E402

CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
SHRINE = ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png"
BOX = (280, 3820, 1000, 4250)            # game px, x0 y0 x1 y1
SHIFT = (5, 3)                           # OSM -> satellite offset in game px (edge-alignment search, iteration 9)
HOUSE_F, FARM_F = 2.6, 1.6               # x real size (map = 2 px per metre)
GAP = 6                                  # min free pixels between ground footprints
ROAD = 289264709
# plot membership checked on the satellite (fences, hedges, driveways; plan.png, iteration 9)
YARD_OVERRIDE = {909989420: "26", 909989369: "26", 909989470: "25", 909989454: "24", 1095382358: "24"}
HOUSES = {909988193: ("27A", HOUSES_DIR / "27A_road_raw.png", 1.0), 909988191: ("28", HOUSES_DIR / "28_road_raw.png", 1.15),
          909988189: ("27", HOUSES_DIR / "27_road_raw.png", 1.0), 909988213: ("26", HOUSES_DIR / "26_v2_raw.png", 1.12),
          909989532: ("25", ROOT / "gen/yards/yard25/house_909989532_raw.png", 1.0),
          909989531: ("24", ROOT / "gen/yards/yard25/../yard24/house_909989531_raw.png", 1.0)}
if STRIP == "east1":     # houses 23, 22, 20, 19 and the unnumbered one east of 19 (OSM 1095382357)
    BOX = (860, 3870, 1180, 4400)
    YARD_OVERRIDE = {}
    HOUSES = {w: (y, ROOT / f"gen/yards/yard{y}/house_{w}_raw.png", 1.0) for w, y in
              [(909989530, "23"), (909989529, "22"), (909989528, "20"), (909988586, "19"), (1095382357, "E1")]}


def osm():
    return json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))


def road_geom(o):
    e = next(e for e in o["elements"] if e["id"] == ROAD)
    return [P(p["lat"], p["lon"]) for p in e["geometry"]]


def road_frame(pt, road):
    """(u along road, v signed distance: + = north of road, unit normal pointing north) at the nearest segment."""
    best = None
    for (ax, ay), (bx, by) in zip(road, road[1:]):
        dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy)
        t = max(0, min(1, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L ** 2))
        px, py = ax + t * dx, ay + t * dy; d = math.hypot(pt[0] - px, pt[1] - py)
        if best is None or d < best[0]:
            nx, ny = dy / L, -dx / L                       # left normal of an eastward road = north
            if ny > 0: nx, ny = -nx, -ny
            best = (d, (pt[0] - px) * nx + (pt[1] - py) * ny, (nx, ny), ax + t * dx)
    return best[1], best[2]


def buildings(o):
    fin = ROOT / "gen/yards/final/placements.json"
    done = {q["id"] for q in json.loads(fin.read_text(encoding="utf-8"))
            if q.get("strip", "west") != STRIP} if fin.exists() else set()      # already drawn by another strip
    out = []
    for e in o["elements"]:
        t = e.get("tags", {})
        if "building" not in t or not e.get("geometry") or e["id"] in done: continue
        pts = [(x + SHIFT[0], y + SHIFT[1]) for x, y in (P(p["lat"], p["lon"]) for p in e["geometry"][:-1])]
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        if not (BOX[0] < cx < BOX[2] and BOX[1] < cy < BOX[3]): continue
        edges = [(math.hypot(b[0] - a[0], b[1] - a[1]) / A, math.degrees(math.atan2(b[0] - a[0], -(b[1] - a[1]))) % 180)
                 for a, b in zip(pts, pts[1:] + pts[:1])]
        lng = max(edges)
        ns_long = min(lng[1], 180 - lng[1]) < 30          # long side runs north-south
        tilt = min(lng[1] % 90, 90 - lng[1] % 90)          # deviation from axis-aligned
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        out.append(dict(id=e["id"], kind=t["building"], addr=t.get("addr:housenumber"), c=(cx, cy), pts=pts,
                        ew_m=round((max(xs) - min(xs)) / A, 1), ns_m=round((max(ys) - min(ys)) / A, 1),
                        long_m=round(lng[0], 1), ns_long=ns_long, tilt=round(tilt), house=e["id"] in HOUSES))
    return out


def snap(b):
    """Per-building correction: move the OSM outline (max +-12 game px) to where it best follows roof edges on the
    satellite. Kept only if clearly better than the global SHIFT (gain > 1.25)."""
    half = max(b["ew_m"], b["ns_m"]) * 0.5 + 10; size = 512; k = size / (2 * half * A)
    im = sat_crop(*b["c"], half, [], size=size)
    gimg = np.array(im.convert("L"), float); mag = np.hypot(ndimage.sobel(gimg, 0), ndimage.sobel(gimg, 1))
    base = [((x - b["c"][0]) * k + size / 2, (y - b["c"][1]) * k + size / 2) for x, y in b["pts"]]

    def score(dx, dy):
        m = Image.new("L", (size, size)); ImageDraw.Draw(m).line([(x + dx * k, y + dy * k) for x, y in base + base[:1]], fill=1, width=3)
        return mag[np.array(m, bool)].mean()
    s0 = score(0, 0); best = max((score(dx, dy), dx, dy) for dx in range(-6, 7, 2) for dy in range(-6, 7, 2))
    if best[0] / s0 > 1.4:
        dx, dy = best[1], best[2]
        b["pts"] = [(x + dx, y + dy) for x, y in b["pts"]]; b["c"] = (b["c"][0] + dx, b["c"][1] + dy)
        b["snap"] = (dx, dy, round(best[0] / s0, 2))
    else:
        b["snap"] = (0, 0, round(best[0] / s0, 2))


def plan():
    o = osm(); road = road_geom(o); B = buildings(o)
    for b in B:
        if not b["house"]: snap(b)
        b["v"], b["n"] = road_frame(b["c"], road)
    houses = [b for b in B if b["house"]]
    for b in B:
        if b["house"]: b["yard"] = HOUSES[b["id"]][0]; continue
        same_side = [h for h in houses if (h["v"] > 0) == (b["v"] > 0)]
        # plots are strips perpendicular to the road: nearest house measured ALONG the road
        def along(h):
            dx, dy = b["c"][0] - h["c"][0], b["c"][1] - h["c"][1]; nx, ny = b["n"]
            return abs(dx * -ny + dy * nx)
        h = min(same_side, key=along) if same_side else None
        b["yard"] = HOUSES[h["id"]][0] if h and along(h) < 40 and abs(b["v"]) > abs(h["v"]) else None
        b["yard"] = YARD_OVERRIDE.get(b["id"], b["yard"])
    OUT.mkdir(parents=True, exist_ok=True)
    keep = [dict({k: v for k, v in b.items()}) for b in B]
    (OUT / "plan.json").write_text(json.dumps(keep, indent=1), encoding="utf-8")
    for b in sorted(B, key=lambda b: (str(b["yard"]), b["c"][0])):
        print(f"{b['id']:>11} {b['kind']:15s} yard={b['yard']!s:4s} c=({b['c'][0]:.0f},{b['c'][1]:.0f}) v={b['v']:.0f} "
              f"{b['ew_m']}x{b['ns_m']} m long={b['long_m']} {'N-S' if b['ns_long'] else 'E-W'} tilt={b['tilt']} snap={b.get('snap')}")
    from sat_strip import strip
    im = strip(BOX, 2, outlines=False); d = ImageDraw.Draw(im)
    cols = {}
    pal = [(255, 0, 255), (0, 255, 255), (255, 255, 0), (255, 120, 0), (120, 255, 0), (0, 160, 255), (255, 80, 80)]
    for b in B:
        col = cols.setdefault(b["yard"], pal[len(cols) % len(pal)]) if b["yard"] else (255, 255, 255)
        pts = [((x - BOX[0]) * 2, (y - BOX[1]) * 2) for x, y in b["pts"]]
        d.line(pts + pts[:1], fill=col, width=3 if b["house"] else 2)
        d.text(((b["c"][0] - BOX[0]) * 2 - 10, (b["c"][1] - BOX[1]) * 2 - 5), (b["yard"] or "-") + ("H" if b["house"] else ""), fill=col)
    im.save(OUT / "plan.png")


# ---------------------------------------------------------------- satellite crops
def merc(lat, lon, z):
    n = 256 * 2 ** z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def ll(x, y):
    return BBOX[2] - y / (MY * A), BBOX[1] + x / (MX * A)


_tiles = {}


def tile(z, tx, ty):
    if (z, tx, ty) not in _tiles:
        cache = OUT / "_tiles" / f"{z}_{tx}_{ty}.jpg"
        if cache.exists():
            _tiles[(z, tx, ty)] = Image.open(cache).convert("RGB"); return _tiles[(z, tx, ty)]
        import time
        for attempt in range(5):
            try:
                b = urllib.request.urlopen(urllib.request.Request(f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={z}",
                                           headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read(); break
            except OSError:
                time.sleep(2 + 3 * attempt)
        else:
            raise RuntimeError(f"tile {z}/{tx}/{ty} failed")
        cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(b)
        _tiles[(z, tx, ty)] = Image.open(io.BytesIO(b)).convert("RGB")
    return _tiles[(z, tx, ty)]


def sat_crop(cx, cy, half_m, pts, size=768, z=20, others=()):
    """North-up satellite crop centred on game point (cx, cy), half_m metres each side, target outline magenta."""
    h = half_m * A
    la0, lo0 = ll(cx - h, cy - h); la1, lo1 = ll(cx + h, cy + h)
    x0, y0 = merc(la0, lo0, z); x1, y1 = merc(la1, lo1, z)
    big = Image.new("RGB", (int(x1 // 256 - x0 // 256 + 1) * 256, int(y1 // 256 - y0 // 256 + 1) * 256))
    for tx in range(int(x0 // 256), int(x1 // 256) + 1):
        for ty in range(int(y0 // 256), int(y1 // 256) + 1):
            big.paste(tile(z, tx, ty), ((tx - int(x0 // 256)) * 256, (ty - int(y0 // 256)) * 256))
    ox, oy = int(x0 // 256) * 256, int(y0 // 256) * 256
    im = big.crop((round(x0 - ox), round(y0 - oy), round(x1 - ox), round(y1 - oy))).resize((size, size), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(im); k = size / (2 * h)
    for q, col, w in [(p, (255, 255, 0), 2) for p in others] + [(pts, (255, 0, 255), 4)]:
        pp = [((x - (cx - h)) * k, (y - (cy - h)) * k) for x, y in q]
        d.line(pp + pp[:1], fill=col, width=w)
    return im


def refs():
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    for b in P_:
        if b["house"] or not b["yard"]: continue
        d = OUT / str(b["id"]); d.mkdir(exist_ok=True)
        r = max(b["ew_m"], b["ns_m"]) * 0.5 + 6
        sat_crop(*b["c"], r, b["pts"]).save(d / "sat_tight.png")
        mates = [q["pts"] for q in P_ if q["yard"] == b["yard"] and q["id"] != b["id"]]
        sat_crop(*b["c"], 40, b["pts"], others=mates).save(d / "sat_yard.png")
        print(b["id"], "refs ok")


# ---------------------------------------------------------------- generation
STYLE = ("Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, 1 pixel "
         "dark outline, 2-3 step shading, cheerful but in the real colour family, about 20 flat colours, no "
         "anti-aliasing, no gradients, no noise, no photorealism, no text. Plain perfectly flat solid magenta #FF00FF "
         "background, no ground, no grass, no cast shadow, nothing but the building.")


def expected(b, F):
    s = A * F
    return round(b["ew_m"] * s), round((b["ns_m"] * 0.75 + 2.4) * s)


def anchor_for(yard):
    hid = next(k for k, v in HOUSES.items() if v[0] == yard)
    p = OUT / f"anchor_{yard}.png"
    if not p.exists():
        from process import clean, pixelate
        s = house_sprite(hid, clean, pixelate)
        s.resize((s.width * 8, s.height * 8), Image.Resampling.NEAREST).save(p)
    return p, hid


def house_sprite(hid, clean, pixelate):
    o = osm(); e = next(e for e in o["elements"] if e["id"] == hid)
    xs = [P(p["lat"], p["lon"])[0] for p in e["geometry"]]
    w = round((max(xs) - min(xs)) * HOUSE_F); _, raw, k = HOUSES[hid]
    im = clean(raw)
    return pixelate(im.resize((w, round(im.height * w / im.width * k)), Image.Resampling.LANCZOS), w)


def prompt(b):
    w, h = expected(b, FARM_F)
    if b["tilt"] <= 12:
        orient = ("It is NOT rotated: its walls run exactly north-south and east-west, so draw it perfectly straight, "
                  "no diagonal, no perspective turn. ")
        if b["ns_long"]:
            orient += ("It is long in the north-south direction, so in this top-down view it is a TALL NARROW sprite: "
                       "the long roof seen from above runs up the picture, and only the short south end wall is "
                       "visible at the bottom. ")
        else:
            orient += ("It is long in the east-west direction, so it is a WIDE sprite: the long roof seen from above, "
                       "the long south wall visible below it. ")
    else:
        orient = (f"It is turned about {b['tilt']} degrees from north-south/east-west exactly as in image 1; keep that "
                  "orientation, roof seen from above, the south-facing walls visible below it. ")
    return (
        "Image 1: north-up satellite photo of ONE farm building (barn / cowshed / shed / garage) in the Polish village "
        "Chlopkow, outlined in magenta. Image 2: wider satellite view of the same farm yard; the same building is "
        "outlined in magenta, the other buildings of the yard in yellow. Image 3: style reference. Image 4: the "
        "house of this yard, already made for the game; copy its camera (oblique top-down 3/4 view from the south, "
        "roof mostly seen from above, the south wall visible below it), pixel size, outline and shading, light from "
        "the left.\nDraw ONLY the magenta-outlined building as one game sprite, exactly as it looks on the "
        "satellite (the outline is from a map and can be a few metres off: draw the real roof under or next to it): the same roof shape (ridge direction, L-shape, lean-to parts, flat parts, skylights), the same "
        f"roof colour and material, the same proportions: {b['ew_m']} m wide (left-right) and {b['ns_m']} m long "
        f"(front-back). " + orient + "Only the satellite is known, so keep the walls plain (plain grey plaster or "
        "the colour that fits the roof), no windows, no doors, no stairs, no plants, no invented details. Single "
        f"storey farm building. It must fit about {w}x{h} pixels; the house in image 4 is "
        f"{Image.open(anchor_for(b['yard'])[0]).width // 8} pixels wide at the same scale. " + STYLE)


def gen(only):
    """Whole yard in ONE image (Tomek, iteration 9: 'do the whole yards, maybe together'): all outbuildings of a yard
    are drawn together, arranged as on the satellite, then cut apart (cut_yards) and placed by the solver."""
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    for yard in sorted({b["yard"] for b in P_ if b["yard"] and not b["house"]}):
        if only and yard not in only: continue
        farms = sorted([b for b in P_ if b["yard"] == yard and not b["house"]], key=lambda b: (b["c"][1], b["c"][0]))
        d = OUT / f"yard_{yard}"; d.mkdir(exist_ok=True); raw = d / "raw.png"
        if raw.exists(): print(yard, "raw exists"); continue
        house = next(b for b in P_ if b["house"] and b["yard"] == yard)
        allpts = [p for b in farms + [house] for p in b["pts"]]
        xs = [p[0] for p in allpts]; ys = [p[1] for p in allpts]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        half = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 / A + 8
        clean_im = sat_crop(cx, cy, half, [], size=1024); clean_im.save(d / "sat_clean.png")
        lab = sat_crop(cx, cy, half, house["pts"], size=1024, others=[])
        dr = ImageDraw.Draw(lab); k = 1024 / (2 * half * A)
        for i, b in enumerate(farms, 1):
            pp = [((x - (cx - half * A)) * k, (y - (cy - half * A)) * k) for x, y in b["pts"]]
            dr.line(pp + pp[:1], fill=(0, 255, 255), width=4)
            tx = (b["c"][0] - (cx - half * A)) * k; ty = (b["c"][1] - (cy - half * A)) * k
            dr.rectangle([tx - 14, ty - 16, tx + 14, ty + 16], fill=(0, 0, 0)); dr.text((tx - 5, ty - 8), str(i), fill=(255, 255, 0))
        lab.save(d / "sat_labelled.png")
        lines = []
        for i, b in enumerate(farms, 1):
            w, h = expected(b, FARM_F)
            if b["tilt"] <= 12:
                o = ("straight, walls exactly north-south / east-west, NOT diagonal; " +
                     ("long north-south: a TALL NARROW shape, long roof running up the picture, short south end wall at the bottom"
                      if b["ns_long"] else "long east-west: a WIDE shape, long south wall below the roof"))
            else:
                o = f"turned about {b['tilt']} degrees exactly as on the satellite"
            lines.append(f"  {i}: {b['ew_m']} m wide x {b['ns_m']} m long, {o}, about {w}x{h} px in the game.")
        anchor, _ = anchor_for(yard)
        text = (
            f"Image 1: north-up satellite photo of one farm yard in the Polish village Chlopkow. The house is outlined in "
            f"magenta, the {len(farms)} farm buildings are outlined in cyan and numbered. Image 2: the same satellite photo "
            "without outlines, to see the real roofs. Image 3: style reference. Image 4: the house of this yard, already "
            "made for the game: copy its camera (oblique top-down 3/4 view from the south, roof mostly seen from above, "
            "the south wall visible below it), pixel size, outline and shading, light from the left.\n"
            f"Draw ALL {len(farms)} numbered farm buildings (NOT the house) in one picture, arranged like on the satellite "
            "(same relative positions, north up), but each building SEPARATE with clear magenta background between them, "
            "never touching or overlapping. Each building exactly as it looks on the satellite (the outlines come from a "
            "map and can be a few metres off: draw the real roof under or next to them): the same roof shape (ridge "
            "direction, L-shapes, lean-to parts, flat parts, skylights), roof colour and material, and proportions. "
            "Same scale for all buildings:\n" + "\n".join(lines) + "\n"
            "Only the satellite is known: walls plain (grey plaster, or the colour that fits the roof), no windows, no "
            "doors, no stairs, no plants, no invented details. No numbers or labels in the picture. " + STYLE)
        (d / "prompt.txt").write_text(text, encoding="utf-8")
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", text, "--out", str(raw)]
        for r in (d / "sat_labelled.png", d / "sat_clean.png", SHRINE, anchor):
            args += ["--ref", str(r)]
        res = ""
        for _ in range(3):
            res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if '"ok": true' in res: break
        print(yard, len(farms), res[-80:])
        (d / "ids.json").write_text(json.dumps([b["id"] for b in farms]), encoding="utf-8")


def cut_yards():
    """Split each yard image into its buildings and match them to the numbered footprints by relative position."""
    from scipy.optimize import linear_sum_assignment
    from process import clean
    P_ = {b["id"]: b for b in json.loads((OUT / "plan.json").read_text(encoding="utf-8"))}
    for d in sorted(OUT.glob("yard_*")):
        if not (d / "raw.png").exists(): continue
        ids = json.loads((d / "ids.json").read_text()); im = clean(d / "raw.png"); a = np.array(im)
        mask = ndimage.binary_closing(a[..., 3] > 0, iterations=3)
        lab, n = ndimage.label(mask); sizes = np.bincount(lab.ravel()); sizes[0] = 0
        comps = [i for i in range(1, n + 1) if sizes[i] > sizes.max() * 0.04]
        print(d.name, "buildings", len(ids), "pieces", len(comps))
        if len(comps) < len(ids):
            print("  !! fewer pieces than buildings (some drawn touching); unmatched buildings get no sprite")
        cen = np.array([ndimage.center_of_mass(lab == i) for i in comps])[:, ::-1]      # (x, y)
        foot = np.array([P_[i]["c"] for i in ids])
        norm = lambda v: (v - v.mean(0)) / (np.ptp(v, 0).max() + 1e-6)  # noqa: E731
        cost = np.linalg.norm(norm(cen)[:, None, :] - norm(foot)[None, :, :], axis=2)
        r, c = linear_sum_assignment(cost)
        for ci, fi in zip(r, c):
            ys, xs = np.nonzero(lab == comps[ci]); piece = a.copy(); piece[lab != comps[ci], 3] = 0
            p = Image.fromarray(piece).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
            bg = Image.new("RGB", p.size, (255, 0, 255)); bg.paste(p, mask=p.getchannel("A"))
            (OUT / str(ids[fi])).mkdir(exist_ok=True); bg.save(OUT / str(ids[fi]) / "raw.png")
            print(f"  piece {ci} -> {ids[fi]} (#{fi + 1}) cost {cost[ci, fi]:.2f}")


def gen_single(only):
    """Fallback: one image per outbuilding."""
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    for b in P_:
        if b["house"] or not b["yard"] or (only and str(b["id"]) not in only): continue
        d = OUT / str(b["id"]); raw = d / "raw.png"
        if raw.exists(): print(b["id"], "raw exists"); continue
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", prompt(b), "--out", str(raw)]
        for r in (d / "sat_tight.png", d / "sat_yard.png", SHRINE, anchor_for(b["yard"])[0]):
            args += ["--ref", str(r)]
        res = ""
        for _ in range(3):
            res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if '"ok": true' in res: break
        print(b["id"], res[-80:])


# ---------------------------------------------------------------- sprites + layout
def OLD_OBJECTS(cx, cy, objs, taken):
    """Old procedural map object(s) a new sprite replaces (strip default: the smallest box containing the centre).
    Other boxes (yard_j12) override this to keep the match one-to-one and catch duplicate OSM ways."""
    import process3 as p3
    return [p3.old_object(cx, cy, objs)]


def farm_sprite(b, clean, pixelate, scale=1.0):
    im = clean(OUT / str(b["id"]) / "raw.png"); w, h_exp = expected(b, FARM_F)
    w = max(8, round(w * scale)); h_exp = h_exp * scale
    h_nat = im.height * w / im.width; h = min(max(h_exp, h_nat / 1.15), h_nat * 1.15)
    b["ratio_off"] = round(h_nat / h_exp, 2)
    return pixelate(im.resize((w, round(h)), Image.Resampling.LANCZOS), w)


def render():
    import process3 as p3
    from process import clean, pixelate, arek, SHADOW
    o = osm(); road = road_geom(o)
    objs = json.load(open(ROOT / "docs/map.json", encoding="utf-8"))["objects"]
    P_ = json.loads((OUT / "plan.json").read_text(encoding="utf-8"))
    new = [b for b in P_ if b["house"] or (b["yard"] and (OUT / str(b["id"]) / "raw.png").exists())]
    for b in new:
        b["sprite"] = house_sprite(b["id"], clean, pixelate) if b["house"] else farm_sprite(b, clean, pixelate)
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    ob_layer = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    replaced = set()
    taken = set()
    for b in P_:
        if not (b["house"] or b in new): continue
        cx, cy = b["c"][0] - SHIFT[0], b["c"][1] - SHIFT[1]
        try:
            obs = OLD_OBJECTS(cx, cy, objs, taken)
        except ValueError:
            continue
        for ob in obs:
            replaced.add(id(ob)); taken.add(id(ob)); g = p3.remove_old_shadow(g, ob)
            ImageDraw.Draw(ob_layer).rectangle([ob["x"], ob["y"], ob["x"] + ob["w"], int(ob["base"]) + 2], fill=(0, 0, 0, 0))
        ob = obs[0]
        b["old"] = (ob["x"] + ob["w"] / 2, ob["base"] - ob["h"] * .225)   # ground centre of the old map building
    # blocked ground: old buildings left in place, tree trunks, road
    Wb, Hb = BOX[2] - BOX[0], BOX[3] - BOX[1]
    blocked = np.zeros((Hb, Wb), bool)
    for ob in objs:
        if id(ob) in replaced: continue
        if ob.get("kind") == "tree":
            x0, y0, x1, y1 = ob["x"] + ob["w"] * .35, ob["base"] - 4, ob["x"] + ob["w"] * .65, ob["base"]
        else:
            x0, y0, x1, y1 = ob["x"], ob["base"] - ob["h"] * .45, ob["x"] + ob["w"], ob["base"]
        blocked[max(0, int(y0) - BOX[1]):max(0, int(y1) - BOX[1]), max(0, int(x0) - BOX[0]):max(0, int(x1) - BOX[0])] = True
    rm = Image.new("L", (Wb, Hb)); ImageDraw.Draw(rm).line([(x - BOX[0], y - BOX[1]) for x, y in road], fill=1, width=22)
    blocked |= np.array(rm, bool)
    placed = []
    occ = blocked.copy()

    def put(b, tx, ty, test):
        s = b["sprite"]; c = p3.collision(s); ys, xs = np.nonzero(c)
        x0 = round(tx - xs.mean()); y0 = round(ty - ys.mean())
        gx, gy = xs + x0 - BOX[0], ys + y0 - BOX[1]
        if gx.min() < 0 or gy.min() < 0 or gx.max() >= Wb or gy.max() >= Hb: return None
        if test is not None and test[gy, gx].any(): return None
        return x0, y0, gx, gy

    report = []
    # Tomek (iteration 9): positions must stay as on the map. Every building sits exactly on its OSM footprint
    # centre (the same place as the old map object); conflicts are solved by shrinking outbuildings, never moving.
    def home(b):
        # true ground centre: OSM footprint centroid + per-building satellite snap, in map coords (iteration 9c).
        # (9b used the old procedural box centre, which drifted up to 13 px south for tall buildings.)
        return b["c"][0] - SHIFT[0], b["c"][1] - SHIFT[1]
    for b in sorted(new, key=lambda b: (not b["house"], abs(b["v"]))):
        if b["house"]:
            r = put(b, *home(b), None)
        else:
            test = ndimage.binary_dilation(occ, iterations=3)
            r = None; best = None
            for scale in (1.0, 0.9, 0.8, 0.7, 0.6):
                b["sprite"] = farm_sprite(b, clean, pixelate, scale)
                r = put(b, *home(b), test)
                if r: break
                rr = put(b, *home(b), None)
                if rr:
                    hit = int(test[rr[3], rr[2]].sum())
                    if best is None or hit < best[0]: best = (hit, scale, rr)
            if r is None and best:
                b["sprite"] = farm_sprite(b, clean, pixelate, best[1]); r = best[2]; scale = best[1]
            report.append((b["id"], b["yard"], "scale", scale, "overlap px", 0 if not best or r is not best[2] else best[0],
                           "ratio", b.get("ratio_off")))
            if r is None:
                print("NO PLACE", b["id"]); continue
        x0, y0, gx, gy = r; occ[gy, gx] = True; placed.append((b, x0, y0))
    for row in report: print(*row)
    # export for osm/render_map.py (YARD_SPRITES): sprite PNGs + top-left positions in map px
    fin = ROOT / "gen/yards/final"; fin.mkdir(parents=True, exist_ok=True)
    plc = []
    for b, x0, y0 in placed:
        b["sprite"].save(fin / f"{b['id']}.png")
        plc.append(dict(id=b["id"], yard=b["yard"], house=b["house"], strip=STRIP, png=f"gen/yards/final/{b['id']}.png", x=int(x0), y=int(y0)))
    old = json.loads((fin / "placements.json").read_text(encoding="utf-8")) if (fin / "placements.json").exists() else []
    keep = [q for q in old if q["id"] not in {p["id"] for p in plc}]
    (fin / "placements.json").write_text(json.dumps(keep + plc, indent=1), encoding="utf-8")

    def panel(coll):
        gg = g.crop(BOX); oo = ob_layer.crop(BOX)
        for b, x0, y0 in placed:
            s = b["sprite"]; sh = Image.new("RGBA", s.size, SHADOW + (255,)); sh.putalpha(s.getchannel("A"))
            gg.alpha_composite(sh.crop((0, s.height // 2, s.width, s.height)), (x0 - BOX[0] + 5, y0 - BOX[1] + s.height // 2 + 3))
        gg.alpha_composite(oo)
        for b, x0, y0 in sorted(placed, key=lambda t: t[2] + t[0]["sprite"].height):
            gg.alpha_composite(b["sprite"], (x0 - BOX[0], y0 - BOX[1]))
            if coll:
                c = p3.collision(b["sprite"]); ov = np.zeros((*c.shape, 4), np.uint8); ov[c] = (255, 0, 0, 120)
                gg.alpha_composite(Image.fromarray(ov), (x0 - BOX[0], y0 - BOX[1]))
        a = arek(); gg.alpha_composite(a, (215, 245 - a.height))
        return gg.resize((gg.width * 3, gg.height * 3), Image.Resampling.NEAREST)

    def now():
        im = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA").crop(BOX)
        im.alpha_composite(Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA").crop(BOX))
        return im.resize((im.width * 3, im.height * 3), Image.Resampling.NEAREST)

    from sat_strip import strip
    from process5 import stack
    panels = [("satelita (ten sam obszar)", strip(BOX, 3, outlines=False).convert("RGBA")), ("teraz w grze", now()),
              (f"nowe podworka ({STRIP}): srodki = prawdziwe obrysy (OSM + korekta z satelity)", panel(False)), ("+ blokada", panel(True))]
    stack(panels, HOUSES_DIR / f"compare{TAG}.png")
    # position check: old map, footprint outlines (cyan, real position) vs new ground centres (red)
    pc = now(); d = ImageDraw.Draw(pc)
    for b, x0, y0 in placed:
        c = p3.collision(b["sprite"]); ys, xs = np.nonzero(c)
        nx_, ny_ = (xs.mean() + x0 - BOX[0]) * 3, (ys.mean() + y0 - BOX[1]) * 3
        pp = [((x - SHIFT[0] - BOX[0]) * 3, (y - SHIFT[1] - BOX[1]) * 3) for x, y in b["pts"]]
        d.line(pp + pp[:1], fill=(0, 255, 255), width=2)
        tx, ty = (home(b)[0] - BOX[0]) * 3, (home(b)[1] - BOX[1]) * 3
        print("pos", b["id"], "delta px", round(nx_ / 3 - tx / 3, 1), round(ny_ / 3 - ty / 3, 1))
        d.ellipse([nx_ - 4, ny_ - 4, nx_ + 4, ny_ + 4], fill=(255, 0, 0))
    pc.save(HOUSES_DIR / f"pos_check{TAG}{'c' if STRIP == 'west' else ''}.png")
    k = 4; ss = [b["sprite"] for b in new if not b["house"]]
    if not ss: return
    row = Image.new("RGBA", (sum(s.width * k + 16 for s in ss), max(s.height for s in ss) * k), (40, 40, 40, 255)); x = 0
    for s in ss:
        row.alpha_composite(s.resize((s.width * k, s.height * k), Image.Resampling.NEAREST), (x, row.height - s.height * k)); x += s.width * k + 16
    row.save(HOUSES_DIR / f"sprites{TAG}_x4.png")


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"plan": plan, "refs": refs, "render": render, "cut": cut_yards,
     "single": lambda: gen_single(sys.argv[2:])}.get(cmd, lambda: gen(sys.argv[2:]))()
