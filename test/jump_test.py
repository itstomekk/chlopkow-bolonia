import os
import time
from playwright.sync_api import sync_playwright
import sys
X, RY = int(sys.argv[1]), int(sys.argv[2])
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game")
    pg.evaluate("localStorage.clear()"); pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)
    pos = lambda: pg.evaluate("[Math.round(__game.P.x), Math.round(__game.P.y), __game.P.air]")
    pg.evaluate(f"__game.P.x={X}; __game.P.y={RY + 40}"); time.sleep(.4)
    pg.keyboard.down("ArrowUp"); time.sleep(1.2); pg.keyboard.up("ArrowUp"); print('walk into river ->', pos())
    pg.keyboard.down("ArrowUp"); pg.keyboard.press("KeyX"); time.sleep(.22); pg.screenshot(path="test/j1_midair.png"); time.sleep(.6); pg.keyboard.up("ArrowUp")
    print('after jump ->', pos(), 'river row', RY); time.sleep(.3); pg.screenshot(path="test/j2_landed.png")
    print('errors', errs); b.close()
