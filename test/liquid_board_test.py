"""WOJNA PŁYNÓW / LIQUID WAR minigame (docs/js/boards/liquid.js on docs/js/board.js).

Static checks of the generated levels (docs/data/liquid-maps.json vs docs/map.json + map_collide.png), then a browser run:
venue flag -> lobby -> rounds on every level -> rules (constant total, conversions, elimination, timer end) -> controls
(keyboard, mouse/touch) -> CPU cursor -> saves -> performance -> sprint board still on its old contract.
Usage (ALWAYS through the isolated runner, a direct run publishes arrivals to public Nostr and cloud):
  ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/liquid_board_test.py
Screenshots go to ARK_SHOTS (default asset-review/2026-10-15-liquid)."""
import json, os, sys, time
from collections import deque
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = os.environ.get("ARK_SHOTS", os.path.join(ROOT, "asset-review", "2026-10-15-liquid"))
os.makedirs(SHOTS, exist_ok=True)
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)


# ------------------------------------------------------------------ static: the levels are built from OUR map
GW, GH = 160, 84
mp = json.load(open(os.path.join(ROOT, "docs/map.json"), encoding="utf-8"))
lm = json.load(open(os.path.join(ROOT, "docs/data/liquid-maps.json"), encoding="utf-8"))
collide = np.array(Image.open(os.path.join(ROOT, "docs/img/map_collide.png")))
check(lm["source"]["w"] == mp["w"] and lm["source"]["h"] == mp["h"] and lm["source"]["bbox"] == mp["bbox"], "liquid-maps.json was built from the current map.json size and bbox")
check(collide.shape == (mp["h"], mp["w"]), "collision mask matches map.json")
check(len(lm["levels"]) >= 3, f"at least 3 levels ({len(lm['levels'])})")
check(len({l["cell"] for l in lm["levels"]}) >= 3, f"levels use at least 3 different zoom levels {[(l['id'], l['cell']) for l in lm['levels']]}")
check(len({l["id"] for l in lm["levels"]}) == len(lm["levels"]) and all(l["name"]["pl"] and l["name"]["en"] for l in lm["levels"]), "unique ids, PL and EN names")


def components(op):
    lab = np.zeros(op.shape, np.int32); sizes = [0]
    for sy, sx in zip(*np.nonzero(op)):
        if lab[sy, sx]: continue
        n = len(sizes); sizes.append(0); lab[sy, sx] = n; q = deque([(sy, sx)])
        while q:
            y, x = q.popleft(); sizes[n] += 1
            for dx, dy in [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < GW and 0 <= ny < GH) or not op[ny, nx] or lab[ny, nx]: continue
                if dx and dy and not (op[y, nx] and op[ny, x]): continue
                lab[ny, nx] = n; q.append((ny, nx))
    return lab, sizes


for l in lm["levels"]:
    rows = l["rows"]; op = np.array([[ch == "." for ch in r] for r in rows])
    ok_shape = len(rows) == GH and all(len(r) == GW for r in rows)
    lab, sizes = components(op)
    check(ok_shape and op.sum() == l["open"], f"{l['id']}: {GW}x{GH} grid, open count matches ({l['open']})")
    check(len(sizes) == 2, f"{l['id']}: exactly one connected open region ({len(sizes) - 1})")
    check(not (op[0].any() or op[-1].any() or op[:, 0].any() or op[:, -1].any()), f"{l['id']}: border is wall")
    a = l["anchors"]
    check(len(a) == 4 and all(op[y, x] and lab[y, x] == 1 for x, y in a), f"{l['id']}: four start areas, open and in the region")
    dmin = min(((a[i][0] - a[j][0]) ** 2 + (a[i][1] - a[j][1]) ** 2) ** .5 for i in range(4) for j in range(i + 1, 4))
    check(dmin >= 30, f"{l['id']}: start areas are {dmin:.0f} cells apart at least")
    check(op.sum() * 0.30 / 4 >= 100 and 0.25 < op.mean() < 0.97, f"{l['id']}: room for four armies ({int(op.sum())} open cells, {op.mean():.0%} open) and a real maze (walls exist)")
    x0, y0 = l["origin"]; k = l["cell"]
    check(0 <= x0 and 0 <= y0 and x0 + GW * k <= mp["w"] and y0 + GH * k <= mp["h"], f"{l['id']}: crop window lies inside the village map")
    # the walls really come from the map: re-derive the share of blocked mask pixels in wall cells vs open cells
    sub = collide[y0:y0 + GH * k, x0:x0 + GW * k] > 64
    frac = sub.reshape(GH, k, GW, k).mean(axis=(1, 3))
    inner = np.zeros_like(op); inner[1:-1, 1:-1] = True
    check(frac[~op & inner].mean() > frac[op].mean() * 2, f"{l['id']}: wall cells are the blocked cells of map_collide.png ({frac[~op & inner].mean():.2f} vs {frac[op].mean():.2f})")

# venue is on open ground (the collision mask at the flag)
cx, cy = mp["corral"]["cx"] + 160, mp["corral"]["cy"]
check(not (collide[cy - 12:cy + 12, cx - 12:cx + 12] > 0).any(), f"venue ({cx},{cy}) next to the corral stands on open ground")

# ------------------------------------------------------------------ browser
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; bad_urls = []
    pg.on("response", lambda r: bad_urls.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text and "WebSocket is already in CLOSING or CLOSED state" not in m.text else None)
    pg.goto(URL); pg.wait_for_function("!!(window.__game && window.__board && window.__liquid)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__game && window.__board && window.__liquid)")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("Tester"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'"); time.sleep(.3)
    ev = pg.evaluate

    def slots(*spec):   # (type, ctrl) per slot, substances fixed
        subs = ["slurry", "melior", "milk", "orange"]; chars = ["arek", "damian", "edytka", "soltys"]; out = []
        for i in range(4):
            t, c = spec[i] if i < len(spec) else ("off", "kb1")
            out.append({"type": t, "char": chars[i], "ctrl": c, "name": f"G{i + 1}" if t == "human" else "", "sub": subs[i]})
        return json.dumps(out)

    def begin(level, spec, tune="{}"):
        ev(f"Object.keys(__liquid.tune).forEach(k => delete __liquid.tune[k]); Object.assign(__liquid.tune, {tune})")
        if not ev("!!__board.ui"): ev("__board.open('liquid')")
        pg.wait_for_function("__liquid.status === 'ok'")
        ev(f"__board.setOpts({{level: '{level}'}})"); ev(f"__board.setSlots({slots(*spec)})")
        ev("__board.start()"); ev("__board.pause()"); ev("__board.step(215)")   # through the 3.4 s countdown

    def leave():
        ev("__board.toLobby()")

    # ---- the descriptor, the flag, the entry
    check(ev("window.ARK_BOARDS.liquid && ARK_BOARDS.liquid.title(true)") == "WOJNA PŁYNÓW" and ev("ARK_BOARDS.liquid.title(false)") == "LIQUID WAR", "titles: WOJNA PŁYNÓW / LIQUID WAR")
    check(ev("!JSON.stringify(Object.values(ARK_BOARDS).map(d => d.title(true) + d.sub(true) + d.logName(true))).includes('GNOJÓWEK')"), "the old working title WOJNA GNOJÓWEK appears nowhere")
    v = ev("__board.venues.liquid"); mc = ev("__game.MAP.corral")
    check(v == {"x": mc["cx"] + 160, "y": mc["cy"]}, f"flag venue is read from the current map.json: corral + offset -> {v}")
    check(ev("__liquid.VENUE.kind") == "flag" and ev("__liquid.venue({MAP: {corral: {cx: 10, cy: 20}}})") == {"x": 170, "y": 20}, "venue is a descriptor resolved at runtime (kind 'flag', ready for a building kind)")
    near = ev(f"ARK.HOOKS.near.flatMap(f => f(__game.P)).filter(c => Math.hypot(c.x - {v['x']}, c.y - {v['y']}) < 40).map(c => c._board || 'other')")
    check(near == ["liquid"], f"exactly one interaction at the flag: {near}")
    ev(f"ARK.teleport({v['x'] + 6}, {v['y'] + 4})"); time.sleep(.4)
    pg.keyboard.press("KeyE")
    pg.wait_for_function("!!__board.ui", timeout=4000)
    check(ev("__board.ui.id === 'liquid' && __board.ui.lobby"), "E at the flag opens the minigame lobby")
    check(ev("ARK.HOOKS.busy.some(f => f())"), "village is busy while the minigame is open")
    pg.wait_for_function("__liquid.status === 'ok'")
    time.sleep(.6)
    check(pg.locator("#board-overlay .board-slot").count() == 4, "four slots")
    order = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k]')].map(e => e.dataset.k).join()")
    check(order == "name,type,char,sub,ctrl", f"slot controls: name, human/CPU, character, substance, controls ({order})")
    subs_pl = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=sub] option')].map(o => o.textContent)")
    check(subs_pl == ["GNOJÓWKA", "MELIORANKA", "MLEKO", "ORANŻADA", "KOMPOT", "BIMBER"], f"six substances (PL): {subs_pl}")
    lev_pl = ev("[...document.querySelectorAll('.board-opt[data-opt=level] option')].map(o => o.textContent)")
    check(len(lev_pl) == len(lm["levels"]) + 1 and lev_pl[-1] == "LOSOWY" and all(l["name"]["pl"] in lev_pl for l in lm["levels"]), f"lobby picks a level or random: {lev_pl}")
    check(ev("document.querySelector('#board-lobby h2').textContent") == "WOJNA PŁYNÓW", "lobby heading")
    check(ev("__board.ui.slots.map(s => s.sub).join()") == "slurry,melior,milk,orange", "default substances")
    check(ev("__liquid.LEVELS.every(l => { const d = __liquid.data.levels.find(x => x.id === l.id); return d && d.name.pl === l.pl && d.name.en === l.en; })"), "lobby level names equal the data file names")
    pg.screenshot(path=f"{SHOTS}/liquid_lobby_desktop.png")
    # duplicate substance blocks start
    arr = json.loads(slots(("human", "kb1"), ("cpu", "kb2"))); arr[1]["sub"] = "slurry"
    ev(f"__board.setSlots({json.dumps(arr)})"); pg.locator("#board-start").click(); time.sleep(.1)
    check(ev("__board.run === null") and "GNOJÓWKA" in pg.locator("#board-error").inner_text(), "two players with the same substance block the start")
    ev("__board.toLobby()")
    # level choice is remembered
    ev("__board.setOpts({level: 'church'})"); ev("__board.close()")
    ev("__board.open('liquid')"); time.sleep(.2)
    check(ev("__board.ui.opts.level") == "church", "lobby remembers the chosen level")
    ev("__board.close()")

    # ---- every level: 4 teams, constant total, valid occupancy, fighters only on open cells
    for l in lm["levels"]:
        begin(l["id"], [("human", "kb1"), ("cpu", "kb2"), ("cpu", "kb3"), ("cpu", "kb4")])
        g0 = ev("__board.state.game"); a0 = ev("__liquid.audit()")
        check(g0["level"] == l["id"] and g0["open"] == l["open"], f"{l['id']}: browser runs the level from the data file ({g0['open']} open cells)")
        check(3000 <= g0["total"] <= 4500 and all(t["count"] == g0["per"] for t in g0["teams"]), f"{l['id']}: {g0['total']} fighters, {g0['per']} per team")
        ev("__board.step(900)"); a1 = ev("__liquid.audit()"); g1 = ev("__board.state.game")
        check(a1["total"] == a0["total"] == a1["countsSum"] == a1["occupied"] and a1["bad"] == 0 and a1["byTeamMatches"] and a1["hpOk"], f"{l['id']}: total constant {a1['total']}, no overlaps, no fighter in a wall, health 1..max")
        check(g1["conv"] > 0, f"{l['id']}: conversions happen ({g1['conv']} in 900 ticks)")
        leave()

    # ---- rules on a controlled fight: two armies attack one idle team
    begin("church", [("human", "kb1"), ("human", "kb2"), ("human", "kb3")])
    ev("(() => { const s = __liquid.sim, a = __liquid.game.level.anchors[0]; for (const t of [1, 2]) { s.cur[t].x = a[0] + .5; s.cur[t].y = a[1] + .5; } })()")
    before = ev("__board.state.game.teams.map(t => t.count)")
    ev("__board.step(1500)"); g = ev("__board.state.game"); a = ev("__liquid.audit()")
    after = [t["count"] for t in g["teams"]]
    check(after[0] < before[0] * .9 and after[1] + after[2] > before[1] + before[2], f"a team whose cursor sits in the middle of two attacking armies loses fighters {before} -> {after}")
    check(g["conv"] > 0 and a["total"] == sum(before) == sum(after) and a["bad"] == 0, f"converted fighters are not removed: total {sum(after)} = {sum(before)}, {g['conv']} conversions")
    check(after[0] > 0 or g["teams"][0]["out"], "team 0 is either alive or flagged out")
    leave()
    # small armies, 2 against 1: someone is eliminated and the round ends on 'last one standing'
    begin("church", [("human", "kb1"), ("human", "kb2"), ("human", "kb3")], "{armyFrac: .01}")
    ev("(() => { const s = __liquid.sim, a = __liquid.game.level.anchors[0]; for (const t of [1, 2]) { s.cur[t].x = a[0] + .5; s.cur[t].y = a[1] + .5; } })()")
    ev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 6000) { __board.step(20); k += 20; } })()")
    s = ev("__board.state"); g = s["game"]
    check(s["phase"] == "done" and g["why"] == "last" and g["time"] < 89, f"round ends when one team is left ({g['why']} at {g['time']:.1f} s)")
    alive = [t for t in g["teams"] if t["count"] > 0]
    check(len(alive) == 1 and all(t["out"] for t in g["teams"] if t["count"] == 0) and all(t["outAt"] > 0 for t in g["teams"] if t["out"]), f"exactly one team left, the others flagged out with a tick: {[(t['count'], t['out'], t['outAt']) for t in g['teams']]}")
    res = s["results"]
    check(res[0]["place"] == 1 and abs(res[0]["score"] - 100) < .01 and res[1]["score"] == 0, f"winner holds 100% and is ranked first: {[(r['name'], r['score'], r['place']) for r in res]}")
    leave()

    # ---- timer end, ranking by count, save, medals, results screen
    ev("delete __game.Q.mg.liquid")
    begin("shop", [("human", "kb1"), ("cpu", "kb2"), ("cpu", "kb3"), ("cpu", "kb4")], "{roundSec: 12}")
    ev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 3000) { __board.step(10); k += 10; } })()")
    s = ev("__board.state"); g = s["game"]; res = s["results"]
    check(s["phase"] == "done" and g["why"] in ("time", "last") and 11.9 <= g["time"] <= 12.2 or g["why"] == "last", f"round ends at the timer ({g['why']} at {g['time']:.2f} s)")
    cnt = {t["slot"]: t["count"] for t in g["teams"]}
    ranked = [cnt[r["slot"]] for r in res]
    check(ranked == sorted(ranked, reverse=True), f"ranking is by fighter count {ranked}")
    check(abs(sum(r["score"] for r in res) - 100) < .3 and all(r["score"] == round(cnt[r["slot"]] / g["total"] * 100, 1) for r in res), f"scores are % of all fighters (0.1 precision), sum {sum(r['score'] for r in res):.1f}")
    q = ev("__game.Q.mg.liquid")
    check(q["tries"] == 1 and q["unit"] == "percent" and len(q["history"]) == 1 and q["best"] > 0, f"save: tries 1, percent unit, one human result ({q})")
    ev("__board.step(60)")
    pg.screenshot(path=f"{SHOTS}/liquid_results_desktop.png")
    lines = ev("(() => { const l = []; ARK.HOOKS.questLog.forEach(f => f(l)); return l.map(x => x[0]); })()")
    check(any("Wojna płynów" in x for x in lines), "quest log lists the minigame")
    leave()

    # ---- controls: real keys on two schemes at once, cursors never enter walls
    begin("church", [("human", "kb1"), ("human", "kb2"), ("off", "kb3"), ("off", "kb4")], "{roundSec: 600}")
    c0 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    pg.keyboard.down("ArrowRight"); pg.keyboard.down("KeyS"); ev("__board.step(40)"); pg.keyboard.up("ArrowRight"); pg.keyboard.up("KeyS")
    c1 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    check(c1[0][0] > c0[0][0] + 5 and abs(c1[0][1] - c0[0][1]) < .5, f"ArrowRight moves cursor 1 right {c0[0]} -> {c1[0]}")
    check(c1[1][1] > c0[1][1] + 5 and abs(c1[1][0] - c0[1][0]) < .5, f"S moves cursor 2 down (WASD) {c0[1]} -> {c1[1]}")
    pg.keyboard.down("ArrowUp"); pg.keyboard.down("ArrowLeft"); ev("__board.step(400)"); pg.keyboard.up("ArrowUp"); pg.keyboard.up("ArrowLeft")
    c2 = ev("__liquid.sim.cur[0]"); check(ev(f"__liquid.sim.open({c2['x']}, {c2['y']})") and c2["x"] >= 1 and c2["y"] >= 1, f"holding up+left into the corner stays on open ground ({c2['x']:.1f},{c2['y']:.1f})")
    # walls: park the cursor next to a wall and push into it
    pos = ev("""(() => { const s = __liquid.sim; for (let y = 5; y < 80; y++) for (let x = 5; x < 150; x++) if (s.open(x, y) && s.open(x + 1, y) && !s.open(x + 3, y) && !s.open(x + 2, y)) { s.cur[0].x = x + .5; s.cur[0].y = y + .5; return [x, y]; } return null; })()""")
    check(pos is not None, f"found a wall edge to push into {pos}")
    pg.keyboard.down("ArrowRight"); ev("__board.step(60)"); pg.keyboard.up("ArrowRight")
    c3 = ev("__liquid.sim.cur[0]"); check(ev(f"__liquid.sim.open({c3['x']}, {c3['y']})") and c3["x"] < pos[0] + 2.1, f"cursor cannot enter a wall ({pos} -> {c3['x']:.2f},{c3['y']:.2f})")
    leave()

    # ---- fighters flow around walls toward the cursor (distance field), not through them
    begin("church", [("human", "kb1"), ("human", "kb2")], "{roundSec: 600}")
    cen = "(() => { const s = __liquid.sim; let x = 0, y = 0, n = 0; for (let i = 0; i < s.total; i++) if (s.fteam[i] === 0) { x += s.fpos[i] % 160; y += (s.fpos[i] / 160 | 0); n++; } return [x / n, y / n]; })()"
    k0 = ev(cen); tgt = ev("(() => { const s = __liquid.sim; let best = null; for (let y = 5; y < 80; y += 3) for (let x = 5; x < 155; x += 3) if (s.open(x, y)) { const d = Math.hypot(x - 100, y - 40); if (!best || d < best[0]) best = [d, x, y]; } return best; })()")
    ev(f"(() => {{ const s = __liquid.sim; s.cur[0].x = {tgt[1]} + .5; s.cur[0].y = {tgt[2]} + .5; }})()")
    d0 = ((k0[0] - tgt[1]) ** 2 + (k0[1] - tgt[2]) ** 2) ** .5
    ev("__board.step(600)"); k1 = ev(cen)
    d1 = ((k1[0] - tgt[1]) ** 2 + (k1[1] - tgt[2]) ** 2) ** .5
    a = ev("__liquid.audit()")
    check(d1 < d0 * .6 and a["bad"] == 0, f"army flows to the cursor: centroid distance {d0:.0f} -> {d1:.0f} cells, no fighter in a wall")
    leave()

    # ---- mouse / touch pointer drags the cursor (real mouse events on the canvas)
    begin("village", [("human", "touch"), ("cpu", "kb2")], "{roundSec: 600}")
    ev("document.getElementById('board-canvas').focus()")
    geo = ev("(() => { const cv = document.getElementById('board-canvas'), r = cv.getBoundingClientRect(), d = cv.width / r.width, k = Math.min(cv.width / 960, cv.height / 540); return { l: r.left, t: r.top, d, k, cw: cv.width, ch: cv.height }; })()")
    toc = lambda bx, by: ((bx * geo["k"] + (geo["cw"] - 960 * geo["k"]) / 2) / geo["d"] + geo["l"], (by * geo["k"] + (geo["ch"] - 540 * geo["k"]) / 2) / geo["d"] + geo["t"])
    cs = ev("__liquid.sim.cur[0]"); goal = (cs["x"] + 40, cs["y"] + 10)
    gx, gy = toc(goal[0] * 6, 36 + goal[1] * 6)
    pg.mouse.move(*toc(cs["x"] * 6, 36 + cs["y"] * 6)); pg.mouse.down(); pg.mouse.move(gx, gy, steps=4); ev("__board.step(150)")
    ce = ev("__liquid.sim.cur[0]"); pg.mouse.up()
    check(ce["x"] > cs["x"] + 15, f"pointer drag steers the cursor ({cs['x']:.1f},{cs['y']:.1f}) -> ({ce['x']:.1f},{ce['y']:.1f}) toward {goal}")
    ev("__board.step(80)"); ce2 = ev("__liquid.sim.cur[0]")
    check(abs(ce2["x"] - ce["x"]) < .01 and abs(ce2["y"] - ce["y"]) < .01, "releasing the pointer stops the cursor")
    leave()

    # ---- CPU cursor moves toward the enemy and the CPU fights
    begin("farmyard", [("cpu", "kb1"), ("cpu", "kb2"), ("human", "kb3")], "{roundSec: 600}")
    c0 = ev("__liquid.sim.cur.map(c => [c.x, c.y])"); ev("__board.step(500)"); c1 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    mv = [((c1[i][0] - c0[i][0]) ** 2 + (c1[i][1] - c0[i][1]) ** 2) ** .5 for i in range(3)]
    check(mv[0] > 5 and mv[1] > 5 and mv[2] < .01, f"CPU cursors move ({mv[0]:.0f}, {mv[1]:.0f} cells), the idle human's does not")
    g = ev("__board.state.game")
    check(g["conv"] > 0 and any(t["count"] != g["per"] for t in g["teams"] if t["cpu"]), f"CPU armies fight: {[t['count'] for t in g['teams']]}, {g['conv']} conversions")
    check(all(t["skill"] is not None and 0.3 <= t["skill"] <= 1 for t in g["teams"] if t["cpu"]), "CPU skill follows the PRZECIĘTNIAK benchmark range")
    leave()

    # ---- performance: ~5000 fighters, real-time loop in the browser (not stepped), tick and draw time
    ev("Object.keys(__liquid.tune).forEach(k => delete __liquid.tune[k]); Object.assign(__liquid.tune, {armyFrac: .45, armyMax: 1500, roundSec: 600})")
    ev("__board.setOpts({level: 'cemetery'})"); ev(f"__board.setSlots({slots(('human', 'kb1'), ('cpu', 'kb2'), ('cpu', 'kb3'), ('cpu', 'kb4'))})")
    ev("__board.start()")
    pg.wait_for_function("__board.state.phase === 'run'", timeout=8000)
    time.sleep(.5)
    t0 = ev("__board.state.game.tick"); wall0 = time.time(); time.sleep(8); t1 = ev("__board.state.game.tick")
    perf = ev("__board.state.game.perf"); gp = ev("__board.state.game")
    hz = (t1 - t0) / (time.time() - wall0)
    print(f"PERF  {gp['total']} fighters, {gp['open']} open cells: tick avg {perf['tickAvg']:.2f} ms  p95 {perf['tickP95']:.2f}  max {perf['tickMax']:.2f};  draw avg {perf['drawAvg']:.2f} ms p95 {perf['drawP95']:.2f} max {perf['drawMax']:.2f};  sim rate {hz:.1f} Hz")
    check(gp["total"] >= 4800, f"performance run has {gp['total']} fighters")
    check(perf["tickAvg"] < 8 and perf["tickP95"] < 12, f"simulation tick fits a 60 Hz frame budget (avg {perf['tickAvg']:.2f} ms, p95 {perf['tickP95']:.2f} ms)")
    check(perf["drawAvg"] < 8, f"drawing fits the frame budget (avg {perf['drawAvg']:.2f} ms)")
    check(hz > 50, f"the loop keeps ~60 simulation ticks per second ({hz:.1f})")
    pg.screenshot(path=f"{SHOTS}/liquid_midfight_desktop.png")
    ev("__board.close()")
    ev("Object.keys(__liquid.tune).forEach(k => delete __liquid.tune[k])")

    # ---- sprint board still follows its old contract
    check(ev("JSON.stringify(ARK_BOARDS.sprint.actions)") == '["left","right"]' and ev("ARK_BOARDS.sprint.pointer === undefined && ARK_BOARDS.sprint.slotOption === undefined && ARK_BOARDS.sprint.options === undefined"), "sprint descriptor unchanged (left/right only, no pointer/slotOption/options)")
    ev("__board.open('sprint')"); time.sleep(.5)
    sk = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k]')].map(e => e.dataset.k).join()")
    sc = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=ctrl] option')].map(o => o.value).join()")
    check(sk == "name,type,char,ctrl" and "touch" not in sc and ev("document.querySelectorAll('.board-opt').length") == 0, f"sprint lobby keeps its 4 controls per slot, no touch scheme ({sk}; {sc})")
    ev("__board.close()")

    # ---- mobile layout: lobby, fight, results (separate context, touch device)
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m = ctx.new_page(); merrs = []
    m.on("pageerror", lambda e: merrs.append(str(e)))
    m.goto(URL); m.wait_for_function("!!(window.__game && window.__board && window.__liquid)")
    m.keyboard.press("KeyN"); m.locator("#player-name-input").fill("Tester"); m.keyboard.press("Enter")
    m.wait_for_function("__game.scene === 'play'"); time.sleep(.3)
    mev = m.evaluate
    mev("__board.open('liquid')"); m.wait_for_function("__liquid.status === 'ok'"); time.sleep(.6)
    check(mev("__board.ui.slots[0].ctrl") == "touch", "on a touch device the first human defaults to the drag control")
    ow = mev("(() => { const s = document.querySelector('#board-lobby section'); return [s.scrollWidth <= s.clientWidth + 1, s.getBoundingClientRect().width <= innerWidth + 1]; })()")
    check(all(ow), f"mobile lobby has no horizontal overflow {ow}")
    m.screenshot(path=f"{SHOTS}/liquid_lobby_mobile.png")
    mev("__liquid.tune.roundSec = 8")
    mev(f"__board.setSlots({slots(('human', 'touch'), ('cpu', 'kb2'), ('cpu', 'kb3'), ('cpu', 'kb4'))})"); mev("__board.setOpts({level: 'church'})")
    mev("__board.start()"); mev("__board.pause()"); mev("__board.step(215 + 240)")
    m.screenshot(path=f"{SHOTS}/liquid_midfight_mobile.png")
    mev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 3000) { __board.step(10); k += 10; } __board.step(70); })()")
    m.screenshot(path=f"{SHOTS}/liquid_results_mobile.png")
    check(mev("__board.state.phase") == "done", "mobile round reaches the results")
    check(not merrs, f"no page errors on mobile {merrs}")
    ctx.close()

    check(not errs, f"no page errors {errs} {bad_urls}")
    check(not bad_urls, f"no failed requests {bad_urls}")
    b.close()
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
