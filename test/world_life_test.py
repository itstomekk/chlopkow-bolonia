"""Standalone browser test for docs/js/world-life.js.

The plugin is loaded after the normal page for isolation, then ark-ready is
redispatched. Production integration should load the script before game.js.
"""
import os
import sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.goto(URL)
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.cars.length === 2")
    page.keyboard.press("KeyN")

    facts = page.evaluate("""(() => {
      const g = __game, wl = __worldLife;
      const allValid = wl.cars.length === 2 && wl.cars.every(c => !g.blocked(c.x, c.y)) &&
        wl.animals.length === 8 && wl.animals.every(a => !g.blocked(a.x, a.y));
      const apart = wl.animals.every((a, i) => Math.hypot(a.x - g.P.x, a.y - g.P.y) >= 29 &&
        wl.animals.every((b, j) => i === j || Math.hypot(a.x - b.x, a.y - b.y) >= 23));
      const oldCars = wl.cars.map(c => `${c.x},${c.y}`).join('|');
      wl.resetCars();
      const reset = wl.cars.length === 2 && wl.cars.map(c => `${c.x},${c.y}`).join('|') !== oldCars;
      g.Q.apples = Array.from({length: 10}, (_, i) => i);
      g.Q.worldLife.spentApples = 0;
      wl.buyRide(0);
      const purchased = wl.rideSeconds === 15 && g.Q.worldLife.spentApples === 10 &&
        wl.balance() === 0 && g.Q.apples.length === 10;
      return {allValid, apart, reset, purchased};
    })()""")
    assert facts == {"allValid": True, "apart": True, "reset": True, "purchased": True}, facts
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.cars.length === 2")
    persisted = page.evaluate("[__game.Q.worldLife.spentApples, __worldLife.balance(), __game.Q.apples.length]")
    assert persisted == [10, 0, 10], persisted
    page.evaluate("__game.scene = 'title'")
    page.keyboard.press("KeyN")
    page.wait_for_function("__game.scene === 'play' && __worldLife.cars.length === 2")
    fresh = page.evaluate("[__game.Q.worldLife.spentApples, __game.Q.apples.length, __worldLife.cars.every(c => !__game.blocked(c.x, c.y))]")
    assert fresh == [0, 0, True], fresh
    assert not errors, errors
    print("world life: PASS", facts)
    browser.close()
