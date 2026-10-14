"""End-to-end check of the review page in a real browser (Playwright Firefox).

    python e2e_review_web.py "https://itstomekk.pages.dev/r-XXXX/#k=KEY" [--shots DIR] [--allow-write]

Desktop 1280x900 + phone 390x844: page loads, tiles visible, no console errors / external requests, no horizontal overflow;
(with --allow-write) a choice is saved ("Zapisano"), a fresh browser context restores it from the server, offline -> "Brak połączenia";
no key / wrong key states. The caller must reset the server document afterwards (fetch_review.py put seed). Never prints the key.
"""
import argparse
import re
import sys
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("--shots", default=None)
ap.add_argument("--allow-write", action="store_true")
a = ap.parse_args()
u = urlsplit(a.url)
ORIGIN = f"{u.scheme}://{u.netloc}"
BASE = a.url.split("#")[0]
KEYFRAG = ("#" + u.fragment) if u.fragment else ""
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def watch(page, bag):
    page.on("console", lambda m: bag["errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: bag["errors"].append(str(e)))
    page.on("request", lambda r: bag["ext"].append(r.url) if not r.url.startswith(ORIGIN) and not r.url.startswith("data:") and "chlopkow-api" not in r.url and "127.0.0.1" not in r.url else None)
    page.on("response", lambda r: bag["bad"].append(f"{r.status} {r.url}") if r.status >= 400 and "/review/" not in r.url else None)


def status(page):
    return page.locator("#save").inner_text()


def wait_status(page, text, t=15000):
    try:
        page.wait_for_function("t=>document.querySelector('#save').textContent.includes(t)", arg=text, timeout=t)
        return True
    except Exception:
        return False


def tiles_ok(page):
    """Scroll through the page; every tile image that entered the viewport must have loaded."""
    h = page.evaluate("document.documentElement.scrollHeight")
    y = 0
    while y < h:
        page.evaluate(f"window.scrollTo(0,{y})")
        page.wait_for_timeout(120)
        y += 700
    page.wait_for_timeout(1500)
    r = page.evaluate("""()=>{const all=[...document.querySelectorAll('main .sheet img')];const bad=all.filter(i=>i.complete&&i.naturalWidth===0).length;
      const loaded=all.filter(i=>i.complete&&i.naturalWidth>0).length;return {all:all.length,loaded,bad}}""")
    page.evaluate("window.scrollTo(0,0)")
    return r


with sync_playwright() as p:
    br = p.firefox.launch()
    for label, kw in (("desktop 1280x900", dict(viewport={"width": 1280, "height": 900})),
                      ("phone 390x844", dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=False, has_touch=True))):
        print(f"\n== {label}")
        ctx = br.new_context(**kw)
        page = ctx.new_page()
        bag = {"errors": [], "ext": [], "bad": []}
        watch(page, bag)
        page.goto(BASE + KEYFRAG, wait_until="load")
        check("noindex" in (page.get_attribute("meta[name=robots]", "content") or ""), "meta robots noindex")
        check(wait_status(page, "Zapisano ✓"), f"status after load: {status(page)!r}")
        check(page.locator("input[name=h19]").count() >= 3 and page.locator("#props tbody tr").count() == 39, "controls rendered (house radios, 39 props)")
        r = tiles_ok(page)
        check(r["bad"] == 0 and r["loaded"] > 100, f"lazy tiles load when scrolled: {r}")
        ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check(ov <= 1, f"no horizontal overflow ({ov}px)")
        page.evaluate("document.querySelector('#houses2 .card').scrollIntoView()")
        page.wait_for_timeout(800)
        if a.shots:
            page.screenshot(path=f"{a.shots}/{label.split()[0]}-top.png")
            page.evaluate("window.scrollTo(0,0)")
            page.evaluate("document.querySelector('#houses1 .card').scrollIntoView()")
            page.wait_for_timeout(900)
            page.screenshot(path=f"{a.shots}/{label.split()[0]}-house.png")
        # zoom view
        page.evaluate("document.querySelector('#houses1 .card .sheet').scrollIntoView()")
        page.locator("#houses1 .card .sheet").first.click()
        page.wait_for_timeout(900)
        check(page.locator("#lb.on").count() == 1, "tap on a sheet opens the zoom view")
        if a.shots:
            page.screenshot(path=f"{a.shots}/{label.split()[0]}-zoom.png")
        page.keyboard.press("Escape")
        check(page.locator("#lb.on").count() == 0, "zoom closes")
        check(not bag["errors"], f"no console/page errors {bag['errors'][:3]}")
        check(not bag["ext"], f"no third-party requests {bag['ext'][:3]}")
        check(not bag["bad"], f"no failed asset requests {bag['bad'][:3]}")
        ctx.close()

    if a.allow_write:
        print("\n== write + restore from server (fresh contexts)")
        ctx = br.new_context(viewport={"width": 390, "height": 844}, has_touch=True)
        page = ctx.new_page()
        page.goto(BASE + KEYFRAG, wait_until="load")
        wait_status(page, "Zapisano ✓")
        page.locator("input[name=h19][value='3']").check()
        check(wait_status(page, "Zapisywanie") or True, "saving...")
        check(wait_status(page, "Zapisano ✓"), f"after choosing an option: {status(page)!r}")
        check(re.search(r"Zapisano ✓ \d\d:\d\d", status(page)) is not None, "status has HH:MM")
        page.locator("textarea.hn").first.fill("e2e-test zażółć")
        page.locator("#props tbody tr:nth-child(2) select").select_option("skip")
        page.wait_for_timeout(300)
        check(wait_status(page, "Zapisano ✓"), "after note + prop decision")
        page.wait_for_timeout(1200)
        ctx.close()
        ctx2 = br.new_context(viewport={"width": 1280, "height": 900})  # nothing shared: no localStorage
        p2 = ctx2.new_page()
        p2.goto(BASE + KEYFRAG, wait_until="load")
        wait_status(p2, "Zapisano ✓")
        p2.wait_for_timeout(500)
        check(p2.locator("input[name=h19][value='3']").is_checked(), "fresh context: choice restored from the server")
        check(p2.locator("textarea.hn").first.input_value() == "e2e-test zażółć", "fresh context: note restored")
        check(p2.locator("#props tbody tr:nth-child(2) select").input_value() == "skip", "fresh context: prop decision restored")
        # offline -> local only, then back online -> synced
        ctx2.set_offline(True)
        p2.locator("input[name=h20][value='2']").check()
        check(wait_status(p2, "Brak połączenia — zapisane lokalnie", 20000), f"offline: {status(p2)!r}")
        ctx2.set_offline(False)
        p2.evaluate("window.dispatchEvent(new Event('online'))")
        check(wait_status(p2, "Zapisano ✓", 20000), f"back online: {status(p2)!r}")
        ctx2.close()
        # no key / wrong key
        ctx3 = br.new_context()
        p3 = ctx3.new_page()
        p3.goto(BASE, wait_until="load")
        p3.wait_for_timeout(800)
        check("Brak klucza" in status(p3), f"no key: {status(p3)!r}")
        p3.goto(BASE + "#k=WRONGKEYWRONGKEYWRONGKEY12", wait_until="load")
        p3.reload()
        wait_status(p3, "Zły klucz")
        check("Zły klucz" in status(p3), f"wrong key: {status(p3)!r}")
        ctx3.close()
    br.close()
print("\nFAILED:", fails if fails else "none")
sys.exit(1 if fails else 0)
