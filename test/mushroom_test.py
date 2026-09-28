"""Verify the fresh-save mushroom field, pickup persistence, and Kasia requirement."""
import os
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html"))
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game", timeout=30000)
    page.keyboard.press("Enter")
    page.locator("#player-name-input").fill("Mushroom test")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    time.sleep(.3)

    assert page.evaluate("__game.mushroomTotal") == 15
    assert page.evaluate("__game.Q.mushroomSpots.length") == 15
    assert page.evaluate("__game.Q.mushroomSpots.every(p => __game.isSpawnReachable(p.x, p.y) && ['grass', 'forest'].includes(__game.terrainAt(p.x, p.y)))")

    page.evaluate("__game.talkTo('kasia')")
    for _ in range(4):
        page.keyboard.press("Space")
        time.sleep(.05)
    for spot in page.evaluate("__game.Q.mushroomSpots")[:10]:
        page.evaluate("([x, y]) => { __game.P.x = x; __game.P.y = y; }", [spot["x"], spot["y"]])
        time.sleep(.12)
    assert page.evaluate("__game.mushroomCount()") == 10
    page.evaluate("__game.talkTo('kasia')")
    assert page.evaluate("__game.Q.kasia") == 2

    saved = page.evaluate("JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).Q.mushrooms.length")
    assert saved == 10
    assert not errors, errors
    print("mushrooms: PASS", page.evaluate("({total: __game.Q.mushroomSpots.length, collected: __game.mushroomCount(), kasia: __game.Q.kasia})"))
    browser.close()
