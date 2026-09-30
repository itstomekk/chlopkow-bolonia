"""P06+P04+P07: map HUD polish — attribution, sector label, clock fit.

Covers (against docs/js/game.js, TDD per card):
  P06 - the "© OPENSTREETMAP CONTRIBUTORS" attribution line is gone from the
        map HUD while the coordinate readout still paints.
  P04 - the coordinate readout shows the grid SECTOR (A5, B6 style) instead of
        raw pixel coordinates, in-play and on the full M-map; the A03 hover
        label behaviour is untouched (covered by hover_label_render_test.py).
  P07 - the in-game clock text fits inside its HUD box (right edge <= box
        right edge, bottom <= box bottom band) at desktop and mobile widths.

Truth comes from a fillText tracer (A01/A03 convention) plus live geometry
accessors __game.sectorAt() / __game.clockGeometry().

Run: ARK_URL=http://127.0.0.1:8899/index.html python test/hud_sector_test.py
"""
import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8899/index.html")
_home = Path(os.environ.get("HERMES_HOME", r"C:\Users\Lenovo\AppData\Local\hermes"))
SCRATCH = Path(os.environ.get("HERMES_SCRATCH", str(_home / "cache" / "scratch" / "chlopkow-p046p07")))
SCRATCH.mkdir(parents=True, exist_ok=True)

TRACER = r"""
(() => {
  window.__hudtrace = [];
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, mw) {
    if (typeof text === 'string' && text) {
      window.__hudtrace.push({ t: text, x: +x, y: +y });
      if (window.__hudtrace.length > 30000) window.__hudtrace.splice(0, 8000);
    }
    return orig.apply(this, arguments);
  };
})();
"""

# sector grid expected from game.js SECTOR_SIZE = 512
# MAP: 5143 x 7091 -> 11 columns (A..K), 14 rows (1..14)
SECTOR_SIZE = 512
MAP_W, MAP_H = 5143, 7091
SECTOR_RE = re.compile(r"^[A-K]\d{1,2}$")
PIXEL_RE = re.compile(r"\d+,\d+")


def sector(x, y):
    col = min((MAP_W + SECTOR_SIZE - 1) // SECTOR_SIZE - 1, int(x) // SECTOR_SIZE)
    row = min((MAP_H + SECTOR_SIZE - 1) // SECTOR_SIZE - 1, int(y) // SECTOR_SIZE) + 1
    return chr(65 + col) + str(row)


def new_page(browser, viewport):
    page = browser.new_page(viewport=viewport)
    page.add_init_script(TRACER)
    return page


def boot(page, name="Zosia"):
    page.goto(URL)
    page.wait_for_function("window.__game && window.__worldLife", timeout=60000)
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="load")
    page.wait_for_function("window.ARK && window.__game", timeout=60000)
    page.keyboard.press("Enter")
    if page.locator("#player-name-input").count():
        page.locator("#player-name-input").fill(name)
        page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'", timeout=30000)
    page.wait_for_timeout(400)


def traced(page):
    return page.evaluate("() => window.__hudtrace.map(e => e.t)")


def traced_all(page):
    return page.evaluate("() => window.__hudtrace")


def clear_trace(page):
    page.evaluate("() => { window.__hudtrace.length = 0; }")


# --------------------------------------------------------------------------
# P06: OSM attribution removed
# --------------------------------------------------------------------------
def run_p04(page, out):
    """Coordinate readout shows the grid SECTOR, never raw pixels, in-play and
    on the full M-map; the hover-label strip keeps its own position."""
    boot(page)
    # map constants: grid sanity A..K x 1..14
    cols = (MAP_W + SECTOR_SIZE - 1) // SECTOR_SIZE
    rows = (MAP_H + SECTOR_SIZE - 1) // SECTOR_SIZE
    assert cols == 11 and rows == 14, (cols, rows)
    assert SECTOR_RE.match("A1") and SECTOR_RE.match("K14"), "sector regex broken"

    # --- in-play line: "NAME SECTOR" and no raw pixels anywhere in the line ---
    clear_trace(page)
    page.wait_for_timeout(250)
    all_t = traced_all(page)
    hn = page.evaluate("() => window.__game.playerName")
    px, py = page.evaluate("() => [Math.round(window.__game.P.x), Math.round(window.__game.P.y)]")
    exp = sector(px, py)
    # the sector hook agrees with the Python-side expectation
    got = page.evaluate("([x, y]) => window.__game.sectorAt(x, y)", [px, py])
    assert got == exp, f"P04: sectorAt({px},{py}) = {got} != {exp}"
    coord_line = [e["t"] for e in all_t if e["t"].startswith(str(hn) + " ")]
    assert coord_line, f"P04: no coordinate readout line painted: {[e['t'] for e in all_t][:20]}"
    line = coord_line[-1]
    assert line == f"{hn} {exp}", f"P04: readout {line!r} != '{hn} {exp}'"
    assert SECTOR_RE.match(line.split()[-1]), f"P04: no sector label in {line!r}"
    assert not PIXEL_RE.search(line), f"P04: raw pixels still displayed: {line!r}"
    assert "52." not in line, f"P04: lat/lon still displayed: {line!r}"
    page.screenshot(path=str(out / "p04_hud_sector.png"))

    # --- full M-map: cursor line shows "KURSOR SECTOR" (no pixels) ---
    page.keyboard.press("KeyM")
    page.wait_for_timeout(250)
    clear_trace(page)
    mx, my = 1200, 2600
    page.evaluate("([x, y]) => { window.__game.mapCursor.seen = true; window.__game.mapCursor.x = x; window.__game.mapCursor.y = y; }", [mx, my])
    page.wait_for_timeout(200)
    texts = traced(page)
    cursor_lines = [t for t in texts if t.startswith("KURSOR")]
    assert cursor_lines, f"P04: no KURSOR line on the big map: {texts[:30]}"
    cline = cursor_lines[-1]
    assert cline == f"KURSOR {sector(mx, my)}", f"P04: cursor line {cline!r} != KURSOR {sector(mx, my)}"
    assert not PIXEL_RE.search(cline), f"P04: cursor raw pixels still displayed: {cline!r}"
    page.screenshot(path=str(out / "p04_map_sector.png"))
    page.keyboard.press("KeyM")
    print("  P04 PASS")


def run_p07(page, out, viewport):
    """P07: the clock text fits inside its HUD box - right edge inside the box
    right edge, bottom inside the top band - at desktop and mobile widths."""
    boot(page)
    # a long session time stresses the worst case ("99:59" is wider than "0:00")
    page.evaluate("() => { window.__game.Q.playTime = 5999; }")
    page.wait_for_timeout(250)
    geo = page.evaluate("() => window.__game.clockGeometry()")
    assert geo and "textRight" in geo, f"P07: clockGeometry hook missing: {geo}"
    # paint-level proof: the traced fillText for the clock sits exactly at the
    # right anchor (right-aligned), and its measured width keeps it inside the box
    painted = page.evaluate("(t) => window.__hudtrace.filter(e => e.t === t)", geo["text"])
    assert painted, f"P07: clock text {geo['text']!r} never painted"
    assert abs(painted[-1]["x"] - (geo["boxRight"] - (geo["boxRight"] - geo["textRight"]))) < 0.01, painted[-1]
    ok = geo["textRight"] <= geo["boxRight"] + 0.01 and \
         geo["textBottom"] <= geo["bandBottom"] + 0.01 and \
         geo["textLeft"] >= geo["boxLeft"] - 0.01
    assert ok, f"P07 {viewport}: clock overflows its box: {geo}"
    # the clock must not collide with the mushroom counter on the same row
    assert geo["textLeft"] >= geo["mushroomRight"] - 0.01, f"P07 {viewport}: clock overlaps mushroom counter: {geo}"
    page.screenshot(path=str(out / f"p07_clock_{viewport['width']}x{viewport['height']}.png"))
    print(f"  P07 PASS {viewport}")


def run_p06(page, out):
    boot(page)
    # in-play HUD: the attribution used to be painted here every frame
    clear_trace(page)
    page.wait_for_timeout(250)
    texts = traced(page)
    bad = [t for t in texts if "OPENSTREETMAP" in t.upper() or "CONTRIBUTORS" in t.upper()]
    assert not bad, f"P06: OSM attribution still painted: {bad}"
    # the coordinate readout must still paint (drawCoords kept)
    hn = page.evaluate("() => window.__game.playerName")
    assert any(t.startswith(str(hn)) for t in texts), f"P06: coordinate readout missing: {texts[:20]}"
    # full M-map open: previously ALSO painted the attribution
    page.keyboard.press("KeyM")
    page.wait_for_timeout(250)
    texts = traced(page)
    bad = [t for t in texts if "OPENSTREETMAP" in t.upper() or "CONTRIBUTORS" in t.upper()]
    assert not bad, f"P06: OSM attribution painted on the big map: {bad}"
    page.screenshot(path=str(out / "p06_map_no_osm.png"))
    page.keyboard.press("KeyM")
    print("  P06 PASS")


def main():
    errs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = new_page(browser, {"width": 1280, "height": 720})
            page.on("pageerror", lambda e: errs.append(str(e)))
            run_p06(page, SCRATCH)
            run_p04(page, SCRATCH)
            run_p07(page, SCRATCH, {"width": 1280, "height": 720})
            page.close()
            page = new_page(browser, {"width": 390, "height": 844})
            page.on("pageerror", lambda e: errs.append(str(e)))
            run_p07(page, SCRATCH, {"width": 390, "height": 844})
            page.close()
        finally:
            browser.close()
    assert not errs, f"page errors: {errs}"
    print("\nhud_sector (P06+P04+P07): PASS")


if __name__ == "__main__":
    main()