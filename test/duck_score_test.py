"""Focused D01 test: duck/skeet hit-count records are hit counts (higher = better),
and a legacy duck record (best stored as seconds, no unit marker) migrates once and
safely. Run: python test/duck_score_test.py [URL]"""
import os, sys, time, threading
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"
fails = []


def ensure_server():
    """Standalone mode: serve docs/ in-process on a dedicated port. Only when the
    caller passes an explicit URL (or ARK_URL) do we assume an external server
    (repo convention: python -m http.server 8765 --directory docs)."""
    global URL
    if sys.argv[1:] or os.environ.get("ARK_URL"):
        return
    import http.server, socketserver
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DOCS = os.path.join(root, "docs")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=DOCS, **kw)

        def log_message(self, *a):
            pass

        def handle_error(self, request, client_address):
            pass  # browsers abort in-flight image fetches on navigation; not server faults

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", 8795), Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    URL = "http://127.0.0.1:8795/index.html"
    time.sleep(.5)


def seed_legacy_save(pg, legacy):
    """Write a legacy save into origin storage without any game JS running, so
    nothing can autosave over it before the next load."""
    throwaway = URL.replace("index.html", "js/minigames.js")   # same origin, no game scripts
    pg.goto(throwaway)
    pg.evaluate("localStorage.clear()")
    pg.evaluate("s => localStorage.setItem('" + SAVE_KEY + "', JSON.stringify(s))", legacy)
    pg.goto(URL)


ensure_server()


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def hit_end(pg, ev, hits, run):
    """Force the current shooting game to finish with `hits` hits and `run` seconds elapsed."""
    ev(f"""(() => {{
      const M = __features.MG;
      M.phase = 'run'; M.run = {run}; M.hits = {hits};
      M.plan.forEach(p => p.done = true); M.targets = [];
    }})()""")
    pg.wait_for_function("__features.MG.phase === 'win' || __features.MG.phase === 'lose'", timeout=10000)
    time.sleep(.1)


def pig_end(pg, ev, run):
    """Force a pig win at ~`run` seconds by putting the pig on Arek."""
    ev(f"""(() => {{
      const M = __features.MG, P = __game.P;
      M.phase = 'run'; M.run = {run}; M.pig.x = P.x; M.pig.y = P.y;
    }})()""")
    pg.wait_for_function("__features.MG.phase === 'win' || __features.MG.phase === 'lose'", timeout=10000)
    time.sleep(.1)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)
    pg.goto(URL)
    pg.wait_for_function("!!(window.__game && window.__features && window.__features.startMG)")
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.wait_for_function("!!(window.__features && window.__features.startMG)")
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Test")
    pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    ev = pg.evaluate

    # ---- A: a 12-hit duck win records hits (not seconds) and a matching medal
    ev("__features.startMG('ducks')")
    hit_end(pg, ev, hits=12, run=20.0)
    d = ev("__game.Q.mg.ducks")
    check(ev("__features.MG.phase === 'win'"), "ducks: forced 12-hit run ends in a win")
    check(d["best"] == 12, f"ducks: rec.best is the hit count 12 (got {d['best']})")
    check(0 <= d["best"] <= 15, f"ducks: recorded best is a valid /15 hit count (got {d['best']})")
    check(d["medal"] == 2, f"ducks: medal agrees with 12 hits = silver (got {d['medal']})")
    mf = ev("__features.medalFor('ducks', __game.Q.mg.ducks.best)")
    check(d["medal"] == mf, f"ducks: medal/display agree (medalFor({d['best']}) = {mf})")

    # ---- B: higher is better for ducks — 10 hits must NOT beat 12, 15 must beat it
    ev("__features.startMG('ducks')")
    hit_end(pg, ev, hits=10, run=19.0)
    d = ev("__game.Q.mg.ducks")
    check(d["best"] == 12, f"ducks: 10 hits keep the 12-hit record (got {d['best']}) — higher is better")
    check(d["medal"] == 2, f"ducks: medal stays silver after weaker run (got {d['medal']})")
    ev("__features.startMG('ducks')")
    hit_end(pg, ev, hits=15, run=25.0)
    d = ev("__game.Q.mg.ducks")
    check(d["best"] == 15, f"ducks: 15 hits become the new record (got {d['best']})")
    check(d["medal"] == 3, f"ducks: 15 hits = gold (got {d['medal']})")

    # ---- C: skeet keeps ranking higher hit counts
    ev("__features.startMG('skeet')")
    hit_end(pg, ev, hits=10, run=30.0)
    s = ev("__game.Q.mg.skeet")
    check(s["best"] == 10 and s["medal"] == 1, f"skeet: 10 hits = best 10 / bronze (got {s})")
    ev("__features.startMG('skeet')")
    hit_end(pg, ev, hits=12, run=30.0)
    s = ev("__game.Q.mg.skeet")
    check(s["best"] == 12 and s["medal"] == 2, f"skeet: 12 hits beat 10 (got {s})")

    # ---- D: pig/race still rank lower times (guard)
    ev("__game.Q.mg.pig = { tries: 0, won: false, best: 5, medal: 0 }")
    ev("__features.startMG('pig')")
    pig_end(pg, ev, run=7.0)
    d = ev("__game.Q.mg.pig")
    check(d["best"] == 5, f"pig: a slower 7 s run does not beat best 5 s (got {d['best']})")
    ev("__features.startMG('pig')")
    pig_end(pg, ev, run=4.0)
    d = ev("__game.Q.mg.pig")
    check(4 <= d["best"] < 5, f"pig: a 4 s run does beat best 5 s (got {d['best']})")

    # ---- E: legacy duck record (best = seconds, no unit marker) migrates once
    legacy = {"Q": {"playerName": "Tomek", "mg": {
        "ducks": {"tries": 2, "won": True, "best": 23.4, "medal": 3},
        "skeet": {"tries": 1, "won": True, "best": 11, "medal": 2},
    }}, "x": 801, "y": 903}
    seed_legacy_save(pg, legacy)
    pg.wait_for_function("!!(window.__features && window.__features.startMG)")
    if pg.evaluate("__game.scene") != "play":
        pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.3)
    d = pg.evaluate("__game.Q.mg.ducks")
    check(d["best"] == 0, f"migration: old seconds best is NOT cast to hits (best = {d['best']})")
    check(d["legacyBest"] == 23.4, f"migration: old best archived as legacyBest (got {d.get('legacyBest')})")
    check(d["legacyMedal"] == 3, f"migration: old medal archived as legacyMedal (got {d.get('legacyMedal')})")
    check(d["medal"] == 0, f"migration: medal reset to 0 (got {d['medal']})")
    check(d["unit"] == "hits", f"migration: unit marked hits (got {d.get('unit')})")
    check(d["won"] is True and d["tries"] == 2, f"migration: won/tries preserved (got won={d['won']} tries={d['tries']})")
    s = pg.evaluate("__game.Q.mg.skeet")
    check(s["best"] == 11 and s["medal"] == 2 and s["unit"] == "hits",
          f"migration: skeet already-hit record kept + unit marked (got {s})")
    check("legacyBest" not in s, f"migration: skeet gets no legacy archive (got {s})")
    saved = pg.evaluate(f"JSON.parse(localStorage.getItem('{SAVE_KEY}'))")
    md = saved["Q"]["mg"]["ducks"]
    check(md["best"] == 0 and md["legacyBest"] == 23.4 and md["unit"] == "hits",
          f"migration: persisted on reload (saved ducks: {md})")

    # ---- F: legacy time >15 still yields a record on a new valid hit result
    pg.evaluate("__features.startMG('ducks')")   # tries 2 -> 3
    hit_end(pg, ev, hits=11, run=8.0)
    d = pg.evaluate("__game.Q.mg.ducks")
    check(d["best"] == 11, f"migration: 11 fresh hits become a record despite legacy 23.4 s (got {d['best']})")
    check(d["legacyBest"] == 23.4, f"migration: legacyBest untouched by the new record (got {d.get('legacyBest')})")
    check(d["medal"] == 1 and d["unit"] == "hits", f"migration: bronze medal for 11 hits (got {d})")
    check(d["won"] is True and d["tries"] == 3, f"migration: won kept / tries 2->3 (got {d['tries']})")
    saved = pg.evaluate(f"JSON.parse(localStorage.getItem('{SAVE_KEY}'))")
    md = saved["Q"]["mg"]["ducks"]
    check(md["best"] == 11 and md["legacyBest"] == 23.4 and md["unit"] == "hits" and md["won"] is True and md["tries"] == 3,
          f"migration: saved payload after new record is hits-typed (got {md})")

    # ---- G: migration is one-time — reload keeps the hits record, no re-archive
    pg.reload()
    pg.wait_for_function("!!(window.__features && window.__features.startMG)")
    if pg.evaluate("__game.scene") != "play":
        pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.3)
    d = pg.evaluate("__game.Q.mg.ducks")
    check(d["best"] == 11, f"reload: hits record survives (not re-reset to 0) — got {d['best']}")
    check(d["legacyBest"] == 23.4, f"reload: legacy archive still intact (got {d.get('legacyBest')})")
    check(d["unit"] == "hits" and d["tries"] == 3, f"reload: still hits-typed, tries intact (got {d})")

    check(not errs, f"no page errors {errs}")
    b.close()
print()
print("FAILED:", fails if fails else "none")
sys.exit(1 if fails else 0)