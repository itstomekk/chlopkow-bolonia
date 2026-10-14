"""Regression test for church Sołtys art and always-visible in-play chat."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(URL)
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.__arekGlobalChat")

    # Chat is hidden on the title/name screens and shown in play.
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")

    assert page.locator("#arek-chat-panel").is_visible(), "in-play chat is not visible"
    assert page.evaluate("document.activeElement !== document.querySelector('#arek-chat-text')"), "default-open chat stole keyboard focus"

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

    # The chat stays in view during the Sołtys dialogue; no user minimization exists.
    page.evaluate("__game.talkTo('wesoly_swiat')")
    page.wait_for_timeout(250)
    assert page.locator("#arek-chat-panel").is_visible()
    assert page.locator("#arek-chat-launch, #arek-chat-close").count() == 0

    browser.close()
    print("PASS: in-play chat stays visible, game keys work, church scene and Sołtys art load")
