"""Capture the Street View panorama graph for the Chlopkow area.

Loads Street View at a known-covered point and stores every photometa response
body (the pano-graph payload the Maps client uses), then reports which panoids
and coordinates are reachable.

Usage: python sv_graph.py <outdir> <lat> <lng>
"""
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

OUT = sys.argv[1]
LAT, LNG = sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

PANOID_RE = re.compile(r"\b([A-Za-z0-9_-]{22})\b")


def looks_like_panoid(tok):
    if tok.startswith("CIHM"):
        return False
    return any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)


bodies = []


def handle(resp):
    u = resp.url
    if "photometa" not in u:
        return
    try:
        if resp.status == 200:
            bodies.append((u, resp.text()))
    except Exception:  # noqa: BLE001
        pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
    ctx = browser.new_context(locale="en-US", user_agent=UA,
                             viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on("response", handle)
    url = (f"https://www.google.com/maps/@?api=1&map_action=pano"
           f"&viewpoint={LAT},{LNG}&heading=0&pitch=0&fov=80")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(10000)
    # pan around a bit so the client requests deeper graph pages
    for key in ("ArrowRight", "ArrowRight", "ArrowUp"):
        page.keyboard.press(key)
        page.wait_for_timeout(3000)

    print("photometa bodies:", len(bodies))
    all_panoids = {}
    for i, (u, text) in enumerate(bodies):
        with open(os.path.join(OUT, f"photometa_{i}.txt"), "w", encoding="utf-8") as fh:
            fh.write(u + "\n\n" + text)
        toks = [t for t in PANOID_RE.findall(text) if looks_like_panoid(t)]
        for t in toks:
            all_panoids[t] = all_panoids.get(t, 0) + 1
        print(f"  [{i}] {len(text):7d} chars, tokens={len(toks)} url={u[:90]}")
    print("unique panoid-like tokens:", len(all_panoids))
    for t, c in list(all_panoids.items())[:15]:
        print(f"   {t} x{c}")

    with open(os.path.join(OUT, "panoids.json"), "w", encoding="utf-8") as fh:
        json.dump(sorted(all_panoids), fh, indent=1)
    browser.close()
