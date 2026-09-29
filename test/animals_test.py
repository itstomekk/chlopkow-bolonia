"""Browser regression test for pixel critters and animal interactions.

Includes the B01 registry contract: every CRIT species is enumerated once in
ANIMAL_TYPES (category, atlas row/scale, habitat, count, movement radius and
visibility policy), spawned animals carry a stable ``kind:index`` id in
spawn order, per-kind counts/habitats match the seeded baseline, placement is
identical across same-seed reloads, and the saved Q.worldLife payload is not
migrated (no per-animal keys).

B03 adds the visual contract: the mouse sprite is rendered at quarter size
(width AND height each 25% of the baseline atlas dims - not quarter area, so
the drawn atlas cell shrinks 32 -> 8 map units), physics/hit radii untouched,
and chicken/mouse/bird draw no A.shadow in the atlas path or the procedural
fallback (when critters.png is unavailable), while dogs/boars/other species
keep their shadows. The render probe re-invokes the world hook with a single
isolated animal and records the sprite destination rect plus shadow calls.
"""
import json
import os
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
META = json.loads((ROOT / "docs/img/critters.json").read_text(encoding="utf-8"))
VEHICLE_META = json.loads((ROOT / "docs/img/vehicles.json").read_text(encoding="utf-8"))
VEHICLE_IMAGE = Image.open(ROOT / "docs/img/vehicles.png").convert("RGBA")
assert VEHICLE_META["cell"] == 64 and VEHICLE_IMAGE.size == (256, 256)
tractor_frames = [VEHICLE_IMAGE.crop((i * 64, 0, (i + 1) * 64, 64)).tobytes() for i in range(4)]
assert len(set(tractor_frames)) == 4, "tractor wheel frames must all show rotation"
assert {"tractor_side", "tractor_front", "tractor_back", "car"} <= set(VEHICLE_META["rows"])

# ---- B07: restore the previous red car art (only), atlas cell mapping unchanged.
# The renderer samples vehicles.png cell (0, row 3) frame 0 via drawCar; the old
# blocky crimson car lives only as docs/img/car_red.png @ commit ba64220 (128x87),
# which gen/build_vehicles_pixel.py pastes into every row-3 tile (NEAREST 60x41 at
# offset (2,9)). All four car frames stay identical: drawCar reads frame 0 only and
# the old art is a static side view - keep the mapping and behavior untouched.
assert list(VEHICLE_META["rows"]) == ["tractor_side", "tractor_front", "tractor_back", "car"], VEHICLE_META["rows"]
assert VEHICLE_META["rows"]["car"]["row"] == 3 and VEHICLE_META["rows"]["car"]["frames"] == ["idle1", "idle2", "idle3", "idle4"]
B07_CAR_SRC = ROOT / "gen/car_red_ba64220.png"
old_car = Image.open(B07_CAR_SRC).convert("RGBA")
assert old_car.size == (128, 87), old_car.size  # provenance: git ba64220:docs/img/car_red.png
expected_cell = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
expected_cell.alpha_composite(old_car.resize((60, 41), Image.NEAREST), (2, 9))
car_frames = [VEHICLE_IMAGE.crop((i * 64, 3 * 64, (i + 1) * 64, 4 * 64)).tobytes() for i in range(4)]
assert len(set(car_frames)) == 1, "B07: car frames must stay identical (drawCar samples frame 0 only)"
assert car_frames[0] == expected_cell.tobytes(), "B07: row-3 frame 0 does not match the restored car_red (ba64220) art"


def _b07_sig(cell_bytes):
    teal = crimson = n = 0
    for i in range(0, len(cell_bytes), 4):
        r, g, b, a = cell_bytes[i], cell_bytes[i + 1], cell_bytes[i + 2], cell_bytes[i + 3]
        if a > 128:
            n += 1
            if abs(r - 0x78) < 40 and abs(g - 0xB5) < 40 and abs(b - 0xC3) < 40:
                teal += 1  # the new hatchback's glass panes (#78b5c3 family)
            if r > 120 and g < 110 and b < 110:
                crimson += 1
    return teal, crimson, n


_b07_teal, _b07_crimson, _b07_n = _b07_sig(car_frames[0])
assert _b07_teal < 30 and _b07_crimson > 500 and _b07_n > 600, ("B07 cell signature", _b07_teal, _b07_crimson, _b07_n)

# Fixed seed so every run boots the exact same game (and, for B01, the exact
# same spawn positions). Reproduced by mulberry32-style LCG.
SEED_JS = """
  let s = 123456789;
  Math.random = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
"""

# B01: the single enumeration the game must agree with (baseline species only).
EXPECTED_SPECIES = {
    "chicken": {"category": "domestic", "row": 0, "px": 30, "h": 12, "count": 12, "habitat": "notForest", "radius": 90, "flies": False},
    "dog": {"category": "domestic", "row": 1, "px": 40, "h": 19, "count": 7, "habitat": "notForest", "radius": 150, "flies": False},
    "bird": {"category": "wild", "row": 2, "px": 22, "h": 7, "count": 24, "habitat": "notForest", "radius": 40, "flies": True},
    "stork": {"category": "wild", "row": 3, "px": 56, "h": 30, "count": 3, "habitat": "notForest", "radius": 90, "flies": False},
    "fox": {"category": "wild", "row": 4, "px": 40, "h": 17, "count": 2, "habitat": "notForest", "radius": 200, "flies": False},
    "boar": {"category": "wild", "row": 5, "px": 44, "h": 21, "count": 4, "habitat": ["forest"], "radius": 140, "flies": False},
    # B03: mouse atlas px widened 18 -> 72 so the drawn cell = 64*9/72 = 8 map
    # units = 25% of the pre-B03 baseline (64*9/18 = 32) in BOTH dimensions;
    # h/count/habitat/radius are unchanged (radius 70 = hit/chase radius).
    "mouse": {"category": "wild", "row": 6, "px": 72, "h": 9, "count": 10, "habitat": ["forest", "field"], "radius": 70, "flies": False},
    "hare": {"category": "wild", "row": 7, "px": 28, "h": 15, "count": 6, "habitat": ["field", "grass", "meadow"], "radius": 120, "flies": False},
    "pig": {"category": "domestic", "row": 8, "px": 42, "h": 18, "count": 5, "habitat": "notForest", "radius": 80, "flies": False},
    "butterfly": {"category": "wild", "row": 9, "px": 21, "h": 5, "count": 8, "habitat": ["field", "grass", "meadow"], "radius": 110, "flies": True},
}
EXPECTED_ORDER = ["chicken", "dog", "boar", "mouse", "hare", "pig", "butterfly", "stork", "fox", "bird"]

REGISTRY_JS = """() => {
  const W = window.__worldLife, A = window.ARK;
  const types = W.animalTypes || null, order = W.speciesOrder || null;
  const counts = {}, ids = {};
  for (const a of W.animals) {
    counts[a.kind] = (counts[a.kind] || 0) + 1;
    (ids[a.kind] = ids[a.kind] || []).push(a.id);
  }
  const hasTypes = !!types && !!order && order.length > 0;
  const idsOk = hasTypes && W.animals.length > 0 &&
    W.animals.every(a => typeof a.id === 'string' && /^[a-z]+:\\d+$/.test(a.id)) &&
    Object.entries(ids).every(([k, list]) => list.every((id, i) => id === k + ':' + i));
  const inMeadow = (x, y) => { const m = A.MAP.meadow; return !!m && x >= m.x0 && x <= m.x1 && y >= m.y0 && y <= m.y1; };
  const allowed = (kind, x, y) => {
    if (!types || !types[kind]) return false;
    const h = types[kind].habitat, t = A.terrainAt(x, y);
    if (h === 'notForest') return t !== 'forest';
    if (Array.isArray(h)) return h.indexOf(t) >= 0 || (h.indexOf('meadow') >= 0 && inMeadow(x, y));
    return false;
  };
  // pig anchors to building fronts without a terrain gate and individual birds
  // jitter around a terrain-filtered flock center - both pre-existing baseline
  // behaviors - so they are excluded from the strict in-habitat invariant.
  const badHabitat = hasTypes ? W.animals.filter(a => a.kind !== 'pig' && a.kind !== 'bird' && !allowed(a.kind, a.x, a.y)).map(a => a.id) : [];
  const noMigrate = hasTypes && !('animals' in (A.Q.worldLife || {})) && !('ids' in (A.Q.worldLife || {}));
  return {
    hasTypes, idsOk, noMigrate, total: W.animals.length,
    counts, badHabitat, order: (order || []).slice(),
    summary: Object.fromEntries(Object.entries(ids).map(([k, v]) => [k, v.length])),
  };
}"""

# Fresh games randomize the player spawn (samplePlayerSpawn) and pre-play
# frames consume a run-varying number of Math.random draws, so a plain seeded
# boot is not position-reproducible. Pin the player spawn via the game's own
# debug ?x=&y= override, then - in one synchronous evaluate - re-seed
# Math.random and force a full worldLife rebuild through the public
# resetCars() hook (it re-runs syncState: animals + cars spawn with no frame
# ticks in between). Anchors are frozen spawn positions, so run 1 vs run 2
# equality proves placement is stable for the fixed seed.
PINNED_URL = URL + ("&" if "?" in URL else "?") + "x=3606&y=1326"
RESEED_AND_SNAPSHOT = """() => {
  const A = window.ARK;
  // Every non-deterministic spawn input is pinned so a fixed-seed rebuild is
  // reproducible regardless of session history (B02b pagehide saves restore state
  // on reload): the player is pinned by the caller, and NPC positions are pinned
  // here because they feed the emptySite rejection filter via tooCloseToStatic.
  const nps = A.ITEMS && A.ITEMS.npcs;
  for (let i = 0; nps && i < nps.length; i++) { nps[i].x = 120 + (i % 70) * 70; nps[i].y = 260 + i * 110; }
  let s = 987654321;
  Math.random = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  window.__worldLife.resetCars();
  return window.__worldLife.animals.map(a => [
    a.kind, a.id, Math.round(a.homeX), Math.round(a.homeY),
  ]);
}"""

DESCRIPTOR_JS = """() => {
  const T = window.__worldLife.animalTypes || {};
  return Object.fromEntries(Object.entries(T).map(([k, d]) => [k, {
    category: d.category, row: d.atlas.row, px: d.atlas.px, h: d.atlas.h,
    count: d.count, habitat: d.habitat, radius: d.radius, flies: d.flies,
  }]));
}"""

# B03: the per-kind no-shadow exclusion flag in the registry.
B03_DESC_JS = """() => {
  const T = window.__worldLife.animalTypes || {};
  const out = {};
  for (const k of Object.keys(T)) out[k] = !!T[k].noShadow;
  return out;
}"""

# B03 render probe: run the world-life world hook with the animals list reduced
# to a single kind and capture (a) how many A.shadow calls that one critter's
# draw callback makes and (b) the destination rect of the atlas sprite draw.
# Other modules also register world hooks, so the world-life one is identified
# by its fingerprint: it pushes cars, then tractors, then (in-view) animals, so
# with one isolated animal its capture is exactly cars+tractors+1 entries and
# contains one entry whose base y equals the animal's y. The animal callback is
# the last of those. zoom is returned so expectations are in unscaled map units.
B03_RENDER_JS = """(kind) => {
  const A = window.ARK, W = window.__worldLife;
  const canvas = document.querySelector('canvas');
  const cctx = canvas.getContext('2d');
  const zoom = A.zoom;
  const ax = W.animals.find(a => a.kind === kind);
  if (!ax) throw new Error('B03: no ' + kind + ' animal in the world');
  const saved = W.animals.slice();
  W.animals.length = 0; W.animals.push(ax);
  const ox = canvas.width / 2 - ax.x * zoom, oy = canvas.height / 2 - ax.y * zoom;
  const S = (x, y) => [ox + x * zoom, oy + y * zoom];
  const want = W.cars.length + W.tractors.length + 1;
  let cap = null;
  for (const h of A.HOOKS.world) {
    const c = [];
    h((b, f) => c.push({ b, f }), S, () => true);
    if (c.length === want && c.some(e => Math.abs(e.b - ax.y) < 1)) { cap = c; break; }
  }
  if (!cap) throw new Error('B03: world-life hook not found (captured ' + JSON.stringify(A.HOOKS.world.map(h => { const c = []; h((b, f) => c.push({ b, f }), S, () => true); return c.length; })) + ' entries)');
  const animalFn = cap[want - 1];
  let shadowCalls = 0;
  const origShadow = A.shadow;
  A.shadow = function (sx, sy, s, w) { shadowCalls++; return origShadow.call(this, sx, sy, s, w); };
  let lastDraw = null;
  const origDraw = cctx.drawImage;
  cctx.drawImage = function (img, sx, sy, sw, sh, dx, dy, dw, dh) {
    if (dw !== undefined) lastDraw = { dw, dh };
    return origDraw.apply(this, arguments);
  };
  try {
    animalFn.f();
  } finally {
    A.shadow = origShadow;
    cctx.drawImage = origDraw;
    W.animals.length = 0; W.animals.push(...saved);
  }
  return { shadowCalls, dw: lastDraw ? lastDraw.dw : null, dh: lastDraw ? lastDraw.dh : null, zoom };
}"""

# B03 pixel probe: same isolated single-animal pass over a black canvas, then
# measure the bounding box of non-black pixels around the canvas center = the
# visible sprite footprint (shadow excluded after GREEN, never counted before).
B03_PIXEL_JS = """(kind) => {
  const A = window.ARK, W = window.__worldLife;
  const canvas = document.querySelector('canvas');
  const cctx = canvas.getContext('2d');
  const zoom = A.zoom;
  const ax = W.animals.find(a => a.kind === kind);
  if (!ax) throw new Error('B03: no ' + kind + ' animal in the world');
  const saved = W.animals.slice();
  const carPos = W.cars.map(c => ({ x: c.x, y: c.y }));
  const tracPos = W.tractors.map(t => ({ x: t.x, y: t.y }));
  W.animals.length = 0; W.animals.push(ax);
  for (const c of W.cars) { c.x += 4000; c.y += 4000; }
  for (const t of W.tractors) { t.x += 4000; t.y += 4000; }
  const ox = canvas.width / 2 - ax.x * zoom, oy = canvas.height / 2 - ax.y * zoom;
  const S = (x, y) => [ox + x * zoom, oy + y * zoom];
  const want = W.cars.length + W.tractors.length + 1;
  const drawn = [];
  for (const h of A.HOOKS.world) {
    const c = [];
    h((b, f) => c.push({ b, f }), S, () => true);
    if (c.length === want && c.some(e => Math.abs(e.b - ax.y) < 1)) { drawn.push(...c); break; }
  }
  if (!drawn.length) throw new Error('B03 pixel: world-life hook not found');
  cctx.fillStyle = '#000';
  cctx.fillRect(0, 0, canvas.width, canvas.height);
  for (const d of drawn) d.f();
  W.animals.length = 0; W.animals.push(...saved);
  W.cars.forEach((cc, i) => { cc.x = carPos[i].x; cc.y = carPos[i].y; });
  W.tractors.forEach((t, i) => { t.x = tracPos[i].x; t.y = tracPos[i].y; });
  const cx = canvas.width >> 1, cy = canvas.height >> 1, win = 110;
  const img = cctx.getImageData(cx - win, cy - win, win * 2, win * 2);
  let minX = 1e9, maxX = -1, minY = 1e9, maxY = -1, n = 0;
  for (let y = 0; y < img.height; y++) for (let x = 0; x < img.width; x++) {
    const i = (y * img.width + x) * 4;
    if (img.data[i + 3] > 0 && (img.data[i] || img.data[i + 1] || img.data[i + 2])) {
      n++;
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
  }
  // restore the frame the game expected (the probe overwrote the canvas)
  return { n, w: n ? maxX - minX + 1 : 0, h: n ? maxY - minY + 1 : 0 };
}"""

# Pre-B03 mouse atlas cell = 64*9/18 = 32 map units on each side; B03 requires
# 25% of that in BOTH dimensions (quarter size, not quarter area -> 8 units).
MOUSE_BASELINE = 64 * 9 / 18
SHOTS_DIR = Path(os.environ.get("HERMES_SCRATCH", r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch")) / "chlopkow-b03"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script(SEED_JS)
    page.goto(PINNED_URL)
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Animals")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play' && window.__worldLife && __worldLife.vehicleSpritesLoaded", timeout=30000)

    required_rows = {"hen", "stray", "bird", "stork", "fox", "boar", "mouse", "hare", "pig", "butterfly"}
    assert required_rows <= set(META["rows"]), f"missing atlas rows: {required_rows - set(META['rows'])}"
    assert META["cell"] == 64 and META["rows"]["butterfly"]["frames"] == ["flap1", "flap2", "flap3", "flap4"]
    assert Image.open(ROOT / "docs/img/critters.png").size == (256, 640)
    atlas = Image.open(ROOT / "docs/img/critters.png").convert("RGBA")
    flap_frames = [atlas.crop((i * 64, 9 * 64, (i + 1) * 64, 10 * 64)).tobytes() for i in range(4)]
    assert len(set(flap_frames)) == 4, "butterfly wing-flap frames must be distinct"
    assert {"tractor_side", "tractor_front", "tractor_back", "car"} <= set(VEHICLE_META["rows"])

    # ---- B01 registry contract (taken before interactions so anchors are clean)
    registry = page.evaluate(REGISTRY_JS)
    assert registry["hasTypes"], "ANIMAL_TYPES not exposed via __worldLife.animalTypes / speciesOrder"
    assert registry["total"] == 81, registry["summary"]
    assert registry["counts"] == {k: v["count"] for k, v in EXPECTED_SPECIES.items()}, registry["summary"]
    assert registry["order"] == EXPECTED_ORDER, registry["order"]
    assert registry["idsOk"], "animals lack stable sequential kind:index ids"
    assert not registry["badHabitat"], f"spawned out of habitat: {registry['badHabitat']}"
    assert registry["noMigrate"], "save payload gained animal keys (no migration allowed in B01)"
    tbl = page.evaluate(DESCRIPTOR_JS)
    assert tbl == EXPECTED_SPECIES, ("descriptor vs baseline table", tbl)
    run1_anchors = page.evaluate(RESEED_AND_SNAPSHOT)
    assert len(run1_anchors) == 81

    # ---- B03 (RED -> GREEN): quarter-size mouse art + three shadow exclusions.
    # The probes exercise the atlas path, so wait for critters.png to be loaded.
    page.wait_for_function("window.__worldLife && window.__worldLife.crittersLoaded", timeout=15000)
    # 1) registry flags: chicken/mouse/bird declare noShadow, all others keep
    #    shadowScale/shadowBlur as today (dogs/boars/others must NOT be flagged).
    b03_desc = page.evaluate(B03_DESC_JS)
    for kind in ("chicken", "mouse", "bird"):
        assert b03_desc[kind] is True, ("B03 noShadow missing for", kind, b03_desc)
    for kind in ("dog", "boar", "stork", "fox", "hare", "pig", "butterfly"):
        assert b03_desc[kind] is False, ("B03 noShadow leaked to", kind, b03_desc)
    # mouse descriptor itself: radius (hit/chase), count and habitat unchanged.
    mouse_desc = page.evaluate("() => window.__worldLife.animalTypes.mouse")
    assert mouse_desc["radius"] == 70 and mouse_desc["count"] == 10 and mouse_desc["atlas"]["row"] == 6, mouse_desc
    # 2) per-kind render probe over the real atlas path: every kind's drawn cell
    #    must match its descriptor formula, and the mouse must be exactly 25% of
    #    the pre-B03 baseline (32 units) in width AND height - quarter size, not
    #    quarter area (that would be 16).
    b03 = {}
    for kind in ("chicken", "dog", "bird", "stork", "fox", "boar", "mouse", "hare", "pig", "butterfly"):
        b03[kind] = page.evaluate(B03_RENDER_JS, kind)
    for kind, r in b03.items():
        exp = 64 * EXPECTED_SPECIES[kind]["h"] / EXPECTED_SPECIES[kind]["px"]
        assert abs(r["dw"] / r["zoom"] - exp) <= 1.5, ("B03 width mismatch", kind, r, "expected", exp)
        assert abs(r["dh"] / r["zoom"] - exp) <= 1.5, ("B03 height mismatch", kind, r, "expected", exp)
    mouse_r = b03["mouse"]
    quarter = MOUSE_BASELINE * 0.25
    assert abs(mouse_r["dw"] / mouse_r["zoom"] - quarter) <= 1.5, ("B03 mouse NOT quarter width", mouse_r, "quarter", quarter)
    assert abs(mouse_r["dh"] / mouse_r["zoom"] - quarter) <= 1.5, ("B03 mouse NOT quarter height", mouse_r, "quarter", quarter)
    # 3) shadow exclusions in the atlas path: zero A.shadow for the three,
    #    exactly one for every other kind.
    for kind in ("chicken", "mouse", "bird"):
        assert b03[kind]["shadowCalls"] == 0, ("B03 shadow leaked in atlas path", kind, b03[kind])
    for kind in ("dog", "boar", "stork", "fox", "hare", "pig", "butterfly"):
        assert b03[kind]["shadowCalls"] == 1, ("B03 shadow lost in atlas path", kind, b03[kind])
    # 4) visible footprint: pixel bbox around the isolated mouse must match the
    #    atlas art inside the quarter-size cell (25% of baseline, not 50%).
    px_mouse = page.evaluate(B03_PIXEL_JS, "mouse")
    atlas_art = Image.open(ROOT / "docs/img/critters.png").convert("RGBA").crop((0, 6 * 64, 64, 7 * 64)).getchannel("A").getbbox()
    cell_w = atlas_art[2] - atlas_art[0] + 1
    cell_h = atlas_art[3] - atlas_art[1] + 1
    exp_px_w = cell_w / 64 * mouse_r["dw"]
    exp_px_h = cell_h / 64 * mouse_r["dh"]
    assert abs(px_mouse["w"] - exp_px_w) <= 3, ("B03 pixel width mismatch", px_mouse, "expected", exp_px_w)
    assert abs(px_mouse["h"] - exp_px_h) <= 3, ("B03 pixel height mismatch", px_mouse, "expected", exp_px_h)

    facts = page.evaluate("""async () => {
      const A = window.ARK, W = window.__worldLife, kinds = ['mouse','hare','chicken','dog','pig','boar','fox','stork','bird','butterfly'];
      const water = Array.isArray(A.MAP.water) ? A.MAP.water : (W.waterPoints || []);
      const storks = W.animals.filter(a => a.kind === 'stork');
      const storksNearWater = water.length > 0 && storks.length === 3 && storks.every(a => water.some(v => Math.hypot(a.x-v.x,a.y-v.y) <= 100));
      const chase = (() => {
        const m = W.animals.find(a => a.kind === 'mouse');
        const f = A.FRODO;
        m.x = f.x + 18; m.y = f.y; m.homeX = m.x; m.homeY = m.y; m.wait = 60;
        W.resetInteractionCooldown('mouse');
        W.stepInteractions(0.05);
        return f.chase && Number.isFinite(f.chase.x) && Number.isFinite(f.chase.y) && Number.isFinite(f.chase.t) && f.chase.t > 0;
      })();
      const interactions = {};
      for (const kind of kinds) {
        const a = W.animals.find(x => x.kind === kind);
        for (const other of W.animals) if (other !== a) { other.x = A.P.x + 600; other.y = A.P.y + 600; }
        a.x = A.P.x + 24; a.y = A.P.y; a.homeX = a.x; a.homeY = a.y; a.tx = a.x; a.ty = a.y; a.wait = 60;
        A.FRODO.x = A.P.x; A.FRODO.y = A.P.y;
        A.P.moving = false;
        W.resetInteractionCooldown(kind);
        W.stepInteractions(0.05);
        interactions[kind] = W.lastInteraction[kind] || null;
      }
      return {storksNearWater, chase: !!chase, interactions};
    }""")
    assert facts["storksNearWater"], ("storks are not within 100px of MAP.water / water fallback", facts)
    assert facts["chase"], "Frodo chase contract was not set for a nearby mouse"
    assert all(facts["interactions"].get(k) for k in ["mouse","hare","chicken","dog","pig","boar","fox","stork","bird","butterfly"]), facts["interactions"]
    assert not errors, errors

    # ---- B02: mouse continuity under flee and camera changes (same session)
    # A pinned mouse must survive a near-Frodo flee, the >2 s interval where the
    # old code hid it (hiddenT=2), and leaving/re-entering the viewport: same
    # object reference + id, no hiddenT-driven draw suppression, bounded
    # continuous displacement (no teleport/respawn). Ordinary offscreen culling
    # may pause updates but must never despawn or relocate the mouse.
    B02_MOUSE_JS = """() => {
      const A = window.ARK, W = window.__worldLife;
      const arr0 = W.animals;
      const m = W.animals.find(a => a.kind === 'mouse');
      const id0 = m.id, ref0 = m, count0 = W.animals.filter(a => a.kind === 'mouse').length;
      const free = (x, y) => x > 80 && x < A.MAP.w - 80 && y > 130 && y < A.MAP.h - 80 && !A.blocked(x, y);
      let spot = null;
      outer:
      for (let r = 260; r < 900; r += 36) {
        for (let a = 0; a < Math.PI * 2; a += 0.45) {
          const x = A.P.x + Math.cos(a) * r, y = A.P.y + Math.sin(a) * r;
          let ok = free(x, y);
          for (let k = 0; k <= 6 && ok; k++) ok = free(x - 28 * k, y) && free(x - 28 * k, y + 18) && free(x - 28 * k, y - 18);
          ok = ok && free(x + 30, y);
          if (ok) { spot = { x, y }; break outer; }
        }
      }
      if (!spot) throw new Error('B02: no clear runway found');
      m.homeX = spot.x; m.homeY = spot.y; m.x = spot.x; m.y = spot.y;
      m.tx = spot.x + 60; m.ty = spot.y; m.wait = 60;
      let maxHidden = 0, frozen = 0, maxStep = 0, moved = 0;
      let px = m.x, py = m.y;
      // Phase 1: Frodo pins the mouse for 50 frames (2.5 s) - the old code
      // flips hiddenT=2 at fleeT 0 (~frame 32) and freezes the mouse invisible.
      for (let i = 0; i < 50; i++) {
        A.FRODO.x = m.x + 30; A.FRODO.y = m.y;
        W.resetInteractionCooldown('mouse');
        W.stepInteractions(0.05);
        maxHidden = Math.max(maxHidden, m.hiddenT || 0);
        const d = Math.hypot(m.x - px, m.y - py);
        maxStep = Math.max(maxStep, d);
        if (d < 0.001) frozen++; else moved += d;
        px = m.x; py = m.y;
      }
      const dHomeMid = Math.hypot(m.x - m.homeX, m.y - m.homeY);
      // Phase 2: threat leaves; the mouse must keep moving (return home) through
      // the former >2 s invisibility window - never frozen, never hidden.
      const away = Math.min(A.MAP.w - 80, m.x + 1900);
      A.FRODO.x = away; A.FRODO.y = away - 10; A.P.x = away; A.P.y = away - 10;
      let maxHidden2 = 0, frozen2 = 0, maxStep2 = 0, moved2 = 0;
      px = m.x; py = m.y;
      for (let i = 0; i < 40; i++) {
        W.stepInteractions(0.05);
        maxHidden2 = Math.max(maxHidden2, m.hiddenT || 0);
        const d = Math.hypot(m.x - px, m.y - py);
        maxStep2 = Math.max(maxStep2, d);
        if (d < 0.001) frozen2++; else moved2 += d;
        px = m.x; py = m.y;
      }
      const dHomeEnd = Math.hypot(m.x - m.homeX, m.y - m.homeY);
      return {
        idStable: m.id === id0 && m === ref0 && W.animals === arr0,
        countStable: W.animals.filter(a => a.kind === 'mouse').length === count0,
        maxHidden, frozen, maxStep, moved, dHomeMid,
        maxHidden2, frozen2, maxStep2, moved2, dHomeEnd,
      };
    }"""
    b02 = page.evaluate(B02_MOUSE_JS)
    assert b02["idStable"], "mouse object/identity changed during flee or after camera move"
    assert b02["countStable"], "mouse count changed during the scenario (respawn/despawn)"
    assert b02["maxHidden"] == 0 and b02["maxHidden2"] == 0, f"mouse got hiddenT (draw suppressed): {b02}"
    assert b02["frozen"] == 0 and b02["frozen2"] == 0, f"mouse frozen frames during flee/threat-leave: {b02}"
    assert b02["moved"] > 30, f"mouse barely moved while fleeing: {b02}"
    assert b02["moved2"] > 0, f"mouse frozen after threat left (former invisibility window): {b02}"
    assert b02["maxStep"] < 15 and b02["maxStep2"] < 15, f"per-frame jump (teleport) detected: {b02}"
    assert b02["dHomeEnd"] <= b02["dHomeMid"] + 25, f"mouse did not approach home after flee: {b02}"

    # ---- B02: live camera - same mouse survives leaving/re-entering the viewport
    vp = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const m = W.animals.find(a => a.kind === 'mouse');
      const clear = (x, y) => x > 60 && x < A.MAP.w - 60 && y > 130 && y < A.MAP.h - 60 && !A.blocked(x, y);
      const scout = (cx, cy) => { for (let r = 0; r < 500; r += 20) for (let a = 0; a < Math.PI * 2; a += 0.7) { const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r; if (clear(x, y)) return { x, y }; } return { x: cx, y: cy }; };
      const near = scout(m.x + 150, m.y), far = scout(m.x + 1500, m.y);
      A.P.x = near.x; A.P.y = near.y; A.FRODO.x = m.x + 350; A.FRODO.y = m.y - 60;
      return { id: m.id, n: W.animals.filter(a => a.kind === 'mouse').length, far, t0: A.time };
    }""")
    page.wait_for_timeout(400)
    vp1 = page.evaluate("""() => { const A = window.ARK, W = window.__worldLife; const m = W.animals.find(a => a.kind === 'mouse'); return { x: m.x, y: m.y, id: m.id, h: m.hiddenT || 0, t: A.time }; }""")
    assert vp1["t"] > vp["t0"], "game loop did not advance (viewport test needs a live loop)"
    assert vp1["id"] == vp["id"] and vp1["h"] == 0
    page.evaluate("""(far) => { const A = window.ARK; A.P.x = far.x; A.P.y = far.y; A.FRODO.x = far.x; A.FRODO.y = far.y - 10; }""", vp["far"])
    page.wait_for_timeout(600)
    vp2 = page.evaluate("""() => { const A = window.ARK, W = window.__worldLife; const m = W.animals.find(a => a.kind === 'mouse'); return { x: m.x, y: m.y, id: m.id, h: m.hiddenT || 0, t: A.time }; }""")
    page.wait_for_timeout(300)
    vp3 = page.evaluate("""() => { const A = window.ARK, W = window.__worldLife; const m = W.animals.find(a => a.kind === 'mouse'); return { x: m.x, y: m.y, id: m.id, h: m.hiddenT || 0, t: A.time }; }""")
    assert vp2["t"] > vp1["t"] and vp3["t"] > vp2["t"], "game loop stalled"
    assert vp2["id"] == vp["id"] and vp3["id"] == vp["id"], "mouse id changed across viewport leave/re-enter"
    assert vp2["h"] == 0 and vp3["h"] == 0, "mouse hidden while offscreen"
    assert abs(vp2["x"] - vp1["x"]) < 50 and abs(vp2["y"] - vp1["y"]) < 50, f"mouse teleported while leaving viewport: {vp1} -> {vp2}"
    assert abs(vp3["x"] - vp2["x"]) < 15 and abs(vp3["y"] - vp2["y"]) < 15, f"mouse moved while culled offscreen: {vp2} -> {vp3}"
    page.evaluate("""(near) => { const A = window.ARK; A.P.x = near.x; A.P.y = near.y; A.FRODO.x = near.x + 200; A.FRODO.y = near.y; }""", {"x": vp1["x"] + 150 if vp1["x"] < vp["far"]["x"] else vp1["x"] - 150, "y": vp1["y"]})
    page.wait_for_timeout(400)
    vp4 = page.evaluate("""() => { const A = window.ARK, W = window.__worldLife; const m = W.animals.find(a => a.kind === 'mouse'); return { x: m.x, y: m.y, id: m.id, h: m.hiddenT || 0, n: W.animals.filter(a => a.kind === 'mouse').length, t: A.time }; }""")
    assert vp4["id"] == vp["id"] and vp4["n"] == vp["n"], "mouse identity/count changed after re-entering viewport"
    assert vp4["h"] == 0
    assert abs(vp4["x"] - vp3["x"]) < 60 and abs(vp4["y"] - vp3["y"]) < 60, f"mouse teleported on viewport re-entry: {vp3} -> {vp4}"
    assert not errors, errors

    # ---- B01: same fixed seed reboots to the identical animals (ids + home anchors)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    # B02b: the pagehide snapshot resurrects the just-cleared save on reload, so a
    # plain KeyN would hit the continue-name prompt; KeyR forces the intended fresh
    # boot. The seeded rebuild below is then fully deterministic: Math.random is
    # reseeded, the player is pinned to the boot spawn, and NPC positions are pinned
    # inside RESEED_AND_SNAPSHOT (they gate animal-site acceptance).
    page.keyboard.press("KeyR")
    page.locator("#player-name-input").fill("Animals")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play' && window.__worldLife && __worldLife.vehicleSpritesLoaded", timeout=30000)
    page.evaluate("ARK.teleport(3606, 1326)")
    run2_anchors = page.evaluate(RESEED_AND_SNAPSHOT)
    assert run2_anchors == run1_anchors, "seeded reboot produced different animals / placements"
    assert not errors, errors

    # ---- B03 fallback path: boot a fresh context where critters.png never loads,
    # so critters draw through the procedural drawChicken/drawDog/drawSmallWildlife
    # fallbacks. The three excluded kinds must still have zero A.shadow there, the
    # rest exactly one, and the probe must actually be in fallback mode (no atlas
    # drawImage -> dw is None).
    fb = browser.new_page(viewport={"width": 1280, "height": 720})
    fb.route("**/critters.png", lambda route: route.abort())
    fb_errors = []
    fb.on("pageerror", lambda error: fb_errors.append(str(error)))
    fb.add_init_script(SEED_JS)
    fb.goto(PINNED_URL)
    fb.wait_for_function("window.ARK && window.__game", timeout=30000)
    fb.evaluate("localStorage.clear()")
    fb.reload()
    fb.wait_for_function("window.ARK && window.__game", timeout=30000)
    fb.keyboard.press("KeyN")
    fb.locator("#player-name-input").fill("Animals")
    fb.locator("#player-name-submit").click()
    fb.wait_for_function("__game.scene === 'play' && window.__worldLife && __worldLife.animals.length > 0 && !window.__worldLife.crittersLoaded", timeout=30000)
    fb_b03 = {}
    for kind in ("chicken", "mouse", "bird", "dog", "boar", "pig"):
        fb_b03[kind] = fb.evaluate(B03_RENDER_JS, kind)
    assert all(fb_b03[k]["dw"] is None for k in fb_b03), ("fallback page unexpectedly used the atlas", fb_b03)
    for kind in ("chicken", "mouse", "bird"):
        assert fb_b03[kind]["shadowCalls"] == 0, ("B03 fallback still draws a shadow for", kind, fb_b03[kind])
    for kind in ("dog", "boar", "pig"):
        assert fb_b03[kind]["shadowCalls"] == 1, ("B03 fallback dropped the shadow for", kind, fb_b03[kind])
    assert not fb_errors, fb_errors
    fb.close()

    # ---- B03 visual evidence at normal gameplay zoom: real screenshots plus
    # tight crops around each inspected animal (canvas coords from A.camera.S).
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    closeups = {}
    for kind in ("mouse", "chicken", "bird", "dog"):
        shot_pos = page.evaluate("""(kind) => {
          const A = window.ARK, W = window.__worldLife;
          const a = W.animals.find(x => x.kind === kind);
          const spot = (() => {
            for (const [dx, dy] of [[150, 0], [-150, 0], [0, 150], [0, -150], [220, 40], [-220, -40]]) {
              const x = a.x + dx, y = a.y + dy;
              if (x > 60 && x < A.MAP.w - 60 && y > 130 && y < A.MAP.h - 60 && !A.blocked(x, y)) return { x, y };
            }
            return { x: a.x + 150, y: a.y };
          })();
          // hold the animal still while the camera settles so the close-up lands
          a.tx = a.x + 40; a.ty = a.y; a.wait = 1e9; a.fleeT = 0; a.scatterT = 0; a.hop = 0; a.z = 0;
          a.sniffT = 0; a.leaveT = 0; a.chargeT = 0; a.curiosityT = 0; a.clatterT = 0; a.chaseT = 0;
          A.FRODO.x = a.x + 3000; A.FRODO.y = a.y;
          A.teleport(spot.x, spot.y);
          return { ax: a.x, ay: a.y };
        }""", kind)
        # the game camera eases toward the player (0.88^n per frame), so let it settle
        # before screenshotting, then sample S after the shot too
        page.wait_for_timeout(450)
        page.screenshot(path=str(SHOTS_DIR / f"b03_{kind}.png"))
        page.wait_for_timeout(450)
        # camera settled; ask the live camera where the animal now is
        scr = page.evaluate("""(pos) => {
          const A = window.ARK, c = A.camera;
          if (!c) return null;
          const [sx, sy] = c.S(pos.ax, pos.ay);
          return { sx, sy };
        }""", shot_pos)
        closeups[kind] = scr
    page.screenshot(path=str(SHOTS_DIR / "b03_overview.png"))
    for kind, scr in closeups.items():
        if not scr:
            continue
        im = Image.open(SHOTS_DIR / f"b03_{kind}.png").convert("RGB")
        half = 90
        x0 = max(0, int(scr["sx"]) - half)
        y0 = max(0, int(scr["sy"]) - half)
        x1 = min(im.width, int(scr["sx"]) + half)
        y1 = min(im.height, int(scr["sy"]) + half)
        if x1 - x0 < 8 or y1 - y0 < 8:
            print("b03 crop skipped (off-canvas):", kind, scr)
            continue
        im.crop((x0, y0, x1, y1)).save(SHOTS_DIR / f"b03_{kind}_crop.png")
    print("b03 shots:", sorted(p.name for p in SHOTS_DIR.glob("b03_*.png")))

    # ---- B07: car render contract at runtime - drawCar samples vehicles.png
    # cell (0, row 3) frame 0 and draws it 60x38 map units (behavior untouched),
    # plus desktop/mobile visual evidence of the restored car in-game.
    B07_SHOTS_DIR = Path(os.environ.get("HERMES_SCRATCH", r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch")) / "chlopkow-b07-impl"
    B07_SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    b07_car = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const canvas = document.querySelector('canvas');
      const cctx = canvas.getContext('2d');
      const car = W.cars[0], zoom = A.zoom;
      const saved = { a: W.animals.slice(), t: W.tractors.map(t => ({ x: t.x, y: t.y })) };
      W.animals.length = 0;
      for (const t of W.tractors) { t.x += 9000; t.y += 9000; }
      const ox = canvas.width / 2 - car.x * zoom, oy = canvas.height / 2 - car.y * zoom;
      const S = (x, y) => [ox + x * zoom, oy + y * zoom];
      let cap = null;
      for (const h of A.HOOKS.world) {
        const c = [];
        h((b, f) => c.push({ b, f }), S, (x, y) => Math.hypot(x - car.x, y - car.y) < 220);
        if (c.length === 1 && Math.abs(c[0].b - car.y) < 1) { cap = c; break; }
      }
      if (!cap) throw new Error('B07: car world hook not found');
      const origDraw = cctx.drawImage;
      let last = null;
      cctx.drawImage = function (img, sx, sy, sw, sh, dx, dy, dw, dh) {
        if (dw !== undefined) last = { dw, dh, sx, sy, sw, sh };
        return origDraw.apply(this, arguments);
      };
      try { cap[0].f(); } finally { cctx.drawImage = origDraw; }
      W.animals.length = 0; W.animals.push(...saved.a);
      W.tractors.forEach((t, i) => { t.x = saved.t[i].x; t.y = saved.t[i].y; });
      return { dw: last ? last.dw : null, dh: last ? last.dh : null, sx: last ? last.sx : null, sy: last ? last.sy : null, sw: last ? last.sw : null, sh: last ? last.sh : null, zoom };
    }""")
    assert b07_car["dw"] is not None, "B07: car not drawn through the atlas path"
    assert b07_car["sw"] == 64 and b07_car["sh"] == 64 and b07_car["sx"] == 0 and b07_car["sy"] == 192, ("B07: atlas cell mapping changed", b07_car)
    assert abs(b07_car["dw"] / b07_car["zoom"] - 60) <= 1 and abs(b07_car["dh"] / b07_car["zoom"] - 38) <= 1, ("B07: car draw size changed", b07_car)
    # desktop visual evidence: park the player just under the first car so the
    # camera centers it (camera follows the player; car at screen mid-width)
    page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const c = W.cars[0];
      const put = (dx, dy) => { const x = Math.round(c.x + dx), y = Math.round(c.y + dy); A.teleport(x, y); };
      const free = (x, y) => x > 60 && x < A.MAP.w - 60 && y > 130 && y < A.MAP.h - 60 && !A.blocked(x, y);
      if (free(c.x, c.y + 18)) put(0, 18);
      else if (free(c.x + 160, c.y)) put(160, 0);
      else put(-160, 0);
    }""")
    page.wait_for_timeout(450)
    page.screenshot(path=str(B07_SHOTS_DIR / "b07_car_desktop.png"))
    # mobile evidence: same boot flow in a 390x844 viewport
    mob = browser.new_page(viewport={"width": 390, "height": 844})
    mob_errors = []
    mob.on("pageerror", lambda error: mob_errors.append(str(error)))
    mob.add_init_script(SEED_JS)
    mob.goto(PINNED_URL)
    mob.wait_for_function("window.ARK && window.__game", timeout=30000)
    mob.evaluate("localStorage.clear()")
    mob.reload()
    mob.wait_for_function("window.ARK && window.__game", timeout=30000)
    mob.keyboard.press("KeyN")
    mob.locator("#player-name-input").fill("B07")
    mob.locator("#player-name-submit").click()
    mob.wait_for_function("__game.scene === 'play' && window.__worldLife && __worldLife.vehicleSpritesLoaded", timeout=30000)
    mob.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const c = W.cars[0];
      const put = (dx, dy) => { const x = Math.round(c.x + dx), y = Math.round(c.y + dy); A.teleport(x, y); };
      const free = (x, y) => x > 60 && x < A.MAP.w - 60 && y > 130 && y < A.MAP.h - 60 && !A.blocked(x, y);
      if (free(c.x, c.y + 18)) put(0, 18);
      else if (free(c.x + 160, c.y)) put(160, 0);
      else put(-160, 0);
    }""")
    mob.wait_for_timeout(450)
    mob.screenshot(path=str(B07_SHOTS_DIR / "b07_car_mobile.png"))
    assert not mob_errors, mob_errors
    mob.close()
    print("b07 shots:", sorted(p.name for p in B07_SHOTS_DIR.glob("b07_*.png")))

    print("animals: PASS", {"species": len(EXPECTED_SPECIES), "total": 81, "perKind": registry["summary"],
                            "seededRebootStable": True, "vehicleRows": len(VEHICLE_META["rows"]),
                            "b03": {"mouseQuarterW": mouse_r["dw"] / mouse_r["zoom"], "mouseQuarterH": mouse_r["dh"] / mouse_r["zoom"],
                                    "noShadow": [k for k in ("chicken", "mouse", "bird") if b03[k]["shadowCalls"] == 0],
                                    "atlasPath": True, "fallbackPath": True},
                            "b07": {"carCell": (b07_car["sx"], b07_car["sy"], b07_car["sw"], b07_car["sh"]),
                                    "drawSize": (round(b07_car["dw"] / b07_car["zoom"]), round(b07_car["dh"] / b07_car["zoom"])),
                                    "restored": True}})
    browser.close()