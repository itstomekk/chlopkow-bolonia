"""Regression coverage for the presentation, naming, wildlife and menu changes."""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("CHLOPKOW_URL", "http://127.0.0.1:8765/index.html")


def start(page, name="ZOSIA"):
    page.goto(URL + "?debug=1")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("Enter")
    page.locator("#player-name-input").fill(name)
    page.keyboard.press("Enter")
    page.wait_for_function("window.__game && window.__game.scene === 'play'")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        start(page)

        assert page.evaluate("__game.playerName") == "ZOSIA"
        assert page.evaluate("__game.directionSigns") == {
            "left": "← DUŃCY",
            "right": "WIELKIE KSIĘSTWO LITEWSKIE →",
        }
        assert page.evaluate("__game.mushroomPalette.white") is True
        assert page.evaluate("__game.hudCountersSingleLine") is True

        # Escape returns to the title menu; N edits the saved hero name without wiping the save.
        page.keyboard.press("Escape")
        page.wait_for_function("__game.scene === 'title'")
        page.keyboard.press("KeyN")
        page.locator("#player-name-input").fill("OLA")
        page.keyboard.press("Enter")
        page.wait_for_function("__game.scene === 'title'")
        assert page.evaluate("__game.playerName") == "OLA"

        # Chat has one message line and uses the hero name, not an editable nickname field.
        assert page.locator("#arek-chat-nickname").count() == 0
        assert page.locator("#arek-chat-text").count() == 1
        assert page.locator("#arek-chat-text").evaluate("e => e.tagName") == "INPUT"
        assert page.evaluate("__arekGlobalChat.playerName()") == "OLA"
        page.locator("#arek-chat-launch").click()
        assert page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).backgroundColor") in ("rgba(0, 0, 0, 0)", "transparent")
        assert page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).borderWidth") == "0px"
        page.locator("#arek-chat-close").click()

        # Wildlife policy is terrain-aware: no chickens in the forest.
        page.locator("#game").click(position={"x": 1100, "y": 650})
        page.wait_for_function("__game.scene === 'play'")
        page.wait_for_timeout(400)
        animals = page.evaluate("__worldLife.animals.map(a => ({kind:a.kind, terrain:__game.terrainAt(a.x,a.y)}))")
        assert animals
        assert not any(a["kind"] == "chicken" and a["terrain"] == "forest" for a in animals)
        assert any(a["kind"] == "boar" and a["terrain"] == "forest" for a in animals)
        assert any(a["kind"] == "mouse" and a["terrain"] in ("field", "forest") for a in animals)
        assert any(a["kind"] == "hare" and a["terrain"] in ("field", "grass") for a in animals)
        forest_tree = page.evaluate("""(() => {
            for (let y = 100; y < __game.MAP.h; y += 24)
                for (let x = 100; x < __game.MAP.w; x += 24)
                    if (__game.terrainAt(x, y) === 'forest' && __game.blocked(x, y)) return [x, y];
            return null;
        })()""")
        assert forest_tree is not None
        browser.close()
    print("presentation changes: PASS")


if __name__ == "__main__":
    main()
