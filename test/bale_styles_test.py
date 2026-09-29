"""B05: larger, rounder hay bales.

RED/GREEN checks against docs/js/game.js drawBale:
  * art bounds grow beyond the pre-B05 baseline (23x10, aspect 2.30)
  * visible aspect ratio lands in [1.4, 1.7] (rounder, not stretched)
  * the actually rendered sprite at gameplay zoom matches the declared art
  * bale count/coordinates stay identical to docs/map.json (86 bales)
  * pushing still works for the hero AND Frodo; a walkable route stays nearby

Run:  ARK_URL=http://127.0.0.1:8790/index.html python test/bale_styles_test.py
"""
import json
import math
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = Path(os.environ.get("B05_SHOTS", ROOT / "test"))
map_data = json.loads((ROOT / "docs/map.json").read_text(encoding="utf-8"))
OLD = {"w": 23, "h": 10, "aspect": 2.30, "area": 230}   # pre-B05 art baseline (captured in RED)

SCAN_JS = """() => {
  const g = window.__game, A = window.ARK;
  const b = g.bales[0];
  const z = A.zoom;
  const [sx, sy] = A.camera.S(b.x, b.y);
  const crop = 70, size = crop * 2;
  const x0 = Math.max(0, Math.round(sx - crop)), y0 = Math.max(0, Math.round(sy - crop + 10));
  const img = A.ctx.getImageData(x0, y0, size, size), d = img.data;
  const pal = [[0xc9,0x91,0x3c],[0xb0,0x7b,0x30],[0x8a,0x5a,0x22],[0xdc,0xaa,0x4a],[0xf4,0xd2,0x7a],[0x5a,0x3a,0x17]];
  const match = (r, gg, bb) => pal.some(p => Math.abs(r - p[0]) <= 16 && Math.abs(gg - p[1]) <= 16 && Math.abs(bb - p[2]) <= 16);
  const at = (ix, iy) => match(d[(iy * size + ix) * 4], d[(iy * size + ix) * 4 + 1], d[(iy * size + ix) * 4 + 2]);
  const seedX = Math.round(sx - x0), seedY = Math.round(sy - z * 8 - y0);
  let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9, visited = 0;
  const seen = new Uint8Array(size * size);
  const stack = [[seedX, seedY]];
  while (stack.length) {
    const [ix, iy] = stack.pop();
    if (ix < 0 || iy < 0 || ix >= size || iy >= size || seen[ix * size + iy] || !at(ix, iy)) continue;
    seen[ix * size + iy] = 1;
    visited++;
    x1 = Math.min(x1, ix); y1 = Math.min(y1, iy); x2 = Math.max(x2, ix); y2 = Math.max(y2, iy);
    stack.push([ix + 1, iy], [ix - 1, iy], [ix, iy + 1], [ix, iy - 1]);
  }
  return { sx, sy, z, x1: x1 + x0, y1: y1 + y0, x2: x2 + x0, y2: y2 + y0,
           w: x2 - x1 + 1, h: y2 - y1 + 1, visited };
}"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_function("window.__game && window.__worldLife", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="load")
    page.wait_for_function("window.__game && window.__worldLife", timeout=30000)
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Bale")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'", timeout=30000)
    time.sleep(0.4)

    # ---------- 1. bale count + coordinates identical to map.json (before any pushing) ----------
    facts = page.evaluate("() => ({ count: window.__game.bales.length, zoom: window.ARK.zoom })")
    assert facts["count"] == len(map_data["bales"]) == 86, facts["count"]
    got = page.evaluate("__game.bales.map(b => [b.x, b.y, b.hx, b.hy])")
    src = [[b["x"], b["y"], b["x"], b["y"]] for b in map_data["bales"]]
    for i, (g0, s0) in enumerate(zip(got, src)):
        assert all(abs(a - b) < 1e-9 for a, b in zip(g0, s0)), (i, g0, s0)
    print(f"count/coords: 86 bales identical to map.json  (zoom={facts['zoom']:.3f})")

    # ---------- 2. visible bounds at gameplay zoom: rendered canvas pixel scan ----------
    page.evaluate("window.ARK.teleport(window.__game.bales[0].x, window.__game.bales[0].y - 60)")
    time.sleep(0.8)   # let the camera settle
    scan = page.evaluate(SCAN_JS)
    print("pixel scan:", {k: scan[k] for k in ("sx", "sy", "z", "x1", "y1", "x2", "y2", "w", "h", "visited")})
    assert scan["visited"] > 200, scan            # flood fill actually found the bale
    z = scan["z"]
    w_art, h_art = scan["w"] / z, scan["h"] / z
    aspect = scan["w"] / scan["h"]
    area = w_art * h_art
    print(f"visible bounds (art px at zoom {z:.3f}): {w_art:.1f}x{h_art:.1f} aspect={aspect:.2f} area={area:.0f}")
    page.screenshot(path=str(SHOTS / "b05_bale.png"),
                    clip={"x": scan["sx"] - 90, "y": scan["sy"] - 100, "width": 180, "height": 150})
    assert w_art > OLD["w"], (w_art, OLD)
    assert h_art > OLD["h"] * 1.4, (h_art, OLD)     # tall growth = rounder, not stretched
    assert 1.4 <= aspect <= 1.7, aspect
    assert area >= 1.35 * OLD["area"], (area, OLD)
    print(f"visible bounds: LARGER + ROUNDER than old {OLD['w']}x{OLD['h']} (aspect {OLD['aspect']}) -> PASS")

    # ---------- 3. declared art (test hook) agrees with the rendered pixels ----------
    geomz = page.evaluate("window.__game.baleGeometry(window.ARK.zoom)")
    ex0, ey0 = scan["sx"] - geomz["halfW"] * z, scan["sy"] - geomz["top"] * z
    assert abs(scan["x1"] - ex0) <= 4 and abs(scan["y1"] - ey0) <= 4, (scan, ex0, ey0)
    assert abs(scan["w"] - geomz["screenW"]) <= 6 and abs(scan["h"] - geomz["screenH"]) <= 6, (scan, geomz)
    print(f"declared art {geomz['w']}x{geomz['h']} (aspect {geomz['aspect']}, area {geomz['area']}) "
          f"matches rendered {scan['w']}x{scan['h']}px -> PASS")

    # ---------- 4. nearby walkable route (reachable, not blocked) ----------
    route = page.evaluate("""() => {
      const g = window.__game;
      const b = g.bales[0];
      for (let r = 16; r < 260; r += 6) for (let a = 0; a < 6.28; a += 0.35) {
        const x = b.x + Math.cos(a) * r, y = b.y + Math.sin(a) * r;
        if (!g.blocked(x, y) && g.isSpawnReachable(x, y)) return [Math.round(x), Math.round(y), Math.round(r)];
      }
      return null;
    }""")
    assert route, "no walkable route found near bales[0]"
    print(f"walkable route: {route} -> PASS")

    # ---------- 5. hero contact: walking into the bale pushes it, controls still work ----------
    push_pre = page.evaluate("""() => {
      const g = window.__game, A = window.ARK;
      const b = g.bales[0];
      let r = 24;
      while (r < 90 && g.blocked(b.x, b.y + r)) r += 8;
      A.teleport(b.x, b.y + r);
      return { bx: b.x, by: b.y };
    }""")
    page.keyboard.down("ArrowUp")
    time.sleep(0.7)
    page.keyboard.up("ArrowUp")
    time.sleep(0.3)
    hero = page.evaluate("""() => {
      const g = window.__game, A = window.ARK;
      const b = g.bales[0];
      return { bx: b.x, by: b.y, px: A.P.x, py: A.P.y, moved: g.baleMoved(), blocked: g.blocked(A.P.x, A.P.y) };
    }""")
    print("hero push:", hero, "before:", push_pre)
    assert hero["by"] < push_pre["by"] - 8, (push_pre, hero)          # bale shoved up by the hero
    assert hero["moved"] > 0, hero
    assert not hero["blocked"], hero                                   # hero not stuck
    x_before = hero["px"]
    page.keyboard.down("ArrowLeft"); time.sleep(0.5); page.keyboard.up("ArrowLeft")
    after_walk = page.evaluate("[Math.round(window.ARK.P.x), Math.round(window.ARK.P.y)]")
    assert after_walk[0] < x_before - 4, (x_before, after_walk)        # controls still respond
    print(f"hero push + controls: bale y {push_pre['by']:.0f} -> {hero['by']:.0f}, walk-away {after_walk} -> PASS")

    # ---------- 6. Frodo contact: he shoves the bale too ----------
    frodo_pre = page.evaluate("""() => {
      const g = window.__game;
      const b = g.bales[1];
      g.FRODO.x = b.x + 5; g.FRODO.y = b.y; g.FRODO.moving = true; g.FRODO.dir = 'left';
      g.FRODO.wander = 0; g.FRODO.wanderWait = 4; g.FRODO.stuck = 0; g.FRODO.chase = null;
      g.P.x = b.x - 90; g.P.y = b.y - 90; g.P.moving = false; g.P.air = false; g.P.z = 0;
      return { bx: b.x, by: b.y };
    }""")
    time.sleep(1.2)
    frodo = page.evaluate("""() => {
      const g = window.__game;
      const b = g.bales[1];
      return { bx: b.x, by: b.y, fx: g.FRODO.x, fy: g.FRODO.y, px: g.P.x, py: g.P.y, moved: g.baleMoved() };
    }""")
    print("frodo push:", frodo, "before:", frodo_pre)
    disp = math.hypot(frodo["bx"] - frodo_pre["bx"], frodo["by"] - frodo_pre["by"])
    assert disp >= 3, (frodo_pre, frodo)
    assert frodo["bx"] < frodo_pre["bx"] - 1, (frodo_pre, frodo)   # pushed left (towards Arek)
    p_moved = abs(frodo["px"] - (frodo_pre["bx"] - 90)) + abs(frodo["py"] - (frodo_pre["by"] - 90))
    assert p_moved < 1e-6, (p_moved, frodo_pre, frodo)             # Arek never moved; only Frodo pushed
    assert not errors, errors
    print(f"frodo push: bale displaced {disp:.1f}px by Frodo alone -> PASS")

    browser.close()

print("bale styles: PASS")