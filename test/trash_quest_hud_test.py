"""A04 regression: the trash counter leaves the HUD primary row and becomes a
quest-list row.

RED/GREEN contract (fresh isolated context, LEGACY save fixture that predates
the trash feature - no trashSpots/trash keys in the stored Q):

- the HUD primary row paints exactly the apple counter, the mushroom counter
  and the timer - never a ``× n/5`` trash counter (the black-bag icon + counter
  block removed from game.js);
- the quest list shows a localized trash row ``WOREK ŚMIECI (0/5)`` /
  ``TRASH BAG (0/5)`` that advances to ``(1/5)`` and ``(5/5)`` as bags are
  walked over;
- the completed ``(5/5)`` survives a reload using the EXISTING Q.trash
  persistence - no new save key is introduced;
- the Halina quiz row still renders beside the trash row.

Truth comes from a canvas fillText tracer (A01/A03 convention) filtered to the
HUD box region, plus the persisted save payload.

Run: ARK_URL=http://127.0.0.1:8790/index.html python test/trash_quest_hud_test.py
"""
import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8790/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"

_home = Path(os.environ.get("HERMES_HOME", r"C:\Users\Lenovo\AppData\Local\hermes"))
SCRATCH = Path(os.environ.get("HERMES_SCRATCH", str(_home / "cache" / "scratch" / "chlopkow-a04")))
SCRATCH.mkdir(parents=True, exist_ok=True)

# Records every canvas fillText (same convention as A01/A03). Installed before
# the game scripts; game.js binds ctx.fillText at startup, so the patched
# prototype is what its _fill wrapper funnels through.
TRACER = """
(() => {
  window.__a4trace = [];
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y, mw) {
    if (typeof text === 'string' && text) window.__a4trace.push({ t: text, x: +x, y: +y });
    return orig.apply(this, arguments);
  };
})();
"""

# Legacy save: no trashSpots / trash fields (the feature came later). The game's
# ensureTrash() creates the 5 spots and an empty collection on load. Spawn coords
# come from map.json (1187, 4050). halina=1 so the features.js questLog hook adds
# the quiz row; kasia=1 so a normal quest row also renders.
LEGACY_SAVE = {
    "Q": {
        "playerName": "Zosia",
        "kasia": 1, "damian": 0, "marcin": 0, "grandpa": 0,
        "halina": 1, "edytka": 0, "edytkaN": 0,
        "quiz": {}, "mg": {}, "apples": [], "mushrooms": [],
        "cap": False, "orange": False, "playTime": 42,
    },
    "x": 1187, "y": 4050,
    "dog": {"x": 1140, "y": 4050},
    "npcs": [],
}

TRASH_PL_ROW = "WOREK ŚMIECI ({}/5)"
TRASH_EN_ROW = "TRASH BAG ({}/5)"
TIMER_RE = re.compile(r"^\d+:\d\d$")
TRASH_PRIMARY_RE = re.compile(r"^× \d+/5$")          # old primary-row trash counter format
APPLE_ROW = re.compile(r"^× \d+$")                   # primary apple counter: "× 0"
MUSH_ROW = re.compile(r"^× \d+/15$")                 # primary mushroom counter: "× 0/15"
QUIZ_RE = re.compile(r"^(QUIZ O CHŁOPKOWIE|CHŁOPKÓW QUIZ) ★\d+ \(\d+/\d+\)$")


def new_page(browser, viewport):
    page = browser.new_page(viewport=viewport)
    page.add_init_script(TRACER)
    return page


def boot_legacy(page, lang="pl"):
    """Fresh isolated context seeded with the legacy pre-trash save."""
    url = URL + (("&" if "?" in URL else "?") + "lang=en" if lang == "en" else "")
    page.goto(url)
    page.evaluate("localStorage.clear()")
    page.evaluate("(f) => localStorage.setItem('%s', JSON.stringify(f))" % SAVE_KEY, LEGACY_SAVE)
    page.reload()
    page.wait_for_function("window.ARK && window.__game && window.__worldLife", timeout=30000)
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'", timeout=30000)


def bands(page):
    """Split traced texts into the HUD primary row band and the quest-list band."""
    U = page.evaluate("() => { const c = window.ARK.ctx.canvas; return Math.min(c.width, c.height * 1.6) / 100; }")
    trace = page.evaluate("() => window.__a4trace")
    primary = [e["t"] for e in trace if U * 3.2 <= e["y"] <= U * 6.4]
    quest = [e["t"] for e in trace if U * 7.2 <= e["y"] <= U * 60]
    return U, primary, quest


def assert_primary_row(page, where):
    """Primary row = timer + apple + mushroom counters only; never a × n/5 trash counter."""
    _, primary, _ = bands(page)
    assert any(APPLE_ROW.match(t) for t in primary), f"{where}: apple counter missing in primary {primary}"
    assert any(MUSH_ROW.match(t) for t in primary), f"{where}: mushroom counter missing in primary {primary}"
    assert any(TIMER_RE.match(t) for t in primary), f"{where}: timer missing in primary {primary}"
    bad = [t for t in primary if TRASH_PRIMARY_RE.match(t)]
    assert not bad, f"{where}: trash counter still painted on the primary row: {bad}"


def assert_quest_row(page, n, where, lang="pl"):
    row = (TRASH_PL_ROW if lang == "pl" else TRASH_EN_ROW).format(n)
    _, _, quest = bands(page)
    assert row in quest, f"{where}: quest list missing {row!r} (got {sorted(set(quest))})"


def assert_quiz_row(page, where):
    _, _, quest = bands(page)
    assert any(QUIZ_RE.match(t) for t in quest), f"{where}: quiz row missing/render broken: {sorted(set(quest))}"


def collect_bags(page, want):
    """Walk the hero over trash spots until Q.trash has `want` entries (game pushes on proximity)."""
    for i in range(len(page.evaluate("() => __game.Q.trash")), want):
        page.evaluate("(i) => { const t = __game.Q.trashSpots[i]; __game.P.x = t.x; __game.P.y = t.y; }", i)
        page.wait_for_function("__game.Q.trash.length === %d" % (i + 1), timeout=3000)


def run_pl_flow(browser, viewport, out, lang="pl"):
    """Boot with the legacy fixture, verify primary/quest/quiz rows at 0/5, collect
    all five bags (1/5..5/5), keep the completed count across a reload, and prove
    the save did not gain a new key."""
    page = new_page(browser, viewport)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    boot_legacy(page, lang)
    where = f"{viewport['width']}x{viewport['height']} [{lang}]"

    # Legacy fixture loaded intact, trash regenerated by ensureTrash()
    assert page.evaluate("__game.Q.playerName") == "Zosia", "legacy playerName lost"
    assert page.evaluate("__game.Q.kasia") == 1, "legacy kasia lost"
    assert page.evaluate("__game.Q.halina") == 1, "legacy halina lost"
    # playTime is a live per-frame clock (Q.playTime += dt), so it only grows.
    assert page.evaluate("__game.Q.playTime") >= 42, "legacy playTime lost"
    assert page.evaluate("__game.Q.trashSpots.length") == 5, "ensureTrash did not seed 5 spots"
    assert page.evaluate("__game.Q.trash") == [], "legacy save should start with 0 collected"

    # 0/5: primary row clean, quest row present, quiz row present
    assert_primary_row(page, where + " @0/5")
    assert_quest_row(page, 0, where + " @0/5", lang)
    assert_quiz_row(page, where + " @0/5")
    if out:
        page.screenshot(path=SCRATCH / f"{viewport['width']}x{viewport['height']}_trash_0of5.png")

    # (1/5) after the first bag, then (5/5) after all five
    keys_before = set(page.evaluate("() => Object.keys(__game.Q)"))
    collect_bags(page, 1)
    assert_quest_row(page, 1, where + " @1/5", lang)
    assert_primary_row(page, where + " @1/5")
    collect_bags(page, 5)
    assert page.evaluate("__game.Q.trash") == [0, 1, 2, 3, 4], "Q.trash indices"
    assert_quest_row(page, 5, where + " @5/5", lang)
    assert_quiz_row(page, where + " @5/5")
    assert_primary_row(page, where + " @5/5")
    if out:
        page.screenshot(path=SCRATCH / f"{viewport['width']}x{viewport['height']}_trash_5of5.png")

    # Reload: completed count survives via the existing Q.trash persistence; no new key.
    keys_after = set(page.evaluate("() => Object.keys(__game.Q)"))
    assert keys_before == keys_after, f"save gained/lost Q keys: {keys_before ^ keys_after}"
    assert not any("trash" in k and k not in ("trash", "trashSpots") for k in keys_after), \
        f"new trash persistence key invented: {sorted(keys_after)}"
    page.reload()
    page.wait_for_function("window.__game && window.__game.Q", timeout=30000)
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'", timeout=30000)
    assert page.evaluate("__game.Q.trash") == [0, 1, 2, 3, 4], "completed trash count lost on reload"
    assert page.evaluate("__game.Q.playerName") == "Zosia", "legacy fields lost on reload"
    assert_quest_row(page, 5, where + " after reload", lang)
    assert_quiz_row(page, where + " after reload")
    assert_primary_row(page, where + " after reload")
    assert not errors, f"{where}: page errors {errors}"
    page.close()
    print(f"  {where} PASS")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        run_pl_flow(browser, {"width": 1280, "height": 720}, SCRATCH, "pl")
        run_pl_flow(browser, {"width": 390, "height": 844}, SCRATCH, "pl")
        run_pl_flow(browser, {"width": 1280, "height": 720}, None, "en")   # localized row label
        browser.close()
    for name in ("1280x720_trash_0of5.png", "1280x720_trash_5of5.png",
                 "390x844_trash_0of5.png", "390x844_trash_5of5.png"):
        assert (SCRATCH / name).exists(), f"screenshot missing: {SCRATCH / name}"
    print("\ntrash_quest_hud: PASS")


if __name__ == "__main__":
    main()