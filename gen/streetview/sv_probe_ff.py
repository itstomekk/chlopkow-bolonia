"""Firefox variant of gen/streetview/sv_probe.py: find pano ids near coordinates (no frames saved).
Usage: python probe_ff.py lat,lng [lat,lng ...]  -> prints panoid + final URL per point."""
import re, sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.firefox.launch(headless=True)
    ctx = b.new_context(locale="en-US", viewport={"width": 1280, "height": 800})
    for spec in sys.argv[1:]:
        lat, lng = spec.split(",")
        page = ctx.new_page()
        found = []
        page.on("response", lambda r: found.append(r.url) if "panoid=" in r.url else None)
        try:
            page.goto(f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lng}&heading=0&pitch=0",
                      wait_until="domcontentloaded", timeout=60000)
            for _ in range(8):
                page.wait_for_timeout(2500)
                if re.search(r"!1s([A-Za-z0-9_-]{20,})", page.url): break
                try:
                    btn = page.get_by_role("button", name=re.compile("Accept all|Reject all", re.I))
                    if btn.count(): btn.first.click()
                except Exception:
                    pass
        except Exception as e:
            print(spec, "goto failed", type(e).__name__); page.close(); continue
        m = re.search(r"!1s([A-Za-z0-9_-]{20,})", page.url)
        pid = m.group(1) if m else None
        if not pid:
            for u in found:
                m2 = re.search(r"panoid=([A-Za-z0-9_-]{15,})", u)
                if m2: pid = m2.group(1); break
        at = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", page.url)
        print(spec, "PANOID", pid, "AT", at.groups() if at else None, flush=True)
        page.close()
    b.close()
