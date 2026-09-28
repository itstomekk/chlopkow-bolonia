"""Headless play-test: walk around, check collisions and dialogue, save screenshots."""
import os
import time, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.on("pageerror", lambda e: print("[err]", e))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game", timeout=30000)
    time.sleep(.5); pg.screenshot(path="test/01_title.png")
    pg.keyboard.press("Enter"); time.sleep(.3)
    pos = lambda: pg.evaluate("[Math.round(__game.P.x), Math.round(__game.P.y), __game.P.dir]")
    print("spawn", pos())
    def hold(k, s):
        pg.keyboard.down(k); time.sleep(s); pg.keyboard.up(k); print(k, s, pos())
    hold("ArrowDown", .6); pg.screenshot(path="test/02_walk_down.png")
    hold("ArrowLeft", .8)
    pg.keyboard.down("ArrowLeft"); time.sleep(.25); pg.screenshot(path="test/03_walking_left.png"); pg.keyboard.up("ArrowLeft")
    # teleport next to the shop and talk
    shop = pg.evaluate("__game.MAP.pois.find(p=>p.key==='shop')")
    pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=3)for(let a=0;a<6.3;a+=.3){{const x={shop['x']}+Math.cos(a)*r,y={shop['y']}+Math.sin(a)*r; if(!g.blocked(x,y)){{g.P.x=x;g.P.y=y;return}}}}}})()")
    time.sleep(.6); pg.keyboard.press("Space"); time.sleep(2.2); pg.screenshot(path="test/04_shop_talk.png")
    pg.keyboard.press("Space"); time.sleep(.2)
    # church
    ch = pg.evaluate("__game.MAP.pois.find(p=>p.key==='church')")
    pg.evaluate(f"(()=>{{const g=__game; for(let r=40;r<160;r+=3)for(let a=0;a<6.3;a+=.3){{const x={ch['x']}+Math.cos(a)*r,y={ch['y']}+Math.sin(a)*r; if(!g.blocked(x,y)){{g.P.x=x;g.P.y=y;return}}}}}})()")
    time.sleep(1.2); pg.screenshot(path="test/05_church.png")
    pg.keyboard.press("KeyM"); time.sleep(.3); pg.screenshot(path="test/06_map.png"); pg.keyboard.press("KeyM")
    # collision: walk up into a house repeatedly
    hold("ArrowUp", 2.5); pg.screenshot(path="test/07_collide.png")
    b.close()
