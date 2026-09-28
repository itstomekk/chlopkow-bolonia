"""Headless full-quest play-test: talks to every NPC, collects items, finishes the game."""
import os
import time
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game", timeout=30000)
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    pg.keyboard.press("Enter")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    def tp(x, y): pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()"); time.sleep(.35)
    def talk_all():
        pg.keyboard.press("Space"); time.sleep(.1)
        for _ in range(12):
            if not pg.evaluate("!!__game.talk"): break
            pg.keyboard.press("Space"); time.sleep(.08); pg.keyboard.press("Space"); time.sleep(.08)
    npc = {n['id']: n for n in pg.evaluate("__game.ITEMS.npcs")}
    for k in ['kasia', 'damian', 'marcin', 'grandpa']:
        n = npc[k]; tp(n['x'], n['y'] + 20)
        if k == 'kasia': pg.keyboard.press("Space"); time.sleep(.5); pg.screenshot(path="test/q1_kasia.png"); talk_all()
        else: talk_all()
    print('after intros', pg.evaluate("JSON.stringify(__game.Q)"))
    for m in pg.evaluate("__game.Q.mushroomSpots")[:10]: tp(m['x'], m['y'])
    c = pg.evaluate("__game.ITEMS.cap"); tp(c['x'] + 30, c['y']); pg.screenshot(path="test/q2_cap_visible.png"); tp(c['x'], c['y']); time.sleep(.3); talk_all()
    shop = pg.evaluate("__game.MAP.pois.find(p=>p.key==='shop')"); tp(shop['x'], shop['y'] + 30); talk_all()
    print('items', pg.evaluate("JSON.stringify(__game.Q)"))
    for k in ['kasia', 'damian', 'marcin']: n = npc[k]; tp(n['x'], n['y'] + 20); talk_all()
    n = npc['grandpa']; tp(n['x'], n['y'] + 20); pg.screenshot(path="test/q3_grandpa_ready.png"); talk_all(); time.sleep(.5)
    print('final', pg.evaluate("JSON.stringify(__game.Q)"), pg.evaluate("__game.scene"))
    pg.screenshot(path="test/q4_end.png")
    for _ in range(3): pg.keyboard.press("Enter"); time.sleep(.2)  # three archive cards, then resume play
    pg.keyboard.press("KeyM"); time.sleep(.3); pg.screenshot(path="test/q5_map.png")
    print('errors', errs); b.close()
