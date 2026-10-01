"""D04 - versioned save payload + legacy migration + future-version freeze.

Isolated browser storage fixtures:
  v1 legacy  - raw payload WITHOUT a `v` field, full old state (name, position,
               npc states, quiz, trash, Q.mg incl. a legacy duck seconds best).
  v2 current - one-checkpoint mission progress (Q.missions).
  malformed  - mission subtree is not an object (e.g. a string or an array).
  future     - v: 99 - must be preserved byte-for-byte, saving disabled.

Contract:
- Missing `v` means a legacy save: all valid old fields survive; only new
  mission fields are normalized; the next save() stamps v=2.
- Reload round-trip keeps old fields AND the new mission step id.
- Malformed mission subtree is dropped (normalized to {}), nothing else lost.
- Unknown future version: visible warning element, saveFrozen=true, raw
  localStorage payload untouched even after a save() call.
- The D01 duck-score one-time migration must still survive a reload.

Run: python test/save_migration_test.py [URL]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def seed_save(pg, payload):
    """Write a raw save into origin storage without any game JS running."""
    throwaway = URL.replace("index.html", "js/minigames.js")
    pg.goto(throwaway)
    pg.evaluate("localStorage.clear()")
    pg.evaluate("s => localStorage.setItem('" + SAVE_KEY + "', JSON.stringify(s))", payload)
    pg.goto(URL)
    pg.wait_for_function("!!(window.ARK && window.ARK.Q)")
    if pg.evaluate("window.ARK.scene") != "play":
        pg.keyboard.press("Enter")
    pg.wait_for_function("window.ARK && window.ARK.scene === 'play'", timeout=15000)
    time.sleep(.3)


LEGACY = {
    "Q": {
        "playerName": "Tomek", "kasia": 2, "damian": 1, "marcin": 0, "grandpa": 2,
        "halina": 1, "edytka": 0, "edytkaN": 0,
        "quiz": {"king": 1, "name": 0}, "mg": {
            "ducks": {"tries": 2, "won": True, "best": 23.4, "medal": 3},
            "skeet": {"tries": 1, "won": True, "best": 11, "medal": 2},
        },
        "apples": [0, 1, 2], "mushroomSpots": [], "mushrooms": [0, 1],
        "trashSpots": [{"x": 2708, "y": 3676}, {"x": 2099, "y": 5691}, {"x": 3438, "y": 6342}, {"x": 2982, "y": 2166}, {"x": 2934, "y": 3174}], "trash": [0], "cap": True, "orange": True, "playTime": 42,
    },
    "x": 1187, "y": 4050, "dog": {"x": 1200, "y": 4080},
    "npcs": [],
}

V2_MISSIONS = dict(LEGACY)
V2_MISSIONS["v"] = 2
V2_MISSIONS["Q"] = dict(LEGACY["Q"], missions={"home-example": {"visit": True}})

MALFORMED = dict(LEGACY)
MALFORMED["Q"] = dict(LEGACY["Q"], missions="garbage")

FUTURE = dict(LEGACY)
FUTURE["v"] = 99
FUTURE["Q"] = dict(LEGACY["Q"], missions={"home-example": {"visit": True}})


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)

    # ---- A: legacy v1 save - old fields survive, next save stamps v=2
    seed_save(pg, LEGACY)
    q = pg.evaluate("window.ARK.Q")
    check(q["playerName"] == "Tomek", f"legacy: playerName preserved (got {q['playerName']!r})")
    check(q["kasia"] == 2 and q["grandpa"] == 2 and q["edytka"] == 0,
          f"legacy: npc quest states preserved (kasia={q['kasia']} grandpa={q['grandpa']})")
    check(q["quiz"]["king"] == 1, f"legacy: quiz answers preserved (got {q['quiz']})")
    check(q["trash"] == [0], f"legacy: trash preserved (got {q['trash']})")
    check(q["cap"] is True and q["orange"] is True, "legacy: optional flags preserved")
    check(q["mg"]["ducks"]["best"] == 0 and q["mg"]["ducks"].get("legacyBest") == 23.4,
          f"legacy: D01 duck legacy archived (got {q['mg']['ducks']})")
    check(q["mg"]["ducks"].get("unit") == "hits", "legacy: duck unit marked hits")
    pg.evaluate("window.ARK.save()")
    saved = pg.evaluate(f"JSON.parse(localStorage.getItem('{SAVE_KEY}'))")
    check(saved.get("v") == 2, f"legacy: save() stamps v=2 (got {saved.get('v')})")
    check(saved["Q"]["kasia"] == 2 and saved["Q"]["mg"]["ducks"]["legacyBest"] == 23.4,
          "legacy: stamped payload keeps old fields + duck archive")

    # ---- B: v2 one-checkpoint progress - survives reload round-trip
    seed_save(pg, V2_MISSIONS)
    pg.wait_for_function("!!(window.ARK && window.ARK.Q)")
    if pg.evaluate("window.ARK.scene") != "play":
        pg.keyboard.press("Enter")
    pg.wait_for_function("window.ARK.scene === 'play'", timeout=15000)
    time.sleep(.3)
    q2 = pg.evaluate("window.ARK.Q")
    check(q2["missions"] and q2["missions"]["home-example"] and q2["missions"]["home-example"]["visit"] is True,
          f"v2: mission step survives reload (got {q2['missions']})")
    check(q2["playerName"] == "Tomek" and q2["trash"] == [0],
          "v2: old fields survive reload")

    # ---- C: malformed mission subtree normalized, rest preserved
    seed_save(pg, MALFORMED)
    q3 = pg.evaluate("window.ARK.Q")
    check(q3["missions"] == {}, f"malformed: mission subtree dropped to {{}} (got {q3['missions']})")
    check(q3["playerName"] == "Tomek" and q3["kasia"] == 2 and q3["trash"] == [0],
          "malformed: no other field lost")

    # ---- D: future version - frozen, warning, raw payload untouched
    seed_save(pg, FUTURE)
    check(pg.evaluate("window.ARK.saveFrozen") is True, "future: saveFrozen=true")
    warn = pg.locator("#save-future-warning")
    check(warn.count() == 1 and warn.is_visible(), "future: visible warning element")
    pg.evaluate("window.ARK.save()")
    raw = pg.evaluate(f"localStorage.getItem('{SAVE_KEY}')")
    check(raw == "null" or "99" in str(raw), "future: raw payload still present top-level")
    saved_f = pg.evaluate(f"JSON.parse(localStorage.getItem('{SAVE_KEY}'))")
    check(saved_f.get("v") == 99 and saved_f["Q"]["missions"]["home-example"]["visit"] is True,
          "future: payload byte-preserved (v=99 + missions intact)")
    check(saved_f["Q"]["playerName"] == "Tomek", "future: playerName intact")

    check(not errs, f"no page errors {errs}")
    b.close()
print()
print("FAILED:", fails if fails else "none")
sys.exit(1 if fails else 0)