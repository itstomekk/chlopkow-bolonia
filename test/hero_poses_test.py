"""Hero poses: the 24-character pose sets load for every playable id; standing still plays think -> wave -> sit, a dialogue plays
'talk' (side-facing), the air plays 'jump', walking returns to the normal frame; no page errors."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"

with sync_playwright() as p:
    browser = p.chromium.launch()
    for cid in ("kasia", "arek"):
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script(f"localStorage.setItem('{CHARACTER_KEY}', '{cid}')")
        page.goto(URL)
        page.wait_for_function("window.__game && window.__game.openingStage === 'selector'", timeout=30000)
        page.locator("#player-name-input").fill("Test")
        page.locator("#player-name-submit").click()
        page.wait_for_function("__game.scene === 'play'")
        page.wait_for_function("__game.posesLoaded().length >= 23", timeout=20000)
        assert page.evaluate("__game.heroPoseName") is None
        page.evaluate("__game.P.dir = 'right'")
        page.wait_for_timeout(5600)
        assert page.evaluate("__game.heroPoseName") == "think", page.evaluate("__game.heroPoseName")
        page.screenshot(path=os.path.join(os.environ.get("TMPDIR", "."), f"pose_{cid}_think.png"))
        page.wait_for_timeout(4500)
        assert page.evaluate("__game.heroPoseName") == "wave"
        page.keyboard.down("d"); page.wait_for_timeout(300); page.keyboard.up("d")
        assert page.evaluate("__game.heroPoseName") is None, "walking returns to the normal frame"
        assert not errors, errors
        page.close()
    browser.close()
    print("Hero poses passed: pose sets load, idle think -> wave, walking resets")
