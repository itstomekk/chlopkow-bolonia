"""Frodo remains with Arek during ordinary exploration."""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.add_init_script("""
        window.__frodoDraws = 0;
        const drawImage = CanvasRenderingContext2D.prototype.drawImage;
        CanvasRenderingContext2D.prototype.drawImage = function (image, ...args) {
            if (image && image.src && image.src.includes('/img/frodo.png')) window.__frodoDraws++;
            return drawImage.call(this, image, ...args);
        };
    """)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8765/index.html")
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("KeyN")
    page.wait_for_function("__game.scene === 'play'")

    initial = page.evaluate("__game.FRODO && [__game.FRODO.x, __game.FRODO.y]")
    assert initial, "Frodo must be initialized when a new game starts"
    page.wait_for_function("window.__frodoDraws > 0")
    page.keyboard.down("ArrowRight")
    time.sleep(1.0)
    page.keyboard.up("ArrowRight")
    time.sleep(1.0)
    result = page.evaluate("({dog:[__game.FRODO.x,__game.FRODO.y], arek:[__game.P.x,__game.P.y]})")
    moved = ((result["dog"][0] - initial[0]) ** 2 + (result["dog"][1] - initial[1]) ** 2) ** .5
    gap = ((result["dog"][0] - result["arek"][0]) ** 2 + (result["dog"][1] - result["arek"][1]) ** 2) ** .5
    assert moved > 5, f"Frodo should move with Arek; moved {moved:.1f} map pixels"
    assert gap < 100, f"Frodo should stay nearby; distance is {gap:.1f} map pixels"
    page.evaluate("__game.enterChurch()")
    page.wait_for_function("__game.room")
    room_gap = page.evaluate("Math.hypot(__game.FRODO.x-__game.P.x,__game.FRODO.y-__game.P.y)")
    assert room_gap < 100, f"Frodo should enter the church with Arek; distance is {room_gap:.1f} map pixels"
    assert not errors, f"Browser errors: {errors}"
    print(f"Frodo follow check passed: moved {moved:.1f}px, outdoor gap {gap:.1f}px, church gap {room_gap:.1f}px")
    browser.close()
