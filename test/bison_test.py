"""Żubr (bison): rare forest wanderer (docs/js/bison.js).

Checks: no visit before 5 min of play; forest regions found; a forced visit starts in a forest,
moves, keeps distance from Arek (never reachable), is counted once when spotted; screenshot.

    python -m http.server 8765 --directory docs
    python test/bison_test.py [URL]
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOT = os.path.join(os.environ.get("TMPDIR", "."), "bison.png")
fails = []
def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_function("window.__game && window.__bison")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game && window.__bison")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(2)
    info = pg.evaluate("({forests: __bison.forests, state: __bison.state, next: __bison.nextCheck, c: __bison.constants})")
    check(len(info["forests"]) >= 2, f"at least two forest regions to migrate between ({info['forests']})")
    check(info["state"] is None, "no bison at the start of a session")
    check(info["c"]["FIRST_AFTER"] >= 300 and info["next"] >= 300, "first chance only after 5 minutes of play")

    check(pg.evaluate("__bison.start()"), "forced visit starts")
    s = pg.evaluate("__bison.state")
    check(s and s["region"] >= 0, f"bison spawns inside a forest region ({s})")
    # put Arek next to him: he must stop, then walk away, never be reached
    pg.evaluate("(() => { const s = __bison.state, g = __game; for (let r = 40; r < 200; r += 4) for (let a = 0; a < 6.3; a += .3) { const X = s.x + Math.cos(a) * r, Y = s.y + Math.sin(a) * r; if (!g.blocked(X, Y)) { g.P.x = X; g.P.y = Y; return; } } })()")
    d0 = pg.evaluate("Math.hypot(__bison.state.x - __game.P.x, __bison.state.y - __game.P.y)")
    time.sleep(1)
    pg.screenshot(path=SHOT)
    time.sleep(5)
    st = pg.evaluate("({ s: __bison.state, d: Math.hypot(__bison.state.x - __game.P.x, __bison.state.y - __game.P.y), seen: __game.Q.bisonSeen })")
    check(st["d"] > d0, f"bison retreats from Arek ({d0:.0f} -> {st['d']:.0f} px)")
    check(st["seen"] == 1, f"spotting counted once (Q.bisonSeen={st['seen']})")
    time.sleep(2)
    check(pg.evaluate("__game.Q.bisonSeen") == 1, "spotting is not counted twice in one visit")
    check(not errors, f"no page errors {errors}")
    b.close()

print("bison:", "PASS" if not fails else f"FAILED {fails}", "screenshot", SHOT)
sys.exit(1 if fails else 0)
