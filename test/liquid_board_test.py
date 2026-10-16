"""WOJNA PŁYNÓW / LIQUID WAR minigame (docs/js/boards/liquid.js on docs/js/board.js).

Static checks of the generated levels (docs/data/liquid-maps.json vs docs/map.json + map_collide.png + the generator), then a browser run:
venue flag -> lobby (level picker + thumbnail) -> rounds on every level -> rules (constant total, conversions, elimination, timer end)
-> controls (keyboard, mouse/touch) -> CPU cursor -> NO records of any kind (no medals, best, top 10, history, global board) ->
performance (also with 4x CPU throttling) -> sprint board still on its old contract (records kept) -> mobile layout.
Usage (ALWAYS through the isolated runner, a direct run publishes arrivals to public Nostr and cloud):
  ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/liquid_board_test.py
Screenshots go to ARK_SHOTS (default asset-review/2026-10-15-liquid-v2)."""
import json, os, re, sys, time
from collections import deque
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = os.environ.get("ARK_SHOTS", os.path.join(ROOT, "asset-review", "2026-10-15-liquid-v2"))
os.makedirs(SHOTS, exist_ok=True)
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)


# ------------------------------------------------------------------ static: the levels are built from OUR map
GW, GH = 320, 168
sys.path.insert(0, os.path.join(ROOT, "gen"))
import build_liquid_maps as GEN   # the generator: its window()/walls() are re-run below against the shipped file

mp = json.load(open(os.path.join(ROOT, "docs/map.json"), encoding="utf-8"))
raw = open(os.path.join(ROOT, "docs/data/liquid-maps.json"), encoding="utf-8").read()
lm = json.loads(raw)
collide = np.array(Image.open(os.path.join(ROOT, "docs/img/map_collide.png")))
terrain = np.array(Image.open(os.path.join(ROOT, "docs/img/map_terrain.png")))
check(lm["source"]["w"] == mp["w"] and lm["source"]["h"] == mp["h"] and lm["source"]["bbox"] == mp["bbox"], "liquid-maps.json was built from the current map.json size and bbox")
check(collide.shape == (mp["h"], mp["w"]), "collision mask matches map.json")
check(lm["grid"] == {"w": GW, "h": GH}, f"grid is {GW}x{GH} (4x the cells of the first version)")
NL = len(lm["levels"])
check(10 <= NL <= 14, f"10-14 levels ({NL})")
check(len(raw.encode("utf-8")) < 120_000, f"level file stays small: {len(raw.encode('utf-8'))} bytes for {NL} levels")
check(len({l["cell"] for l in lm["levels"]}) >= 5, f"levels use at least 5 different zoom levels {sorted({l['cell'] for l in lm['levels']})}")
check(len({l["id"] for l in lm["levels"]}) == NL and len({l["name"]["pl"] for l in lm["levels"]}) == NL and all(l["name"]["pl"] and l["name"]["en"] for l in lm["levels"]), "unique ids, PL and EN names")
check(len({tuple(l["origin"]) for l in lm["levels"]}) == NL, "every level is a different crop of the village")
check(any("forest" in l["layers"] for l in lm["levels"]) and any("field" in l["layers"] for l in lm["levels"]) and all(l["layers"][0] == "collide" for l in lm["levels"]), "walls come from the collision mask plus terrain layers (forest / field)")
lo, hi = lm["open_bounds"]
check(abs(lo - GEN.OPEN_MIN) < 1e-9 and abs(hi - GEN.OPEN_MAX) < 1e-9 and 0.3 <= lo < hi <= 0.95, f"open-area bounds {lo:.0%}..{hi:.0%} enforced by the generator")


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


LEVEL_PX = {}
for l in lm["levels"]:
    op = GEN.decode(l["rle"])
    LEVEL_PX[l["id"]] = op
    ok_shape = op.shape == (GH, GW)
    lab, sizes = components(op)
    share = op.mean()
    check(ok_shape and op.sum() == l["open"], f"{l['id']}: {GW}x{GH} grid, open count matches ({l['open']})")
    check(len(sizes) == 2, f"{l['id']}: exactly one connected open region ({len(sizes) - 1})")
    check(not (op[0].any() or op[-1].any() or op[:, 0].any() or op[:, -1].any()), f"{l['id']}: border is wall")
    check(lo <= share <= hi, f"{l['id']}: open area {share:.0%} is inside the bounds {lo:.0%}..{hi:.0%} (not near-empty, not near-solid)")
    a = l["anchors"]
    check(len(a) == 4 and all(op[y, x] and lab[y, x] == 1 for x, y in a), f"{l['id']}: four start areas, open and in the region")
    check(all(op[y - 2:y + 3, x - 2:x + 3].all() for x, y in a), f"{l['id']}: start areas have a 5x5 free neighbourhood (no tiny pockets)")
    dmin = min(((a[i][0] - a[j][0]) ** 2 + (a[i][1] - a[j][1]) ** 2) ** .5 for i in range(4) for j in range(i + 1, 4))
    check(dmin >= 60, f"{l['id']}: start areas are {dmin:.0f} cells apart at least")
    ds = [GEN.walk_dist(op, tuple(q)) for q in a]
    wmin = min(int(ds[i][a[j][1], a[j][0]]) for i in range(4) for j in range(i + 1, 4))
    check(wmin >= 60, f"{l['id']}: start areas are {wmin} steps apart by walking around the walls (not touching armies at the start)")
    check(op.sum() * 0.28 / 4 >= 400, f"{l['id']}: room for four armies ({int(op.sum())} open cells)")
    x0, y0 = l["origin"]; k = l["cell"]
    check(0 <= x0 and 0 <= y0 and x0 + GW * k <= mp["w"] and y0 + GH * k <= mp["h"], f"{l['id']}: crop window lies inside the village map")
    # the walls really come from the map: re-run the generator's own wall step and compare. Every open cell of the file must be open
    # there too (the file only additionally closes islands, the border and pockets).
    wall = GEN.walls(dict(cell=k, thr=l["thr"], layers=[n for n in l["layers"] if n != "collide"]), collide, terrain, x0, y0)
    check(not (op & wall).any(), f"{l['id']}: no open cell lies on a wall of the map layers {l['layers']}")
    sub = collide[y0:y0 + GH * k, x0:x0 + GW * k] > 64
    frac = sub.reshape(GH, k, GW, k).mean(axis=(1, 3))
    check(frac[op].mean() < .12, f"{l['id']}: open cells are free in map_collide.png (mean blocked {frac[op].mean():.3f})")

# venue is on open ground (the collision mask at the flag)
cx, cy = mp["corral"]["cx"] + 160, mp["corral"]["cy"]
check(not (collide[cy - 12:cy + 12, cx - 12:cx + 12] > 0).any(), f"venue ({cx},{cy}) next to the corral stands on open ground")

# ------------------------------------------------------------------ browser
HOOK = """
window.__lsw = []; window.__ftx = []; window.__cap = false;
const _si = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { window.__lsw.push(String(k)); return _si.call(this, k, v); };
const _ft = CanvasRenderingContext2D.prototype.fillText; CanvasRenderingContext2D.prototype.fillText = function (t) { if (window.__cap) window.__ftx.push(String(t)); return _ft.apply(this, arguments); };
"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.add_init_script(HOOK)
    errs = []; bad_urls = []; api_calls = []; watch = {"on": False}
    pg.on("response", lambda r: bad_urls.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    pg.on("request", lambda r: api_calls.append(f"{r.method} {r.url}") if watch["on"] and ("workers.dev" in r.url or "chlopkow-api" in r.url or "/scores" in r.url) else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text and "WebSocket is already in CLOSING or CLOSED state" not in m.text else None)
    pg.goto(URL); pg.wait_for_function("!!(window.__game && window.__board && window.__liquid)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__game && window.__board && window.__liquid)")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("Tester"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'"); time.sleep(.3)
    ev = pg.evaluate
    # an OLD record of this board (from the first version) must disappear when the lobby opens
    ev("(() => { __game.Q.mg = __game.Q.mg || {}; __game.Q.mg.liquid = { tries: 5, won: true, best: 41.2, medal: 2, history: [30, 41.2] }; localStorage.setItem('ark_board_liquid_top_v1', JSON.stringify([{ name: 'OLD', score: 41.2 }])); })()")

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
    check(ev("ARK_BOARDS.liquid.records === false && ARK_BOARDS.sprint.records === undefined"), "liquid declares records: false, sprint keeps the default (records on)")
    v = ev("__board.venues.liquid"); mc = ev("__game.MAP.corral")
    check(v == {"x": mc["cx"] + 160, "y": mc["cy"]}, f"flag venue is read from the current map.json: corral + offset -> {v}")
    check(ev("__liquid.VENUE.kind") == "flag" and ev("__liquid.venue({MAP: {corral: {cx: 10, cy: 20}}})") == {"x": 170, "y": 20}, "venue is a descriptor resolved at runtime (kind 'flag', ready for a building kind)")
    near = ev(f"ARK.HOOKS.near.flatMap(f => f(__game.P)).filter(c => Math.hypot(c.x - {v['x']}, c.y - {v['y']}) < 40).map(c => c._board || 'other')")
    check(near == ["liquid"], f"exactly one interaction at the flag: {near}")
    watch["on"] = True
    ev(f"ARK.teleport({v['x'] + 6}, {v['y'] + 4})"); time.sleep(.4)
    pg.keyboard.press("KeyE")
    pg.wait_for_function("!!__board.ui", timeout=4000)
    check(ev("__board.ui.id === 'liquid' && __board.ui.lobby"), "E at the flag opens the minigame lobby")
    check(ev("ARK.HOOKS.busy.some(f => f())"), "village is busy while the minigame is open")
    check(ev("!('liquid' in (__game.Q.mg || {}))") and ev("localStorage.getItem('ark_board_liquid_top_v1') === null"), "opening the lobby removes an old record, medal and top-10 of this board")
    pg.wait_for_function("__liquid.status === 'ok'")
    time.sleep(.6)
    check(pg.locator("#board-overlay .board-slot").count() == 4, "four slots")
    order = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k]')].map(e => e.dataset.k).join()")
    check(order == "name,type,char,sub,ctrl", f"slot controls: name, human/CPU, character, substance, controls ({order})")
    types = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=type] option')].map(o => o.value + ':' + o.textContent).join()")
    check(types == "human:CZŁOWIEK,cpu:KOMPUTER,off:—" and ev("__board.ui.slots.every(s => s.type !== 'avg')"), f"plain KOMPUTER only, no PRZECIĘTNIAK / average-based computer ({types})")
    subs_pl = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=sub] option')].map(o => o.textContent)")
    check(subs_pl == ["GNOJÓWKA", "MELIORANKA", "MLEKO", "ORANŻADA", "KOMPOT", "BIMBER"], f"six substances (PL): {subs_pl}")
    lev_pl = ev("[...document.querySelectorAll('.board-opt[data-opt=level] option')].map(o => o.textContent)")
    check(len(lev_pl) == NL + 1 and lev_pl[-1] == "LOSOWY" and all(l["name"]["pl"] in lev_pl for l in lm["levels"]), f"lobby picks one of {NL} levels or random: {lev_pl}")
    check(ev("document.querySelector('#board-lobby h2').textContent") == "WOJNA PŁYNÓW", "lobby heading")
    check(ev("__board.ui.slots.map(s => s.sub).join()") == "slurry,melior,milk,orange", "default substances")
    check(ev("__liquid.LEVELS.every(l => { const d = __liquid.data.levels.find(x => x.id === l.id); return d && d.name.pl === l.pl && d.name.en === l.en; }) && __liquid.LEVELS.length === __liquid.data.levels.length"), "lobby level names equal the data file names")
    lobby_txt = ev("document.getElementById('board-lobby').innerText")
    check(not re.search(r"REKORD|RECORD|PRZECIĘTNIAK|AVERAGE JOE|NAJLEPSI|ŚWIAT", lobby_txt, re.I) and ev("!document.getElementById('board-global') && !document.querySelector('[data-list]')"), "no record, average or global-board text in the lobby")
    # level thumbnail
    thumbs = {}
    for lid in ["village", "church", "random"]:
        ev(f"(() => {{ const s = document.querySelector('.board-opt[data-opt=level]'); s.value = '{lid}'; s.dispatchEvent(new Event('change')); }})()"); time.sleep(.1)
        thumbs[lid] = ev("(() => { const c = document.getElementById('board-preview'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let walls = 0, open = 0; for (let i = 0; i < d.length; i += 4) { if (d[i] === 0x4c && d[i + 1] === 0x68) walls++; else if (d[i] === 0x1e && d[i + 1] === 0x2e) open++; } return { url: c.toDataURL(), walls, open, w: c.width, h: c.height, remembered: __board.ui.opts.level }; })()")
    check(thumbs["village"]["walls"] > 1500 and thumbs["village"]["open"] > 1500 and thumbs["village"]["url"] != thumbs["church"]["url"] and thumbs["church"]["walls"] > 1500, f"thumbnail shows the chosen level (village walls/open {thumbs['village']['walls']}/{thumbs['village']['open']}, church differs)")
    check(thumbs["random"]["walls"] == 0 and thumbs["random"]["remembered"] == "random", "random level shows a '?' placeholder, no map")
    ev("(() => { const s = document.querySelector('.board-opt[data-opt=level]'); s.value = 'village'; s.dispatchEvent(new Event('change')); })()")
    pg.screenshot(path=f"{SHOTS}/liquid_lobby_desktop.png")
    ev("(() => { const s = document.querySelector('.board-opt[data-opt=level]'); s.value = 'pond'; s.dispatchEvent(new Event('change')); })()"); time.sleep(.15)
    pg.screenshot(path=f"{SHOTS}/liquid_lobby_desktop_pond.png")
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
        check(g0["level"] == l["id"] and g0["open"] == l["open"] and g0["grid"] == [GW, GH], f"{l['id']}: browser runs the level from the data file ({g0['open']} open cells, grid {g0['grid']})")
        check(2400 <= g0["total"] <= 8000 and all(t["count"] == g0["per"] for t in g0["teams"]), f"{l['id']}: {g0['total']} fighters, {g0['per']} per team")
        ev("__board.step(700)"); a1 = ev("__liquid.audit()"); g1 = ev("__board.state.game")
        check(a1["total"] == a0["total"] == a1["countsSum"] == a1["occupied"] and a1["bad"] == 0 and a1["byTeamMatches"] and a1["hpOk"], f"{l['id']}: total constant {a1['total']}, no overlaps, no fighter in a wall, health 1..max")
        check(g1["conv"] > 0, f"{l['id']}: conversions happen ({g1['conv']} in 700 ticks)")
        if l["id"] in ("street", "pond", "river"):
            ev("__board.step(300)"); pg.screenshot(path=f"{SHOTS}/liquid_midfight_{l['id']}_desktop.png")
        leave()

    # ---- rules on a controlled fight: two armies attack one idle team
    begin("church", [("human", "kb1"), ("human", "kb2"), ("human", "kb3")])
    ev("(() => { const s = __liquid.sim, a = __liquid.game.level.anchors[0]; for (const t of [1, 2]) { s.cur[t].x = a[0] + .5; s.cur[t].y = a[1] + .5; } })()")
    before = ev("__board.state.game.teams.map(t => t.count)")
    ev("__board.step(1800)"); g = ev("__board.state.game"); a = ev("__liquid.audit()")
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

    # ---- timer end, ranking by count, results screen WITHOUT any record
    ev("delete __game.Q.mg.liquid")
    ev("window.__lsw.length = 0")
    begin("shop", [("human", "kb1"), ("cpu", "kb2"), ("cpu", "kb3"), ("cpu", "kb4")], "{roundSec: 12}")
    ev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 3000) { __board.step(10); k += 10; } })()")
    s = ev("__board.state"); g = s["game"]; res = s["results"]
    check(s["phase"] == "done" and g["why"] in ("time", "last") and 11.9 <= g["time"] <= 12.2 or g["why"] == "last", f"round ends at the timer ({g['why']} at {g['time']:.2f} s)")
    cnt = {t["slot"]: t["count"] for t in g["teams"]}
    ranked = [cnt[r["slot"]] for r in res]
    check(ranked == sorted(ranked, reverse=True), f"ranking is by fighter count {ranked}")
    check(abs(sum(r["score"] for r in res) - 100) < .3 and all(abs(r["score"] - cnt[r["slot"]] / g["total"] * 100) <= .0501 for r in res), f"scores are % of all fighters (0.1 precision), sum {sum(r['score'] for r in res):.1f}")
    check(s["records"] is False and all(r["medal"] == 0 and r["record"] is False and r["global"] is None for r in res), "no medal, no 'new record', no global rank on any result row")
    ev("window.__ftx.length = 0; window.__cap = true"); ev("__board.step(70)")
    texts = ev("window.__ftx"); ev("window.__cap = false")
    joined = " | ".join(texts)
    check(any(t.startswith("WYGRYWA") for t in texts) and re.search(r"\d+\.\d%", joined) is not None, f"results screen shows the winner and the % per team ({[t for t in texts if t.startswith('WYGRYWA') or '%' in t][:6]})")
    check(not re.search(r"REKORD|RECORD|BRĄZ|SREBRO|ZŁOTO|BRONZE|SILVER|GOLD|NAJLEPSI|REKORDY|ŚWIAT #|WORLD #", joined, re.I), "results screen has no medal, record, top-10 or world-rank text")
    pg.screenshot(path=f"{SHOTS}/liquid_results_desktop.png")
    q = ev("__game.Q.mg || {}")
    check("liquid" not in q, f"no Q.mg.liquid (tries/best/medal/history) after a full round ({list(q)})")
    keys = ev("window.__lsw")
    check(not any(re.search(r"top|best|hist|record|medal", k) and "liquid" in k for k in keys) and "ark_board_liquid_top_v1" not in keys, f"no top-10 / record key written to localStorage (keys written: {sorted(set(keys))})")
    stray = ev("Object.entries(localStorage).filter(([k, v]) => !/^ark_board_liquid_(slots|opts)_v1$/.test(k) && /liquid/i.test(k + v)).map(e => e[0])")
    check(ev("localStorage.getItem('ark_board_liquid_top_v1') === null") and stray == [], f"saved game and localStorage hold no liquid record (stray keys: {stray})")
    lines = ev("(() => { const l = []; ARK.HOOKS.questLog.forEach(f => f(l)); return l.map(x => x[0]); })()")
    check(not any("płynów" in x.lower() or "liquid" in x.lower() for x in lines), "quest log lists no result of the minigame")
    check(ev("!ARK_BOARDS.liquid.flagLabel.includes('★')"), "flag label has no medal star")
    leave()
    # a human win cheers (fireworks) but still stores nothing
    check(not api_calls, f"no scores-server call (read or write) during the whole liquid session: {api_calls}")

    # ---- controls: real keys on two schemes at once, cursors never enter walls
    begin("church", [("human", "kb1"), ("human", "kb2"), ("off", "kb3"), ("off", "kb4")], "{roundSec: 600}")
    c0 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    pg.keyboard.down("ArrowRight"); pg.keyboard.down("KeyS"); ev("__board.step(40)"); pg.keyboard.up("ArrowRight"); pg.keyboard.up("KeyS")
    c1 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    check(c1[0][0] > c0[0][0] + 10 and abs(c1[0][1] - c0[0][1]) < .5, f"ArrowRight moves cursor 1 right {c0[0]} -> {c1[0]}")
    check(c1[1][1] > c0[1][1] + 3 and abs(c1[1][0] - c0[1][0]) < .5, f"S moves cursor 2 down (WASD) {c0[1]} -> {c1[1]}")
    pg.keyboard.down("ArrowUp"); pg.keyboard.down("ArrowLeft"); ev("__board.step(400)"); pg.keyboard.up("ArrowUp"); pg.keyboard.up("ArrowLeft")
    c2 = ev("__liquid.sim.cur[0]"); check(ev(f"__liquid.sim.open({c2['x']}, {c2['y']})") and c2["x"] >= 1 and c2["y"] >= 1, f"holding up+left into the corner stays on open ground ({c2['x']:.1f},{c2['y']:.1f})")
    # walls: park the cursor next to a wall and push into it
    pos = ev("""(() => { const s = __liquid.sim; for (let y = 5; y < 163; y++) for (let x = 5; x < 305; x++) if (s.open(x, y) && s.open(x + 1, y) && !s.open(x + 3, y) && !s.open(x + 2, y)) { s.cur[0].x = x + .5; s.cur[0].y = y + .5; return [x, y]; } return null; })()""")
    check(pos is not None, f"found a wall edge to push into {pos}")
    pg.keyboard.down("ArrowRight"); ev("__board.step(60)"); pg.keyboard.up("ArrowRight")
    c3 = ev("__liquid.sim.cur[0]"); check(ev(f"__liquid.sim.open({c3['x']}, {c3['y']})") and c3["x"] < pos[0] + 2.1, f"cursor cannot enter a wall ({pos} -> {c3['x']:.2f},{c3['y']:.2f})")
    leave()

    # ---- fighters flow around walls toward the cursor (distance field), not through them
    begin("church", [("human", "kb1"), ("human", "kb2")], "{roundSec: 600}")
    cen = "(() => { const s = __liquid.sim; let x = 0, y = 0, n = 0; for (let i = 0; i < s.total; i++) if (s.fteam[i] === 0) { x += s.fpos[i] % 320; y += (s.fpos[i] / 320 | 0); n++; } return [x / n, y / n]; })()"
    k0 = ev(cen); tgt = ev("(() => { const s = __liquid.sim; let best = null; for (let y = 5; y < 163; y += 3) for (let x = 5; x < 315; x += 3) if (s.open(x, y)) { const d = Math.hypot(x - 200, y - 84); if (!best || d < best[0]) best = [d, x, y]; } return best; })()")
    ev(f"(() => {{ const s = __liquid.sim; s.cur[0].x = {tgt[1]} + .5; s.cur[0].y = {tgt[2]} + .5; }})()")
    d0 = ((k0[0] - tgt[1]) ** 2 + (k0[1] - tgt[2]) ** 2) ** .5
    ev("__board.step(900)"); k1 = ev(cen)
    d1 = ((k1[0] - tgt[1]) ** 2 + (k1[1] - tgt[2]) ** 2) ** .5
    a = ev("__liquid.audit()")
    check(d1 < d0 * .6 and a["bad"] == 0, f"army flows to the cursor: centroid distance {d0:.0f} -> {d1:.0f} cells, no fighter in a wall")
    leave()

    # ---- mouse / touch pointer drags the cursor (real mouse events on the canvas)
    begin("village", [("human", "touch"), ("cpu", "kb2")], "{roundSec: 600}")
    ev("document.getElementById('board-canvas').focus()")
    geo = ev("(() => { const cv = document.getElementById('board-canvas'), r = cv.getBoundingClientRect(), d = cv.width / r.width, k = Math.min(cv.width / 960, cv.height / 540); return { l: r.left, t: r.top, d, k, cw: cv.width, ch: cv.height }; })()")
    toc = lambda bx, by: ((bx * geo["k"] + (geo["cw"] - 960 * geo["k"]) / 2) / geo["d"] + geo["l"], (by * geo["k"] + (geo["ch"] - 540 * geo["k"]) / 2) / geo["d"] + geo["t"])
    cs = ev("__liquid.sim.cur[0]"); goal = (cs["x"] + 80, cs["y"] + 20)
    gx, gy = toc(goal[0] * 3, 36 + goal[1] * 3)
    pg.mouse.move(*toc(cs["x"] * 3, 36 + cs["y"] * 3)); pg.mouse.down(); pg.mouse.move(gx, gy, steps=4); ev("__board.step(150)")
    ce = ev("__liquid.sim.cur[0]"); pg.mouse.up()
    check(ce["x"] > cs["x"] + 30, f"pointer drag steers the cursor ({cs['x']:.1f},{cs['y']:.1f}) -> ({ce['x']:.1f},{ce['y']:.1f}) toward {goal}")
    ev("__board.step(80)"); ce2 = ev("__liquid.sim.cur[0]")
    check(abs(ce2["x"] - ce["x"]) < .01 and abs(ce2["y"] - ce["y"]) < .01, "releasing the pointer stops the cursor")
    leave()

    # ---- CPU cursor moves toward the enemy and the CPU fights
    begin("farmyard", [("cpu", "kb1"), ("cpu", "kb2"), ("human", "kb3")], "{roundSec: 600}")
    c0 = ev("__liquid.sim.cur.map(c => [c.x, c.y])"); ev("__board.step(500)"); c1 = ev("__liquid.sim.cur.map(c => [c.x, c.y])")
    mv = [((c1[i][0] - c0[i][0]) ** 2 + (c1[i][1] - c0[i][1]) ** 2) ** .5 for i in range(3)]
    check(mv[0] > 10 and mv[1] > 10 and mv[2] < .01, f"CPU cursors move ({mv[0]:.0f}, {mv[1]:.0f} cells), the idle human's does not")
    g = ev("__board.state.game")
    check(g["conv"] > 0 and any(t["count"] != g["per"] for t in g["teams"] if t["cpu"]), f"CPU armies fight: {[t['count'] for t in g['teams']]}, {g['conv']} conversions")
    skills = [t["skill"] for t in g["teams"] if t["cpu"]]
    check(all(s is not None and 0.3 <= s <= 1 for s in skills) and ev("__board.state.cpuSource") == "default", f"CPU skill is fixed from the board default (no history, no average): {skills}")
    leave()

    # ---- performance: the real-time loop in the browser (not stepped); tick/draw time, unthrottled and with 4x CPU throttling
    cdp = pg.context.new_cdp_session(pg)
    ev("Object.keys(__liquid.tune).forEach(k => delete __liquid.tune[k]); Object.assign(__liquid.tune, {roundSec: 600})")
    perf = {}
    ev(f"__board.setSlots({slots(('human', 'kb1'), ('cpu', 'kb2'), ('cpu', 'kb3'), ('cpu', 'kb4'))})")
    for rate in (1, 4):
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
        for lid in (["farmyard", "village"] if rate == 1 else ["farmyard"]):
            ev(f"__board.setOpts({{level: '{lid}'}})"); ev("__board.start()")
            pg.wait_for_function("__board.state.phase === 'run'", timeout=20000)
            time.sleep(.5)
            t0 = ev("__board.state.game.tick"); wall0 = time.time(); time.sleep(6); t1 = ev("__board.state.game.tick")
            pf = ev("__board.state.game.perf"); gp = ev("__board.state.game"); hz = (t1 - t0) / (time.time() - wall0)
            print(f"PERF  x{rate} {lid}: {gp['total']} fighters, {gp['open']} open cells ({GW}x{GH}): tick avg {pf['tickAvg']:.2f} ms  p95 {pf['tickP95']:.2f}  max {pf['tickMax']:.2f};  flood avg {pf['floodAvg']:.2f};  draw avg {pf['drawAvg']:.2f} ms p95 {pf['drawP95']:.2f} max {pf['drawMax']:.2f};  sim rate {hz:.1f} Hz")
            perf[(rate, lid)] = (pf, hz, gp)
            if rate == 1 and lid == "farmyard": pg.screenshot(path=f"{SHOTS}/liquid_midfight_farmyard_realtime_desktop.png")
            ev("__board.toLobby()")
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 1})
    pf, hz, gp = perf[(1, "farmyard")]
    check(gp["total"] >= 7000, f"performance run has {gp['total']} fighters")
    check(pf["tickAvg"] < 8 and pf["tickP95"] < 12, f"simulation tick fits a 60 Hz frame budget (avg {pf['tickAvg']:.2f} ms, p95 {pf['tickP95']:.2f} ms)")
    check(pf["drawAvg"] < 8, f"drawing fits the frame budget (avg {pf['drawAvg']:.2f} ms)")
    check(hz > 50, f"the loop keeps ~60 simulation ticks per second ({hz:.1f})")
    pf4, hz4, _ = perf[(4, "farmyard")]
    check(hz4 > 30 and pf4["tickAvg"] < 30, f"with 4x CPU throttling the game still runs ({hz4:.1f} Hz, tick avg {pf4['tickAvg']:.2f} ms)")
    ev("__board.close()")
    ev("Object.keys(__liquid.tune).forEach(k => delete __liquid.tune[k])")

    # ---- sprint board still follows its old contract AND keeps its records
    check(ev("JSON.stringify(ARK_BOARDS.sprint.actions)") == '["left","right"]' and ev("ARK_BOARDS.sprint.pointer === undefined && ARK_BOARDS.sprint.slotOption === undefined && ARK_BOARDS.sprint.options === undefined && ARK_BOARDS.sprint.preview === undefined"), "sprint descriptor unchanged (left/right only, no pointer/slotOption/options/preview)")
    ev("__board.open('sprint')"); time.sleep(.5)
    sk = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k]')].map(e => e.dataset.k).join()")
    sc = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=ctrl] option')].map(o => o.value).join()")
    st = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k=type] option')].map(o => o.value).join()")
    check(sk == "name,type,char,ctrl" and "touch" not in sc and ev("document.querySelectorAll('.board-opt').length") == 0 and not ev("!!document.getElementById('board-preview')"), f"sprint lobby keeps its 4 controls per slot, no touch scheme, no preview ({sk}; {sc})")
    check(st == "human,avg,cpu,off" and ev("__board.ui.slots[1].type") == "avg", f"sprint keeps PRZECIĘTNIAK in its lobby ({st})")
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
    mev("__board.setOpts({level: 'street'})"); time.sleep(.2)
    ow = mev("(() => { const s = document.querySelector('#board-lobby section'); return [s.scrollWidth <= s.clientWidth + 1, s.getBoundingClientRect().width <= innerWidth + 1]; })()")
    check(all(ow), f"mobile lobby has no horizontal overflow {ow}")
    check(mev("!!document.getElementById('board-preview') && document.getElementById('board-preview').getBoundingClientRect().width > 100"), "mobile lobby shows the level thumbnail")
    m.screenshot(path=f"{SHOTS}/liquid_lobby_mobile.png")
    mev("(() => { const s = document.querySelector('#board-lobby section'); s.scrollTop = s.scrollHeight; })()"); time.sleep(.1)
    m.screenshot(path=f"{SHOTS}/liquid_lobby_mobile_bottom.png")
    mev("__liquid.tune.roundSec = 8")
    mev(f"__board.setSlots({slots(('human', 'touch'), ('cpu', 'kb2'), ('cpu', 'kb3'), ('cpu', 'kb4'))})"); mev("__board.setOpts({level: 'church'})")
    mev("__board.start()"); mev("__board.pause()"); mev("__board.step(215 + 240)")
    m.screenshot(path=f"{SHOTS}/liquid_midfight_mobile.png")
    mev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 3000) { __board.step(10); k += 10; } __board.step(70); })()")
    m.screenshot(path=f"{SHOTS}/liquid_results_mobile.png")
    check(mev("__board.state.phase") == "done" and mev("__board.state.records") is False, "mobile round reaches the results (no records)")
    mres = mev("__board.state.results.map(r => [r.place, r.score])")
    check([r[0] for r in mres] == [1, 2, 3, 4] and all(mres[i][1] >= mres[i + 1][1] for i in range(3)), f"mobile results are ranked by share, descending {mres}")
    check(not merrs, f"no page errors on mobile {merrs}")
    ctx.close()

    check(not errs, f"no page errors {errs} {bad_urls}")
    check(not bad_urls, f"no failed requests {bad_urls}")
    b.close()
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
