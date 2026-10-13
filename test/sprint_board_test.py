"""Sprint board (BIEG NA 100 METRÓW): flag + Damian intro -> lobby -> race -> results, records, CPU average.
Also asserts the removed lap race and 2P prototype are gone.
Usage: python test/sprint_board_test.py [URL]   (run_all wraps it in isolated_browser_runner.py)"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "test")
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    # stateful fake of chlopkow-api (overrides the runner's isolation route): no real writes
    G = {"rows": [], "posts": []}
    def fake_scores(route):
        import json as _j
        req = route.request
        if req.method == "POST":
            b = _j.loads(req.post_data or "{}"); b["_url"] = req.url; G["posts"].append(b); G["rows"].append(b)
            rank = 1 + len({r["name"] for r in G["rows"] if r["score"] < b["score"] and r["name"] != b["name"]})
            return route.fulfill(status=200, content_type="application/json", body=_j.dumps({"ok": True, "rank": rank, "rankWeek": rank, "percentile": 50, "score": b["score"], "best": b["score"]}))
        best = {}
        for r in G["rows"]:
            if r["name"] not in best or r["score"] < best[r["name"]]["score"]: best[r["name"]] = {"name": r["name"], "char": r.get("char", ""), "score": r["score"], "at": 0}
        rows = G["rows"]; tr = [r["trace"] for r in rows if isinstance(r.get("trace"), list) and len(r["trace"]) == 10]
        body = {"ok": True, "game": "sprint", "best": sorted(best.values(), key=lambda e: e["score"]),
                "recent": [{"name": r["name"], "char": r.get("char", ""), "score": r["score"], "at": 0} for r in reversed(rows)],
                "average": {"score": round(sum(r["score"] for r in rows) / len(rows), 2) if rows else None, "count": len(rows)},
                "cpu": {"score": round(sum(r["score"] for r in rows) / len(rows), 2) if rows else None, "count": len(rows),
                        "trace": [round(sum(t[i] for t in tr) / len(tr), 2) for i in range(10)] if tr else None},
                "players": len(best)}
        route.fulfill(status=200, content_type="application/json", body=_j.dumps(body))
    pg.route("https://chlopkow-api.kolotom.workers.dev/**", fake_scores)
    errs = []; bad_urls = []
    pg.on("response", lambda r: bad_urls.append(f"{r.status} {r.url}") if r.status >= 400 else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text and "WebSocket is already in CLOSING or CLOSED state" not in m.text else None)
    pg.goto(URL); pg.wait_for_function("!!(window.__game && window.__board)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__game && window.__board)")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("Tester"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'"); time.sleep(.3)
    ev = pg.evaluate

    # ---- removed features are gone
    check(ev("window.ARK.localCompetition === undefined && !document.getElementById('local-race-overlay')"), "2P key-mash prototype removed")
    check(ev("__game.MAP.track === undefined && !!__game.MAP.sprint"), "map.json: sprint venue, no race track")
    check(ev("ARK.HOOKS.speed.every(f => f(910, 5579) === 1)"), "no off-track slowdown hook left at the old oval")

    # ---- flag at the map venue, Damian next to it
    v = ev("__board.venues.sprint"); ms = ev("__game.MAP.sprint")
    check(v == {"x": ms["x"], "y": ms["y"]}, f"sprint flag at map.json sprint venue {v}")
    dam = ev("__game.ITEMS.npcs.find(n => n.id === 'damian')")
    check(dam and ((dam["x"] - v["x"]) ** 2 + (dam["y"] - v["y"]) ** 2) ** .5 < 150, f"Damian stands by the flag {dam}")
    near = ev(f"ARK.HOOKS.near.flatMap(f => f(__game.P)).filter(c => Math.hypot(c.x - {v['x']}, c.y - {v['y']}) < 40).map(c => c._board || 'other')")
    check(near == ["sprint"], f"exactly one interaction at the flag: {near}")

    # ---- real interaction: walk up, E, Damian's two lines, board opens
    ev(f"ARK.teleport({v['x'] + 6}, {v['y'] + 4})"); time.sleep(.3)
    pg.keyboard.press("KeyE"); time.sleep(.2)
    check(ev("!!__game.talk && __game.talk.who === 'damian'"), "Damian introduces the sprint")
    for _ in range(12):
        if ev("!!__board.ui"): break
        pg.keyboard.press("Enter"); time.sleep(.15)
    check(ev("!!__board.ui && __board.ui.id === 'sprint' && __board.ui.lobby"), "board lobby opens after the intro")
    check(ev("ARK.HOOKS.busy.some(f => f())"), "village is busy while the board is open")
    check(pg.locator("#board-overlay .board-slot").count() == 4, "lobby has four slots")
    order = ev("[...document.querySelectorAll('.board-slot')[0].querySelectorAll('[data-k]')].map(e => e.dataset.k).join()")
    check(order == "name,type,char,ctrl", f"slot order: name first, then human/CPU ({order})")
    check(ev("__board.ui.slots.map(s => s.type).join()") == "human,avg,cpu,cpu", "default lobby: human, PRZECIĘTNIAK, two CPU")
    time.sleep(.6); pg.screenshot(path=f"{SHOTS}/sprint1_lobby.png")
    check(ev("__board.scoresUrl") == "https://chlopkow-api.kolotom.workers.dev", "scores point at the game server chlopkow-api")
    check(ev("[...document.querySelectorAll('#board-global [data-list]')].map(e => e.dataset.list).join()") == "best,recent,average", "lobby shows NAJLEPSI / AKTUALNE / ŚREDNIA")
    check(ev("document.getElementById('board-global') && document.getElementById('board-global').dataset.status") == "ok", "lobby loaded the global board")
    check(ev("document.getElementById('board-global-send').checked"), "sending to the global board is on by default")
    check(ev("__board.run === null && document.activeElement && document.activeElement.id === 'board-start'"), "dialogue Enter does not start the race; START gets focus afterwards")

    # ---- validation: two humans on the same keys
    ev("__board.setSlots([{type:'human',char:'arek',ctrl:'kb1',name:'Ala'},{type:'human',char:'edytka',ctrl:'kb1',name:'Ola'},{type:'cpu',char:'damian',ctrl:'kb3',name:''},{type:'off',char:'renik',ctrl:'kb4',name:''}])")
    pg.locator("#board-start").click(); time.sleep(.1)
    check(ev("__board.run === null") and pg.locator("#board-error").inner_text().strip() != "", "duplicate controls block the start")
    ev("__board.setSlots([{type:'human',char:'arek',ctrl:'kb1',name:'Ala'},{type:'human',char:'edytka',ctrl:'kb4',name:'Ola'},{type:'avg',char:'damian',ctrl:'kb3',name:''},{type:'off',char:'renik',ctrl:'kb2',name:''}])")
    pg.locator("#board-start").click()
    check(ev("__board.state && __board.state.phase === 'count'"), "START begins the countdown")
    check(abs(ev("__board.state.cpuBase") - 15) < 1e-9, "CPU target defaults to 15 s with no history")
    st = ev("__board.state.game.runners")
    check(len(st) == 3 and [r["cpu"] for r in st] == [False, False, True], f"three runners, one CPU {[(r['slot'], r['cpu']) for r in st]}")

    # ---- false starts (real keys during the countdown): warning, then +2 s, then nothing more
    R = lambda i: ev(f"__board.state.game.runners[{i}]")
    pg.keyboard.press("KeyQ"); time.sleep(.05)
    r0 = R(0); check(r0["falseStarts"] == 1 and r0["penalty"] == 0, f"first false start = warning {r0['falseStarts']}/{r0['penalty']}")
    pg.keyboard.press("KeyW"); time.sleep(.05); pg.keyboard.press("KeyQ"); time.sleep(.05)
    r0 = R(0); check(r0["falseStarts"] >= 2 and r0["penalty"] == 2, f"second false start = +2 s ({r0['falseStarts']}, {r0['penalty']})")
    check(r0["d"] == 0 and r0["strides"] == 0, "false starts do not move the runner")
    check(R(1)["falseStarts"] == 0, "the other player has no false start")
    pg.wait_for_function("__board.state.phase === 'run'", timeout=6000)
    g = ev("__board.state.game")
    check(g["road"] is not None and 0.4 < g["road"][0] < g["road"][1] < 0.85, f"asphalt band found in the road art {g['road']}")
    rt, rb = g["road"][0] * 540, g["road"][1] * 540
    check(rt < g["feet"][0] < g["feet"][1] <= rb + 2 and rb < g["feet"][2] < g["feet"][3] < 540, f"two runners on the asphalt, two on the grass {g['feet']} road {rt:.0f}-{rb:.0f}")

    # ---- real keys while running: alternation strides, auto-repeat ignored, same key = stumble
    for i in range(10): pg.keyboard.press("KeyQ" if i % 2 == 0 else "KeyW"); time.sleep(.04)
    time.sleep(.05); r0 = R(0)
    check(r0["strides"] == 10 and r0["d"] > 0, f"P1 alternating Q/W = 10 strides (got {r0['strides']}, {r0['d']:.1f} m)")
    pg.keyboard.press("ArrowLeft"); time.sleep(.05)
    pg.keyboard.down("ArrowRight"); time.sleep(.05); pg.keyboard.down("ArrowRight"); time.sleep(.05); pg.keyboard.up("ArrowRight"); time.sleep(.05)
    r1 = R(1); check(r1["strides"] == 2 and r1["last"] == "right", f"auto-repeat is ignored (P2 strides {r1['strides']})")
    pg.keyboard.press("ArrowRight"); time.sleep(.03)
    r1 = R(1); check(r1["strides"] == 2 and r1["stumble"] > 0, f"same key twice = stumble (strides {r1['strides']}, stumble {r1['stumble']:.2f})")
    time.sleep(.4); pg.screenshot(path=f"{SHOTS}/sprint2_running.png")

    # ---- deterministic finish: P1 10 strides/s, P2 6 strides/s, fixed 60 Hz ticks
    ev("""(() => { __board.pause(); let k = 0;
        while (__board.state.phase === 'run' && k < 60 * 60) {
          if (k % 6 === 0) __board.press(0, (k / 6) % 2 ? 'right' : 'left');   // P1 last pressed W (right)
          if (k % 10 === 0) __board.press(1, (k / 10) % 2 ? 'right' : 'left');
          __board.step(1); k++;
        } __board.step(60); })()""")
    s = ev("__board.state")
    check(s["phase"] == "done", f"race finishes ({s['phase']})")
    res = s["results"]; print("results:", res)
    order = [r["slot"] for r in res]
    check(order == [0, 2, 1], f"order P1, CPU, P2 (got {order})")
    a, cpu, o = res[0], res[1], res[2]
    g = s["game"]["runners"]
    check(abs(a["score"] - (g[0]["finish"] + 2)) < .006 and a["note"] != "", f"P1 time includes the +2 s penalty ({a['score']:.2f})")
    check(9.0 < g[0]["finish"] < 12.5, f"10 strides/s runs 100 m in ~10-12 s ({g[0]['finish']:.2f})")
    check(15.5 < o["score"] < 22, f"6 strides/s is slower ({o['score']:.2f})")
    check(abs(cpu["score"] - g[2]["target"]) < .05 and 14 < cpu["score"] < 16, f"CPU finishes at its target ({cpu['score']:.2f} vs {g[2]['target']:.2f})")
    medal = lambda v: 3 if v <= 11 else 2 if v <= 13 else 1 if v <= 16 else 0
    check(a["medal"] == medal(a["score"]) and o["medal"] == medal(o["score"]), f"medals follow 16/13/11 s ({a['medal']}, {o['medal']})")
    q = ev("__game.Q.mg.sprint")
    check(q["tries"] == 1 and q["won"] and len(q["history"]) == 2, f"save: tries 1, won, two human results ({q})")
    check(q["best"] == a["score"] and a["record"] and round(a["score"], 2) == a["score"], "best time = P1 (0.01 s precision) and marked as record")
    top = ev("JSON.parse(localStorage.getItem('ark_board_sprint_top_v1'))")
    check(len(top) == 2 and top[0]["name"] == "Ala", f"device top list has both humans, fastest first {top}")
    ev("__board.step(1)"); pg.screenshot(path=f"{SHOTS}/sprint3_results.png")
    pg.wait_for_function("__board.state.results.every(r => r.cpu || Number.isInteger(r.global))", timeout=5000)
    posts = G["posts"]
    check(len(posts) == 2 and {p["name"] for p in posts} == {"Ala", "Ola"} and all(p["_url"].endswith("/v1/games/sprint/runs") and p["proof"]["strides"] > 50 for p in posts), f"both human results posted with a run proof {[(p['name'], p['score'], p['proof']) for p in posts]}")
    check(not any(p["name"] in ("DAMIAN", "PRZECIĘTNIAK") for p in posts), "CPU results are not posted")
    check(all(isinstance(p.get("trace"), list) and len(p["trace"]) == 10 and all(p["trace"][k] < p["trace"][k + 1] for k in range(9)) for p in posts), "each post carries 10 increasing split times")
    check(all(len(p.get("device", "")) >= 8 for p in posts) and posts[0]["device"] == posts[1]["device"] and posts[0]["mode"] == "local2", "posts carry this browser's device id and the local2 mode")
    a_tr = next(p for p in posts if p["name"] == "Ala")["trace"]
    check(abs(a_tr[-1] - (a["score"] - 2)) < .02, f"Ala's trace ends at her time without the false-start penalty ({a_tr[-1]} vs {a['score']})")
    gr = {r["name"]: r["global"] for r in ev("__board.state.results")}
    check(gr["Ala"] == 1 and gr["Ola"] == 2, f"results show world ranks {gr}")
    pg.wait_for_function("__board.global('sprint') && __board.global('sprint').best.length === 2", timeout=5000)
    ev("__board.step(1)"); pg.screenshot(path=f"{SHOTS}/sprint3_results.png")
    lines = ev("(() => { const l = []; ARK.HOOKS.questLog.forEach(f => f(l)); return l.map(x => x[0]); })()")
    check(any("100 m" in l for l in lines), f"quest log lists the sprint {[l for l in lines if '100' in l]}")

    # ---- rematch with ENTER: CPU now targets the average of the human history
    ev("__board.resume()"); time.sleep(.3)
    pg.keyboard.press("Enter"); time.sleep(.1)
    s2 = ev("__board.state")
    hist = q["history"]
    check(s2["phase"] == "count" and round(s2["cpuBase"], 2) == round(sum(hist) / len(hist), 2), f"rematch; CPU base = average of history ({s2['cpuBase']:.2f})")
    check(ev("__game.Q.mg.sprint.tries") == 2, "rematch counts a try")
    mean_tr = [round(sum(p["trace"][k] for p in posts) / 2, 2) for k in range(10)]
    check(s2["cpuSource"] == "global" and s2["cpuTrace"] == mean_tr, f"PRZECIĘTNIAK uses the global averaged trace {s2['cpuTrace']}")
    rr = s2["game"]["runners"][2]
    check(rr["replay"] and abs(rr["target"] - mean_tr[-1]) < 1e-9, f"PRZECIĘTNIAK replays it and finishes at its end ({rr['target']})")
    ev("__board.pause()"); ev("(() => { let k = 0; while (__board.state.phase !== 'done' && k < 60 * 60) { __board.step(1); k++; } })()")
    sp = next(r for r in ev("__board.state.game.runners") if r["slot"] == 2)["splits"]
    check(len(sp) == 10 and max(abs(sp[k] - mean_tr[k]) for k in range(10)) < .03, f"replayed splits match the average trace ({[round(v, 2) for v in sp]})")
    ev("__board.resume()")

    # ---- ESC back to the lobby, ESC closes; the village works again
    pg.keyboard.press("Escape"); time.sleep(.1)
    check(ev("__board.run === null && __board.ui && __board.ui.lobby"), "ESC during a run returns to the lobby (no result)")
    check(len(ev("__game.Q.mg.sprint.history")) == 2, "an aborted run records nothing")
    pg.keyboard.press("Escape"); time.sleep(.1)
    check(ev("__board.ui === null && !document.getElementById('board-overlay')"), "ESC in the lobby closes the board")
    check(not ev("ARK.HOOKS.busy.some(f => f())"), "village is no longer busy")
    x0 = ev("__game.P.x"); pg.keyboard.down("ArrowRight"); time.sleep(.4); pg.keyboard.up("ArrowRight"); x1 = ev("__game.P.x")
    check(abs(x1 - x0) > 5 or abs(ev("__game.P.y") - v["y"]) > 1, f"player walks again after closing ({x0:.0f} -> {x1:.0f})")
    pg.screenshot(path=f"{SHOTS}/sprint4_village.png")

    check(not errs, f"no page errors {errs} {bad_urls}")
    b.close()
print('\nFAILED:', fails if fails else 'none')
sys.exit(1 if fails else 0)
