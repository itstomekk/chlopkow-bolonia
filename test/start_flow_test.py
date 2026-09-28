"""Fresh-game name entry, random reachable spawn, and backwards-compatible resume."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"

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

    # N opens a name prompt, and blank input cannot launch a fresh game.
    page.keyboard.press("KeyN")
    prompt = page.locator("#player-name-overlay")
    assert prompt.is_visible(), "new game must request a player name"
    page.locator("#player-name-input").fill("   ")
    page.locator("#player-name-submit").click()
    assert page.evaluate("__game.scene") == "title", "blank names must not start the game"

    # Untrusted markup/control characters are removed and the name is length-limited.
    dirty_name = " Łukasz <script>alert(1)</script> " + "x" * 40
    page.locator("#player-name-input").fill(dirty_name)
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    name = page.evaluate("__game.Q.playerName")
    assert name == "Łukasz scriptalert1s", name
    assert len(name) <= 20, name
    saved = page.evaluate(f"JSON.parse(localStorage.getItem('{SAVE_KEY}'))")
    assert saved["Q"]["playerName"] == name, saved

    # Spawn is clear of collision and belongs to the same spawn-connected walkable component.
    first_spawn = page.evaluate("[__game.P.x, __game.P.y]")
    assert page.evaluate("p => !__game.blocked(p[0], p[1])", first_spawn), first_spawn
    assert page.evaluate("p => __game.isSpawnReachable(p[0], p[1])", first_spawn), first_spawn

    # Continue (Enter) restores exact position and name without asking again.
    page.evaluate("__game.P.x += 37; __game.P.y += 19; ARK.save()")
    expected_position = page.evaluate("[__game.P.x, __game.P.y]")
    page.reload()
    page.wait_for_function("window.__game")
    assert page.evaluate("__game.scene") == "title"
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    assert not page.locator("#player-name-overlay").count(), "resume must not prompt"
    assert page.evaluate("[__game.P.x, __game.P.y]") == expected_position
    assert page.evaluate("__game.Q.playerName") == name

    # A legacy save without playerName still resumes, preserving progress and coordinates.
    legacy = {"Q": {"kasia": 1, "apples": [0]}, "x": 801, "y": 903}
    page.evaluate("s => localStorage.setItem('" + SAVE_KEY + "', JSON.stringify(s))", legacy)
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("[__game.P.x, __game.P.y]") == [801, 903]
    assert page.evaluate("__game.Q.kasia === 1 && __game.Q.apples[0] === 0")
    assert not page.locator("#player-name-overlay").count()

    # NEW GAME with an existing save still waits for the name; Enter submits the form.
    page.evaluate("__game.scene = 'title'")
    page.keyboard.press("KeyN")
    assert page.locator("#player-name-input").is_visible()
    page.locator("#player-name-input").fill("Again")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.Q.playerName") == "Again"
    second_spawn = page.evaluate("[__game.P.x, __game.P.y]")
    assert second_spawn != first_spawn, (first_spawn, second_spawn)
    assert page.evaluate("p => !__game.blocked(p[0], p[1]) && __game.isSpawnReachable(p[0], p[1])", second_spawn)

    # Explicit debug coordinates remain authoritative for a fresh game.
    debug = browser.new_page(viewport={"width": 1280, "height": 720})
    debug.goto(URL + "?x=1243&y=901")
    debug.wait_for_function("window.__game")
    debug.keyboard.press("KeyN")
    debug.locator("#player-name-input").fill("Tester")
    debug.locator("#player-name-submit").click()
    debug.wait_for_function("__game.scene === 'play'")
    assert debug.evaluate("[__game.P.x, __game.P.y]") == [1243, 901]

    # On a touch-sized screen, tapping the title also opens the same usable prompt.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    mobile.wait_for_function("window.__game")
    mobile.touchscreen.tap(195, 422)
    assert mobile.locator("#player-name-input").is_visible()
    mobile.locator("#player-name-input").fill("Mobile")
    mobile.locator("#player-name-submit").tap()
    mobile.wait_for_function("__game.scene === 'play'")
    assert mobile.evaluate("__game.Q.playerName") == "Mobile"

    assert not errors, errors
    print("Start flow passed: name prompt/sanitization/save, resume and legacy save, reachable random spawn, debug coordinates, mobile input")
    browser.close()
