"""Headless tunnel / passages test: loose brick in the crypt's hidden chamber -> wall slides open -> lazy-loaded tunnel -> hidden slab in the
cemetery as a two-way shortcut. Also: gate evaluator, lazy-load assertions, load failure handling, reload safety, room stack.

Run (server first: python -m http.server 8771 --directory docs):
    ARK_URL=http://127.0.0.1:8771/index.html python test/isolated_browser_runner.py test/tunnel_test.py
Set TUNNEL_SHOTS=<dir> to also write the documentation screenshots there (flat files).
"""
import time, os, json, math
from playwright.sync_api import sync_playwright
EXE = os.environ.get("CHROME")
SHOTS = os.environ.get("TUNNEL_SHOTS")
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8771/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def start_game(b, vw=1280, vh=720, watch=True):
    pg = b.new_page(viewport={"width": vw, "height": vh})
    errs = []
    if watch:
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" and "favicon" not in m.text else None)
    pg.goto(URL); pg.wait_for_function("window.__game", timeout=30000)
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    pg.keyboard.press("Enter")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    return pg, errs


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE) if EXE else p.chromium.launch()
    pg, errs = start_game(b)

    def shot(name):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True); time.sleep(1.0); pg.screenshot(path=os.path.join(SHOTS, name))

    def tp(x, y):
        pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()")
        time.sleep(.3)

    def talk_all():
        n = 0
        for _ in range(30):
            if not pg.evaluate("!!__game.talk"): break
            pg.keyboard.press("Space"); time.sleep(.07); pg.keyboard.press("Space"); time.sleep(.07); n += 1
        return n

    def poi(key, nth=0): return pg.evaluate(f"__game.room.pois.filter(p=>p.key==='{key}')[{nth}] || null")
    def kind(): return pg.evaluate("__game.room && (__game.room.kind || 'church')")
    def Q(k): return pg.evaluate(f"__game.Q.{k}")
    def P(): return pg.evaluate("[__game.P.x, __game.P.y]")
    def dist(a, b2): return math.hypot(a[0] - b2[0], a[1] - b2[1])
    def pst(): return pg.evaluate("PASSAGES.state()")
    def stack(): return pg.evaluate("ARK.rooms.stackIds")
    def saved(): return pg.evaluate(f"(()=>{{const s=JSON.parse(localStorage.getItem('{SAVE_KEY}')); return [s.x,s.y]}})()")
    def wait_kind(k, timeout=4):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if kind() == k: return True
            time.sleep(.1)
        return False
    def wait_village(timeout=4):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if not pg.evaluate("!!__game.room") and not pg.evaluate("ARK.rooms.busy"): return True
            time.sleep(.1)
        return False
    def hold(key, secs):
        pg.keyboard.down(key); time.sleep(secs); pg.keyboard.up(key)
    def slab_hooks(): return pg.evaluate("ARK.HOOKS.near.flatMap(f=>f(ARK.P)).filter(c=>c._passage).length")
    def reload_continue():
        pg.reload(); pg.wait_for_function("window.__game"); time.sleep(.6)
        pg.keyboard.press("Enter"); time.sleep(.6)
        for _ in range(40):
            if pg.evaluate("__game.scene") == "play": break
            time.sleep(.2)

    cem = pg.evaluate("__game.MAP.pois.find(p=>p.key==='cemetery')")
    church = pg.evaluate("__game.MAP.pois.find(p=>p.key==='church')")
    cem_pt = [cem["x"], cem["y"]]

    # ---------------- 0. engine: registry, gate evaluator, lazy state on a fresh save
    pg.wait_for_function("PASSAGES.state().registryLoaded", timeout=10000)
    s = pst()
    check(s["passages"] == ["church-cemetery"], f"registry loaded: {s['passages']}")
    check(not s["scripts"] and not s["data"] and not s["status"] and not s["kinds"], f"nothing lazy is loaded at startup {s}")
    check(not pg.evaluate("[...document.scripts].some(x=>/underground-tunnel/.test(x.src))"), "tunnel module has no <script> tag at startup")
    html = pg.evaluate("fetch('index.html').then(r=>r.text())")
    check("passages.js" in html and "underground-tunnel" not in html and "tunnel-church-cemetery" not in html, "index.html lists passages.js only (tunnel module and data are not eager)")
    g = lambda d: pg.evaluate(f"PASSAGES.gate({json.dumps(d)})")
    check(g({"type": "always"})["open"] is True, "gate always: open")
    check(g({"type": "flag", "key": "tunnelOpen"})["open"] is False, "gate flag tunnelOpen: closed on a fresh save")
    qg = g({"type": "quiz", "quiz": "x"}); mg = g({"type": "mission", "mission": "x", "step": "y"})
    check(qg["open"] is False and "TODO" in qg["reason"], f"gate quiz is a locked stub: {qg['reason'][:50]}")
    check(mg["open"] is False and "TODO" in mg["reason"], "gate mission is a locked stub")
    check(g({"type": "any", "of": [{"type": "always"}, {"type": "quiz"}]})["open"] is True and g({"type": "all", "of": [{"type": "always"}, {"type": "quiz"}]})["open"] is False, "gate any/all combinators")
    check(g({"type": "bogus"})["open"] is False, "unknown gate type is closed, not a crash")
    # the cemetery slab does not exist before the secret is known
    check(slab_hooks() == 0, "no slab hook on a fresh save")
    tp(cem_pt[0] + 8, cem_pt[1] - 20)
    check(slab_hooks() == 0, "still no slab hook standing right next to the slab spot")
    pg.keyboard.press("KeyE"); time.sleep(.4)
    t = pg.evaluate("__game.talk && __game.talk.lines[0]")
    check(not t or "pęknięcie" not in t, f"E at the slab spot does not reveal the slab ({t})")
    talk_all()
    check(pst()["scripts"] == [], "E at the hidden spot loaded nothing")

    # ---------------- 1. into the crypt (Q flags set directly, like crypt_test), door still shut
    pg.evaluate("__game.Q.cryptHint=true; __game.Q.cryptOpen=true; ARK.save()")
    tp(church["x"], church["y"] + 40)
    out = P()
    pg.keyboard.press("KeyE"); time.sleep(.8)
    check(kind() == "church", "entered the church"); talk_all()
    conf = poi("confession"); tp(conf["x"], conf["y"]); pg.keyboard.press("KeyE")
    check(wait_kind("crypt"), "descended into the crypt"); time.sleep(.3); talk_all()
    check(poi("cryptBrick") is None, "no loose brick POI before the stone door is open")
    check(stack() == ["church"] and pg.evaluate("ARK.rooms.depth") == 2, "stack in the crypt is [church]")
    for key in ["symCrux", "symRosa", "symCirculus", "symLux"]:
        pt = poi(key); tp(pt["x"], pt["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    time.sleep(.2); talk_all()
    check(Q("cryptDoor") is True and pg.evaluate("__game.room.doorOpen"), "four signs open the stone door")
    brick = poi("cryptBrick")
    check(brick is not None, "loose brick POI exists after the door is open")
    check(not pst()["scripts"] and not pst()["data"], "tunnel module and data still NOT loaded before the brick")
    check(pg.evaluate("__game.room.tunnelOpened") is False and Q("tunnelOpen") is False, "tunnel not open before the brick")
    check(pg.evaluate("__game.blocked(280,122)") is True, "the east wall is solid before the brick")
    tp(brick["x"] - 30, brick["y"] + 12); shot("01_chamber_loose_brick.png")

    # ---------------- 2. press the brick: lines, 0.6 s slide, toast, lazy-load starts
    tp(brick["x"], brick["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("__game.talk && __game.talk.lines.length") == 2, "brick plays its two lines")
    talk_all(); time.sleep(.15)
    check(Q("tunnelOpen") is True, "Q.tunnelOpen set")
    check(pg.evaluate("__game.toastText") is not None, "toast shown")
    time.sleep(.2)
    if SHOTS: pg.screenshot(path=os.path.join(SHOTS, "02a_wall_opening.png"))
    time.sleep(.8)
    check(pg.evaluate("__game.room.tunnelOpened") and pg.evaluate("__game.blocked(280,122)") is False, "wall carved: the passage is walkable")
    pg.wait_for_function("PASSAGES.state().status['church-cemetery']==='ready'", timeout=8000)
    s = pst()
    check(any("underground-tunnel" in x for x in s["scripts"]) and any("tunnel-church-cemetery" in x for x in s["data"]), f"tunnel module + data lazy-loaded by the brick {s['scripts']} {s['data']}")
    talk_all(); time.sleep(.2)
    shot("02_wall_open.png")
    tp(brick["x"], brick["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("__game.talk && __game.talk.lines.length") == 1, "brick again: short line"); talk_all()

    # ---------------- 3. reload inside the crypt: flag persists, nothing lazy is loaded until needed
    pg.evaluate("ARK.save()")
    sv = pg.evaluate(f"(()=>{{const s=JSON.parse(localStorage.getItem('{SAVE_KEY}')); return [s.x,s.y,s.Q.tunnelOpen,s.Q.cryptDoor]}})()")
    check(dist(sv[:2], out) < 40 and sv[2] is True and sv[3] is True, f"save inside crypt = village door + tunnelOpen {sv}")
    reload_continue()
    check(pg.evaluate("__game.scene") == "play" and not pg.evaluate("!!__game.room"), "continues in the village after reload")
    check(dist(P(), out) < 60, f"respawn at the church door {P()}")
    check(Q("tunnelOpen") is True, "Q.tunnelOpen survived the reload")
    pg.wait_for_function("PASSAGES.state().registryLoaded")
    check(not pst()["scripts"], "after reload the tunnel is not loaded again until needed")

    # ---------------- 4. back down; walk through the open mouth -> lazy build -> tunnel
    pg.keyboard.press("KeyE"); time.sleep(.8); talk_all()
    conf = poi("confession"); tp(conf["x"], conf["y"]); pg.keyboard.press("KeyE")
    check(wait_kind("crypt"), "second descent"); time.sleep(.3); talk_all()
    check(pg.evaluate("__game.room.tunnelOpened") is True and pg.evaluate("__game.room.openPassages['church-cemetery']") is True, "crypt rebuilt with the passage already open")
    tp(240, 122)
    hold("ArrowRight", .6)
    check(wait_kind("tunnel", 6), "walking into the mouth enters the tunnel")
    time.sleep(.5)
    check(stack() == ["church", "crypt"] and pg.evaluate("ARK.rooms.depth") == 3, f"stack is [church, crypt] {stack()}")
    check(pg.evaluate("__game.room.h") <= 2000 and pg.evaluate("__game.room.w * __game.room.h") < 600000, "tunnel canvases are modest")
    check(Q("tunnelSeen") is True, "Q.tunnelSeen set on first entry")
    check(pg.evaluate("__game.talk && __game.talk.lines.length") == 2, "first-visit lines"); talk_all()
    here = P(); check(here[1] > 1400, f"Arek starts at the south end {here}")
    check(dist(saved(), out) < 40, "save inside the tunnel = village church door")
    shot("03_tunnel_start.png")

    # ---------------- 5. the tunnel: long corridor, lore POIs, music kind
    check(pg.evaluate("__game.room.pois.map(p=>p.key).sort().join()") == "tunnelBones,tunnelNiche,tunnelSealed,tunnelStairs", "tunnel POIs: bones, niche, sealed door, stairs")
    for key in ["tunnelNiche", "tunnelSealed", "tunnelBones"]:
        pt = poi(key); tp(pt["x"], pt["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
        t = pg.evaluate("__game.talk && __game.talk.lines[0]"); check(bool(t), f"{key}: {str(t)[:60]}")
        if key == "tunnelSealed": check(t == "Zamurowane. Na razie.", "sealed door says 'Zamurowane. Na razie.'")
        talk_all()
    check(pg.evaluate("ARK.room.kind") == "tunnel", "room kind tunnel (music.js maps it to krypta)")
    tp(128, 1410); y0 = P()[1]; hold("ArrowUp", 2.0); y1 = P()[1]
    check(y0 - y1 > 150, f"2 s of walking covers {y0 - y1:.0f} px of corridor")
    tp(128, 760); shot("04_tunnel_middle.png")
    tp(128, 150); shot("05_tunnel_north_stairs.png")

    # ---------------- 6. up the stairs: surfaces in the VILLAGE beside the slab, stack cleared
    hold("ArrowUp", 1.2)
    check(wait_village(6), "climbing the stairs leaves the tunnel")
    time.sleep(.4)
    check(pg.evaluate("ARK.room") is None and pg.evaluate("ARK.rooms.depth") == 0 and stack() == [], "room null, stack empty")
    pos = P(); d = dist(pos, cem_pt)
    check(d < 150, f"Arek is at the cemetery {d:.0f} px from the poi")
    check(dist(saved(), pos) < 5, "save written at the surfaced position")
    check(dist(pg.evaluate("[__game.FRODO.x,__game.FRODO.y]"), pos) < 200, "Frodo came along")
    check(slab_hooks() == 1, "slab hook exists now that the secret is known")
    check(pg.evaluate("__game.blocked(__game.P.x, __game.P.y)") is False, "not standing in a wall")
    shot("06_village_cemetery_slab.png")

    # ---------------- 7. slab shortcut down; walk south to the crypt; unwind the stack
    slab = pg.evaluate("(()=>{const c=ARK.HOOKS.near.flatMap(f=>f(ARK.P)).filter(c=>c._passage)[0]; return [c.x,c.y]})()")
    check(dist(slab, cem_pt) < 60 and not pg.evaluate(f"__game.blocked({slab[0]},{slab[1]})"), f"slab is inside the cemetery on open ground {slab}")
    tp(slab[0], slab[1] + 16); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("__game.talk && __game.talk.lines.length") == 2, "E at the slab: two lines"); talk_all()
    check(wait_kind("tunnel", 6), "slab leads down into the tunnel"); time.sleep(.5)
    check(stack() == [] and pg.evaluate("ARK.rooms.depth") == 1, f"entered from the village: stack empty {stack()}")
    check(P()[1] < 200, f"arrives at the north end {P()}")
    check(dist(saved(), pos) < 120, f"save while in the tunnel = village spot at the slab {saved()}")
    tp(128, 1410); hold("ArrowDown", 1.4)
    check(wait_kind("crypt", 6), "walking south from a village-entered tunnel arrives in the crypt"); time.sleep(.5)
    check(stack() == ["church"], f"stack rebuilt to [church] {stack()}")
    cp = P(); check(200 < cp[0] < 276 and 100 < cp[1] < 140, f"Arek stands in the crypt passage {cp}")
    hold("ArrowRight", .8)
    check(wait_kind("tunnel", 6), "re-enter the tunnel from the crypt"); time.sleep(.5)
    check(stack() == ["church", "crypt"], f"stack [church, crypt] {stack()}")
    tp(128, 1410); hold("ArrowDown", 1.4)
    check(wait_kind("crypt", 6), "south end returns to the crypt"); time.sleep(.5)
    check(stack() == ["church"], "stack unwound to [church]")
    pg.evaluate("__game.P.x=160; __game.P.y=480"); hold("ArrowDown", .9); time.sleep(.7)
    check(kind() == "church", "stairs lead back up into the church")
    pg.evaluate("__game.P.x=160; __game.P.y=426"); hold("ArrowDown", .6); time.sleep(.7)
    check(wait_village(4), "left the church")
    check(dist(P(), out) < 60, f"back at the village door {P()}")

    # ---------------- 8. reload while inside the tunnel
    tp(slab[0], slab[1] + 16); pg.keyboard.press("KeyE"); time.sleep(.3); talk_all()
    check(wait_kind("tunnel", 6), "down again"); time.sleep(.4)
    tp(128, 700); pg.evaluate("ARK.save()")
    reload_continue()
    check(pg.evaluate("__game.scene") == "play" and not pg.evaluate("!!__game.room"), "reload in the tunnel continues in the village")
    check(dist(P(), cem_pt) < 150 or dist(P(), out) < 60, f"respawn on the village side {P()}")
    check(Q("tunnelOpen") is True and Q("tunnelSeen") is True, "flags persisted")
    check(not pg.evaluate("ARK.rooms.depth"), "stack empty after reload")

    # ---------------- 9. mobile viewport
    pg.set_viewport_size({"width": 390, "height": 844}); time.sleep(.5)
    slab = pg.evaluate("(()=>{const c=ARK.HOOKS.near.flatMap(f=>f(ARK.P)).filter(c=>c._passage)[0]; return c?[c.x,c.y]:null})()") or slab
    tp(slab[0], slab[1] + 16); pg.keyboard.press("KeyE"); time.sleep(.3); talk_all()
    check(wait_kind("tunnel", 6), "tunnel on mobile viewport"); time.sleep(.4)
    tp(128, 770); shot("07_tunnel_mobile_390x844.png")
    check(not errs, f"no page errors {errs[:3]}")

    # ---------------- 10. texts: PL + EN for every new key, no dashes
    keys = ["tunnelBrick", "tunnelWallOpen", "tunnelBrickAgain", "tunnelClick", "tunnelToast", "tunnelLabel", "passageHint", "passageFail", "passageLocked", "tunnelSlab"]
    pg2 = b.new_page(viewport={"width": 800, "height": 500}); pg2.goto(URL.split("?")[0] + "?lang=en"); pg2.wait_for_function("window.__game", timeout=30000)
    miss = pg2.evaluate(f"{json.dumps(keys)}.filter(k=>!ARK.T[k])"); check(not miss, f"EN texts present {miss}")
    en = pg2.evaluate(f"JSON.stringify({json.dumps(keys)}.map(k=>ARK.T[k]))"); check("\u2014" not in en and "\u2013" not in en, "no dashes in EN tunnel text")
    pg2.close()
    pl = pg.evaluate(f"JSON.stringify({json.dumps(keys)}.map(k=>ARK.T[k]))"); check("\u2014" not in pl and "\u2013" not in pl, "no dashes in PL tunnel text")
    data = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "data", "tunnel-church-cemetery.json"), encoding="utf-8"))
    check(sorted(data["text"]["pl"]) == sorted(data["text"]["en"]), "tunnel data has the same text keys in PL and EN")
    dumped = json.dumps(data["text"], ensure_ascii=False)
    check("\u2014" not in dumped and "\u2013" not in dumped, "no dashes in tunnel data text")
    for k in ["tunnelNiche", "tunnelSealed", "tunnelBones", "tunnelStairs", "tunnelFirst"]:
        check(bool(pg.evaluate(f"ARK.T.{k}")), f"tunnel text {k} merged into ARK.T (PL)")
    pg.close()

    # ---------------- 11. load failure: friendly toast, no crash, retry works; closed gate refuses politely
    pg3, _ = start_game(b, watch=False)
    pg3.evaluate("__game.Q.tunnelOpen=true; __game.Q.cryptDoor=true; __game.Q.cryptOpen=true")
    pg3.route("**/underground-tunnel.js", lambda r: r.abort())
    pg3.wait_for_function("PASSAGES.state().registryLoaded")
    pg3.evaluate("PASSAGES.enter('church-cemetery','cemetery')")
    pg3.wait_for_function("PASSAGES.state().status['church-cemetery']==='failed'", timeout=8000)
    time.sleep(.2)
    st = pg3.evaluate("PASSAGES.state()")
    check(pg3.evaluate("__game.toastText") == pg3.evaluate("ARK.T.passageFail"), f"failed load shows the friendly toast: {pg3.evaluate('__game.toastText')}")
    check(not pg3.evaluate("!!__game.room") and st["status"].get("church-cemetery") == "failed" and not st["entering"], f"Arek stays put, state failed, retry allowed {st['status']}")
    pg3.unroute("**/underground-tunnel.js")
    pg3.evaluate("PASSAGES.enter('church-cemetery','cemetery')"); time.sleep(1.5)
    check(pg3.evaluate("__game.room && __game.room.kind") == "tunnel", "retry after the failure works")
    pg3.close()
    pg4, _ = start_game(b, watch=False)
    r = pg4.evaluate("PASSAGES.enter('church-cemetery','cemetery')"); time.sleep(.3)
    check(r is False and pg4.evaluate("__game.toastText") == pg4.evaluate("ARK.T.passageLocked") and not pg4.evaluate("PASSAGES.state().scripts.length"), "closed gate: refused with a toast, nothing loaded")
    pg4.close()

    print("tunnel", "OK" if not fails else "FAILED", "errors", errs)
    b.close()
if fails:
    raise SystemExit("FAIL " + "; ".join(fails))
