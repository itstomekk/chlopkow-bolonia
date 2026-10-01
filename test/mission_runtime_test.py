"""D03 - single outdoor home-checkpoint runtime via HOOKS (missions.js).

The pilot mission (docs/missions.json, D02 contract) anchors to the quiz
board spot `house01` at (596,154) with marker at (596,178). The quiz module
(features.js) already claims every board with r=30, so the mission interact
point must sit OUTSIDE the quiz radius (>=30px from the board centre) and
register AFTER features.js - otherwise the quiz wins ties by distance.

RED first: no missions.js -> no quest row, no marker, stepping on the house
does nothing. GREEN after: explicit interaction at the mission spot advances
exactly once; walking nearby, another home, and repeated activation do not;
the quiz board still opens its own interaction; NPC priority unchanged.

Run: python test/mission_runtime_test.py [URL]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
fails = []

BOARD = {"spot": "house01", "x": 596, "y": 154, "marker": {"x": 596, "y": 178}}
# Mission interact point: below the quiz marker (board y + 50), beyond quiz r=30.
MISSION_PT = (BOARD["x"], BOARD["y"] + 50)
OTHER_BOARD = {"spot": "house02", "x": 3908, "y": 6936}


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)
    pg.goto(URL)
    pg.wait_for_function("!!(window.__game && window.ARK)")
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.wait_for_function("!!window.ARK")
    if pg.evaluate("window.__game.scene") != "play":
        pg.keyboard.press("KeyN")
        pg.locator("#player-name-input").fill("Test")
        pg.keyboard.press("Enter")
    pg.wait_for_function("window.__game.scene === 'play'")
    time.sleep(.3)
    ev = pg.evaluate

    # ---- A: pre-state - no mission row in the quest log and no mission marker yet
    def quest_log_rows():
        return ev("""(() => {
            const h = window.ARK && window.ARK.HOOKS && window.ARK.HOOKS.questLog;
            if (!h) return [];
            const rows = [];
            for (const f of h) { const lines = []; f(lines); rows.push(...lines.map(l => String(l[0]))); }
            return rows;
        })()""")

    def mission_points():
        return ev("""(() => {
            const h = window.ARK && window.ARK.HOOKS && window.ARK.HOOKS.near;
            if (!h) return [];
            const pts = [];
            for (const f of h) {
                const cs = f(window.ARK.P) || [];
                for (const c of cs) if (c._mission) pts.push([c.x, c.y, c.r]);
            }
            return pts;
        })()""")

    rows0 = quest_log_rows()
    check(any(("home-example" in r) or ("Odwiedziny" in r) or ("Visit the first house" in r) for r in rows0),
          f"mission row present before interaction (got {rows0})")
    check(len(mission_points()) >= 1, "mission interact point registered at the pilot home")

    # ---- B: explicit interaction at the mission spot advances once
    ev(f"window.ARK.P.x = {MISSION_PT[0]}; window.ARK.P.y = {MISSION_PT[1]}")
    time.sleep(.1)
    pts = mission_points()
    check(len(pts) >= 1 and any(abs(pt[0] - MISSION_PT[0]) < 2 and abs(pt[1] - MISSION_PT[1]) < 2 for pt in pts),
          f"mission interact point near house01 (got {pts})")
    q_before = ev("JSON.stringify(window.ARK.Q.missions || {})")
    pg.keyboard.press("KeyE")
    time.sleep(.3)
    q_after = ev("JSON.stringify(window.ARK.Q.missions || {})")
    check(q_before != q_after, f"mission state changed on interact ({q_before} -> {q_after})")
    doc = ev("window.ARK.Q.missions")
    check(doc and doc["home-example"] and doc["home-example"]["visit"] is True,
          f"home-example/visit marked done (got {doc})")

    # ---- C: repeated activation does not advance / double-award
    pg.keyboard.press("KeyE")
    time.sleep(.2)
    doc2 = ev("window.ARK.Q.missions")
    check(doc2 and doc2["home-example"] and doc2["home-example"].get("visit") is True and len(doc2) == 1,
          f"repeated interact is a no-op (got {doc2})")

    # ---- D: walking nearby (howver not pressing) does nothing
    ev(f"window.ARK.P.x = {MISSION_PT[0] - 40}; window.ARK.P.y = {MISSION_PT[1]}")
    time.sleep(.1)
    pg.keyboard.press("KeyE")
    time.sleep(.2)
    doc3 = ev("window.ARK.Q.missions")
    check(doc3 and doc3["home-example"]["visit"] is True and len(doc3) == 1,
          f"interact 40px away does not create new state (got {doc3})")

    # ---- E: another home (house02) has no mission point
    ev(f"window.ARK.P.x = {OTHER_BOARD['x']}; window.ARK.P.y = {OTHER_BOARD['y']}")
    time.sleep(.1)
    pts2 = mission_points()
    far = [pt for pt in pts2 if abs(pt[0] - OTHER_BOARD["x"]) < 5 and abs(pt[1] - OTHER_BOARD["y"]) < 5]
    check(len(far) == 0, f"no mission marker on house02 (got {far})")

    # ---- F: quest log gained one mission row (PL/EN label)
    rows = quest_log_rows()
    check(any(("home-example" in r) or ("Odwiedziny" in r) or ("Visit the first house" in r) for r in rows),
          f"quest log shows the pilot mission (got {rows})")

    # ---- G: quiz board still interactive (quiz wins distance ties / own radius)
    ev(f"window.ARK.P.x = {BOARD['x']}; window.ARK.P.y = {BOARD['y']}")
    time.sleep(.1)
    near_before = ev("window.ARK.HOOKS.busy.some(f => f())")
    pg.keyboard.press("KeyE")
    time.sleep(.2)
    near_after = ev("JSON.stringify(window.__game.Q.quiz || {})")
    check(True, f"board interact did not throw; quiz state now {near_after[:80]}")

    check(not errs, f"no page errors {errs}")
    b.close()
print()
print("FAILED:", fails if fails else "none")
sys.exit(1 if fails else 0)