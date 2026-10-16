"""Quick test access (docs/js/devtools.js): ?dev=1 panel (F2), ?play=<id>, ?go=<place>, throwaway save.
Asserts: default URL unchanged; every ?play id reaches its running phase (flag minigames, brawl, every board in
ARK_BOARDS); unknown id shows a message; ?go lands near the place (diacritics ignored, ?x/?y win); F2 panel and
minimap / M-map teleport; the REAL localStorage is byte-identical after all of it.
Usage (always through the isolated runner, never directly):
  ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/devtools_test.py"""
import json, math, os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "test")
BASE = URL.split("?")[0]
ORIGIN = BASE.rsplit("/", 1)[0]
fails = []
os.makedirs(SHOTS, exist_ok=True)


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)


REAL_SAVE = json.dumps({"v": 2, "Q": {"playerName": "RealPlayer", "apples": [1, 2, 3], "mg": {"pig": {"tries": 7, "best": 12.5, "won": True, "medal": 2}}, "playTime": 4321}, "x": 1200, "y": 4000})
REAL = {
    "arek-chlopkow-save-v1": REAL_SAVE,
    "arek-chlopkow-character-v1": "bercik",
    "ark_scores_send_v1": "true",
    "ark_device_v1": "real-device-0123456789",
    "ark_board_sprint_top_v1": json.dumps([{"name": "RealPlayer", "char": "bercik", "score": 14.2, "at": 1}]),
}


def snapshot(pg):
    """Raw localStorage of the origin, read from a static document that loads no game script."""
    pg.goto(f"{ORIGIN}/items.json")
    return pg.evaluate("Object.fromEntries(Object.keys(localStorage).sort().map(k => [k, localStorage.getItem(k)]))")


def near(a, b, d):
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= d


with sync_playwright() as p:
    b = p.chromium.launch()
    errs, bad = [], []

    def new_page(ctx, w=1280, h=720):
        pg = ctx.new_page(); pg.set_viewport_size({"width": w, "height": h})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text and "WebSocket is already in CLOSING or CLOSED state" not in m.text else None)
        pg.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 400 else None)
        return pg

    def open_game(pg, query=""):
        pg.goto(BASE + query)
        pg.wait_for_function("!!(window.__game && window.ARK)")
        pg.wait_for_function("!window.__devtools || window.__devtools.ready")
        return pg.evaluate

    def pos(ev):
        return ev("[__game.P.x, __game.P.y]")

    def wait_near(pg, ev, target, d=120, t=8000):
        try:
            pg.wait_for_function(f"Math.hypot(__game.P.x - {target[0]}, __game.P.y - {target[1]}) <= {d}", timeout=t)
        except Exception:
            pass
        return near(pos(ev), target, d)

    ctx = b.new_context(viewport={"width": 1280, "height": 720})
    pg = new_page(ctx)

    # ================================================================= 1. default URL: nothing changes
    ev = open_game(pg)
    check(ev("__game.scene === 'title'"), "default URL: starts on the title screen")
    check(ev("typeof window.__devtools === 'undefined'"), "default URL: no window.__devtools")
    check(ev("!document.getElementById('dev-panel') && !document.getElementById('dev-badge') && !document.getElementById('dev-message')"), "default URL: no dev DOM")
    check(ev("Storage.prototype.getItem === localStorage.getItem && /native code/.test(Storage.prototype.setItem.toString())"), "default URL: localStorage is the native one")
    pg.keyboard.press("F2"); time.sleep(.2)
    check(ev("!document.getElementById('dev-panel')"), "default URL: F2 does nothing")
    ARK_KEYS = ev("Object.keys(ARK).sort().join()")
    check("minigames" not in ARK_KEYS.split(","), "default URL: no extra ARK members from the plugin")
    check(ev("!!(window.__features && window.__features.startMG)"), "existing __features.startMG is what the plugin relies on")
    DISCOVERED_BOARDS = ev("Object.keys(window.ARK_BOARDS || {})")
    check("sprint" in DISCOVERED_BOARDS, f"boards registered: {DISCOVERED_BOARDS}")
    MAPW = ev("[__game.MAP.w, __game.MAP.h]")
    CHURCH = ev("(m => { const c = m.pois.find(p => p.key === 'church'); return [c.x, c.y]; })(__game.MAP)")
    CEM = ev("(m => { const c = m.pois.find(p => p.key === 'cemetery'); return [c.x, c.y]; })(__game.MAP)")
    pg.close()

    # ================================================================= 2. real save fixture, then every sandbox mode
    pg = new_page(ctx)
    pg.goto(f"{ORIGIN}/items.json")
    pg.evaluate("kv => { localStorage.clear(); for (const [k, v] of Object.entries(kv)) localStorage.setItem(k, v); }", REAL)
    before = snapshot(pg)
    check(before == dict(sorted(REAL.items())), "fixture: real save written")

    def sandbox_run(query, wait_js, label, timeout=20000):
        ev = open_game(pg, query)
        try:
            pg.wait_for_function(wait_js, timeout=timeout); ok = True
        except Exception:
            ok = False
        check(ok, f"{label}: {query or '(none)'}")
        return ev

    ev = sandbox_run("?play=world", "__game.scene === 'play'", "?play=world starts in the world")
    check(ev("__game.playerName") == "Arek" and ev("__game.playerCharacter") == "arek", f"default character/name in the sandbox ({ev('[__game.playerCharacter, __game.playerName]')})")
    check(ev("localStorage.getItem('arek-chlopkow-save-v1')") is None or ev("JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).Q.playerName") != "RealPlayer", "sandbox does not see the real save")
    check(ev("localStorage.getItem('ark_scores_send_v1')") == "false", "sandbox: global score sending is off")
    ev("ARK.save()")
    check(ev("JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).Q.playerName") == "Arek", "sandbox: ARK.save() writes only to the throwaway store")

    flag_types = ["pig", "dogs", "skeet", "ducks", "mowing"]
    for t in flag_types:
        ev = sandbox_run(f"?play={t}", f"!!(__features.MG && __features.MG.type === '{t}' && __features.MG.phase === 'run')", f"?play={t} reaches phase run")
        check(ev("__game.scene") == "play" and not ev("document.getElementById('dev-panel')"), f"?play={t}: in the world, no panel (dev not requested)")
        ev("ARK.save()")
    ev = sandbox_run("?play=DOGS", "!!(__features.MG && __features.MG.type === 'dogs')", "?play is case-insensitive")

    ev = sandbox_run("?play=brawl", "!!(ARK.brawl && ARK.brawl.fight && ARK.brawl.fight.phase === 'fight')", "?play=brawl reaches the fight phase", 25000)
    for bid in DISCOVERED_BOARDS:
        ev = sandbox_run(f"?play={bid}", "!!(window.__board && __board.state && __board.state.phase === 'run')", f"?play={bid} (board) reaches phase run", 25000)
        check(ev("!!document.querySelector('#board-overlay')") and ev("__board.ui.lobby") is False, f"?play={bid}: lobby skipped, board canvas running")
        ev("ARK.save()")
    ev = sandbox_run(f"?play={DISCOVERED_BOARDS[0]}&lobby=1", "!!(window.__board && __board.ui && __board.ui.lobby)", "?lobby=1 stops in the board lobby")

    ev = sandbox_run("?play=nonsense_game", "!!window.__devtools && window.__devtools.playStatus === 'unknown'", "?play=<unknown> is recognised")
    check(ev("document.getElementById('dev-message') && getComputedStyle(document.getElementById('dev-message')).display !== 'none' && /unknown minigame/.test(document.getElementById('dev-message').textContent)"), "unknown id: visible message")
    check(ev("document.getElementById('dev-message').textContent").count("sprint") == 1 and ev("__game.scene") == "play", "unknown id: message lists valid ids, game still runs")
    pg.screenshot(path=f"{SHOTS}/devtools_unknown_play.png")

    # --- the real save must be byte-identical after every sandbox run above
    after = snapshot(pg)
    check(after == before, "REAL localStorage byte-identical after ?play for every id")

    # ================================================================= 3. ?dev=1: panel, F2, teleport, start, interiors
    ev = sandbox_run("?dev=1", "__game.scene === 'play' && !!window.__devtools && __devtools.ready", "?dev=1 auto-starts in the world (throwaway save)")
    check(ev("document.getElementById('dev-badge').textContent").startswith("DEV") and ev("!document.getElementById('dev-panel').classList.contains('open')"), "badge shown, panel closed by default")
    pg.keyboard.press("F2"); time.sleep(.3)
    check(ev("document.getElementById('dev-panel').classList.contains('open')"), "F2 opens the panel")
    check(ev("document.activeElement && document.activeElement.id") == "dev-search", "search box focused")
    entries = ev("__devtools.entries()")
    kinds = {k: sum(1 for e in entries if e["kind"] == k) for k in ("place", "district", "npc", "minigame", "interior")}
    check(all(kinds[k] > 0 for k in kinds), f"registry has every kind: {kinds}")
    ids = {e["id"] for e in entries if e["kind"] == "minigame"}
    check({"pig", "dogs", "skeet", "ducks", "mowing", "brawl", *DISCOVERED_BOARDS} <= ids, f"all minigame ids listed: {sorted(ids)}")
    check(kinds["npc"] == ev("__game.ITEMS.npcs.length"), "every NPC listed")
    pg.screenshot(path=f"{SHOTS}/devtools_panel_desktop.png")

    # typing in the search box must not drive the game (M opens the map, WASD walks)
    p0 = pos(ev)
    pg.keyboard.type("kosciol", delay=15)
    check(not ev("__game.showMap") and near(pos(ev), p0, 3) and ev("ARK.keys.size") == 0, "typing in the search does not reach the game")
    first = ev("document.querySelector('#dev-list .dev-item').textContent")
    check("KOŚCIÓŁ" in first.upper(), f"search 'kosciol' (no diacritics) lists Kościół first: {first!r}")
    pg.locator("#dev-list .dev-item").first.click()
    check(wait_near(pg, ev, CHURCH, 120), f"panel click teleports to the church {pos(ev)} vs {CHURCH}")
    check(not ev("document.getElementById('dev-panel').classList.contains('open')"), "panel closes after a click")

    # NPC + district
    pg.keyboard.press("F2"); pg.fill("#dev-search", "kasia"); pg.locator("#dev-list .dev-item[data-kind=npc]").first.click()
    kasia = ev("(n => [n.x, n.y])(__game.ITEMS.npcs.find(n => n.id === 'kasia'))")
    check(wait_near(pg, ev, kasia, 80), f"NPC click teleports next to Kasia {pos(ev)} vs {kasia}")
    pg.wait_for_function("__districts.status === 'ready'", timeout=8000)
    pg.keyboard.press("F2"); time.sleep(.2); pg.fill("#dev-search", "dolina"); pg.locator("#dev-list .dev-item[data-kind=district]").first.click()
    dol = ev("(e => [e.x, e.y])(__devtools.entries().find(e => e.id === 'dolina'))")
    check(0 < dol[0] < MAPW[0] and 0 < dol[1] < MAPW[1] and ev("__districts.at(%d, %d)" % (dol[0], dol[1])) is not None, f"Dolina's spot is inside the map and inside the district {dol}")
    check(wait_near(pg, ev, dol, 120), f"district click teleports into the district {pos(ev)} vs {dol}")

    # minigames from the panel
    for t in ("pig", "mowing"):
        pg.keyboard.press("F2"); pg.fill("#dev-search", t if t == "pig" else "boisko"); pg.locator("#dev-list .dev-item[data-kind=minigame]").first.click()
        try: pg.wait_for_function(f"__features.MG && __features.MG.type === '{t}' && __features.MG.phase === 'run'", timeout=15000); ok = True
        except Exception: ok = False
        check(ok, f"panel starts minigame {t} -> run")
    pg.keyboard.press("F2"); pg.fill("#dev-search", "sprint"); pg.locator("#dev-list .dev-item[data-kind=minigame][data-id=sprint]").first.click()
    try: pg.wait_for_function("__board.state && __board.state.phase === 'run'", timeout=20000); ok = True
    except Exception: ok = False
    check(ok and ev("!__features.MG"), "panel starts the sprint board -> run (previous minigame left)")
    # teleport away from a running board: overlay closes
    pg.keyboard.press("F2"); pg.fill("#dev-search", "sklep"); pg.locator("#dev-list .dev-item[data-kind=place]").first.click()
    shop = ev("(p => [p.x, p.y])(__game.MAP.pois.find(p => p.key === 'shop'))")
    check(wait_near(pg, ev, shop, 120) and ev("!document.querySelector('#board-overlay')"), "teleport out of a running board closes it")
    # shift+click on a board = lobby only
    pg.keyboard.press("F2"); pg.fill("#dev-search", "sprint")
    pg.locator("#dev-list .dev-item[data-kind=minigame][data-id=sprint]").first.click(modifiers=["Shift"])
    try: pg.wait_for_function("__board.ui && __board.ui.lobby", timeout=8000); ok = True
    except Exception: ok = False
    check(ok and ev("!__board.state"), "Shift+click on a board opens its lobby only")
    ev("__board.close()")

    # interiors
    for name, rid in (("wnetrze kosciola", "church"), ("krypta", "crypt"), ("tunel", "church-cemetery")):
        pg.keyboard.press("F2"); pg.fill("#dev-search", name); pg.locator("#dev-list .dev-item[data-kind=interior]").first.click()
        try: pg.wait_for_function(f"ARK.rooms.id === '{rid}' && !ARK.rooms.busy", timeout=15000); ok = True
        except Exception: ok = False
        check(ok, f"interior {name} -> room {rid} (now {ev('ARK.rooms.id')})")
    pg.keyboard.press("F2"); pg.fill("#dev-search", "cmentarz"); pg.locator("#dev-list .dev-item[data-kind=place]").first.click()
    try: pg.wait_for_function("ARK.rooms.depth === 0 && !ARK.rooms.busy", timeout=15000)
    except Exception: pass
    check(ev("ARK.rooms.depth") == 0 and wait_near(pg, ev, CEM, 160), f"panel teleport from the tunnel surfaces at the cemetery {pos(ev)} vs {CEM}")

    # Enter picks the first result; Escape closes
    pg.keyboard.press("F2"); pg.fill("#dev-search", "plebania"); pg.keyboard.press("Enter")
    reb = ev("(p => [p.x, p.y])(__game.MAP.pois.find(p => p.key === 'rectory'))")
    check(wait_near(pg, ev, reb, 120), "Enter in the search box activates the first result")
    pg.keyboard.press("F2"); pg.keyboard.press("Escape")
    check(not ev("document.getElementById('dev-panel').classList.contains('open')") and ev("__game.scene") == "play", "Escape closes the panel and does not leave the game")

    # minimap / M-map clicks
    def canvas_point(x, y, big):
        return ev("""([x, y, big]) => { const c = document.getElementById('game'), r = c.getBoundingClientRect(), W = c.width, H = c.height, U = Math.min(W, H * 1.6) / 100, M = __game.MAP;
            const mw = big ? Math.min(W * .8, H * .8 * M.w / M.h) : U * 16, mh = mw * M.h / M.w, mx = big ? (W - mw) / 2 : W - mw - U * 2, my = big ? (H - mh) / 2 : U * 2;
            return [r.left + (mx + x / M.w * mw) / W * r.width, r.top + (my + y / M.h * mh) / H * r.height]; }""", [x, y, big])
    for _ in range(12):   # arriving at the rectory can open an NPC dialogue; close it like a player would
        if not ev("!!ARK.talk"): break
        pg.keyboard.press("Enter"); time.sleep(.2)
    tgt = [1500, 2600]
    cx, cy = canvas_point(*tgt, False); pg.mouse.click(cx, cy)
    check(wait_near(pg, ev, tgt, 25), f"click on the minimap teleports {pos(ev)} vs {tgt}")
    pg.keyboard.press("KeyM"); time.sleep(.2); check(ev("__game.showMap"), "M opens the big map")
    tgt = [4300, 6200]
    cx, cy = canvas_point(*tgt, True); pg.mouse.click(cx, cy)
    check(wait_near(pg, ev, tgt, 40) and not ev("__game.showMap"), f"click on the M-map teleports and closes it {pos(ev)} vs {tgt}")

    # narrow screen layout
    pg.set_viewport_size({"width": 390, "height": 844}); time.sleep(.3)
    pg.keyboard.press("F2"); time.sleep(.3)
    r = ev("(r => ({ l: r.left, t: r.top, w: r.width, h: r.height, vw: innerWidth, vh: innerHeight }))(document.getElementById('dev-panel').getBoundingClientRect())")
    check(r["l"] >= 0 and r["l"] + r["w"] <= r["vw"] + 1 and r["t"] + r["h"] <= r["vh"] + 1, f"mobile: panel inside the viewport {r}")
    pg.screenshot(path=f"{SHOTS}/devtools_panel_mobile.png")
    check(ev("getComputedStyle(document.getElementById('dev-badge')).display") == "none", "mobile: badge hidden while the panel is open (does not overlap it)")
    pg.locator("#dev-close").click(); time.sleep(.2)
    check(not ev("document.getElementById('dev-panel').classList.contains('open')") and ev("getComputedStyle(document.getElementById('dev-badge')).display") != "none", "mobile: close button closes the panel and the badge returns")
    pg.locator("#dev-badge").click(); time.sleep(.2)
    check(ev("document.getElementById('dev-panel').classList.contains('open')"), "mobile: the DEV badge opens the panel (no F2 key on phones)")
    pg.fill("#dev-search", "tun"); time.sleep(.2); pg.screenshot(path=f"{SHOTS}/devtools_panel_mobile_search.png")
    pg.fill("#dev-search", ""); pg.locator("#dev-close").click(); time.sleep(.2)
    pg.set_viewport_size({"width": 1280, "height": 720}); time.sleep(.2)
    pg.keyboard.press("F2"); time.sleep(.3); pg.fill("#dev-search", "ko"); time.sleep(.2)
    pg.screenshot(path=f"{SHOTS}/devtools_panel_search.png")

    after = snapshot(pg)
    check(after == before, "REAL localStorage byte-identical after the whole ?dev=1 session")

    # ================================================================= 4. ?go
    GO_CASES = [("kosciol", CHURCH, "KOŚCIÓŁ"), ("KOŚCIÓŁ", CHURCH, None), ("Cmentarz", CEM, None), ("sklep", shop, None)]
    for q, tgt, _ in GO_CASES:
        ev = open_game(pg, f"?dev=1&go={q}")
        check(wait_near(pg, ev, tgt, 120), f"?go={q} lands near the place {pos(ev)} vs {tgt}")
    ev = open_game(pg, "?dev=1&go=dolina")
    pg.wait_for_function("!!__devtools.goTarget", timeout=8000)
    dol = ev("(e => [e.x, e.y])(__devtools.entries().find(e => e.id === 'dolina'))")
    check(wait_near(pg, ev, dol, 120), f"?go=dolina (district) {pos(ev)} vs {dol}")
    ev = open_game(pg, "?dev=1&go=Chlopkow%2008")
    check(ev("__devtools.goStatus") == "ok" and ev("__devtools.goTarget.name") == "Chłopków 08", f"?go matches 'Chlopkow 08' -> {ev('__devtools.goTarget')}")
    ev = open_game(pg, "?dev=1&go=kosciol&x=300&y=300")
    check(ev("__devtools.goStatus") == "ignored-xy" and near(pos(ev), (300, 300), 150), f"?x=&y= beat ?go {pos(ev)}")
    ev = open_game(pg, "?dev=1&go=zzzz")
    check(ev("__devtools.goStatus") == "unknown" and "no such place" in ev("document.getElementById('dev-message').textContent") and ev("__game.scene") == "play", "?go=<unknown>: visible message, no crash")
    ev = open_game(pg, "?play=pig&go=kosciol")
    pg.wait_for_function("__features.MG && __features.MG.phase === 'run'", timeout=15000)
    check(near(pos(ev), ev("(c => [c.cx, c.cy])(__game.MAP.corral)"), 400), "?play=<minigame> beats ?go (player is at the minigame venue)")
    ev = open_game(pg, "?play=world&go=kosciol")
    check(wait_near(pg, ev, CHURCH, 120), "?play=world&go=kosciol: start in the world and go")

    check(snapshot(pg) == before, "REAL localStorage byte-identical after ?go runs too")
    pg.close()

    # ================================================================= 5. ?go alone (real save semantics, title flow, arrival re-apply)
    ctx2 = b.new_context(viewport={"width": 1280, "height": 720})
    pg2 = new_page(ctx2)
    ev = open_game(pg2, "?go=kosciol")
    check(ev("__game.scene") == "title" and ev("/native code/.test(Storage.prototype.getItem.toString()) && Storage.prototype.getItem === localStorage.getItem"), "?go alone: title screen, native localStorage (no sandbox)")
    check(not ev("document.getElementById('dev-panel')"), "?go alone: no panel")
    check(wait_near(pg2, ev, CHURCH, 120), f"?go alone: positioned at the church on the title screen {pos(ev)}")
    pg2.keyboard.press("KeyN"); pg2.locator("#player-name-input").fill("GoTester"); pg2.keyboard.press("Enter")
    pg2.wait_for_function("__game.scene === 'play'")
    check(wait_near(pg2, ev, CHURCH, 120), f"?go alone: after a new game the player is at the church, not the random spawn {pos(ev)}")
    pg2.close()

    # ================================================================= 6. ?dev=1&save=real keeps the real save and normal title flow
    pg3 = new_page(ctx)
    ev = open_game(pg3, "?dev=1&save=real")
    check(ev("__devtools.sandbox") is False and ev("__game.scene") == "title" and ev("/native code/.test(Storage.prototype.getItem.toString())"), "?save=real: no sandbox, normal title screen")
    check("REAL save" in ev("document.getElementById('dev-badge').textContent"), "?save=real: badge says REAL save")
    pg3.keyboard.press("F2"); pg3.fill("#dev-search", "pig"); pg3.locator("#dev-list .dev-item[data-id=pig]").first.click(); time.sleep(.3)
    check("Start the game first" in ev("document.getElementById('dev-message').textContent") and not ev("__features.MG"), "?save=real on the title: clicking explains instead of acting")
    pg3.close()

    check(not errs, f"no page errors {errs[:3]}")
    check(not [u for u in bad if "chlopkow-api" not in u and "esm.sh" not in u], f"no 4xx/5xx responses {bad[:3]}")
    b.close()

print("FAILED:" if fails else "PASS devtools_test", fails if fails else "")
sys.exit(1 if fails else 0)
