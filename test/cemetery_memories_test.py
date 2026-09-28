"""Win-screen cemetery archive reveals all three generated memories in order."""
import os
import time
from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("""
        window.__memoryDraws = [];
        const original = CanvasRenderingContext2D.prototype.drawImage;
        CanvasRenderingContext2D.prototype.drawImage = function (image, ...args) {
            if (image && image.src && image.src.includes('/img/memories/')) window.__memoryDraws.push(image.src);
            return original.call(this, image, ...args);
        };
    """)
    page.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html"))
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")

    page.evaluate("""(() => {
      const g = __game;
      g.Q.kasia = g.Q.damian = g.Q.marcin = 2;
      g.Q.grandpa = 1;
      const n = g.ITEMS.npcs.find(v => v.id === 'grandpa');
      for (let r = 20; r < 42; r += 2) for (let a = 0; a < 6.28; a += .2) {
        const x = n.x + Math.cos(a) * r, y = n.y + Math.sin(a) * r;
        if (Math.hypot(x - n.x, y - n.y) < 42 && !g.blocked(x, y)) { g.P.x = x; g.P.y = y; return; }
      }
      throw new Error('No reachable interaction point by Grandpa');
    })()""")
    for _ in range(8):
        if page.evaluate("__game.scene === 'end'"):
            break
        page.keyboard.press("KeyE")
        time.sleep(.15)
    page.wait_for_function("__game.scene === 'end'", timeout=5000)
    assert page.evaluate("__game.memoryCount") == 3
    assert page.evaluate("__game.memoryIndex") == 0
    time.sleep(.2)
    page.screenshot(path="test/cemetery_memory_1.png")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.memoryIndex === 1")
    time.sleep(.2)
    page.screenshot(path="test/cemetery_memory_2.png")
    page.keyboard.press("Space")
    page.wait_for_function("__game.memoryIndex === 2")
    time.sleep(.2)
    page.screenshot(path="test/cemetery_memory_3.png")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")

    drawn = page.evaluate("[...new Set(__memoryDraws.map(url => url.split('/').pop()))]")
    assert sorted(drawn) == ['memorial.png', 'procession.png', 'wooden_cross.png'], drawn
    assert not errors, f"Browser errors: {errors}"

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mobile_errors = []
    mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
    mobile.goto(os.environ.get("ARK_URL", os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")) + ("&" if "?" in os.environ.get("ARK_URL", os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")) else "?") + "lang=en")
    mobile.wait_for_function("window.__game", timeout=30000)
    mobile.keyboard.press("KeyN")
    mobile.locator("#player-name-input").fill("Test"); mobile.keyboard.press("Enter")
    mobile.wait_for_function("__game.scene === 'play'")
    mobile.evaluate("__game.scene = 'end'")
    mobile.screenshot(path="test/cemetery_memory_mobile.png")
    for expected in (1, 2):
        mobile.touchscreen.tap(195, 422)
        mobile.wait_for_function(f"__game.memoryIndex === {expected}")
        mobile.screenshot(path=f"test/cemetery_memory_mobile_{expected + 1}.png")
    mobile.touchscreen.tap(195, 422)
    mobile.wait_for_function("__game.scene === 'play'")
    assert not mobile_errors, f"Mobile browser errors: {mobile_errors}"
    print(f"Cemetery archive passed: {drawn}; desktop win/replay and mobile tap flows; no browser errors")
    browser.close()
