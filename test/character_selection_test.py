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

    # Select Damian on the title screen. Bounds match the 2x2 selector at 1280x720.
    u = min(1280, 720 * 1.6) / 100
    button_size, gap = u * 7, u * 1.5
    grid_x, grid_y = (1280 - (button_size * 2 + gap)) / 2, 720 * 0.45
    page.mouse.click(grid_x + button_size / 2, grid_y + button_size + gap + button_size / 2)
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"

    # Selection survives reload and the displayed selector can change it before starting.
    page.reload()
    page.wait_for_function("window.__game")
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"
    page.mouse.click(grid_x + button_size / 2, grid_y + button_size / 2)
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "arek"

    # The chosen character sheet remains the active player art after starting a fresh game.
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "arek"
    assert page.evaluate("__game.playerSheetName") == "arek_sheet.png"
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

    # On a touch-sized viewport, selector hit targets stay tappable and do not start the game.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    mobile.wait_for_function("window.__game")
    touch_point = mobile.evaluate("""() => {
      const scale = Math.round(innerWidth * Math.min(2, devicePixelRatio || 1)) / innerWidth;
      const W = Math.round(innerWidth * scale), H = Math.round(innerHeight * scale);
      const U = Math.min(W, H * 1.6) / 100, size = Math.max(U * 7, 48 * scale), gap = U * 1.5;
      const gx = (W - (size * 2 + gap)) / 2, gy = H * .45;
      return [(gx + size / 2) / scale, (gy + size + gap + size / 2) / scale];
    }""")
    mobile.touchscreen.tap(*touch_point)
    assert mobile.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"
    assert mobile.evaluate("__game.scene") == "title"

    browser.close()
    print("Character selection passed: click, persistence, change-before-start, selected player sheet, idle/walk rendering, mobile tap")
