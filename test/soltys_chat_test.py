"""Regression test for the church Sołtys art and persistent default-open global chat."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
CHAT_MINIMIZED_KEY = "arek-chlopkowie-chat-minimized-v1"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(URL)
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.__arekGlobalChat")

    assert page.locator("#arek-chat-panel").is_visible(), "global chat is not open for a fresh visitor"
    assert page.evaluate(f"localStorage.getItem('{CHAT_MINIMIZED_KEY}')") is None
    assert page.evaluate("document.activeElement !== document.querySelector('#arek-chat-text')"), "default-open chat stole keyboard focus"

    # Starting the game with the visible chat open proves it does not consume game keys.
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")

    assert page.evaluate("__game.enterChurch instanceof Function"), "church scene entry hook is unavailable"
    page.evaluate("__game.enterChurch()")
    page.wait_for_function("__game.room !== null && __game.room !== undefined")
    before = page.evaluate("[__game.P.x, __game.P.y]")
    page.locator("#arek-chat-text").focus()
    page.keyboard.press("ArrowUp")
    page.wait_for_timeout(250)
    after = page.evaluate("[__game.P.x, __game.P.y]")
    assert after == before, f"focused chat input leaked a game movement key: {before} -> {after}"
    loaded = page.evaluate("new Promise(resolve => { const img = new Image(); img.onload = () => resolve(img.naturalWidth > 0); img.onerror = () => resolve(false); img.src = 'img/church/soltys.png'; })")
    assert loaded, "docs/img/church/soltys.png failed to load"
    assert page.evaluate("window.CHURCH_ART.soltys && window.CHURCH_ART.soltys.naturalWidth > 0"), "church did not load the Sołtys artwork"
    page.screenshot(path="C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/soltys-church.png")

    # the panel steps aside while a dialogue box is open (e.g. the Sołtys greeting in the church); wait for it to return
    try:
        page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=10000)
        page.locator("#arek-chat-close").click()
    except Exception:
        page.evaluate("window.__arekGlobalChat.close()")
    assert not page.locator("#arek-chat-panel").is_visible(), "chat did not minimise"
    assert page.evaluate(f"localStorage.getItem('{CHAT_MINIMIZED_KEY}')") == "1"
    page.reload()
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    assert not page.locator("#arek-chat-panel").is_visible(), "minimised preference did not survive reload"

    browser.close()
    print("PASS: fresh chat open, game keys work, minimised state persists, church scene and Sołtys art load")
