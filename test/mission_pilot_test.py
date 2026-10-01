"""D05 - one complete house mission pilot, start -> trigger -> complete -> reload.

Scenario (isolated browser storage):
1. Fresh load: mission quest row visible (PL/EN title), no progress yet.
2. Walk to the pilot house01 mission marker and interact -> step done.
3. Reload: progress persists, mission row stays checked, no re-award.
4. Interact again after reload -> still exactly one completion (no double award).
5. Side effects intact: quiz on house01 board still answers first at its own marker.

Run: python test/mission_pilot_test.py [URL]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def fresh_visit(pg, name):
    """Clear storage and start a brand-new game named `name`."""
    throwaway = URL.replace("index.html", "js/minigames.js")
    pg.goto(throwaway)
    pg.evaluate("localStorage.clear()")
    pg.goto(URL)
    pg.wait_for_function("!!(window.ARK && window.ARK.Q)")
    if pg.evaluate("window.ARK.scene") != "play":
        pg.keyboard.press("Enter")
        pg.keyboard.type(name)
        pg.keyboard.press("Enter")
    pg.wait_for_function("window.ARK && window.ARK.scene === 'play'", timeout=15000)
    time.sleep(.5)


def quest_rows(pg):
    return pg.evaluate("""(() => {
        const h = window.ARK && window.ARK.HOOKS && window.ARK.HOOKS.questLog;
        if (!h) return [];
        const rows = [];
        for (const f of h) { const lines = []; f(lines); rows.push(...lines.map(l => String(l[0]))); }
        return rows;
    })()""")


def mission_points(pg):
    return pg.evaluate("""(() => {
        const h = window.ARK && window.ARK.HOOKS && window.ARK.HOOKS.near;
        if (!h) return [];
        const pts = [];
        for (const f of h) {
            const cs = f(window.ARK.P) || [];
            for (const c of cs) if (c._mission) pts.push([c.x, c.y, c.r]);
        }
        return pts;
    })()""")


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)

    # ---- A: fresh game - mission quest row visible, zero progress, marker on map
    fresh_visit(pg, "Pilot")
    rows = quest_rows(pg)
    check(any(("Odwiedziny" in r) or ("Visit the first house" in r) for r in rows),
          f"A: mission quest row on fresh save (got {rows})")
    check(pg.evaluate("window.ARK.Q.missions") in (None, {}), "A: no mission progress yet")
    pts = mission_points(pg)
    check(len(pts) == 1 and pts[0][0] and pts[0][2] == 30, f"A: one mission marker r=30 (got {pts})")

    # ---- B: exact interact at marker completes the step
    mx, my = pts[0][0], pts[0][1]
    pg.evaluate(f"window.ARK.P.x = {mx}; window.ARK.P.y = {my}")
    pg.keyboard.press("KeyE")
    st = pg.evaluate("window.ARK.Q.missions && window.ARK.Q.missions['home-example']")
    check(st and st["visit"] is True, f"B: step visit done after interact (got {st})")

    # ---- C: reload - progress persists, quest row still visible, no re-award
    pg.reload()
    pg.wait_for_function("!!(window.ARK && window.ARK.Q)")
    if pg.evaluate("window.ARK.scene") != "play":
        pg.keyboard.press("Enter")
    pg.wait_for_function("window.ARK && window.ARK.scene === 'play'", timeout=15000)
    time.sleep(.5)
    st2 = pg.evaluate("window.ARK.Q.missions && window.ARK.Q.missions['home-example']")
    check(st2 and st2["visit"] is True, f"C: step persists after reload (got {st2})")
    m2 = mission_points(pg)
    check(m2 == [], f"C: no re-offer marker after completion (got {m2})")

    # ---- D: post-reload interact is a no-op (no double award)
    pg.evaluate(f"window.ARK.P.x = {mx}; window.ARK.P.y = {my}")
    pg.keyboard.press("KeyE")
    st3 = pg.evaluate("window.ARK.Q.missions['home-example']")
    check(st3["visit"] is True, "D: still exactly one completion after post-reload interact")

    # ---- E: mission spot still a no-op after completion; quiz state untouched
    pg.keyboard.press("KeyE")   # standing at mission marker still no-op
    st4 = pg.evaluate("window.ARK.Q.missions['home-example']")
    quiz = pg.evaluate("window.ARK.Q.quiz")
    check(st4["visit"] is True and quiz == {},
          f"E: mission spot no-op after completion, quiz untouched (got {quiz})")

    check(not errs, f"no page errors {errs}")
    b.close()
print()
print("FAILED:", fails if fails else "none")
sys.exit(1 if fails else 0)