"""Street View coverage check + reference harvester (browser path).

For each coordinate: open Street View the way the Maps client does, report
whether a panorama exists, and if it does save reference views at 4 headings.

Usage: python sv_check.py <outdir> lat,lng,label ...
"""
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
PTS = [a.split(",") for a in sys.argv[2:]]

THUMB = ("https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={p}"
         "&cb_client=maps_sv.tactile&w=1200&h=800&yaw={y}&pitch=0&thumbfov=80")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
    ctx = browser.new_context(locale="en-US", user_agent=UA,
                             viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    net = []
    page.on("response", lambda r: net.append(r.url)
            if ("streetviewpixels" in r.url or "photometa" in r.url) else None)

    results = {}
    for lat, lng, label in PTS:
        net.clear()
        url = (f"https://www.google.com/maps/@?api=1&map_action=pano"
               f"&viewpoint={lat},{lng}&heading=0&pitch=0&fov=80")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print(f"{label:12s} goto failed {type(e).__name__}")
            continue
        page.wait_for_timeout(8000)
        try:
            txt = page.inner_text("body")[:200].replace("\n", " | ")
        except Exception:  # noqa: BLE001
            txt = ""
        pano = None
        m = re.search(r"!1s([A-Za-z0-9_-]{20,})", page.url)
        if m:
            pano = m.group(1)
        else:
            for u in net:
                m2 = re.search(r"panoid=([A-Za-z0-9_-]{15,})", u)
                if m2:
                    pano = m2.group(1)
                    break
        results[label] = {"lat": lat, "lng": lng, "panoid": pano,
                          "sv_requests": len(net), "text": txt}
        print(f"{label:12s} panoid={pano} sv_reqs={len(net)} | {txt[:130]}")
        if pano:
            for yaw in (0, 90, 180, 270):
                rr = ctx.request.get(THUMB.format(p=pano, y=yaw), timeout=30000)
                body = rr.body()
                with open(os.path.join(OUT, f"{label}_yaw{yaw}.jpg"), "wb") as fh:
                    fh.write(body)
                results[label][f"yaw{yaw}"] = f"{rr.status}/{len(body)}b"
                print(f"    yaw={yaw} status={rr.status} bytes={len(body)}")

    with open(os.path.join(OUT, "coverage.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1)
    browser.close()
