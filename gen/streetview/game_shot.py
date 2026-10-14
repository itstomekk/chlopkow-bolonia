"""In-game screenshot(s) at map points. Usage: game_shot.py URL out_prefix x,y [x,y ...]"""
import sys, time
from playwright.sync_api import sync_playwright

url, prefix, pts = sys.argv[1], sys.argv[2], [tuple(map(int, a.split(","))) for a in sys.argv[3:]]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(url); pg.wait_for_function("typeof window.__game !== 'undefined'", timeout=90000)
    pg.evaluate("localStorage.clear()"); pg.reload(wait_until="load")
    pg.wait_for_function("typeof window.__game !== 'undefined'", timeout=90000)
    pg.keyboard.press("KeyN")
    pg.wait_for_function("!!document.querySelector('#player-name-input')", timeout=15000)
    pg.locator("#player-name-input").fill("Test"); pg.locator("#player-name-submit").click()
    pg.wait_for_function("window.__game.scene === 'play'", timeout=30000)
    time.sleep(1)
    for i, (x, y) in enumerate(pts):
        pg.evaluate(f"window.ARK.teleport({x},{y})"); time.sleep(1.5)
        pg.screenshot(path=f"{prefix}_{i + 1}.png")
    print("errors", errs[:5])
    b.close()
