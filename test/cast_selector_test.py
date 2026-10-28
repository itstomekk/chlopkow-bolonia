"""Full-cast selector (23 cards; PATRYK is NPC-only): every card fits the viewport without overlap, Start + the Nostr
disclosure sit clear of the cards inside the viewport, the name input replaces the selected card label, an older NPC
(Kasia) is playable with her own pixel sheet, a stale stored 'patryk' falls back to Arek, and the UI font renders Polish letters."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"
NPC_CAST = ("kasia", "grandpa", "halina", "kuba", "soltys", "michal", "mateusz", "wesoly_swiat")
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
        assert "patryk" not in ids and len(ids) == 23, ids
        assert len(set(tuple(c["c"]) for c in cards)) == len(cards), "duplicate card centres"
        for c in cards:
            x, y = c["c"]
            assert 0 < x < w and 0 < y < h, (w, h, c)
        rects = page.evaluate("__game.characterButtonRects()")
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                assert not overlap(a, b), (w, h, a, b)
        parts = {}
        for key, sel in (("start", "#player-name-submit"), ("disclosure", "#player-name-disclosure"), ("input", "#player-name-input")):
            box = page.locator(sel).bounding_box()
            parts[key] = {"x": box["x"], "y": box["y"], "w": box["width"], "h": box["height"]}
        for key in ("start", "disclosure"):
            for a in rects:
                assert not overlap(a, parts[key]), (w, h, key, "covers card", a, parts[key])
            assert parts[key]["x"] >= 0 and parts[key]["x"] + parts[key]["w"] <= w, (w, h, key, parts[key])
            assert parts[key]["y"] >= 0 and parts[key]["y"] + parts[key]["h"] <= h, (w, h, key, parts[key])
        sel = next(r for r in rects if r["id"] == page.evaluate("__game.playerCharacter"))
        icx, icy = parts["input"]["x"] + parts["input"]["w"] / 2, parts["input"]["y"] + parts["input"]["h"] / 2
        assert sel["x"] <= icx <= sel["x"] + sel["w"] and sel["y"] <= icy <= sel["y"] + sel["h"] + 12, (w, h, "input must sit on the selected card", sel, parts["input"])
        assert not errors, errors
        page.close()

    # The UI font has the Polish letters (no fallback glyphs) once loaded.
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(URL)
    ready(page)
    assert page.evaluate("document.fonts.check('20px PixelifySans', 'ĄĆĘŁŃÓŚŹŻąćęłńóśźż')")

    # PATRYK left the selector: a stale stored choice falls back to Arek and is cleaned up.
    stale = browser.new_page(viewport={"width": 1280, "height": 720})
    stale.add_init_script(f"localStorage.setItem('{CHARACTER_KEY}', 'patryk')")
    stale.goto(URL)
    ready(stale)
    assert stale.evaluate("__game.playerCharacter") == "arek"
    assert stale.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == "arek"
    assert stale.locator("#player-name-input").get_attribute("placeholder") == "Arek"
    stale.close()

    # Every card has a default name: Arek/Marcin/... keep person casing, the rest use their selector label.
    expected = {"arek": "Arek", "marcin": "Marcin", "damian": "Damian", "edytka": "Edytka", "renik": "DJ Renik", "bercik": "BERCIK",
                "grandpa": "DZIADEK GIENEK", "halina": "BABCIA IRENKA", "michal": "BUKAŁA", "wesoly_swiat": "WESOŁYCH ŚWIĄT"}
    for cid in page.evaluate("__game.playableCharacters"):
        page.mouse.click(*page.evaluate("id => __game.characterButtonCenter(id)", cid))
        placeholder = page.locator("#player-name-input").get_attribute("placeholder")
        assert placeholder and page.evaluate("__game.playerCharacter") == cid, (cid, placeholder)
        if cid in expected:
            assert placeholder == expected[cid], (cid, placeholder)

    # Play as KASIA: the hero uses her own pixel walk sheet.
    page.mouse.click(*page.evaluate("__game.characterButtonCenter('kasia')"))
    assert page.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == "kasia"
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "kasia"
    assert page.evaluate("__game.playerSheetName") == "kasia_sheet.png"
    browser.close()
    print(f"Cast selector passed: {len(ids)} cards in {len(SIZES)} viewports, no overlaps, Start/disclosure clear and in view, PATRYK hidden (stale choice -> Arek), Polish font, KASIA playable")
