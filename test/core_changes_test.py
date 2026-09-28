"""Focused smoke test for input, randomized NPC placement, saving, and the big map."""
import os
import time
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")

    first = page.evaluate("__game.ITEMS.npcs.filter(n => !n.secret).map(n => [n.id, n.x, n.y])")
    saved = page.evaluate("JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).npcs")
    assert saved == [{"id": n[0], "x": n[1], "y": n[2]} for n in first]

    page.reload()
    page.wait_for_function("window.__game")
    restored = page.evaluate("__game.ITEMS.npcs.filter(n => !n.secret).map(n => [n.id, n.x, n.y])")
    assert restored == first, (first, restored)

    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    second = page.evaluate("__game.ITEMS.npcs.filter(n => !n.secret).map(n => [n.id, n.x, n.y])")
    assert second != first, "N must sample a new NPC layout"

    page.mouse.click(900, 350)
    assert page.evaluate("__game.clickTarget.active"), "desktop click should create a move target"
    page.keyboard.press("KeyM")
    before = page.evaluate("[__game.P.x, __game.P.y]")
    page.mouse.click(640, 360)
    after = page.evaluate("[__game.P.x, __game.P.y]")
    cursor = page.evaluate("({seen: __game.mapCursor.seen, x: __game.mapCursor.x, y: __game.mapCursor.y})")
    assert after == before and cursor["seen"], (before, after, cursor)
    assert page.evaluate("__game.mapPlaceName(2096, 3696)") == "WIATRAK KOŹLAK"

    time.sleep(0.2)
    assert not errors, errors
    print("Core changes passed: NPC layout randomizes and persists, mouse movement and map cursor are isolated")
    browser.close()
