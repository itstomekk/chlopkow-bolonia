"""Phase 1: crawl the Street View panorama graph around Chlopkow.

Browser is used only to discover panoids; the crawl walks outward from a known
covered seed along the road, harvesting every panorama Google has.

Usage: python sv_crawl.py <outdir> <seed_lat> <seed_lng> [max_seeds]
"""
import json
import math
import os
import re
import sys

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

OUT = sys.argv[1]
SEED = (float(sys.argv[2]), float(sys.argv[3]))
MAX_SEEDS = int(sys.argv[4]) if len(sys.argv) > 4 else 14
os.makedirs(OUT, exist_ok=True)

PANO_RE = re.compile(r'\[\[2,"([A-Za-z0-9_-]{22})"\],null,\[\[null,null,(-?[0-9.]+),(-?[0-9.]+)\]')
M_PER_LAT = 111320.0


def m_per_lng(lat):
    return M_PER_LAT * math.cos(math.radians(lat))


def dist_m(a, b):
    return math.hypot((a[0] - b[0]) * M_PER_LAT, (a[1] - b[1]) * m_per_lng(a[0]))


def bearing(a, b):
    """Compass heading from a to b, degrees 0-360 (0 = north)."""
    dx = (b[1] - a[1]) * m_per_lng(a[0])
    dy = (b[0] - a[0]) * M_PER_LAT
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


panos = {}          # panoid -> (lat, lng)
seeds_done = []
queue = [SEED]
harvested_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
    ctx = browser.new_context(locale="en-US", user_agent=UA,
                             viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    payloads = []

    def handle(resp):
        if "photometa" in resp.url and resp.status == 200:
            try:
                payloads.append(resp.text())
            except Exception:  # noqa: BLE001
                pass

    page.on("response", handle)

    while queue and len(seeds_done) < MAX_SEEDS:
        seed = queue.pop(0)
        if any(dist_m(seed, s) < 60 for s in seeds_done):
            continue
        seeds_done.append(seed)
        payloads.clear()
        url = (f"https://www.google.com/maps/@?api=1&map_action=pano"
               f"&viewpoint={seed[0]},{seed[1]}&heading=0&pitch=0&fov=80")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print(f"seed {seed} goto {type(e).__name__}")
            continue
        page.wait_for_timeout(7000)
        fresh = {}
        for text in payloads:
            for m in PANO_RE.finditer(text):
                fresh[m.group(1)] = (float(m.group(2)), float(m.group(3)))
        new = {k: v for k, v in fresh.items() if k not in panos}
        panos.update(fresh)
        print(f"seed {len(seeds_done):2d} {seed[0]:.5f},{seed[1]:.5f} "
              f"cluster={len(fresh)} new={len(new)} total={len(panos)}")
        harvested_urls.append(url)

        if not new and len(seeds_done) > 1:
            continue
        # walk outward from this cluster along its principal axis
        pts = list(fresh.values())
        if len(pts) >= 3:
            clat = sum(p[0] for p in pts) / len(pts)
            clng = sum(p[1] for p in pts) / len(pts)
            mx = [((p[1] - clng) * m_per_lng(clat), (p[0] - clat) * M_PER_LAT) for p in pts]
            sxx = sum(v[0] ** 2 for v in mx)
            syy = sum(v[1] ** 2 for v in mx)
            sxy = sum(v[0] * v[1] for v in mx)
            theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
            ax, ay = math.cos(theta), math.sin(theta)
            proj = [v[0] * ax + v[1] * ay for v in mx]
            for sign in (1, -1):
                idx = proj.index(max(proj) if sign > 0 else min(proj))
                edge = pts[idx]
                d = 150.0 * sign
                nlat = edge[0] + (ay * d) / M_PER_LAT
                nlng = edge[1] + (ax * d) / m_per_lng(clat)
                queue.append((nlat, nlng))
        else:  # tiny cluster: fan out in 4 directions
            clat, clng = pts[0] if pts else seed
            for dlat, dlng in ((0.00135, 0), (-0.00135, 0), (0, 0.0022), (0, -0.0022)):
                queue.append((clat + dlat, clng + dlng))

    browser.close()

panos_list = [{"panoid": k, "lat": v[0], "lng": v[1]} for k, v in panos.items()]
with open(os.path.join(OUT, "panos_all.json"), "w", encoding="utf-8") as fh:
    json.dump({"seeds": seeds_done, "count": len(panos_list), "panos": panos_list},
              fh, indent=1)
print(f"\nDONE: {len(panos_list)} unique panoramas from {len(seeds_done)} seeds")
if panos_list:
    lats = [p["lat"] for p in panos_list]
    lngs = [p["lng"] for p in panos_list]
    print(f"covered area: lat {min(lats):.5f}..{max(lats):.5f} "
          f"({round((max(lats)-min(lats))*M_PER_LAT)} m), "
          f"lng {min(lngs):.5f}..{max(lngs):.5f} "
          f"({round((max(lngs)-min(lngs))*m_per_lng(lats[0]))} m)")
