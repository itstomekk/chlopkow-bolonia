"""BIJATYKA follows original LF2 physics and combat rules (numbers from F.LF global.js / stock davis.dat), in our units.

Units: S = 100 px standing hurtbox / 62 LF2 px Davis body = 1.6129 px per LF2 px; 1 TU = 1/30 s = 2 simulation ticks.
Run: ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/brawl_lf2_physics_test.py
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
FAILS = []
S = 100 / 62          # px per LF2 px
TU = 1 / 30           # s


def check(ok, msg):
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


def near(a, b, tol):
    return abs(a - b) <= tol


F = "window.ARK.brawl.fight"
RESET = f"""() => {{ const F = {F}.fighters; for (const f of F) {{ f.st = 'stand'; f.t = 0; f.frameT = 0; f.inv = 0; f.fall = 0; f.bdef = 0; f.vx = f.vy = f.vz = 0; f.y = 0; f.hold = null; f.grabbing = null; f.grabbedBy = null; f.hitstop = 0; f.running = 0; f.hist = []; f.ko = false; f.ammo = 0; f.hp = f.hpMax; f.hpDark = f.hpMax; f.burn = 0; f.mp = 500; f.buf = null; f.queueAtk = false; f.thrownBy = null; f.hitSet = new Set(); f.tap = {{ left: -1, right: -1 }}; }}
  F[0].x = 100; F[0].z = 100; F[0].face = 1; F[1].x = 900; F[1].z = 100; F[1].face = -1; {F}.items = []; {F}.balls = []; }}"""
# record n ticks of fighter 0: [x, y, z, st, vx, vy]
REC = f"""n => {{ const f = {F}.fighters[0], out = []; for (let i = 0; i < n; i++) {{ window.ARK.brawl.step(1); out.push([f.x, f.y, f.z, f.st, f.vx, f.vy]); }} return out; }}"""


def step(page, ticks):
    page.evaluate("n => window.ARK.brawl.step(n)", ticks)


def ev(page, js, arg=None):
    return page.evaluate(js, arg) if arg is not None else page.evaluate(js)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errs, bad = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("response", lambda r: bad.append(r.url) if r.status >= 400 else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_function("window.ARK && window.ARK.brawl && window.ARK.brawl.venue")
    ev(page, "localStorage.removeItem('ark_brawl_keys_v1'); localStorage.removeItem('ark_brawl_slots_v1'); localStorage.removeItem('ark_brawl_opts_v1')")
    if ev(page, "window.ARK.scene") != "play":
        page.keyboard.press("KeyN")
        page.locator("#player-name-input").fill("Pilot")
        page.keyboard.press("Enter")
        page.wait_for_function("window.ARK.scene === 'play'")
    ev(page, "window.ARK.brawl.open()")
    ev(page, "window.ARK.brawl.setOpts({stage:'shop', items:false, sound:false})")
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'human',fighter:'edytka',ctrl:'kb2',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    ev(page, "window.ARK.brawl.loaded()")
    page.locator("#brawl-start").click()
    page.wait_for_function(f"{F} && {F}.phase === 'fight'")
    ev(page, f"{F}.paused = true")

    # ---- constants
    k = ev(page, "({S: window.ARK.brawl.LF2.S, pxtu: window.ARK.brawl.PXTU, grav: window.ARK.brawl.LF2.gravity, hp: Object.values(window.ARK.brawl.FIGHTERS).map(f => f.hp), mv: Object.values(window.ARK.brawl.FIGHTERS).some(f => 'walk' in f || 'run' in f)})")
    check(near(k["S"], S, 1e-9) and near(k["pxtu"], S * 30, 1e-6) and k["grav"] == 1.7, f"scale S = 100/62 and gravity 1.7 px/TU^2 ({k['S']:.4f}, {k['pxtu']:.1f} px/s per px/TU)")
    check(all(h == 500 for h in k["hp"]) and not k["mv"], "every fighter has LF2 hp 500 and Davis' movement (no per-fighter walk/run)")

    # ---- walk 5 px/TU, run 10 px/TU
    ev(page, RESET)
    page.keyboard.down("KeyD")
    step(page, 20)
    x0 = ev(page, f"{F}.fighters[0].x")
    step(page, 60)       # 30 TU
    x1 = ev(page, f"{F}.fighters[0].x")
    page.keyboard.up("KeyD")
    check(near((x1 - x0) / 30, 5 * S, 0.05), f"walk speed 5 px/TU = {5 * S:.2f} px/TU = {5 * S * 30:.0f} px/s (measured {(x1 - x0) / 30:.3f} px/TU)")

    ev(page, RESET)
    ev(page, f"{F}.fighters[0].x = 60")
    page.keyboard.down("KeyD"); step(page, 3); page.keyboard.up("KeyD"); step(page, 3); page.keyboard.down("KeyD")
    step(page, 16)
    running = ev(page, f"{F}.fighters[0].running")
    x0 = ev(page, f"{F}.fighters[0].x")
    step(page, 60)
    x1 = ev(page, f"{F}.fighters[0].x")
    page.keyboard.up("KeyD")
    check(running == 1 and near((x1 - x0) / 30, 10 * S, 0.1), f"run speed 10 px/TU = {10 * S:.2f} px/TU = {10 * S * 30:.0f} px/s (measured {(x1 - x0) / 30:.3f} px/TU)")

    # ---- standing jump: vy 16.3, gravity 1.7 -> apex 86.5 LF2 px, 20 TU in the air
    ev(page, RESET)
    page.keyboard.press("KeyG")
    rec = ev(page, REC, 80)
    ys = [r[1] for r in rec]
    air = [i for i, y in enumerate(ys) if y > 0]
    apex = max(ys)
    airtime = (air[-1] - air[0] + 1) / 60 if air else 0
    check(near(apex, 86.5 * S, 0.5), f"standing jump apex = 86.5 LF2 px = {86.5 * S:.1f} px (measured {apex:.1f})")
    check(near(airtime, 20 * TU, 1 / 60 + 1e-9), f"standing jump airtime = 20 TU = {20 * TU:.3f} s (measured {airtime:.3f} s)")
    check(all(abs(r[4]) < 1e-6 for r in rec if r[1] > 0), "a standing jump goes straight up (vx 0)")
    check(rec[-1][3] in ("stand", "land") and rec[-1][1] == 0, f"lands on the feet ({rec[-1][3]})")

    # forward jump: vx = jump_distance - 1 = 9 px/TU
    ev(page, RESET)
    page.keyboard.down("KeyD"); page.keyboard.press("KeyG")
    rec = ev(page, REC, 50)
    page.keyboard.up("KeyD")
    air = [i for i, r in enumerate(rec) if r[1] > 0]
    vxs = {round(rec[i][4] / (S * 30), 2) for i in air}
    check(vxs == {9.0}, f"forward jump moves 9 px/TU (jump_distance - 1) in the air ({vxs})")

    # ---- dash (run + jump): dash_distance - 1 = 17 px/TU, dash_height 10 -> apex 34.5 LF2 px, 12 TU of flight
    ev(page, RESET)
    ev(page, f"{F}.fighters[0].x = 60")
    page.keyboard.down("KeyD"); step(page, 3); page.keyboard.up("KeyD"); step(page, 3); page.keyboard.down("KeyD"); step(page, 16)
    page.keyboard.press("KeyG")
    rec = ev(page, REC, 50)
    page.keyboard.up("KeyD")
    ys = [r[1] for r in rec]
    air = [i for i, y in enumerate(ys) if y > 0]
    airtime = (air[-1] - air[0] + 1) / 60 if air else 0
    check(near(max(ys), 34.5 * S, 0.5) and near(airtime, 12 * TU, 1 / 60 + 1e-9), f"dash apex 34.5 LF2 px = {34.5 * S:.1f} px, 12 TU airtime (measured {max(ys):.1f} px, {airtime:.3f} s)")
    check(near(rec[air[1]][4] / (S * 30), 17, 0.01), f"dash speed 17 px/TU (measured {rec[air[1]][4] / (S * 30):.2f})")

    # ---- fall meter: punch fall 20 -> hurt, hurt, dizzy (>40), knocked down (>60); meter and guard recover per TU
    ev(page, RESET)
    seq = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl, out = []; o.x = a.x + 40; o.face = -1;
      for (let i = 0; i < 4; i++) {{ o.hitstop = 0; B.applyHit(a, o, B.ATK.punch, a.x); out.push(o.st); }} return out; }})()""")
    check(seq == ["hurt", "hurt", "dizzy", "fall"], f"punch (fall 20): hurt, hurt, dizzy on the 3rd hit, knocked down on the 4th ({seq})")
    ev(page, RESET)
    st = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl; o.x = a.x + 40; o.face = -1; B.applyHit(a, o, B.ATK.super, a.x); return [o.st, o.vy > 0]; }})()""")
    check(st == ["fall", True], f"super punch (fall 70) knocks a standing target down in one hit and launches it ({st})")
    ev(page, RESET)
    ev(page, f"{F}.fighters[1].fall = 40; {F}.fighters[1].bdef = 40; {F}.fighters[1].x = 500")
    step(page, 60)
    fb = ev(page, f"[{F}.fighters[1].fall, {F}.fighters[1].bdef]")
    check(near(fb[0], 40 - 0.45 * 30, 0.5) and near(fb[1], 40 - 0.5 * 30, 0.5), f"fall meter -0.45/TU and guard meter -0.5/TU (30 TU: {fb[0]:.1f}, {fb[1]:.1f})")

    # ---- guard: block while total bdefend <= 40 (GC.defend.break_limit; punch 16 -> the 3rd punch breaks), hit outside the guard sets the counter to 45
    ev(page, RESET)
    g = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl, out = []; o.x = a.x + 40; o.face = -1; o.st = 'defend';
      const hp0 = o.hp; for (let i = 0; i < 3; i++) {{ o.hitstop = 0; B.applyHit(a, o, B.ATK.punch, a.x); out.push([o.st, +o.bdef.toFixed(1), +(hp0 - o.hp).toFixed(1)]); }} return out; }})()""")
    check(g[0] == ["defend", 16, 2] and g[1] == ["defend", 32, 4] and g[2][0] == "brokendef" and g[2][1] == 48,
          f"guard: punches 1 and 2 blocked for 2 hp each (10 %), the 3rd breaks it (16+16+16 = 48 > 40) ({g})")
    ev(page, RESET)
    g = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl, out = []; o.x = a.x + 40; o.face = -1; o.st = 'defend'; o.bdef = 24;
      B.applyHit(a, o, B.ATK.punch, a.x); out.push([o.st, o.bdef]); o.hitstop = 0; B.applyHit(a, o, B.ATK.punch, a.x); out.push([o.st, o.bdef]); return out; }})()""")
    check(g[0] == ["defend", 40] and g[1][0] == "brokendef", f"guard total exactly 40 still holds, 41+ breaks ({g})")
    ev(page, RESET)
    g = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl; o.x = a.x + 40; o.face = -1; o.st = 'defend'; B.applyHit(a, o, B.ATK.super, a.x); return [o.st, o.bdef]; }})()""")
    check(g[0] in ("fall", "brokendef"), f"super punch (bdefend 60 > 40) cannot be guarded in one hit ({g})")
    ev(page, RESET)
    g = ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl; o.x = a.x + 40; o.face = -1; o.st = 'defend'; o.bdef = 0; a.x = o.x + 40; B.applyHit(a, o, B.ATK.punch, o.x + 80); return [o.st, o.bdef]; }})()""")
    check(g[0] == "hurt" and g[1] == 45, f"a hit from behind is not blocked and sets the guard counter to 45 ({g})")

    # ---- a falling body only takes hits with fall > 40; a lying fighter takes none
    def ball_hit(state, fall):
        ev(page, RESET)
        return ev(page, f"""(() => {{ const [a, o] = {F}.fighters; o.x = 400; o.z = 100; o.face = -1; o.st = '{state}'; o.t = 0; o.y = 60; o.vy = 0;
          {F}.balls.push({{ owner: a, team: a.team, item: 'apple', x: 360, z: 100, y: 90, vx: 300, dmg: 10, fall: {fall}, life: 1, spin: 0 }});
          const hp0 = o.hp; for (let i = 0; i < 6; i++) window.ARK.brawl.step(1); return hp0 - o.hp; }})()""")
    check(ball_hit("fall", 20) == 0 and ball_hit("fall", 40) == 0, "a falling fighter ignores hits with fall <= 40")
    check(ball_hit("fall", 70) > 0, "a falling fighter is hit by fall 70 (juggle)")
    check(ball_hit("jump", 20) > 0, "a jumping (not falling) fighter is hit normally")
    check(ball_hit("lying", 70) == 0, "a lying fighter cannot be hit")

    # ---- durations in TU: hurt 7, dizzy 28, lying 31 + getup 3, then 30 TU invulnerable
    def duration(setup_js, leave):
        ev(page, RESET)
        ev(page, setup_js)
        n = 0
        while n < 400 and ev(page, f"{F}.fighters[1].st") == leave:
            step(page, 1); n += 1
        return n / 2
    ev(page, RESET)
    hu = duration(f"(() => {{ const [a, o] = {F}.fighters; o.x = a.x + 40; o.hitstop = 0; window.ARK.brawl.applyHit(a, o, window.ARK.brawl.ATK.punch, a.x); o.hitstop = 0; }})()", "hurt")
    di = duration(f"(() => {{ const [a, o] = {F}.fighters; o.x = a.x + 40; o.fall = 25; window.ARK.brawl.applyHit(a, o, window.ARK.brawl.ATK.punch, a.x); o.hitstop = 0; o.fall = 0; }})()", "dizzy")
    check(near(hu, 7, 0.5) and near(di, 28, 0.5), f"hurt lasts 7 TU, dizzy 28 TU (measured {hu} / {di})")
    ly = duration(f"(() => {{ const o = {F}.fighters[1]; o.st = 'lying'; o.t = 0; o.vx = 0; }})()", "lying")
    ev(page, RESET)
    ev(page, f"(() => {{ const o = {F}.fighters[1]; o.st = 'lying'; o.t = 0; }})()")
    step(page, 63)
    inv = ev(page, f"({{ st: {F}.fighters[1].st, inv: {F}.fighters[1].inv }})")
    check(near(ly, 31, 0.5) and inv["st"] == "getup" and near(inv["inv"], 30 * TU, 0.05), f"lying 31 TU, then getup with 30 TU invulnerability (lying {ly} TU, {inv})")

    # ---- knock-down arc: super punch dvy -10, gravity 1.7 -> flight time and landing slide
    ev(page, RESET)
    ev(page, f"(() => {{ const [a, o] = {F}.fighters; o.x = 400; o.face = -1; window.ARK.brawl.applyHit(a, o, window.ARK.brawl.ATK.super, o.x - 40); o.hitstop = 0; }})()")
    rec = ev(page, f"""n => {{ const o = {F}.fighters[1], out = []; for (let i = 0; i < n; i++) {{ window.ARK.brawl.step(1); out.push([o.y, o.x, o.st]); }} return out; }}""", 140)
    peak = max(r[0] for r in rec)
    check(near(peak, sum(max(0, 10 - 1.7 * i) for i in range(7)) * S, 1.0), f"knock-down peak follows vy 10 px/TU (super punch dvy -10) and gravity 1.7 ({peak:.1f} px)")
    check(rec[-1][2] in ("lying", "getup", "stand"), f"knocked-down fighter ends up lying/standing ({rec[-1][2]})")

    # ---- rowing: JUMP in the 4 TU window of the fall animation flips; the flip hovers 3 TU
    ev(page, RESET)
    ev(page, f"(() => {{ const [a, o] = {F}.fighters; o.x = 400; o.face = -1; window.ARK.brawl.applyHit(a, o, window.ARK.brawl.ATK.super, o.x - 40); o.hitstop = 0; o.ctrl = 'kb2'; }})()")
    step(page, 12)                   # 6 TU after the hit: inside frame 182 (5..9 TU)
    page.keyboard.press("Slash")     # kb2 jump
    step(page, 1)
    check(ev(page, f"{F}.fighters[1].st") == "flip", "JUMP 6 TU after being knocked down flips (LF2 rowing, frame 182)")

    # ---- regen: +1 hp / 12 TU up to the dark bound, +1 + floor(lost / 100) mp / 3 TU
    ev(page, RESET)
    ev(page, f"(() => {{ const f = {F}.fighters[0]; f.hp = 400; f.hpDark = 400; f.mp = 100; }})()")
    step(page, 180)                  # 90 TU
    r = ev(page, f"[{F}.fighters[0].hp, {F}.fighters[0].mp]")
    check(near(r[1], 100 + 30 * 2, 2), f"mp +1 + floor(100 hp lost / 100) = +2 per 3 TU (90 TU: mp {r[1]:.1f})")
    ev(page, f"(() => {{ const f = {F}.fighters[0]; f.hp = 400; f.hpDark = 500; f.mp = 500; }})()")
    step(page, 180)
    check(near(ev(page, f"{F}.fighters[0].hp"), 400 + 90 / 12, 1), "hp +1 per 12 TU up to the dark bound (90 TU: +7.5)")

    # ---- roll: run + DEFEND = 12 TU at 9 px/TU, no bdy
    ev(page, RESET)
    ev(page, f"{F}.fighters[0].x = 60")
    page.keyboard.down("KeyD"); step(page, 3); page.keyboard.up("KeyD"); step(page, 3); page.keyboard.down("KeyD"); step(page, 16)
    x0 = ev(page, f"{F}.fighters[0].x")
    page.keyboard.up("KeyD"); page.keyboard.press("KeyH")
    step(page, 2)
    st_roll = ev(page, f"{F}.fighters[0].st")
    x_mid = x0
    step(page, 26)
    x1 = ev(page, f"{F}.fighters[0].x")
    check(st_roll == "roll" and (x1 - x0) >= 100 * S, f"roll slides 12 TU at 9 px/TU (>= {100 * S:.0f} px; measured {x1 - x0:.0f} px, state {st_roll})")

    # ---- Davis attacks through the real inputs: run attack 55 / dash attack 80 / jump attack 60 injury (hp regen may give back up to ~3)
    def attack(kind, off):
        ev(page, RESET)
        ev(page, f"(() => {{ const [a, o] = {F}.fighters; a.x = 60; o.x = 60 + {off}; o.z = a.z; o.face = -1; }})()")
        if kind in ("run", "dash"):
            page.keyboard.down("KeyD"); step(page, 6); page.keyboard.up("KeyD"); step(page, 6); page.keyboard.down("KeyD"); step(page, 16)
            ev(page, f"(() => {{ const [a, o] = {F}.fighters; o.x = a.x + {off}; }})()")
            if kind == "dash":
                page.keyboard.press("KeyG"); step(page, 2)
            page.keyboard.press("KeyF")
            page.keyboard.up("KeyD")
        else:
            page.keyboard.press("KeyG"); step(page, 30)
            page.keyboard.press("KeyF")
        res = ev(page, "n => { const [a, o] = window.ARK.brawl.fight.fighters, hp0 = o.hp; for (let i = 0; i < n; i++) window.ARK.brawl.step(1); return [hp0 - o.hp, o.st]; }", 90)
        ev(page, f"{F}.fighters[0].st = 'stand'")
        return res
    ra, da, ja = attack("run", 150), attack("dash", 220), attack("jump", 40)
    # the lunging attacker catches the flung victim again once vrest 7 TU is over: frame 87 hit 55, then frame 88 hit 40 (55 + 40 = 95, minus hp regen)
    check(88 <= ra[0] <= 95 and ra[1] in ("fall", "lying", "getup", "stand"), f"run attack: 55 injury (+ 40 from the 2nd itr after vrest), fall 70 knocks down ({ra})")
    check(76 <= da[0] <= 80 and da[1] in ("fall", "lying", "getup", "stand"), f"dash attack: 80 injury, fall 70 knocks down ({da})")
    check(56 <= ja[0] <= 60 and ja[1] in ("fall", "lying", "getup", "stand"), f"jump attack: 60 injury, fall 70 knocks down ({ja})")

    # ---- stock davis.dat attack table (LF2 1.9): injury / fall / bdefend / dvx / dvy / arest / vrest per itr
    tab = ev(page, """(() => { const B = window.ARK.brawl, k = B.LF2.atk, ph = a => a.itr.map(i => [i.injury, i.fall, i.bdef, i.dvx, i.dvy === undefined ? null : i.dvy, i.arest || 0, i.vrest || 0]);
      return Object.fromEntries(Object.keys(k).map(n => [n, ph(k[n])])); })()""")
    want = {
        "punch": [[20, 20, 16, 2, None, 0, 0]], "punch2": [[20, 20, 16, 2, None, 0, 0]],
        "super": [[40, 70, 60, 3, -10, 15, 0], [40, 70, 60, 7, -13, 15, 0]],
        "runatk": [[55, 70, 60, 20, None, 0, 7], [40, 70, 60, 17, None, 0, 10]],
        "jkick": [[60, 70, 30, 9, -5, 15, 0], [60, 70, 30, 9, -5, 15, 0]],
        "dashkick": [[80, 70, 60, 14, -5, 9, 0], [80, 70, 60, 14, -5, 9, 0]],
    }
    check(tab == want, f"Davis attack table matches stock davis.dat ({tab})")
    chk = ev(page, "(() => { const B = window.ARK.brawl; return [B.LF2.bdef.limit, B.LF2.bdef.ignore === undefined, B.ATK.punch.dmg, B.ATK.super.dmg, B.ATK.jkick.dmg, B.ATK.runatk.dmg, B.ATK.dashkick.dmg]; })()")
    check(chk == [40, True, 20, 40, 60, 55, 80], f"guard break limit 40, no 'bdefend > 60 ignores guard' rule, injuries 20 / 40 / 60 / 55 / 80 ({chk})")

    # ---- vrest: the run attack hits the same victim again only after 7 TU (frame 87) / 10 TU (frame 88); arest: super punch waits 15 TU between hits
    def melee(atk, t_tu, setup=""):
        return ev(page, f"""(() => {{ const [a, o] = {F}.fighters, B = window.ARK.brawl; a.x = 100; a.z = o.z = 100; a.face = 1; o.x = 155; o.face = -1; a.st = 'stand';
          o.st = 'stand'; o.fall = 0; o.hitstop = 0; o.inv = 0; o.y = 0; o.vy = 0; o.hp = o.hpDark = 500; {setup}
          a.t = {t_tu} / 30; B.meleeCheck(a, B.ATK.{atk}); return 500 - o.hp; }})()""")
    ev(page, RESET)
    h1 = melee("runatk", 6)
    h2 = melee("runatk", 6)                 # immediately again: vrest 7 TU blocks it
    step(page, 10)                          # 5 TU
    h3 = melee("runatk", 6)
    step(page, 6)                           # 8 TU after the first hit
    h4 = melee("runatk", 6)
    check(h1 == 55 and h2 == 0 and h3 == 0 and h4 == 55, f"run attack: hit 55, vrest 7 TU blocks a re-hit at 0 and 5 TU, hits again after 8 TU ({h1}, {h2}, {h3}, {h4})")
    ev(page, RESET)
    melee("runatk", 6); step(page, 16)      # 8 TU later the 7 TU rest of the first itr is over: the second itr (frame 88) hits and sets vrest 10
    h5 = melee("runatk", 8)
    h6 = melee("runatk", 8)
    step(page, 14)                          # 7 TU after the second hit: its vrest 10 TU still blocks
    h7 = melee("runatk", 8)
    step(page, 8)                           # 11 TU after the second hit
    h8 = melee("runatk", 8)
    check(h5 == 40 and h6 == 0 and h7 == 0 and h8 == 40, f"run attack frame 88 itr: injury 40, vrest 10 TU blocks a re-hit at 0 and 7 TU, hits again after 11 TU ({h5}, {h6}, {h7}, {h8})")
    ev(page, RESET)
    a1 = melee("super", 5)
    a2 = melee("super", 16)                 # second itr (frame 38) while arest 15 TU runs
    step(page, 20)                          # 10 TU: still resting
    a3 = melee("super", 16)
    step(page, 22)                          # 21 TU after the first hit
    a4 = melee("super", 16)
    check(a1 == 40 and a2 == 0 and a3 == 0 and a4 == 40, f"super punch: injury 40, arest 15 TU blocks the second itr until 15 TU passed ({a1}, {a2}, {a3}, {a4})")

    check(not errs, f"no page errors ({errs[:3]})")
    check(not bad, f"no failed requests ({bad[:3]})")
    browser.close()

print("RESULT:", "PASS" if not FAILS else f"FAIL {len(FAILS)}")
if not FAILS:
    print("PASS brawl_lf2_physics_test")
sys.exit(1 if FAILS else 0)
