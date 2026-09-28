"""Edytka's quest: bring Frodo to her 3 times; each time he stays ~10 s and then runs back to Arek.

    python -m http.server 8765 --directory docs
    python test/edytka_test.py
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOT = os.path.join(os.environ.get("TMPDIR", "."), "edytka_visit.png")

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errors = []; pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL); pg.wait_for_function("window.__game")
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    pg.keyboard.press("KeyN"); pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    stay = pg.evaluate("__game.edytkaStay"); assert stay == 10, stay
    e = pg.evaluate("__game.ITEMS.npcs.find(n => n.id === 'edytka')")
    assert e, "Edytka is not on the map"

    def go(x, y, dog=True):   # teleport Arek (and Frodo with him, unless he is visiting Edytka)
        pg.evaluate(f"(()=>{{const g=__game;for(let r=0;r<160;r+=2)for(let a=0;a<6.3;a+=.25){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r;if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;if({'true' if dog else 'false'}){{g.FRODO.x=X;g.FRODO.y=Y}};return}}}}}})()")

    def close_talk():
        for _ in range(8):
            if not pg.evaluate("!!__game.talk"): return
            pg.keyboard.press("Space"); time.sleep(.15)

    # first meeting: she explains the quest
    go(e["x"] + 900, e["y"]); time.sleep(.3)
    go(e["x"] + 30, e["y"] + 20); time.sleep(.2)
    pg.evaluate("__game.talkTo('edytka')"); close_talk()
    assert pg.evaluate("__game.Q.edytka") == 1, "quest should be active after talking"
    pg.wait_for_function("!!__game.FRODO.visit || __game.Q.edytkaN === 0", timeout=3000)
    if pg.evaluate("__game.Q.edytkaN") == 1:   # Frodo was already beside her when she finished talking
        pg.wait_for_function("!__game.FRODO.visit", timeout=15000); close_talk()
        pg.evaluate("__game.Q.edytkaN = 0")      # start the count clean for the loop below
    for n in (1, 2, 3):
        go(e["x"] + 700, e["y"] + 300); time.sleep(.4)            # away from her
        go(e["x"] + 30, e["y"] + 20); time.sleep(.6)              # bring Frodo close
        close_talk()
        assert pg.evaluate("__game.Q.edytkaN") == n, pg.evaluate("__game.Q")
        assert pg.evaluate("!!__game.FRODO.visit"), "Frodo should be visiting Edytka"
        if n == 1: time.sleep(1.5); pg.screenshot(path=SHOT)
        go(e["x"] + 500, e["y"] + 200, dog=False)                 # Arek walks off; Frodo stays with her
        time.sleep(1)
        f = pg.evaluate("[__game.FRODO.x, __game.FRODO.y]")
        assert abs(f[0] - e["x"]) < 90 and abs(f[1] - e["y"]) < 90, f"Frodo left Edytka too early {f}"
        pg.wait_for_function("!__game.FRODO.visit", timeout=15000)   # after ~10 s he runs back
        close_talk()
        pg.wait_for_function("Math.hypot(__game.FRODO.x-__game.P.x, __game.FRODO.y-__game.P.y) < 120", timeout=15000)
    assert pg.evaluate("__game.Q.edytka") == 2, "quest should be done after 3 visits"
    assert not errors, errors
    print("edytka: PASS - 3 visits, Frodo stays ~10 s each time and returns to Arek; screenshot", SHOT)
    b.close()
