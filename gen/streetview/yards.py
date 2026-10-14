"""Whole-yard pipeline for real buildings (house + every outbuilding of its plot), following the numbered rules in
plans/asset-style-guide.md ("Real buildings from Street View + satellite").

    python gen/streetview/yards.py plan  <yard_name> <house_way> [<outbuilding_way> ...]   # refs + angles + jobs.json
    python gen/streetview/yards.py gen   <yard_name> [building ...]                         # Codex, skips existing raws
    python gen/streetview/yards.py sprites <yard_name>                                      # raw -> game sprites

Everything for a yard lives in gen/yards/<yard_name>/ (jobs.json, *_raw.png, *.png). Reference packs go to
C:/Users/Lenovo/Hermes/image-gen/2026-10-03-chlopkow-building-refs/w<way>/ (building_refs.py).
GPT drawings are never rotated or sheared afterwards (rule 20); only width fit + at most 15% height stretch (14).
"""
import io
import json
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
REF = Path(r"C:\Users\Lenovo\Hermes\image-gen\2026-10-03-chlopkow-building-refs")
CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
ANCHOR = ROOT / "gen/pilot_2026-10-03-houses/anchor_27A_road_x8.png"
SHRINE = ROOT / "gen/pilot_2026-10-02/ref_shrine_stone.png"
HOUSE_PXM, FARM_PXM = 7.5, 5.0
STYLE = ("Style: genuine low-resolution game pixel art, chunky crisp square pixels, large flat colour clusters, 1 pixel "
         "dark outline, 2-3 step shading, cheerful and a bit more colourful than the photos but in the real colour "
         "family, about 24 flat colours, no anti-aliasing, no gradients, no noise, no photorealism, no text. Plain "
         "perfectly flat solid magenta #FF00FF background, no ground, no cast shadow.")
PROJ = ("Use EXACTLY the projection, camera height, pixel size, outline and shading of image 4 (a house already made "
        "for the same game): oblique top-down 3/4 view, roof seen mostly from above, front wall visible below it "
        "with real depth. Light from the left (west).")


def sat_angle(lat, lon):
    """Dominant wall direction (deg, 0-180) of the building at lat/lon from a z20 satellite crop."""
    z = 20; n = 256 * 2 ** z
    cx = (lon + 180) / 360 * n; cy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x0, y0 = int(cx - 40), int(cy - 40); c = Image.new("RGB", (80, 80))
    for tx in range(x0 // 256, (x0 + 80) // 256 + 1):
        for ty in range(y0 // 256, (y0 + 80) // 256 + 1):
            b = urllib.request.urlopen(urllib.request.Request(
                f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={z}", headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read()
            c.paste(Image.open(io.BytesIO(b)).convert("RGB"), (tx * 256 - x0, ty * 256 - y0))
    im = np.array(c.convert("L"), float); gx = ndimage.sobel(im, 1); gy = ndimage.sobel(im, 0); mag = np.hypot(gx, gy)
    ang = (np.degrees(np.arctan2(gx, -gy)) + 90) % 180; m = mag > np.percentile(mag, 85)
    h, _ = np.histogram(ang[m], bins=90, range=(0, 180), weights=mag[m]); h = ndimage.uniform_filter1d(h, 3, mode="wrap")
    return float(np.argmax(h) * 2 + 1)


def refs_pack(way):
    d = REF / f"w{way}"
    if not (d / "refs.json").exists():
        subprocess.run([sys.executable, str(ROOT / "gen/streetview/building_refs.py"), str(way), str(d), "--maxdist", "70"],
                       cwd=ROOT, check=True, capture_output=True)
    frames = sorted(d.glob("sv_*.jpg"))
    if frames and not (d / "sv_sheet.jpg").exists():
        s = Image.new("RGB", (1200, 800))
        for i, f in enumerate(frames[:4]):
            s.paste(Image.open(f).convert("RGB").resize((600, 400)), ((i % 2) * 600, (i // 2) * 400))
        s.save(d / "sv_sheet.jpg", quality=88)
    return d, json.loads((d / "refs.json").read_text(encoding="utf-8"))


def plan(yard, house, others):
    out = ROOT / "gen/yards" / yard; out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for i, way in enumerate([house] + others):
        d, r = refs_pack(way)
        edges = r["edges"]; e_long = max(edges, key=lambda e: e["len_m"]); e_short = min(edges, key=lambda e: e["len_m"])
        sat = sat_angle(r["lat"], r["lon"])
        # which OSM edge length runs east-west-ish on the satellite (the game's horizontal)
        ew = sat if abs(((sat - 90) + 90) % 180 - 90) < 45 else (sat + 90) % 180
        long_is_ew = abs(((e_long["dir"] - 90) + 90) % 180 - 90) < 45
        along, depth = (e_long["len_m"], e_short["len_m"]) if long_is_ew else (e_short["len_m"], e_long["len_m"])
        house_sv = r["frames"] and min(f["dist_m"] for f in r["frames"]) <= 40
        kind = "house" if i == 0 else "farm"
        if kind == "house":
            road_n = all(f["facade_seen"] == "N" for f in r["frames"][:2]) if r["frames"] else False
            w = round(along * HOUSE_PXM); h_rule = round(depth * HOUSE_PXM * 1.1 * 0.75 + 12 + 6 * (int(r.get("levels") or 1) - 1))
        else:
            road_n = False
            w = round(max(along, depth * 0.6) * FARM_PXM); h_rule = None
        jobs.append(dict(name=("house_" if kind == "house" else f"farm{i}_") + str(way), way=way, kind=kind,
                         address=r["address"], levels=r.get("levels"), along_m=along, depth_m=depth, sat_deg=sat,
                         ew_wall_deg=ew, w=w, h_rule=h_rule, satellite_only=not r["frames"],
                         street_photos_close=bool(house_sv), road_north=road_n, refdir=str(d)))
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1, ensure_ascii=False), encoding="utf-8")
    for j in jobs:
        print(f"{j['name']:22s} {j['kind']:5s} {j['along_m']}x{j['depth_m']} m sat {j['sat_deg']} -> {j['w']}px "
              f"sv={'none' if j['satellite_only'] else ('close' if j['street_photos_close'] else 'far')} road_north={j['road_north']}")


def prompt(j):
    d = Path(j["refdir"])
    if j["satellite_only"]:
        refs = [d / "sat.png", d / "sat_wide.png"]
        intro = ("Images 1-2: north-up satellite views (close, wide) of ONE building in the Polish village Chlopkow, "
                 "outlined in magenta; there are no street photos. Draw ONLY what the satellite shows: roof shape, ridge, "
                 "roof colour, chimneys, annexes. Walls plain, with NO windows, NO doors, NO stairs, NO balcony, NO plants.")
    else:
        refs = [d / "sv_sheet.jpg", d / "sat.png"]
        what = "house" if j["kind"] == "house" else "farm building (barn / shed / garage), possibly partly hidden"
        intro = (f"Image 1: real street photos towards ONE {what} in the Polish village Chlopkow. Image 2: north-up "
                 "satellite view of it, outlined in magenta. Copy the real building: roof shape, ridge, roof and wall "
                 "colours, doors, windows, extensions, as far as visible; where it is hidden, use the satellite and keep "
                 "walls simple. Ignore trees, fences, cars.")
        if j["road_north"]:
            intro += " The photos show its street side (the road is north of it); draw THAT side as the visible front."
    refs += [SHRINE, ANCHOR]
    along, depth = j["along_m"], j["depth_m"]
    if along >= depth:
        orient = ("Orientation: the building stands like the house in image 4, its long side running from upper-left "
                  "to lower-right with the right end lower, the long front wall facing the viewer.")
    else:
        orient = ("Orientation: a building whose long side runs AWAY from the viewer, perpendicular to the house in "
                  "image 4: we see its short gable end as the front wall, the long roof recedes from the viewer, "
                  "consistent with image 4's rotation.")
    size = f"{j['w']}x{j['h_rule']}" if j["h_rule"] else f"{j['w']} pixels wide"
    deep = " The roof is deep, nearly as deep as long, do not flatten it." if j["kind"] == "house" else ""
    text = (intro + " Image 3: style reference. Image 4: a house of the same game.\n" + orient + f" Real size about "
            f"{along} m along the front and {depth} m deep." + deep + " " + PROJ + f" Fits about {size} pixels, whole "
            "building visible. Draw ONLY the building itself: NO lawn, NO bushes, NO trees, NO fence, NO car, NO "
            "path, NO ground patch. Right end of the building LOWER than the left end, like image 4. " + STYLE)
    return text, refs


def gen(yard, names):
    out = ROOT / "gen/yards" / yard; jobs = json.loads((out / "jobs.json").read_text(encoding="utf-8"))
    for j in jobs:
        if names and j["name"] not in names: continue
        raw = out / f"{j['name']}_raw.png"
        if raw.exists(): print(j["name"], "raw exists"); continue
        text, refs = prompt(j)
        args = [CODEX_PY, str(ROOT / "gen/codex_gen.py"), "--aspect", "square", "--prompt", text, "--out", str(raw)]
        for r in refs: args += ["--ref", str(r)]
        for _ in range(3):
            res = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()
            if '"ok": true' in res: break
        print(j["name"], res[-90:])


def sprites(yard):
    sys.path.insert(0, str(ROOT / "gen/pilot_2026-10-03-house-27A"))
    from process import clean, pixelate
    out = ROOT / "gen/yards" / yard; jobs = json.loads((out / "jobs.json").read_text(encoding="utf-8"))
    for j in jobs:
        if not (out / f"{j['name']}_raw.png").exists(): print(j["name"], "no raw (reused elsewhere)"); continue
        im = clean(out / f"{j['name']}_raw.png"); w = j["w"]; h_nat = im.height * w / im.width
        h = h_nat if not j["h_rule"] else min(max(j["h_rule"], h_nat / 1.15), h_nat * 1.15)
        s = pixelate(im.resize((w, round(h)), Image.Resampling.LANCZOS), w); s.save(out / f"{j['name']}.png")
        print(j["name"], s.size)


if __name__ == "__main__":
    cmd, yard = sys.argv[1], sys.argv[2]
    if cmd == "plan": plan(yard, int(sys.argv[3]), [int(x) for x in sys.argv[4:]])
    elif cmd == "gen": gen(yard, sys.argv[3:])
    elif cmd == "sprites": sprites(yard)
