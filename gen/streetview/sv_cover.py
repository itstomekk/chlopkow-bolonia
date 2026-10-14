"""Street View coverage + view harvester.

Uses the endpoint the Google Maps web client itself calls (photometa/si/v1),
so no API key is needed. For each coordinate: report coverage, panoid, and if
covered, save N reference views.

Usage: python sv_cover.py <outdir> [lat,lng,label ...]
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

POINTS = []
for arg in sys.argv[2:]:
    lat, lng, label = arg.split(",")
    POINTS.append((float(lat), float(lng), label))

PB = ("!1m4!1smaps_sv.tactile!11m2!2m1!1b1!2m4!1m2!3d{lat}!4d{lng}!2d50"
      "!3m17!1m2!1m1!1e2!2m2!1sen!2spl!9m1!1e2!11m8!1m3!1e2!2b1!3e2!1m3!1e3!2b1!3e2"
      "!4m61!1e1!1e2!1e3!1e4!1e5!1e6!1e8!1e12!1e17!2m1!1e1!4m1!1i48!5m1!1e1!5m1!1e2"
      "!6m1!1e1!6m1!1e2!9m36!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e3!2b1!3e2!1m3!1e3!2b0!3e3")

METADATA_URL = "https://www.google.com/maps/photometa/si/v1?authuser=0&hl=en&gl=pl&pb="
THUMB = ("https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={p}"
         "&cb_client=maps_sv.tactile&w=1200&h=800&yaw={y}&pitch=0&thumbfov=80")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
    ctx = browser.new_context(locale="en-US", user_agent=UA)
    # warm up on google.com so the request context has the usual cookies
    ctx.request.get("https://www.google.com/maps", timeout=30000)

    for lat, lng, label in POINTS:
        url = METADATA_URL + PB.format(lat=lat, lng=lng)
        try:
            r = ctx.request.get(url, timeout=30000)
            text = r.text()
        except Exception as e:  # noqa: BLE001
            print(f"{label:22s} lat={lat} lng={lng}  ERROR {type(e).__name__}")
            continue
        panos = re.findall(r'"([A-Za-z0-9_-]{22})"', text) or re.findall(r"!1s([A-Za-z0-9_-]{20,})", text)
        # the pano id appears as a quoted token; filter obvious noise
        panos = [x for x in panos if not x.startswith("AIza")]
        print(f"{label:22s} lat={lat} lng={lng}  status={r.status} len={len(text)} "
              f"panoids={panos[:3]}")
        if panos:
            pano = panos[0]
            for yaw in (0, 90, 180, 270):
                rr = ctx.request.get(THUMB.format(p=pano, y=yaw), timeout=30000)
                body = rr.body()
                path = os.path.join(OUT, f"{label}_yaw{yaw}.jpg")
                with open(path, "wb") as fh:
                    fh.write(body)
                print(f"    yaw={yaw} status={rr.status} bytes={len(body)} -> {os.path.basename(path)}")
        else:
            with open(os.path.join(OUT, f"{label}_meta.txt"), "w", encoding="utf-8") as fh:
                fh.write(text[:2000])
    browser.close()
