"""
Regression coverage for the presentation, naming, wildlife and menu changes.

NOTE: the earlier pre-existing '#arek-chat-launch' abort (the full flow clicked the
launch chip while the panel was already open by default) was fixed in A06 together
with the transparent right-side chat; the full flow passes now. The A01 direction-sign
regression still runs standalone via ``python test/presentation_changes_test.py --guard``.
"""
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
# A01: the suite convention is ARK_URL (see test/run_all.py); CHLOPKOW_URL stays as a legacy fallback.
URL = os.environ.get("ARK_URL") or os.environ.get("CHLOPKOW_URL", "http://127.0.0.1:8765/index.html")


def start(page, name="ZOSIA"):
    page.goto(URL + "?debug=1")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("Enter")
    page.locator("#player-name-input").fill(name)
    page.keyboard.press("Enter")
    page.wait_for_function("window.__game && window.__game.scene === 'play'")


# A01 guard: direction signs must be drawn only on their own map edge.
# "← DUŃCY" belongs to the west (map) edge, "WIELKIE KSIĘSTWO LITEWSKIE →" to the east edge.
SIGN_LEFT = "\u2190 DU\u0143CY"
SIGN_RIGHT = "WIELKIE KSI\u0118STWO LITEWSKIE \u2192"

# Records every frame in which the game actually fills one of the two direction labels onto
# the canvas (exact string + alpha at draw time). game.js wraps ctx.fillText on its own
# context for the 'Ć' glyph and captures the prototype method at startup; init scripts run
# before page scripts, so the patched prototype is what that wrapper funnels through.
SIGN_TRACER = """
(() => {
  window.__signDraw = [];
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, maxWidth) {
    const t = String(text);
    if (t === %(left)r || t === %(right)r) {
      window.__signDraw.push({ text: t, alpha: this.globalAlpha, x: +x, y: +y });
    }
    return orig.apply(this, arguments);
  };
})();
""" % {"left": SIGN_LEFT, "right": SIGN_RIGHT}


def sign_edge_points(page):
    """Walkable hero spots near both map edges, away from them and mid-map (per viewport)."""
    return page.evaluate("""() => {
        const g = window.__game, W = g.MAP.w, H = g.MAP.h;
        const scan = (x0, x1) => {
            for (let x = x0; x <= x1; x += 3)
                for (let y = 200; y < H - 200; y += 6)
                    if (!g.blocked(x, y)) return [x, y];
            return null;
        };
        return {
            west: scan(8, 60) || [10, Math.round(H / 2)],
            westAway: scan(700, 1100) || [900, Math.round(H / 2)],
            mid: scan(Math.round(W / 2) - 80, Math.round(W / 2) + 80) || [Math.round(W / 2), Math.round(H / 2)],
            eastAway: scan(W - 1100, W - 700) || [W - 900, Math.round(H / 2)],
            east: scan(W - 60, W - 8) || [W - 10, Math.round(H / 2)],
        };
    }""")


def snap_hero(page, pt, settle_ms=1200):
    """Teleport the hero (the camera lerps to it) and record every sign-draw frame since."""
    page.evaluate("""([x, y]) => {
        const g = window.__game;
        g.showMap = false;
        g.P.x = x; g.P.y = y; g.P.air = false; g.P.z = 0;
        window.__signDraw.length = 0;
    }""", pt)
    page.wait_for_timeout(settle_ms)
    return page.evaluate("() => ({ vis: window.__game.directionSignVisibility, drawn: window.__signDraw })")


def assert_signs_clear(page, wait_ms=150):
    page.evaluate("() => { window.__signDraw.length = 0; }")
    page.wait_for_timeout(wait_ms)
    leftovers = page.evaluate("() => window.__signDraw")
    assert not leftovers, f"stale direction label after the camera settled: {leftovers[-3:]}"


def check_sign_edge(page, pt, side, settle_ms=1200):
    """At a true map edge exactly one label is drawn with real opacity; the opposite one never appears."""
    snap = snap_hero(page, pt, settle_ms)
    texts = {d["text"] for d in snap["drawn"]}
    if side == "west":
        assert SIGN_RIGHT not in texts, f"east label visible at the west edge: {snap['drawn'][-3:]}"
        assert any(d["text"] == SIGN_LEFT and d["alpha"] >= 0.5 for d in snap["drawn"]), \
            f"west label never drawn at the west edge: {snap['drawn'][-3:]}"
        assert snap["vis"]["left"] >= 0.9 and snap["vis"]["right"] <= 0.02, snap["vis"]
    else:
        assert SIGN_LEFT not in texts, f"west label visible at the east edge: {snap['drawn'][-3:]}"
        assert any(d["text"] == SIGN_RIGHT and d["alpha"] >= 0.5 for d in snap["drawn"]), \
            f"east label never drawn at the east edge: {snap['drawn'][-3:]}"
        assert snap["vis"]["right"] >= 0.9 and snap["vis"]["left"] <= 0.02, snap["vis"]


def check_sign_away(page, pt, never, settle_ms=1200):
    """Away from every edge: semantic visibility is zero and no label remains after settling."""
    snap = snap_hero(page, pt, settle_ms)
    texts = {d["text"] for d in snap["drawn"]}
    for label in never:
        assert label not in texts, f"wrong-side label drawn at {pt}: {snap['drawn'][-3:]}"
    assert snap["vis"]["left"] <= 0.02 and snap["vis"]["right"] <= 0.02, snap["vis"]
    assert_signs_clear(page)


def direction_signs_guard(browser, viewport):
    """A01 regression: west/east sign semantics at one viewport in a fresh isolated context."""
    page = browser.new_page(viewport=viewport)
    page.add_init_script(SIGN_TRACER)
    start(page)
    assert page.evaluate("__game.directionSigns") == {"left": SIGN_LEFT, "right": SIGN_RIGHT}, \
        "direction sign strings changed"

    pts = sign_edge_points(page)
    check_sign_edge(page, pts["west"], "west")
    check_sign_away(page, pts["westAway"], [SIGN_RIGHT])      # walked away from the west edge
    check_sign_away(page, pts["mid"], [SIGN_LEFT, SIGN_RIGHT])  # middle of the map: nothing
    check_sign_away(page, pts["eastAway"], [SIGN_LEFT])       # walked away from the east edge
    check_sign_edge(page, pts["east"], "east")

    # M-map open at the west edge: the render gate (!showMap) must hide both labels…
    page.evaluate("""([x, y]) => {
        const g = window.__game;
        g.showMap = false; g.P.x = x; g.P.y = y; g.P.air = false; g.P.z = 0;
        window.__signDraw.length = 0;
    }""", pts["west"])
    page.wait_for_timeout(1200)
    page.evaluate("() => { window.__signDraw.length = 0; window.__game.showMap = true; }")
    page.wait_for_timeout(300)
    assert page.evaluate("() => window.__signDraw") == [], "direction label drawn while the M-map is open"
    # …and closing it brings only the correct label straight back.
    page.evaluate("() => { window.__signDraw.length = 0; window.__game.showMap = false; }")
    page.wait_for_timeout(300)
    after = page.evaluate("() => window.__signDraw")
    assert SIGN_RIGHT not in {d["text"] for d in after}, f"east label after closing the map at the west edge: {after[-3:]}"
    assert any(d["text"] == SIGN_LEFT and d["alpha"] >= 0.5 for d in after), \
        f"west label missing after closing the map: {after[-3:]}"
    print(f"direction sign edges OK @ {viewport['width']}x{viewport['height']}")
    page.close()


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
        # A06: the chat is a transparent right-side overlay, open by default for a fresh
        # visitor. The old flow clicked the launch button while the panel was already open
        # (the chip is display:none then), so it aborted with "element is not visible".
        # Correct sequence: verify the open transparent panel, minimise, reopen via the chip.
        assert page.locator("#arek-chat-panel").is_visible(), "chat must be open by default"
        assert page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).backgroundColor") in ("rgba(0, 0, 0, 0)", "transparent")
        assert page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).borderWidth") == "0px"
        page.locator("#arek-chat-close").click()
        assert page.locator("#arek-chat-launch").is_visible(), "launch chip must appear when minimised"
        page.locator("#arek-chat-launch").click()
        assert page.locator("#arek-chat-panel").is_visible(), "launch chip must reopen the chat"
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
        direction_signs_guard(browser, {"width": 1280, "height": 720})
        direction_signs_guard(browser, {"width": 390, "height": 844})
        browser.close()
    print("presentation changes: PASS")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--guard":
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            direction_signs_guard(browser, {"width": 1280, "height": 720})
            direction_signs_guard(browser, {"width": 390, "height": 844})
            browser.close()
        print("presentation changes: A01 direction-sign guard PASS")
    else:
        main()
