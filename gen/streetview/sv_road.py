"""Street View sweep along the game's own road geometry.

Reads the road ways out of osm/chlopkow.json, resamples them at a fixed
interval, and shoots each sample from the nearest panorama: left side, right
side and straight down the street.

Usage: python sv_road.py <chlopkow.json> <panos_all.json> <outdir> [interval_m] [way_ids]
"""
import json
import math
import os
import sys
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
M_PER_LAT = 111320.0
TILE = ("https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={p}"
        "&cb_client=maps_sv.tactile&w=1200&h=800&yaw={y}&pitch={pi}&thumbfov={f}")

OSM_JSON, PANOS_JSON, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
INTERVAL = float(sys.argv[4]) if len(sys.argv) > 4 else 50.0
WAY_IDS = set(int(x) for x in sys.argv[5].split(",")) if len(sys.argv) > 5 else None
os.makedirs(OUT, exist_ok=True)
MAP_BBOX = (52.252935, 22.8586, 52.2850, 22.896352)  # from osm/geo.py


def m_per_lng(lat):
    return M_PER_LAT * math.cos(math.radians(lat))


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * M_PER_LAT, (a[1] - b[1]) * m_per_lng(a[0]))


def bearing(a, b):
    dx = (b[1] - a[1]) * m_per_lng(a[0])
    dy = (b[0] - a[0]) * M_PER_LAT
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def fetch(panoid, yaw, pitch=6, fov=70):
    url = TILE.format(p=panoid, y=round(yaw % 360), pi=pitch, f=fov)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


osm = json.load(open(OSM_JSON, encoding="utf-8"))
ways = []
for e in osm["elements"]:
    t = e.get("tags", {})
    if t.get("highway") not in ("tertiary", "secondary", "primary",
                               "unclassified", "residential"):
        continue
    if "geometry" not in e:
        continue
    if WAY_IDS and e["id"] not in WAY_IDS:
        continue
    ways.append((e["id"], [(p["lat"], p["lon"]) for p in e["geometry"]]))

panos = [(p["panoid"], p["lat"], p["lng"])
         for p in json.load(open(PANOS_JSON, encoding="utf-8"))["panos"]]
print(f"ways={len(ways)} panos={len(panos)} interval={INTERVAL} m")

samples = []
for wid, pts in ways:
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = dist_m(a, b)
        n = max(1, int(seg // INTERVAL))
        for k in range(n):
            f = k / n
            lat = a[0] + (b[0] - a[0]) * f
            lng = a[1] + (b[1] - a[1]) * f
            samples.append({"way": wid, "lat": lat, "lng": lng,
                            "hdg": bearing(a, b)})
print(f"samples={len(samples)}")

index = []
for i, s in enumerate(samples):
    target = (s["lat"], s["lng"])
    pano, plat, plng = min(panos, key=lambda p: dist_m((p[1], p[2]), target))
    d = dist_m((plat, plng), target)
    in_map = (MAP_BBOX[0] <= s["lat"] <= MAP_BBOX[2]
              and MAP_BBOX[1] <= s["lng"] <= MAP_BBOX[3])
    rec = {"i": i, "way": s["way"], "lat": round(s["lat"], 6),
           "lng": round(s["lng"], 6), "in_game_map": in_map,
           "road_heading": round(s["hdg"]), "pano": pano, "pano_dist_m": round(d),
           "shots": []}
    if d > 60:
        rec["error"] = f"nearest pano {round(d)} m"
        index.append(rec)
        print(f"  [{i:02d}] {s['lat']:.5f},{s['lng']:.5f} skip (pano {round(d)} m)")
        continue
    # Frame by the ROAD's own heading. Bearing from a pano that sits 2-5 m away
    # is noise, which pointed the side views at empty fields.
    view_hdg = s["hdg"]
    for view, yaw in (("left", view_hdg - 90), ("right", view_hdg + 90),
                      ("ahead", view_hdg)):
        try:
            body = fetch(pano, yaw)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i:02d}] {view} failed {type(e).__name__}")
            continue
        name = (f"{'IN' if in_map else 'out'}_{i:02d}_{s['lat']:.5f}_{s['lng']:.5f}"
                f"_{view}_yaw{round(yaw % 360)}.jpg")
        with open(os.path.join(OUT, name), "wb") as fh:
            fh.write(body)
        rec["shots"].append({"view": view, "file": name, "yaw": round(yaw % 360),
                             "bytes": len(body)})
    index.append(rec)
    print(f"  [{i:02d}] {s['lat']:.5f},{s['lng']:.5f} in_map={in_map} "
          f"pano={pano} d={round(d)} m shots={len(rec['shots'])}")

with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
    json.dump(index, fh, indent=1)

# contact sheet
rows = []
for rec in index:
    if not rec.get("shots"):
        continue
    cells = "".join(
        f'<figure><img src="{sh["file"]}" loading="lazy">'
        f'<figcaption>{sh["view"]} yaw{sh["yaw"]}</figcaption></figure>'
        for sh in rec["shots"])
    tag = "IN MAP" if rec["in_game_map"] else "outside map"
    rows.append(f'<section><h3>#{rec["i"]:02d} {rec["lat"]},{rec["lng"]} '
                f'<small>{tag} | road hdg {rec["road_heading"]} | pano '
                f'{rec["pano_dist_m"]} m</small></h3><div class="g">{cells}</div></section>')
html = ("<!doctype html><meta charset=utf-8><title>Chlopkow street sweep</title>"
        "<style>body{font:14px system-ui;background:#111;color:#eee;margin:20px}"
        ".g{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}"
        "figure{margin:0}img{width:100%;display:block;border:1px solid #444}"
        "figcaption{font-size:11px;color:#9c9}section{margin:18px 0}"
        "h3{margin:0 0 6px;font-size:13px}small{color:#888;font-weight:400}"
        "</style>" + "".join(rows))
with open(os.path.join(OUT, "sweep.html"), "w", encoding="utf-8") as fh:
    fh.write(html)
shots = sum(len(r.get("shots", [])) for r in index)
print(f"\nDONE {shots} shots from {len(index)} samples -> {OUT}")
