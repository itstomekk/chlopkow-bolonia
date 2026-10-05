"""Forest shade: the hero is drawn darker on 'forest' terrain, fades in/out, and is normal elsewhere.

Run:  ARK_URL=http://127.0.0.1:8765/index.html python test/forest_shade_test.py
"""
import os
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = Path(os.environ.get("SHADE_SHOTS", ROOT / "test"))

# a deep-forest point and the spawn (grass/road), from docs/img/map_terrain.png (220 = forest)
ter = Image.open(ROOT / "docs/img/map_terrain.png")
px, (tw, th) = ter.load(), ter.size
forest = None
for y in range(40, th - 40, 8):
    for x in range(40, tw - 40, 8):
        if all(px[x + dx, y + dy] == 220 for dx in (-30, 0, 30) for dy in (-30, 0, 30)):
            forest = (x, y)
            break
    if forest:
        break
assert forest, "no forest patch found"

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL)
    pg.wait_for_function("window.__game && window.__worldLife", timeout=40000)
    pg.evaluate("localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("window.__game && window.__worldLife", timeout=40000)
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Shade")
    pg.locator("#player-name-submit").click()
    pg.wait_for_function("__game.scene === 'play'", timeout=30000)
    time.sleep(0.8)

    k = pg.evaluate("window.MAP_K || (window.__game.MAP.w / %d)" % tw)
    fx, fy = forest[0] * k, forest[1] * k
    # Reproduce a legal random start in forest, independently of Math.random.
    if os.environ.get("SHADE_START_IN_FOREST") == "1":
        pg.evaluate(f"ARK.teleport({fx}, {fy})")
        pg.wait_for_function("__game.terrainAt(__game.P.x, __game.P.y) === 'forest' && __game.heroShade > .97", timeout=10000)
    # New games spawn randomly and may correctly start shaded in forest.
    # Establish the known grass/road control and let any initial shade fade out.
    pg.evaluate("ARK.teleport(__game.MAP.spawn.x, __game.MAP.spawn.y)")
    pg.wait_for_function("__game.terrainAt(__game.P.x, __game.P.y) !== 'forest' && __game.heroShade === 0", timeout=10000)
    assert pg.evaluate("__game.heroShade") == 0, "shade on grass at start"

    pg.evaluate(f"window.ARK.teleport({fx}, {fy})")
    pg.wait_for_function("__game.terrainAt(__game.P.x, __game.P.y) === 'forest'", timeout=5000)
    time.sleep(0.15)
    mid = pg.evaluate("__game.heroShade")
    assert 0 < mid < 1, f"shade should fade in, got {mid}"
    time.sleep(2.5)
    full = pg.evaluate("__game.heroShade")
    assert full > 0.97, f"full shade in forest, got {full}"
    pg.screenshot(path=str(SHOTS / "forest_shade.png"))

    pg.evaluate("ARK.teleport(__game.MAP.spawn.x, __game.MAP.spawn.y)")
    time.sleep(2.5)
    back = pg.evaluate("__game.heroShade")
    assert back < 0.03, f"shade should fade out on grass, got {back}"
    assert not errors, errors
    br.close()

print(f"forest shade OK: fade-in {mid:.2f} -> {full:.2f} in forest, {back:.2f} back on grass")
