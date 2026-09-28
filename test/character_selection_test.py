"""Character selection persists and controls the player sprite sheet."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"

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

    # Select Damian on the title screen, using the game's own selector geometry.
    center = lambda pg, cid: pg.evaluate(f"__game.characterButtonCenter('{cid}')")
    page.mouse.click(*center(page, "damian"))
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"

    # Selection survives reload and the displayed selector can change it before starting.
    page.reload()
    page.wait_for_function("window.__game")
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"
    page.mouse.click(*center(page, "arek"))
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "arek"

    # DJ Renik is selectable and his button sits fully above the bottom prompt strip.
    page.mouse.click(*center(page, "renik"))
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "renik"
    assert center(page, "renik")[1] + 50 < 720 - min(1280, 720 * 1.6) / 100 * 9.5, center(page, "renik")
    page.mouse.click(*center(page, "arek"))
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "arek"

    # The chosen character sheet remains the active player art after starting a fresh game.
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "arek"
    assert page.evaluate("__game.playerSheetName") == "arek_sheet_8dir.png"
    assert not errors, errors

    # A saved choice is loaded before init; non-Arek sprites idle and animate from walk rows.
    other = browser.new_page(viewport={"width": 1280, "height": 720})
    other_errors = []
    other.on("pageerror", lambda error: other_errors.append(str(error)))
    other.goto(URL)
    other.wait_for_function("window.__game")
    other.evaluate(f"localStorage.setItem('{CHARACTER_KEY}', 'marcin')")
    other.reload()
    other.wait_for_function("window.__game")
    other.keyboard.press("KeyN")
    other.locator("#player-name-input").fill("Marcin")
    other.locator("#player-name-submit").click()
    other.wait_for_function("__game.scene === 'play'")
    other.evaluate("__game.P.moving = true; __game.P.dir = 'down'; __game.P.step = 1")
    other.wait_for_timeout(100)
    assert other.evaluate("__game.playerCharacter") == "marcin"
    assert other.evaluate("__game.playerSheetName") == "marcin_sheet.png"
    assert not other_errors, other_errors

    # DJ Renik plays with his own walk sheet; his NPC twin is swapped to Arek's art (existing rule).
    other.evaluate(f"localStorage.clear(); localStorage.setItem('{CHARACTER_KEY}', 'renik')")
    other.reload()
    other.wait_for_function("window.__game")
    other.keyboard.press("KeyN")
    other.locator("#player-name-input").fill("Renik")
    other.locator("#player-name-submit").click()
    other.wait_for_function("__game.scene === 'play'")
    other.evaluate("__game.P.moving = true; __game.P.dir = 'down_right'; __game.P.step = 1")
    other.wait_for_timeout(100)
    assert other.evaluate("__game.playerCharacter") == "renik"
    assert other.evaluate("__game.playerSheetName") == "renik_sheet.png"
    assert not other_errors, other_errors

    # On a touch-sized viewport, selector hit targets stay tappable and do not start the game.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    mobile.wait_for_function("window.__game")
    mobile.touchscreen.tap(*center(mobile, "damian"))
    assert mobile.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"
    assert mobile.evaluate("__game.scene") == "title"
    mobile.touchscreen.tap(*center(mobile, "renik"))
    assert mobile.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "renik"
    assert mobile.evaluate("__game.scene") == "title"

    browser.close()
    print("Character selection passed: click, persistence, change-before-start, selected player sheet, idle/walk rendering, DJ Renik, mobile tap")
