"""Prototype Arek 8-direction sheet and diagonal input smoke test."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Osiem")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")

    assert page.evaluate("__game.playerSheetName") == "arek_sheet_8dir.png"
    directions = page.evaluate("fetch('img/arek_sheet_8dir.json').then(r => r.json()).then(x => x.directions)")
    assert directions == ["down", "down_right", "right", "up_right", "up", "up_left", "left", "down_left"]

    page.keyboard.down("ArrowRight")
    page.keyboard.down("ArrowDown")
    page.wait_for_timeout(180)
    page.keyboard.up("ArrowRight")
    page.keyboard.up("ArrowDown")
    assert page.evaluate("__game.P.dir") == "down_right"
    assert not errors, errors
    browser.close()
    print("8-direction Arek passed: asset metadata, diagonal input, runtime sheet")
