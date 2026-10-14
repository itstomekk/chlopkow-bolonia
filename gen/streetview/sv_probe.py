"""Street View probe: find the pano id for a coordinate and pull reference views.

Usage: python sv_probe.py <lat> <lng> <outdir>
Caches nothing outside <outdir>. Reference use only (Google ToS: no redistribution).
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

LAT = float(sys.argv[1])
LNG = float(sys.argv[2])
OUT = sys.argv[3]
os.makedirs(OUT, exist_ok=True)

FOUND = []


def on_response(resp):
    u = resp.url
    if "streetviewpixels" in u or "/cbk?" in u or "photometa" in u or "GeoPhotoService" in u:
        FOUND.append(f"{resp.status} {u[:300]}")


URLS = [
    f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={LAT},{LNG}&heading=0&pitch=0",
    f"https://www.google.com/maps/@{LAT},{LNG},3a,75y,0h,90t/data=!3m1!1e1",
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--enable-unsafe-swiftshader", "--disable-blink-features=AutomationControlled",
              "--lang=en-US"],
    )
    ctx = browser.new_context(locale="en-US", user_agent=UA,
                              viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on("response", on_response)

    panoid = None
    for i, url in enumerate(URLS):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}] goto failed: {type(e).__name__}")
            continue
        page.wait_for_timeout(11000)
        print(f"[{i}] URL: {page.url[:220]}")
        print(f"[{i}] TITLE: {page.title()}")
        try:
            print(f"[{i}] TEXT: {page.inner_text('body')[:300].replace(chr(10), ' | ')}")
        except Exception:
            pass
        m = re.search(r"!1s([A-Za-z0-9_-]{20,})", page.url)
        if m:
            panoid = m.group(1)
        if not panoid:
            for line in FOUND:
                m2 = re.search(r"panoid=([A-Za-z0-9_-]{15,})", line)
                if m2:
                    panoid = m2.group(1)
                    break
        print(f"[{i}] PANOID: {panoid}")
        if panoid:
            break

    print("CAPTURED STREETVIEW REQUESTS:", len(FOUND))
    for line in FOUND[:6]:
        print("  ", line)

    if panoid:
        for yaw in (0, 90, 180, 270):
            u = (f"https://streetviewpixels-pa.googleapis.com/v1/thumbnail?panoid={panoid}"
                 f"&cb_client=maps_sv.tactile&w=1200&h=800&yaw={yaw}&pitch=0&thumbfov=80")
            r = ctx.request.get(u)
            body = r.body()
            path = os.path.join(OUT, f"probe_yaw{yaw}.jpg")
            open(path, "wb").write(body)
            print(f"yaw={yaw} status={r.status} bytes={len(body)} -> {path}")
    else:
        print("NO PANOID FOUND")

    browser.close()
