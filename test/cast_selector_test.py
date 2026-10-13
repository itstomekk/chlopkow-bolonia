"""Full-cast selector: every playable card fits the viewport without overlap, the name form never covers a card,
an older NPC (Kasia) is playable with her own pixel sheet, and the UI font renders Polish letters."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"
NPC_CAST = ("kasia", "grandpa", "halina", "kuba", "soltys", "michal", "mateusz", "patryk", "wesoly_swiat")
SIZES = [(1280, 720), (1920, 1080), (390, 844), (844, 390), (768, 1024)]


def ready(page):
    page.wait_for_function("window.__game && window.__game.openingStage === 'selector'", timeout=30000)
    page.wait_for_function("document.querySelector('#player-name-overlay')", timeout=30000)


def overlap(a, b):
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in SIZES:
        page = browser.new_page(viewport={"width": w, "height": h})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        ready(page)
        page.wait_for_timeout(300)
        cards = page.evaluate("""() => {
            const k = innerWidth / document.getElementById('game').width;
            return __game.playableCharacters.map(id => {
                const c = __game.characterButtonCenter(id);
                return { id, c };
            });
        }""")
        ids = [c["id"] for c in cards]
        for cid in NPC_CAST:
            assert cid in ids, (cid, ids)
        assert len(set(tuple(c["c"]) for c in cards)) == len(cards), "duplicate card centres"
        for c in cards:
            x, y = c["c"]
            assert 0 < x < w and 0 < y < h, (w, h, c)
        rects = page.evaluate("__game.characterButtonRects()")
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert not overlap(a, b), (w, h, a, b)
        form = page.locator("#player-name-overlay form").bounding_box()
        f = {"x": form["x"], "y": form["y"], "w": form["width"], "h": form["height"]}
        for a in rects:
            assert not overlap(a, f), (w, h, "form covers card", a, f)
        assert f["y"] + f["h"] <= h, (w, h, f)
        assert not errors, errors
        page.close()

    # The UI font has the Polish letters (no fallback glyphs) once loaded.
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(URL)
    ready(page)
    assert page.evaluate("document.fonts.check('20px PixelifySans', 'ĄĆĘŁŃÓŚŹŻąćęłńóśźż')")

    # Play as KASIA: the hero uses her own pixel walk sheet.
    page.mouse.click(*page.evaluate("__game.characterButtonCenter('kasia')"))
    assert page.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == "kasia"
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "kasia"
    assert page.evaluate("__game.playerSheetName") == "kasia_sheet.png"
    browser.close()
    print(f"Cast selector passed: {len(ids)} cards in {len(SIZES)} viewports, no overlaps, form clear, Polish font, KASIA playable")
