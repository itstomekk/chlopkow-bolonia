"""One-off end-to-end check: the game in a browser talking to a LOCAL `wrangler dev` scores Worker (real CORS,
real validation, local D1). Usage: python cloud/scores-worker/e2e_local.py GAME_URL WORKER_URL"""
import sys, json, urllib.request
from playwright.sync_api import sync_playwright

GAME, WORKER = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{GAME}?scores={WORKER}"); pg.wait_for_function("!!(window.__game && window.__board)")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("!!(window.__game && window.__board)")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("E2E"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    pg.evaluate("__board.open('sprint')")
    pg.wait_for_function("document.getElementById('board-global') && document.getElementById('board-global').dataset.status === 'ok'", timeout=8000)
    pg.evaluate("__board.setSlots([{type:'human',char:'arek',ctrl:'kb1',name:'E2E Tomek'},{type:'avg',char:'damian',ctrl:'kb2',name:''},{type:'off',char:'renik',ctrl:'kb3',name:''},{type:'off',char:'renik',ctrl:'kb4',name:''}])")
    pg.locator("#board-start").click()
    pg.wait_for_function("__board.state.phase === 'run'", timeout=6000)
    pg.evaluate("""(() => { __board.pause(); let k = 0;
        while (__board.state.phase === 'run' && k < 3600) { if (k % 6 === 0) __board.press(0, (k / 6) % 2 ? 'right' : 'left'); __board.step(1); k++; } })()""")
    pg.wait_for_function("__board.state.results[0] && __board.state.results.find(r => !r.cpu).global !== 'sending' && __board.state.results.find(r => !r.cpu).global !== null", timeout=8000)
    me = [r for r in pg.evaluate("__board.state.results") if not r["cpu"]][0]
    print("result", me)
    board = json.load(urllib.request.urlopen(f"{WORKER}/v1/games/sprint/board"))
    hit = [e for e in board["best"] if e["name"] == "E2E Tomek"]
    print("cpu trace from server:", board["cpu"]["trace"])
    print("worker board has it:", hit)
    ok = isinstance(me["global"], int) and hit and abs(hit[0]["score"] - me["score"]) < .006 and board["cpu"]["trace"] and len(board["cpu"]["trace"]) == 10 and not errs
    print("E2E", "PASS" if ok else "FAIL", errs)
    b.close()
    sys.exit(0 if ok else 1)
