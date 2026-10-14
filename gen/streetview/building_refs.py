"""Reference pack for one real building: OSM footprint + address, satellite top view, aimed Street View frames,
current in-game crop. No API keys (Google tiles / streetviewpixels thumbnails, as in sv_shoot.py).

    python gen/streetview/building_refs.py <osm_way_id> <outdir> [--panos N] [--maxdist M]

Writes into outdir: sat.png (footprint outlined, north up, facade sides labelled N/E/S/W),
sv_<k>_<side>_d<m>_yaw<deg>.jpg, game.png, refs.json (address, size, ridge, which facade each frame shows).
"""
import argparse
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "osm"))
from geo import P  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
PANOS = Path(r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\sv\crawl\panos_all.json")
SVURL = ("https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={p}&cb_client=maps_sv.tactile"
         "&w=1200&h=800&yaw={y}&pitch={pi}&thumbfov={f}")
MLAT = 111320.0


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=45) as r:
        return r.read()


def local(lat, lon, lat0, lon0):  # metres east, north
    return (lon - lon0) * MLAT * math.cos(math.radians(lat0)), (lat - lat0) * MLAT


def bearing(a, b):
    e, n = local(b[0], b[1], a[0], a[1])
    return (math.degrees(math.atan2(e, n)) + 360) % 360


def side_name(deg):
    return "NESW"[int(((deg + 45) % 360) // 90)]


def merc(lat, lon, z):
    n = 256 * 2 ** z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def satellite(lat, lon, z, half_px, poly_ll):
    cx, cy = merc(lat, lon, z)
    x0, y0 = int(cx - half_px), int(cy - half_px)
    canvas = Image.new("RGB", (2 * half_px, 2 * half_px))
    for tx in range(x0 // 256, (x0 + 2 * half_px) // 256 + 1):
        for ty in range(y0 // 256, (y0 + 2 * half_px) // 256 + 1):
            tile = Image.open(io.BytesIO(get(f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={z}")))
            canvas.paste(tile.convert("RGB"), (tx * 256 - x0, ty * 256 - y0))
    k = 3 if half_px < 200 else 2
    big = canvas.resize((canvas.width * k, canvas.height * k), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(big)
    pts = [((merc(a, b, z)[0] - x0) * k, (merc(a, b, z)[1] - y0) * k) for a, b in poly_ll]
    d.line(pts + [pts[0]], fill=(255, 0, 255), width=2)
    W = big.width
    for s, (x, y) in {"N": (W / 2, 12), "S": (W / 2, W - 22), "W": (8, W / 2), "E": (W - 18, W / 2)}.items():
        d.rectangle([x - 4, y - 4, x + 14, y + 16], fill=(0, 0, 0)); d.text((x, y), s, fill=(255, 255, 0))
    return big


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("way", type=int); ap.add_argument("out")
    ap.add_argument("--panos", type=int, default=4); ap.add_argument("--maxdist", type=float, default=90)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
    e = next(x for x in osm["elements"] if x["id"] == a.way)
    t = e["tags"]; ring = [(g["lat"], g["lon"]) for g in e["geometry"]]
    if ring[0] == ring[-1]: ring = ring[:-1]
    lat = sum(p[0] for p in ring) / len(ring); lon = sum(p[1] for p in ring) / len(ring)
    loc = [local(p[0], p[1], lat, lon) for p in ring]
    edges = []
    for i in range(len(loc)):
        (x1, y1), (x2, y2) = loc[i], loc[(i + 1) % len(loc)]
        L = math.hypot(x2 - x1, y2 - y1)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        normal = (math.degrees(math.atan2(mx, my)) + 360) % 360      # outward-ish, from centroid
        edges.append(dict(len_m=round(L, 1), dir=round((math.degrees(math.atan2(x2 - x1, y2 - y1)) + 360) % 180),
                          faces=round(normal), side=side_name(normal)))
    longest = max(edges, key=lambda x: x["len_m"])
    addr = " ".join(v for v in (t.get("addr:place") or t.get("addr:street"), t.get("addr:housenumber")) if v)
    info = dict(osm_way=a.way, address=addr or None, building=t.get("building"), levels=t.get("building:levels"),
                lat=round(lat, 7), lon=round(lon, 7), game_xy=[round(v) for v in P(lat, lon)],
                ridge_bearing_guess=longest["dir"], edges=edges, frames=[])
    # satellite, ~45 m box at z20 (0.09 m/px at this latitude)
    satellite(lat, lon, 20, 160, ring).save(out / "sat.png")
    satellite(lat, lon, 19, 160, ring).save(out / "sat_wide.png")
    # Street View: nearest panos within maxdist, aimed at the centroid, fov fitted to the building
    panos = json.load(open(PANOS, encoding="utf-8"))["panos"]
    span = max(math.hypot(p[0], p[1]) for p in loc) * 2
    ranked = sorted(panos, key=lambda p: math.hypot(*local(p["lat"], p["lng"], lat, lon)))
    picks, used = [], []
    for p in ranked:
        d = math.hypot(*local(p["lat"], p["lng"], lat, lon))
        if d > a.maxdist or len(picks) >= a.panos: break
        b = bearing((p["lat"], p["lng"]), (lat, lon))
        if any(abs(((b - u + 180) % 360) - 180) < 12 for u in used): continue   # want different angles
        picks.append((p, d, b)); used.append(b)
    for k, (p, d, b) in enumerate(picks):
        fov = max(35, min(90, round(math.degrees(2 * math.atan(span * .75 / max(d, 1))))))
        seen = side_name((b + 180) % 360)   # camera looks at the facade facing back towards it
        name = f"sv_{k}_{seen}side_d{round(d)}m_yaw{round(b)}.jpg"
        (out / name).write_bytes(get(SVURL.format(p=p["panoid"], y=round(b), pi=4, f=fov)))
        info["frames"].append(dict(file=name, panoid=p["panoid"], dist_m=round(d), yaw=round(b), fov=fov,
                                   facade_seen=seen))
    # in-game crop (x3), centred on the footprint
    g = Image.open(ROOT / "docs/img/map_ground.png").convert("RGBA")
    o = Image.open(ROOT / "docs/img/map_objects.png").convert("RGBA")
    gx, gy = P(lat, lon); box = (int(gx) - 90, int(gy) - 70, int(gx) + 90, int(gy) + 70)
    c = g.crop(box); c.alpha_composite(o.crop(box))
    c.resize((c.width * 3, c.height * 3), Image.Resampling.NEAREST).save(out / "game.png")
    (out / "refs.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
