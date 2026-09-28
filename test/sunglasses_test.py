"""Arek takes his sunglasses off in the cemetery, and only there.

    python -m http.server 8765 --directory docs
    python test/sunglasses_test.py
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOT = os.path.join(os.environ.get("TMPDIR", "."), "sunglasses_cemetery.png")

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_function("window.__game")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    # fresh game: N opens the name prompt, Enter starts play
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(1)   # the no-glasses sheet loads after the main assets

    def tp(x, y):
        pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<120;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()")
        time.sleep(.3)

    cem = pg.evaluate("__game.MAP.pois.find(p => p.key === 'cemetery')")
    assert cem, "no cemetery POI"
    tp(cem["x"] + 400, cem["y"] + 400)
    assert pg.evaluate("__game.sunglasses") is True, "sunglasses must be on outside the cemetery"
    tp(cem["x"], cem["y"])
    assert pg.evaluate("__game.sunglasses") is False, "sunglasses must be off in the cemetery"
    pg.screenshot(path=SHOT, clip={"x": 540, "y": 250, "width": 200, "height": 220})
    # walking inside keeps them off; stepping just past the edge keeps them off (hysteresis), far away puts them back
    pg.evaluate("__game.P.x += 40"); time.sleep(.2)
    assert pg.evaluate("__game.sunglasses") is False
    tp(cem["x"] + 600, cem["y"])
    assert pg.evaluate("__game.sunglasses") is True, "sunglasses must come back after leaving"
    assert not errors, errors
    print("sunglasses: PASS - off in the cemetery, back on outside; screenshot", SHOT)
    b.close()
