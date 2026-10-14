"""Phase 2: shoot reference frames of named coordinates (no browser, no API key).

For each target coordinate, pick the panoramas nearest to it, aim the camera at
the target from each, and save 3-4 frames per target.

Usage: python sv_shoot.py <panos_json> <outdir> [lat,lng,label ...]
"""
import json
import math
import os
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
M_PER_LAT = 111320.0
TILE = ("https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={p}"
        "&cb_client=maps_sv.tactile&w=1200&h=800&yaw={y}&pitch={pi}&thumbfov={f}")

PANOS_JSON = sys.argv[1]
OUT = sys.argv[2]
TARGETS = sys.argv[3:]
os.makedirs(OUT, exist_ok=True)


def m_per_lng(lat):
    return M_PER_LAT * math.cos(math.radians(lat))


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * M_PER_LAT, (a[1] - b[1]) * m_per_lng(a[0]))


def bearing(a, b):
    dx = (b[1] - a[1]) * m_per_lng(a[0])
    dy = (b[0] - a[0]) * M_PER_LAT
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def fetch(panoid, yaw, pitch, fov):
    url = TILE.format(p=panoid, y=round(yaw % 360), pi=pitch, f=fov)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


graph = json.load(open(PANOS_JSON, encoding="utf-8"))
panos = [(p["panoid"], p["lat"], p["lng"]) for p in graph["panos"]]
print(f"graph: {len(panos)} panoramas, seeds={len(graph.get('seeds', []))}")

index = {}
for spec in TARGETS:
    lat, lng, label = spec.split(",")
    target = (float(lat), float(lng))
    ranked = sorted(panos, key=lambda p: dist_m((p[1], p[2]), target))
    picks = [p for p in ranked if dist_m((p[1], p[2]), target) <= 200][:3]
    tdir = os.path.join(OUT, label)
    os.makedirs(tdir, exist_ok=True)
    rec = {"lat": float(lat), "lng": float(lng), "shots": []}
    if not picks:
        near = ranked[0] if ranked else None
        d = round(dist_m((near[1], near[2]), target)) if near else None
        print(f"{label:16s} NO PANO within 200 m (nearest {d} m)")
        rec["error"] = f"no pano within 200 m (nearest {d} m)"
        index[label] = rec
        continue
    views = []
    for i, (pano, plat, plng) in enumerate(picks):
        d = dist_m((plat, plng), target)
        hdg = bearing((plat, plng), target)
        # nearest pano: two framings of the subject; the others: one each
        angles = [hdg] if i else [hdg - 18, hdg + 18]
        for a in angles:
            views.append((pano, d, hdg, a))
    for k, (pano, d, hdg, yaw) in enumerate(views):
        for pitch in (6,):
            for fov in (70,):
                try:
                    body = fetch(pano, yaw, pitch, fov)
                except Exception as e:  # noqa: BLE001
                    print(f"  {label} shot {k} failed {type(e).__name__}")
                    continue
                name = f"{label}_{k}_d{round(d)}m_yaw{round(yaw % 360)}.jpg"
                with open(os.path.join(tdir, name), "wb") as fh:
                    fh.write(body)
                rec["shots"].append({"file": f"{label}/{name}", "panoid": pano,
                                     "dist_m": round(d), "yaw": round(yaw % 360),
                                     "pitch": pitch, "fov": fov, "bytes": len(body)})
    print(f"{label:16s} panos={len(picks)} distances={[round(dist_m((p[1], p[2]), target)) for p in picks]} shots={len(rec['shots'])}")
    index[label] = rec

with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
    json.dump(index, fh, indent=1)
print("index ->", os.path.join(OUT, "index.json"))
