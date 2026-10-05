"""Opening reveal, integrated name/character controls, crest phase and reduced motion."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8798/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game")

    page.wait_for_function("__game.openingStage === 'selector'", timeout=8000)
    name = page.locator("#player-name-input")
    assert name.is_visible(), "player name must be visible on the opening screen"
    assert page.locator("#player-name-submit").is_visible()
    assert page.evaluate("__game.scene") == "title"

    # The existing selector remains usable while the background changes to the emblem.
    center = page.evaluate("__game.characterButtonCenter('damian')")
    page.mouse.click(*center)
    assert page.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "damian"
    page.wait_for_function("__game.openingStage === 'emblem'", timeout=8000)
    assert name.is_visible(), "the name field must remain available after the crest appears"
    assert page.locator("#player-name-submit").is_visible()
    assert page.evaluate("__game.scene") == "title", "the timed logo must never auto-start the game"

    name.fill("Tomek")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.Q.playerName") == "Tomek"
    assert page.evaluate("__game.playerCharacter") == "damian"
    assert not errors, errors

    reduced = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    reduced.emulate_media(reduced_motion="reduce")
    reduced_errors = []
    reduced.on("pageerror", lambda error: reduced_errors.append(str(error)))
    reduced.goto(URL)
    reduced.wait_for_function("window.__game")
    reduced.wait_for_function("__game.openingStage === 'emblem'", timeout=3000)
    assert reduced.locator("#player-name-input").is_visible()
    assert reduced.locator("#player-name-submit").is_visible()
    assert reduced.evaluate("__game.scene") == "title"
    assert not reduced_errors, reduced_errors

    browser.close()
    print("Brand opening flow: reveal, name/character selection, crest, no auto-start, reduced-motion/mobile passed")
