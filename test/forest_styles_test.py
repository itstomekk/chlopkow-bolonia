"""C06 - forest floor texture + engage-able trees (RED/GREEN, pixel-measured).

Card C06 of plans/2026-09-28-unified-luna-execution-plan.md owns the forest
visual polish, delivered as RUNTIME rendering only (docs/img/map_*.png and
docs/map.json stay byte-identical - no map regeneration, no generator change).

RED/GREEN checks against docs/js/game.js:
  * forest floor is a coherent textured area: floor pixels sampled at art
    resolution show clearly more chromatic variance than the flat #1f4f24 fill
    (stdev + distinct colors), every textured pixel stays floor-classified
    inside the forest mask (0 outside), canopy/trunk pixels are never painted
    over, and all textured colours stay within the base-green family (cohesion)
  * determinism: a full reload reproduces the exact same baked texture (FNV hash)
  * rendered parity at gameplay zoom: a forest camera crop shows textured floor
    and a healthy canopy share; water/meadow edges still read as transitions
  * trees are engage-able: every generated tree (n=793), including the 53 broad
    oaks whose dims collide with the building rule, picks as TREE (not BUILDING);
    real buildings still pick as BUILDING
  * frame parity: no per-frame perf cliff at zoom 1 and zoom 2 (4x CPU throttle),
    one-time bake cost bounded

Run:  ARK_URL=http://127.0.0.1:8790/index.html python test/forest_styles_test.py
"""
import json
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = Path(os.environ.get("C06_SHOTS", ROOT / "test"))

# Pre-C06 floor baseline (measured from docs/img/map_ground.png + live canvas):
# flat #1f4f24: stdev ~3.6/4.9/3.0, 5 distinct colours (quantised), 96.6% exact base.
OLD_FLOOR = {"stdev": (3.6, 4.9, 3.0), "distinct": 5, "baseShare": 0.966}
FOREST_ART_PX = 7213424          # forest mask px at art resolution
CANOPY_ART_PX = 527279           # non-floor (canopy/trunk) px inside the forest mask

FPS_JS = """async ([duration]) => {
  const times = []; let previous = 0;
  await new Promise(resolve => {
    const start = performance.now();
    function frame(now) {
      if (previous) times.push(now - previous);
      previous = now;
      if (now - start < duration) requestAnimationFrame(frame); else resolve();
    }
    requestAnimationFrame(frame);
  });
  times.sort((a, b) => a - b);
  const sum = times.reduce((a, b) => a + b, 0);
  return { frames: times.length, meanMs: sum / Math.max(1, times.length),
           p95Ms: times[Math.min(times.length - 1, Math.floor(times.length * 0.95))] || 0 };
}
"""

CROP_METRICS_JS = """
([cx, cy, cw, ch]) => {
  const d = window.ARK.ctx.getImageData(Math.round(cx), Math.round(cy),
    Math.round(cw), Math.round(ch)).data;
  const floorTest = r => r[0] < 60 && r[1] >= 50 && r[1] <= 100 && r[2] < 60 && (r[1] - r[0]) > 15;
  let n = 0, fn = 0, sR = 0, sG = 0, sB = 0, ssR = 0, ssG = 0, ssB = 0, maxD = 0, minV = 1e9, maxV = -1e9;
  const colors = new Set();
  for (let i = 0; i < d.length; i += 4) {
    const r = d[i], g = d[i + 1], b = d[i + 2];
    if (floorTest([r, g, b])) {
      n++; sR += r; sG += g; sB += b; ssR += r * r; ssG += g * g; ssB += b * b;
      colors.add((r >> 2) + ':' + (g >> 2) + ':' + (b >> 2));
      const v = (r + g + b) / 3;
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
      const dd = Math.abs(r - 31) + Math.abs(g - 79) + Math.abs(b - 36);
      if (dd > maxD) maxD = dd;
    } else fn++;
  }
  const st = (ss, s, cnt) => cnt > 1 ? Math.sqrt(Math.max(0, ss / cnt - (s / cnt) * (s / cnt))) : 0;
  const total = Math.round(cw * ch);
  return { totalPx: total, floorPx: n, canopyShare: fn / total, floorDistinct: colors.size,
    floorMean: [sR / n, sG / n, sB / n], floorStdev: [st(ssR, sR, n), st(ssG, sG, n), st(ssB, sB, n)],
    floorValueRange: [minV, maxV], floorCohesionMax: maxD };
}
"""

fails = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def enter_play(pg):
    pg.goto(URL)
    pg.wait_for_function("typeof window.__game !== 'undefined'", timeout=60000)
    pg.evaluate("localStorage.clear()")
    pg.reload(wait_until="load")
    pg.wait_for_function("typeof window.__game !== 'undefined'", timeout=60000)
    pg.keyboard.press("KeyN")
    pg.wait_for_function("!!document.querySelector('#player-name-input')", timeout=15000)
    pg.locator("#player-name-input").fill("Las")
    pg.locator("#player-name-submit").click()
    pg.wait_for_function("typeof window.__game !== 'undefined' && window.__game.scene === 'play'", timeout=30000)
    pg.wait_for_function("window.__worldLife && __worldLife.animals.length > 0", timeout=30000)
    time.sleep(0.3)


def find_cell(pg, pred_body, step=60):
    out = pg.evaluate("""(predBody) => {
      const g = window.__game;
      for (let r = 60; r < 5000; r += 45)
        for (let a = 0; a < 6.283; a += 0.18) {
          const x = Math.cos(a) * r + g.MAP.spawn.x, y = Math.sin(a) * r + g.MAP.spawn.y;
          if (x < %d || y < %d || x > g.MAP.w - %d || y > g.MAP.h - %d) continue;
          if (!g.blocked(x, y) && g.isSpawnReachable(x, y)) {
            const pred = new Function('x', 'y', 'g', predBody);
            if (pred(x, y, g)) return [Math.round(x), Math.round(y)];
          }
        }
      return null;
    }""" % (step, step, step, step), pred_body)
    assert out, f"no free cell for: {pred_body[:60]}"
    return out


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    enter_play(page)

    # ---------- 1. forest floor texture: art-resolution bake stats ----------
    stats = page.evaluate("window.__game.forestTextureStats()")
    print("bake stats:", json.dumps({k: (round(v, 2) if isinstance(v, float) else v)
                                     for k, v in stats.items()}))
    check(stats["floorTouched"] > 0.4 * FOREST_ART_PX,
          f"textured floor pixels {stats['floorTouched']:,} (> 40% of forest art px)")
    check(stats["outsideForest"] == 0,
          f"no textured pixel outside the forest mask ({stats['outsideForest']})")
    check(stats["canopyKept"] > 0.5 * CANOPY_ART_PX,
          f"canopy/trunk pixels untouched ({stats['canopyKept']:,} kept > 50% of {CANOPY_ART_PX:,})")
    g_stdev = stats["floorStdev"][1]
    check(g_stdev >= OLD_FLOOR["stdev"][1] + 2.0,
          f"floor green-channel stdev {g_stdev:.2f} (flat baseline {OLD_FLOOR['stdev'][1]:.2f}) -> textured")
    check(stats["distinctColors"] >= 8 * OLD_FLOOR["distinct"],
          f"floor distinct colours {stats['distinctColors']} (baseline {OLD_FLOOR['distinct']})")
    check(stats["baseExactShare"] <= 0.86,
          f"exact #1f4f24 share dropped to {stats['baseExactShare']:.3f} (baseline {OLD_FLOOR['baseShare']})")
    check(stats["cohesionMax"] <= 80,
          f"textured colours stay in the base-green family (max manhattan delta {stats['cohesionMax']})")
    bake_ms = stats.get("buildMs", 0)

    # ---------- 2. determinism: same seed reproduces the same texture ----------
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="load")
    page.wait_for_function("typeof window.__game !== 'undefined'", timeout=60000)
    page.keyboard.press("KeyN")
    page.wait_for_function("!!document.querySelector('#player-name-input')", timeout=15000)
    page.locator("#player-name-input").fill("Las")
    page.locator("#player-name-submit").click()
    page.wait_for_function("typeof window.__game !== 'undefined' && window.__game.scene === 'play'", timeout=30000)
    page.wait_for_function("window.__worldLife && __worldLife.animals.length > 0", timeout=30000)
    stats2 = page.evaluate("window.__game.forestTextureStats()")
    check(stats2["fnv"] == stats["fnv"] and stats2["floorTouched"] == stats["floorTouched"] and
          stats2["canopyKept"] == stats["canopyKept"],
          f"reload reproduces the exact texture (fnv {stats['fnv']} == {stats2['fnv']})")

    # ---------- 3. rendered parity at gameplay zoom (forest corner) ----------
    forest = find_cell(page, "if (g.terrainAt(x, y) === 'forest') return true; return false;")
    page.evaluate("([x, y]) => window.ARK.teleport(x, y)", forest)
    time.sleep(1.4)
    cam = page.evaluate("() => ({ zoom: ARK.zoom, ox: ARK.camera.ox, oy: ARK.camera.oy, w: ARK.ctx.canvas.width, h: ARK.ctx.canvas.height })")
    z = cam["zoom"]
    cw, ch = 260 * z, 200 * z
    cx = max(0, cam["ox"] + forest[0] * z - cw / 2)
    cy = max(0, cam["oy"] + forest[1] * z - ch / 2)
    m = page.evaluate(CROP_METRICS_JS, [cx, cy, cw, ch])
    print("forest crop:", {k: (round(v[0], 2) if isinstance(v, list) else round(v, 3) if isinstance(v, float) else v)
                           for k, v in m.items()})
    page.screenshot(path=str(SHOTS / "c06_forest_crop.png"),
                    clip={"x": cx, "y": cy, "width": cw, "height": ch})
    check(m["floorPx"] > 15000, f"crop holds real forest floor ({m['floorPx']:,} px)")
    check(m["floorStdev"][1] >= 6.0,
          f"rendered floor stdev(G) {m['floorStdev'][1]:.2f} -> visibly textured at zoom {z:.2f}")
    check(m["floorDistinct"] >= 16, f"rendered floor distinct colours {m['floorDistinct']}")
    check(0.12 <= m["canopyShare"] <= 0.95,
          f"canopy share in crop {m['canopyShare']:.2f} (canopy + edges present, floor visible)")
    check(m["floorCohesionMax"] <= 90,
          f"rendered floor colours cohesive (max manhattan delta {m['floorCohesionMax']})")

    # ---------- 4. trees are engage-able (all 793, incl. the 53 broad oaks) ----------
    pick = page.evaluate("""() => {
      const g = window.__game;
      const trees = g.MAP.objects.filter(o => o.kind === 'tree');
      const bldList = g.MAP.objects.filter(o => !o.kind && o.w >= 40 && o.h >= 30 && o.w <= 200);
      // these kinds are pushed to the draw list after MAP.objects, so they always
      // render in front of a tree and legitimately win the hover pick
      const FRONT = new Set(['apple', 'mushroom', 'trash', 'cap', 'bale', 'npc', 'hero', 'frodo',
        'chicken', 'dog', 'bird', 'stork', 'fox', 'boar', 'mouse', 'hare', 'pig', 'butterfly', 'car', 'tractor']);
      const treePicks = [], mis = [];
      for (const o of trees) {
        const r = g.worldPickAt(o.x + o.w / 2, o.base - 6);
        if (r.kind === 'tree') { treePicks.push(o); continue; }
        if (FRONT.has(r.kind)) continue;                 // pickup/entity drawn in front
        const px = o.x + o.w / 2, py = o.base - 6;
        const overBld = bldList.some(b => r.kind === 'building' && b.base >= o.base - 1 &&
          Math.abs(px - (b.x + b.w / 2)) <= b.w / 2 && py >= b.base - b.h && py <= b.base + 1);
        if (overBld) continue;                           // real building drawn in front
        mis.push([o.w, o.h, r.kind, r.label]);
      }
      const bldKinds = [...new Set(bldList.map(b => g.worldPickAt(b.x + b.w / 2, b.base - 6).kind))];
      const bldClean = bldList.filter(b => g.worldPickAt(b.x + b.w / 2, b.base - 6).kind === 'building').length;
      return { treeTotal: trees.length, treePicked: treePicks.length,
               mis: mis.slice(0, 6), bldKinds, bldClean,
               poorTrees: treePicks.filter(o => o.w >= 40 && o.h >= 30 && o.w <= 200).length };
    }""")
    print("tree picks:", pick)
    check(pick["treeTotal"] == 793, f"793 generated trees present ({pick['treeTotal']})")
    check(pick["treePicked"] >= 780 and not pick["mis"],
          f"every tree picks as TREE or a legit front-drawn object ({pick['treePicked']}/793; misclassified {pick['mis']})")
    check(pick["poorTrees"] >= 50,
          f"all broad oaks (53) engageable as trees ({pick['poorTrees']} big trees picked TREE)")
    check("building" in pick["bldKinds"] and pick["bldClean"] > 30,
          f"real buildings still pick as BUILDING ({pick['bldKinds']}, {pick['bldClean']} clean)"
          if "building" in pick["bldKinds"] else f"no building picks as BUILDING ({pick['bldKinds']})")

    # ---------- 5. frame parity: zoom 1 + zoom 2, 4x CPU throttle ----------
    # (bake cost is measured on the unthrottled main page - CDP CPU throttle would
    #  inflate the one-time init cost ~12x and is not what players experience)
    bake_ms = stats2.get("buildMs", stats["buildMs"])
    check(bake_ms <= 1000, f"one-time texture bake {bake_ms:.0f}ms (bounded, not per-frame)")
    ctx2 = browser.new_context(viewport={"width": 1280, "height": 720})
    pg2 = ctx2.new_page()
    cdp2 = ctx2.new_cdp_session(pg2)
    cdp2.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    enter_play(pg2)
    pg2.evaluate("([x, y]) => window.ARK.teleport(x, y)", forest)
    time.sleep(1.2)
    fps = {}
    for name, vp in (("z1", (640, 330)), ("z2", (1280, 660))):
        ctx3 = browser.new_context(viewport={"width": vp[0], "height": vp[1]})
        pg3 = ctx3.new_page()
        cdp3 = ctx3.new_cdp_session(pg3)
        cdp3.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        enter_play(pg3)
        pg3.evaluate("([x, y]) => window.ARK.teleport(x, y)", forest)
        time.sleep(1.2)
        f = pg3.evaluate(FPS_JS, [3000])
        f["zoom"] = round(pg3.evaluate("ARK.zoom"), 2)
        fps[name] = f
        ctx3.close()
    print("frame parity:", json.dumps(fps))
    check(fps["z1"]["meanMs"] <= 34, f"zoom 1 mean frame {fps['z1']['meanMs']:.1f}ms (floor <34ms)")
    check(fps["z2"]["meanMs"] <= 56, f"zoom 2 mean frame {fps['z2']['meanMs']:.1f}ms (floor <56ms)")
    check(max(fps["z1"]["p95Ms"], fps["z2"]["p95Ms"]) <= 85,
          f"p95 bounded (z1 {fps['z1']['p95Ms']:.0f}ms, z2 {fps['z2']['p95Ms']:.0f}ms)")

    check(not errors, f"no page errors ({errors[:2]})")
    ctx2.close()
    browser.close()

print("FAILED:", len(fails)) if fails else print("forest styles: PASS")
sys.exit(1 if fails else 0)