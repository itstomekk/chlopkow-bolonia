"""Headless test of the four minigames (race, pig, dogs, skeet): win/lose paths, medals, retry, ghost, off-track slowdown.
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
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL); pg.wait_for_function("!!(window.__game && window.__features && window.__features.startMG)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__features && window.__features.startMG)")
    pg.keyboard.press("KeyN"); time.sleep(.2)
    ev = pg.evaluate
    mg = lambda: ev("__features.MG && {phase: __features.MG.phase, type: __features.MG.type, medal: __features.MG.medal, msg: __features.MG.msg}")

    # ---- race: win by driving through the checkpoints, ghost gets stored, then retry shows the ghost
    ev("__features.startMG('race')"); time.sleep(3.3)
    tr = ev("__game.MAP.track")
    for lap in range(2):
        for k in range(1, 17):
            a = math.pi / 2 + k * 2 * math.pi / 16
            ev(f"__game.P.x={tr['cx'] + math.cos(a) * tr['rx']}; __game.P.y={tr['cy'] + math.sin(a) * tr['ry']}"); time.sleep(.07)
    time.sleep(.2); r = mg(); check(r and r['phase'] == 'win', f"race win -> {r}")
    check(r and r['medal'] == 3, "race teleport-lap earns gold")
    check(ev("!!(__game.Q.mg.race.ghost && __game.Q.mg.race.ghost.length)"), "race ghost saved")
    pg.screenshot(path="test/m1_race_result.png")
    time.sleep(.6); pg.keyboard.press("KeyR"); time.sleep(3.6)
    check(ev("__features.MG.phase === 'run' && !!__features.MG.ghost"), "retry restarts race with ghost")
    # off-track slowdown: walk onto the infield grass
    ev(f"__game.P.x={tr['cx']}; __game.P.y={tr['cy'] + tr['ry'] - 60}")
    x0 = ev("__game.P.x"); pg.keyboard.down("ArrowRight"); time.sleep(.5); pg.keyboard.up("ArrowRight"); x1 = ev("__game.P.x")
    check(0 < x1 - x0 < 45, f"off-track speed reduced ({x1 - x0:.0f}px in .5s)")
    pg.screenshot(path="test/m2_race_ghost.png")
    pg.keyboard.press("Escape"); time.sleep(.2)
    # race lose: stand still
    ev("__features.startMG('race')"); time.sleep(3.2 + 16.8)
    r = mg(); check(r and r['phase'] == 'lose', f"race idle -> lose ({r and r['msg']})"); pg.keyboard.press("Escape")

    # ---- pig: catch → medal by time; timeout → lose
    ev("__features.startMG('pig')"); time.sleep(3.3)
    pig = ev("__features.MG.pig"); ev(f"__game.P.x={pig['x']}; __game.P.y={pig['y']}"); time.sleep(.2)
    r = mg(); check(r and r['phase'] == 'win' and r['medal'] == 3, f"pig quick catch = gold ({r})"); pg.screenshot(path="test/m3_pig_win.png"); pg.keyboard.press("Escape")

    # ---- dogs: lose to a lunge, then win by collecting eggs
    ev("__features.startMG('dogs')"); time.sleep(3.2)
    d = ev("__features.MG.dogs[1]"); ev(f"__game.P.x={d['x'] - 90}; __game.P.y={d['y']}")
    seen_windup = False
    for _ in range(40):
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

    # ---- save + quest log
    q = ev("JSON.stringify(Object.fromEntries(Object.entries(__game.Q.mg).map(([k, v]) => [k, {won: v.won, medal: v.medal, best: v.best}])))")
    print('mg save:', q)
    check(all(ev(f"!!(__game.Q.mg.{k} && __game.Q.mg.{k}.won)") for k in ['race', 'pig', 'dogs', 'skeet']), "all four minigames recorded as won")
    check(not errs, f"no page errors {errs}")
    b.close()
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
