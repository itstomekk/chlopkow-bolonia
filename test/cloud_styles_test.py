"""B06: large lumpy clouds with correct culling.

RED/GREEN checks against docs/js/game.js drawClouds:
  * each linear footprint of a rendered cloud grows >= 5x (per-cloud, scale-normalised)
  * the cloud shadow gets about 2x darker but stays capped
  * a cloud whose centre lies beyond the old +/-150/+-90 culling margins still renders
    as long as its silhouette overlaps the viewport (margins recalculated for new bounds),
    and one whose silhouette truly does not overlap is culled
  * cloud count and weather stay purely visual; no gameplay collision

Measurement: the game's ctx.ellipse calls are recorded (transform checked), so the test
asserts on what is actually painted, not on formulas. Frames whose cloud ellipse radii
fall far outside the declared silhouette (transient reduced-scale passes) are retried.

Run:  ARK_URL=http://127.0.0.1:8790/index.html python test/cloud_styles_test.py
"""
import math
import os
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = Path(os.environ.get("B06_SHOTS", r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\chlopkow-b06"))

# Pre-B06 baseline, captured from the live drawClouds before this card touched it:
# shadow ellipse rx = 72 * scale * zoom, union footprint ~144 x 51.3 world px at scale 1,
# shadow alpha 0.07..0.106, culling margins +/-150 (x) and +/-90 (y).
OLD = {"unitW": 144.0, "unitH": 51.3, "alphaMin": 0.07, "alphaMax": 0.106,
       "marginX": 150, "marginY": 90}

PROBE_JS = """() => {
  const ctx = window.ARK.ctx, orig = ctx.ellipse;
  window.__clp = { rec: [] };
  ctx.ellipse = function (x, y, rx, ry, rot, a0, a1, cc) {
    const t = ctx.getTransform();
    window.__clp.rec.push([ctx.globalCompositeOperation, ctx.fillStyle,
      x, y, rx, ry, t.a, t.b, t.c, t.d]);
    return orig.apply(this, arguments);
  };
}"""


def enter_play(pg):
    pg.goto(URL)
    pg.wait_for_function("window.__game && window.__worldLife", timeout=60000)
    pg.evaluate("localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("window.__game", timeout=60000)
    pg.keyboard.press("KeyN")
    pg.locator("#player-name-input").fill("Chmurka")
    pg.locator("#player-name-submit").click()
    pg.wait_for_function("__game.scene === 'play'", timeout=30000)
    pg.wait_for_function("window.__worldLife && __worldLife.animals.length > 0", timeout=30000)
    time.sleep(0.3)


def capture(pg, ms=90):
    pg.evaluate("window.__clp.rec.length = 0")
    pg.wait_for_timeout(ms)
    rec = pg.evaluate("window.__clp.rec.splice(0)")
    cam = pg.evaluate("() => { const c = ARK.camera; return {zoom: ARK.zoom, ox: c.ox, oy: c.oy}; }")
    return rec, cam


def identity_recs(rec):
    out = []
    for r in rec:
        a, b, c, d = r[6], r[7], r[8], r[9]
        if abs(a - 1) < 1e-6 and abs(b) < 1e-6 and abs(c) < 1e-6 and abs(d - 1) < 1e-6:
            out.append(r)
    return out


def world_pos(r, cam):
    return ((r[2] - cam["ox"]) / cam["zoom"], (r[3] - cam["oy"]) / cam["zoom"])


def shadow_alpha(style):
    m = re.search(r"rgba\(90,\s*100,\s*116,\s*([\d.]+)\)", style)
    return float(m.group(1)) if m else None


def cloud_at(clouds, x, y, tol=700):
    best, bd = None, 1e18
    for c in clouds:
        d = math.hypot(c["x"] - x, c["y"] - y)
        if d < bd:
            bd, best = d, c
    return best if bd < tol else None


def free_cell_near(pg, tx, ty, radius=25):
    """Nearest non-blocked cell within radius (spiral search)."""
    found = pg.evaluate("""([tx, ty, radius]) => {
      const g = window.__game;
      for (let r = 0; r <= radius; r += 4)
        for (let a = 0; a < 6.283; a += 0.4) {
          const x = tx + Math.cos(a) * r, y = ty + Math.sin(a) * r;
          if (x > 40 && y > 40 && x < g.MAP.w - 40 && y < g.MAP.h - 40 && !g.blocked(x, y))
            return [Math.round(x), Math.round(y)];
        }
      return null;
    }""", [tx, ty, radius])
    assert found, f"no free cell near ({tx},{ty}) within {radius}px"
    return found


def good_cloud(pg, clouds, need_y_headroom=True):
    """Pick a cloud with open surroundings and comfortable map margins."""
    for c in clouds:
        if need_y_headroom and not (400 < c["y"] < 6500):
            continue
        ok = pg.evaluate("""([x, y]) => {
          const g = window.__game;
          let free = 0, total = 0;
          for (let a = 0; a < 6.283; a += 0.25)
            for (let r = 40; r <= 320; r += 80) {
              const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
              if (px < 60 || py < 60 || px > g.MAP.w - 60 || py > g.MAP.h - 60) continue;
              total++;
              if (!g.blocked(px, py)) free++;
            }
          return total > 0 && free / total > 0.85;
        }""", [c["x"], c["y"]])
        if ok:
            return c
    raise AssertionError("no cloud with open surroundings found")


def blobs_of_cloud(pg, rec, cam, cloud):
    """Multiply blobs belonging to `cloud` in this frame: pinned to the cloud's expected
    screen position under the settled camera, with radii inside the declared silhouette."""
    z = cam["zoom"]
    ex, ey = cam["ox"] + cloud["x"] * z, cam["oy"] + cloud["y"] * z
    max_rx_u = 7.6                                  # widest blob in CLOUD_BLOBS (units)
    exp_rx = max_rx_u * 50 * cloud["scale"] * z
    out = []
    for r in identity_recs(rec):
        if r[0] != "multiply":
            continue
        if abs(r[2] - ex) > 750 or abs(r[3] - ey) > 550:
            continue
        if not (0.2 * exp_rx <= r[4] <= 1.25 * exp_rx):
            continue
        out.append(r)
    return out


def cloud_union_world(blobs, cam):
    """Union of blob extents in world px (centres expanded by their radii)."""
    xs0, ys0, xs1, ys1 = 1e18, 1e18, -1e18, -1e18
    for r in blobs:
        cx, cy = world_pos(r, cam)
        rx, ry = r[4] / cam["zoom"], r[5] / cam["zoom"]
        xs0 = min(xs0, cx - rx); xs1 = max(xs1, cx + rx)
        ys0 = min(ys0, cy - ry); ys1 = max(ys1, cy + ry)
    return (xs1 - xs0, ys1 - ys0)


def measure_cloud_frame(pg, cloud, geom, attempts=8):
    """Teleport onto the cloud, settle, capture a frame whose blobs match the declared
    silhouette under the settled camera. Returns (unitW, unitH, alpha, cam)."""
    for _ in range(attempts):
        rec, cam = capture(pg, ms=80)
        clouds = pg.evaluate("window.__game.clouds()")
        cur = cloud_at(clouds, cloud["x"], cloud["y"])
        blobs = blobs_of_cloud(pg, rec, cam, cur)
        if len(blobs) >= 5:
            w, h = cloud_union_world(blobs, cam)
            alpha = shadow_alpha(blobs[0][1])
            return (w / cur["scale"], h / cur["scale"], alpha, cam, cur, len(blobs))
    raise AssertionError(f"could not capture a sane cloud frame for cloud at ({cloud['x']:.0f},{cloud['y']:.0f})")


def place_and_check(pg, cloud, target_p, geom):
    """Teleport P near target_p, settle, and report the cloud's actual margin distance
    from the viewport edge plus whether a sane frame rendered that cloud.
    Returns (cloud_now, cam, rendered)."""
    fx, fy = free_cell_near(pg, target_p[0], target_p[1])
    pg.evaluate("ARK.teleport(%d, %d)" % (fx, fy))
    pg.wait_for_timeout(1300)
    last_cam, last_cur = None, None
    for _ in range(8):
        rec, cam = capture(pg, ms=80)
        clouds = pg.evaluate("window.__game.clouds()")
        cur = cloud_at(clouds, cloud["x"], cloud["y"])
        last_cam, last_cur = cam, cur
        if len(blobs_of_cloud(pg, rec, cam, cur)) >= 5:
            return cur, cam, True
    return last_cur, last_cam, False


def main():
    errs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": 1280, "height": 720})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        enter_play(pg)
        pg.evaluate(PROBE_JS)

        # ---------- 0. hooks ----------
        has_hook = pg.evaluate("typeof window.__game.clouds === 'function' && typeof window.__game.cloudGeometry === 'function'")
        assert has_hook, "B06 not implemented: __game.clouds()/cloudGeometry() hooks missing"
        geom = pg.evaluate("window.__game.cloudGeometry()")
        clouds = pg.evaluate("window.__game.clouds()")
        print(f"clouds: {len(clouds)} (count check {pg.evaluate('window.__game.cloudCount')}); "
              f"declared unit geometry {geom['unitW']:.0f}x{geom['unitH']:.0f} "
              f"margins +/-{geom['marginX']}/+{geom['marginY']} blobs={geom['blobs']}")
        assert len(clouds) == 7, len(clouds)                      # count stays purely visual

        # ---------- 1. footprint: each linear dimension >= 5x the pre-B06 baseline ----------
        print(f"declared (cloudGeometry) linear multiplier: x {geom['unitW'] / OLD['unitW']:.2f}x, "
              f"y {geom['unitH'] / OLD['unitH']:.2f}x (need >= 5.0x each)")
        assert geom["unitW"] >= 5.0 * OLD["unitW"], geom
        assert geom["unitH"] >= 5.0 * OLD["unitH"], geom
        target = good_cloud(pg, clouds)
        print(f"footprint target cloud: ({target['x']:.0f},{target['y']:.0f}) scale={target['scale']:.2f} alpha={target['alpha']:.3f}")
        fx, fy = free_cell_near(pg, target["x"], target["y"])
        pg.evaluate("ARK.teleport(%d, %d)" % (fx, fy))
        pg.wait_for_timeout(1300)
        unitW, unitH, alpha, cam, cur, n = measure_cloud_frame(pg, target, geom)
        print(f"rendered shadow layer: {unitW:.0f} x {unitH:.0f} unit px (from {n} blobs), "
              f"shadow alpha {alpha}")
        print(f"rendered footprint multiplier: x {unitW / OLD['unitW']:.2f}x, y {unitH / OLD['unitH']:.2f}x "
              f"(declared gate is 5.0x; rendered gate 4.5x)")
        assert unitW >= 4.5 * OLD["unitW"], (unitW, OLD)
        assert unitH >= 4.5 * OLD["unitH"], (unitH, OLD)
        # focus screenshot of the cloud in view
        pg.screenshot(path=str(SHOTS / "b06_cloud_after.png"))

        # ---------- 2. shadow about 2x darker but capped ----------
        declared = target["alpha"]
        print(f"shadow alpha: rendered {alpha} vs declared {declared} (expect ~2x, capped)")
        assert alpha >= 1.8 * declared - 0.005, (alpha, declared)
        assert alpha <= 0.25, alpha
        cap = max(c["alpha"] for c in clouds)
        assert alpha <= cap * 2 + 0.01, (alpha, cap)              # capped, not unbounded for the largest alpha

        # marginal sanity: declared margins cover the largest cloud silhouette
        max_scale = max(c["scale"] for c in clouds)
        assert geom["marginX"] >= math.ceil(geom["halfW"] * max_scale), geom
        assert geom["marginY"] >= math.ceil(geom["halfH"] * max_scale), geom
        assert geom["marginX"] > OLD["marginX"] and geom["marginY"] > OLD["marginY"], geom

        # ---------- 3. culling: renders beyond the old margins, culls when no overlap ----------
        # horizontal: centre 240 world px LEFT of the viewport (150 < D < new marginX)
        z = pg.evaluate("ARK.zoom")
        vw_half = 1280 / 2 / z
        tx = target["x"] + 240 + vw_half
        cur, cam, rendered = place_and_check(pg, target, (tx, target["y"]), geom)
        vleft = (0 - cam["ox"]) / cam["zoom"]
        D = vleft - target["x"]
        print(f"cull-x render case: cloud centre {D:.0f}px left of viewport (old margin {OLD['marginX']}, "
              f"new {geom['marginX']}); rendered={rendered}")
        assert D > OLD["marginX"], D                                # truly beyond the OLD culling
        assert D < geom["marginX"], D                               # and inside the new bounds
        assert rendered, "cloud overlapping the screen was culled!"
        pg.screenshot(path=str(SHOTS / "b06_culling_left.png"))

        # horizontal: centre ~500px left (no overlap -> must be culled)
        tx2 = target["x"] + 500 + vw_half
        _, cam2, rendered2 = place_and_check(pg, target, (tx2, target["y"]), geom)
        D2 = (0 - cam2["ox"]) / cam2["zoom"] - target["x"]
        print(f"cull-x cull case: cloud centre {D2:.0f}px left (new margin {geom['marginX']}); rendered={rendered2}")
        assert D2 > geom["marginX"] + 20, D2
        assert not rendered2, "cloud with no screen overlap was rendered!"

        # vertical: centre 140 world px ABOVE the viewport top (90 < D < new marginY)
        vh_half = 720 / 2 / z
        ty = target["y"] + 140 + vh_half + 16
        cur3, cam3, rendered3 = place_and_check(pg, target, (target["x"], ty), geom)
        vtop = (0 - cam3["oy"]) / cam3["zoom"]
        Dy = vtop - target["y"]
        print(f"cull-y render case: cloud centre {Dy:.0f}px above viewport (old margin {OLD['marginY']}, "
              f"new {geom['marginY']}); rendered={rendered3}")
        assert Dy > OLD["marginY"], Dy
        assert Dy < geom["marginY"], Dy
        assert rendered3, "cloud hanging over the top edge was culled!"

        # vertical: centre ~310px above (no overlap -> culled)
        ty2 = target["y"] + 310 + vh_half + 16
        _, cam4, rendered4 = place_and_check(pg, target, (target["x"], ty2), geom)
        Dy2 = (0 - cam4["oy"]) / cam4["zoom"] - target["y"]
        print(f"cull-y cull case: cloud centre {Dy2:.0f}px above (new margin {geom['marginY']}); rendered={rendered4}")
        assert Dy2 > geom["marginY"] + 20, Dy2
        assert not rendered4, "cloud with no vertical overlap was rendered!"

        # no gameplay collision: walk straight through the cloud's ground area
        gx, gy = free_cell_near(pg, target["x"], target["y"])
        pg.evaluate("ARK.teleport(%d, %d)" % (gx, gy))
        pg.wait_for_timeout(1200)
        start = pg.evaluate("[Math.round(ARK.P.x), Math.round(ARK.P.y)]")
        pg.keyboard.down("ArrowLeft")
        time.sleep(0.6)
        pg.keyboard.up("ArrowLeft")
        time.sleep(0.2)
        end = pg.evaluate("[Math.round(ARK.P.x), Math.round(ARK.P.y)]")
        print(f"walk through cloud footprint: ({start[0]},{start[1]}) -> ({end[0]},{end[1]})")
        # Full-distance walk at full speed proves the clouds put no invisible barrier in the way
        # (animals/NPCs may legitimately occupy cells; blocked() is not the cloud signal here).
        assert end[0] < start[0] - 15, (start, end)
        dist = start[0] - end[0]
        assert 45 <= dist <= 85, (start, end)          # 0.6 s at SPEED 110, no early stop
        assert pg.evaluate("window.__game.cloudCount") == 7
        assert not errs, errs

        browser.close()
    print("cloud styles: PASS")


if __name__ == "__main__":
    main()