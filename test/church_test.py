"""Headless church test: enter from the village, walk the aisle, talk to the sołtys, walk out through the door."""
import time, os
from playwright.sync_api import sync_playwright
EXE = os.environ.get("CHROME")   # optional explicit Chromium path
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE) if EXE else p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game", timeout=30000)
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    pg.keyboard.press("Enter")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    def tp(x, y): pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()"); time.sleep(.35)
    def talk_all():
        for _ in range(12):
            if not pg.evaluate("!!__game.talk"): break
            pg.keyboard.press("Space"); time.sleep(.08); pg.keyboard.press("Space"); time.sleep(.08)
    c = pg.evaluate("__game.MAP.pois.find(p=>p.key==='church')"); tp(c['x'], c['y'] + 40)
    out = pg.evaluate("[__game.P.x, __game.P.y]")
    pg.keyboard.press("KeyE"); time.sleep(.8)
    assert pg.evaluate("!!__game.room"), "did not enter the church"
    pg.screenshot(path="test/c1_inside_door.png"); talk_all()
    pg.keyboard.down("ArrowUp"); time.sleep(1.2); pg.keyboard.up("ArrowUp")   # walk up the aisle
    pg.screenshot(path="test/c2_aisle.png")
    tp(216, 176); pg.keyboard.press("KeyE"); time.sleep(.6); pg.screenshot(path="test/c3_soltys.png")
    assert pg.evaluate("__game.talk && __game.talk.who") == "soltys", "sołtys did not talk"
    talk_all()
    tp(38, 164); pg.keyboard.press("KeyE"); time.sleep(.5); assert pg.evaluate("__game.talk && __game.talk.who") == "arek"; talk_all()
    pg.evaluate("__game.P.x=160; __game.P.y=426"); pg.keyboard.down("ArrowDown"); time.sleep(.6); pg.keyboard.up("ArrowDown"); time.sleep(.6)
    assert not pg.evaluate("!!__game.room"), "did not leave the church"
    back = pg.evaluate("[__game.P.x, __game.P.y]")
    assert abs(back[0] - out[0]) < 40 and abs(back[1] - out[1]) < 40, (out, back)
    pg.screenshot(path="test/c4_outside.png")
    print("church OK", out, back, "errors", errs); b.close()
