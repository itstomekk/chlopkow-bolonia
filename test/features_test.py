"""Headless test: Halina + quiz, and the three minigames (race / pig / dogs)."""
import os
import time, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "wss://" not in m.text else None)   # public Nostr relays (global chat) being down is not a game error
    pg.goto(URL); pg.wait_for_function("window.__game && window.__features")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game && window.__features")
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    def tp(x, y): pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()"); time.sleep(.35)
    def skip_talk():
        for _ in range(15):
            if not pg.evaluate("!!__game.talk"): break
            pg.keyboard.press("Enter"); time.sleep(.08); pg.keyboard.press("Enter"); time.sleep(.08)
    # --- A question marker opens before meeting Irenka
    bd = [x for x in pg.evaluate("__game.ITEMS.boards") if x['spot'] == 'windmill'][0]
    tp(bd['x'], bd['y'] + 12); pg.keyboard.press("Enter")
    pg.wait_for_function("!!(__features.QZ && __features.QZ.q)")
    print('board quiz before halina:', pg.evaluate("__features.QZ && __features.QZ.q.id"))
    slot = pg.evaluate("__features.QZ.order.indexOf(__features.QZ.q.ok)"); pg.keyboard.press(f"Digit{slot+1}"); time.sleep(.3); pg.keyboard.press("Space"); time.sleep(.2)

    # --- Irenka + first question
    h = [n for n in pg.evaluate("__game.ITEMS.npcs") if n['id'] == 'halina'][0]
    tp(h['x'], h['y'] + 18); pg.keyboard.press("Enter"); time.sleep(.2); skip_talk(); time.sleep(.2)
    print('quiz open after halina:', pg.evaluate("__features.QZ && __features.QZ.q.id"))
    pg.screenshot(path="test/f1_quiz.png")
    pg.keyboard.press("Digit1"); time.sleep(.4); pg.screenshot(path="test/f2_quiz_result.png"); pg.keyboard.press("Space"); time.sleep(.2)
    # --- another marker (church)
    bd = [x for x in pg.evaluate("__game.ITEMS.boards") if x['spot'] == 'church'][0]
    tp(bd['x'], bd['y'] + 12); pg.keyboard.press("Enter")
    pg.wait_for_function("!!(__features.QZ && __features.QZ.q)")
    print('board quiz:', pg.evaluate("__features.QZ && __features.QZ.q.id"))
    # pick the correct answer through the UI mapping
    slot = pg.evaluate("__features.QZ.order.indexOf(__features.QZ.q.ok)"); pg.keyboard.press(f"Digit{slot+1}"); time.sleep(.3); pg.keyboard.press("Space"); time.sleep(.2)
    print('quiz state', pg.evaluate("JSON.stringify(__game.Q.quiz)"))
    # --- completion still works when every question was answered before the meeting
    pg.evaluate("(()=>{ __game.Q.halina=0; __game.Q.quiz=Object.fromEntries(window.QUIZ.map(q=>[q.id,1])); })()")
    tp(h['x'], h['y'] + 18); pg.keyboard.press("Enter"); time.sleep(.25)
    print('scorekeeper after pre-meeting completion:', pg.evaluate("__game.Q.halina"))
    skip_talk(); time.sleep(.2)
    # --- pig
    pg.evaluate("__features.startMG('pig')"); time.sleep(3.3); pg.screenshot(path="test/f3_pig.png")
    pig = pg.evaluate("__features.MG.pig"); pg.evaluate(f"__game.P.x={pig['x']}; __game.P.y={pig['y']}"); time.sleep(.2)
    print('pig:', pg.evaluate("__features.MG.phase"), pg.evaluate("__features.MG.msg")); pg.screenshot(path="test/f4_pig_win.png"); pg.keyboard.press("Escape")
    # --- dogs: lose by standing still next to a dog
    pg.evaluate("__features.startMG('dogs')"); time.sleep(3.2); pg.screenshot(path="test/f5_dogs.png")
    d = pg.evaluate("__features.MG.dogs[0]"); pg.evaluate(f"__game.P.x={d['x']-20}; __game.P.y={d['y']}"); time.sleep(2.5)
    print('dogs:', pg.evaluate("__features.MG.phase"), pg.evaluate("__features.MG.msg")); pg.keyboard.press("Escape")
    # --- dogs: win by collecting eggs quickly
    pg.evaluate("__features.startMG('dogs')"); time.sleep(3.1)
    for e in pg.evaluate("__features.MG.eggs"): pg.evaluate(f"__game.P.x={e['x']}; __game.P.y={e['y']}"); time.sleep(.05)
    time.sleep(.2); print('dogs2:', pg.evaluate("__features.MG.phase"), pg.evaluate("__features.MG.msg")); pg.keyboard.press("Escape")
    # --- race: Damian must win if we stand still; then we "drive" through checkpoints
    pg.evaluate("__features.startMG('race')"); time.sleep(3.6); pg.screenshot(path="test/f6_race.png")
    tr = pg.evaluate("__game.MAP.track")
    import math
    for lap in range(2):
        for k in range(1, 17):
            a = math.pi / 2 + k * 2 * math.pi / 16
            pg.evaluate(f"__game.P.x={tr['cx'] + math.cos(a) * tr['rx']}; __game.P.y={tr['cy'] + math.sin(a) * tr['ry']}"); time.sleep(.06)
    time.sleep(.2); print('race:', pg.evaluate("__features.MG && __features.MG.phase"), pg.evaluate("__features.MG && __features.MG.msg"))
    pg.screenshot(path="test/f7_race_end.png"); pg.keyboard.press("Escape")
    pg.evaluate("__features.startMG('race')"); time.sleep(3.2 + 27.5)
    print('race idle:', pg.evaluate("__features.MG.phase"), pg.evaluate("__features.MG.msg"))
    print('mg', pg.evaluate("JSON.stringify(__game.Q.mg)"))
    print('errors', errs); b.close()
