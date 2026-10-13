"""Headless test of the village minigames (pig, dogs, skeet, ducks, mowing): win/lose paths, medals, retry.
The lap race was removed on 2026-10-12 (replaced by the sprint board, see sprint_board_test.py).
Usage: python test/minigames_test.py [URL]"""
import os
import math, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)   # public Nostr relays (global chat) being down is not a game error
    pg.goto(URL); pg.wait_for_function("!!(window.__game && window.__features && window.__features.startMG)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__features && window.__features.startMG)")
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    ev = pg.evaluate
    mg = lambda: ev("__features.MG && {phase: __features.MG.phase, type: __features.MG.type, medal: __features.MG.medal, msg: __features.MG.msg}")

    # ---- the old lap race is gone: no race type, flag or off-track slowdown
    check(ev("__game.MAP.track === undefined && !!__game.MAP.sprint"), "map exports a sprint venue and no race track")

    # ---- pig: catch → medal by time; timeout → lose
    ev("__features.startMG('pig')"); time.sleep(3.3)
    pig = ev("__features.MG.pig"); ev(f"__game.P.x={pig['x']}; __game.P.y={pig['y']}"); time.sleep(.2)
    r = mg(); check(r and r['phase'] == 'win' and r['medal'] == 3, f"pig quick catch = gold ({r})"); pg.screenshot(path="test/m3_pig_win.png"); pg.keyboard.press("Escape")

    # ---- dogs: lose to a lunge, then win by collecting eggs
    ev("__features.startMG('dogs')"); time.sleep(3.2)
    d = ev("__features.MG.dogs[1]"); ev(f"__game.P.x={d['x'] - 90}; __game.P.y={d['y']}")
    seen_windup = False
    for _ in range(60):
        time.sleep(.05)
        st = ev("__features.MG && __features.MG.dogs && __features.MG.dogs.map(d => d.st).join(',')") or ''
        if 'windup' in st: seen_windup = True; pg.screenshot(path="test/m4_dog_windup.png")
        if ev("__features.MG.phase") != 'run': break
    check(seen_windup, "a dog telegraphs its lunge ('!')")
    r = mg(); check(r and r['phase'] == 'lose', f"dog catches a standing Arek ({r and r['msg']})"); pg.keyboard.press("Escape")
    ev("__features.startMG('dogs')"); time.sleep(3.1)
    for e in ev("__features.MG.eggs"): ev(f"__game.P.x={e['x']}; __game.P.y={e['y']}"); time.sleep(.04)
    time.sleep(.15); r = mg(); check(r and r['phase'] == 'win', f"dogs: all eggs -> win ({r})"); pg.keyboard.press("Escape")

    # ---- skeet: click on the flying moorhens
    ev("__features.startMG('skeet')"); time.sleep(3.2)
    shots = 0
    t_end = time.time() + 40
    while time.time() < t_end and ev("__features.MG && __features.MG.phase") == 'run':
        tgt = ev("""(() => { const M = __features.MG, c = ARK.camera; const t = M.targets.find(t => t.alive && t.t > .25);
                   if (!t || M.reload > 0 || M.barrel <= 0) return null; const r = c.S(t.x, t.y - t.z); return [r[0], r[1]]; })()""")
        if tgt:
            box = pg.evaluate("(() => { const r = document.getElementById('game').getBoundingClientRect(); const c = document.getElementById('game'); return [r.left, r.top, r.width / c.width, r.height / c.height]; })()")
            pg.mouse.click(box[0] + tgt[0] * box[2], box[1] + tgt[1] * box[3]); shots += 1
            if shots == 3: pg.screenshot(path="test/m5_skeet.png")
        time.sleep(.05)
    r = mg(); hits = ev("__features.MG && __features.MG.hits")
    check(r and r['phase'] == 'win', f"skeet win by aiming at targets (hits {hits}, {r})")
    pg.screenshot(path="test/m6_skeet_result.png"); pg.keyboard.press("Escape")

    # ---- ducks: the former "kurki" game now lives at a separate south-east venue
    ev("__features.startMG('ducks')"); time.sleep(3.2)
    shots = 0; t_end = time.time() + 40
    while time.time() < t_end and ev("__features.MG && __features.MG.phase") == 'run':
        tgt = ev("""(() => { const M = __features.MG, c = ARK.camera; const t = M.targets.find(t => t.alive && t.t > .25);
                   if (!t || M.reload > 0 || M.barrel <= 0) return null; const r = c.S(t.x, t.y - t.z); return [r[0], r[1]]; })()""")
        if tgt:
            box = pg.evaluate("(() => { const r = document.getElementById('game').getBoundingClientRect(); const c = document.getElementById('game'); return [r.left, r.top, r.width / c.width, r.height / c.height]; })()")
            pg.mouse.click(box[0] + tgt[0] * box[2], box[1] + tgt[1] * box[3]); shots += 1
        time.sleep(.05)
    r = mg(); check(r and r['phase'] == 'win', f"ducks win by aiming at targets ({r})"); pg.keyboard.press("Escape")

    # ---- mowing: holding SPACE while walking paints every pitch strip green
    ev("__features.startMG('mowing')")
    pg.wait_for_function("__features.MG && __features.MG.phase === 'run'")
    fp = ev("__game.MAP.football_pitch")
    pg.keyboard.down("ArrowRight"); pg.keyboard.down("Space")
    for cy in range(10):
        for cx in range(7):
            ev(f"__game.P.x={fp['cx'] - fp['w'] / 2 + (cx + .5) * fp['w'] / 7}; __game.P.y={fp['cy'] - fp['h'] / 2 + (cy + .5) * fp['h'] / 10}")
            # Teleports must survive until the frame-driven update actually records this tile.
            pg.wait_for_function("key => __features.MG.cut.has(key)", arg=f'{cx},{cy}', timeout=3000)
    pg.keyboard.up("Space"); pg.keyboard.up("ArrowRight")
    pg.wait_for_function("__features.MG.phase === 'win'", timeout=3000)
    r = mg(); check(r and r['phase'] == 'win', f"mowing covers the pitch ({r})"); pg.keyboard.press("Escape")

    # ---- save + quest log
    q = ev("JSON.stringify(Object.fromEntries(Object.entries(__game.Q.mg).map(([k, v]) => [k, {won: v.won, medal: v.medal, best: v.best}])))")
    print('mg save:', q)
    check(all(ev(f"!!(__game.Q.mg.{k} && __game.Q.mg.{k}.won)") for k in ['pig', 'dogs', 'skeet', 'ducks', 'mowing']), "all five minigames recorded as won")
    check(not errs, f"no page errors {errs}")
    b.close()
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
