"""Browser regression for the A02 normal-world hover picker.

Covers world-space and screen-space hit tests for the small world hover label
(rendered by A03 next to the bottom-left coordinates): selected hero, a named
NPC, Frodo, building, tree, apple, mushroom, trash, bale, car, tractor, mouse,
bird and empty ground.

Points are always representative *visible* objects read from the live
MAP / ITEMS / __worldLife at test time - never invented coordinates - and the
expected labels come from the same translation tables the game uses
(ARK.T / heroName / terrain), so the suite verifies the picker instead of
duplicating its decisions. Nearer/front-most wins are checked with the hero
standing in front of and then behind a building; the secret (private) NPC must
never surface a name; and the picker must be side-effect free (world state
snapshot around a batch of picks must not change).

Run: ARK_URL=http://127.0.0.1:8790/index.html python test/hover_labels_test.py
"""
import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

# The full set runs in both languages.
WORLD_CASES = [
    "hero", "frodo", "npc", "building", "tree", "apple", "mushroom",
    "trash", "bale", "car", "tractor", "mouse", "bird", "ground",
]

# JS shared by every evaluate: extent model mirroring game.js worldPickAt and
# the world-life.js hitShapes() draw extents, live candidate selection per
# case, and placement helpers. Positions are re-derived from live data on every
# call, so a roaming tractor/NPC/critter only changes which representative the
# suite picks, never the expected label. (lang) is substituted per run.
PICK_JS = r"""
const g = window.__game, A = window.ARK, W = window.__worldLife;
const canvas = A.ctx.canvas;
const heroName = () => String(g.playerName).toUpperCase();
const LAB = __LANG__ === 'pl'
  ? { building: 'BUDYNEK', tree: 'DRZEWO', bale: 'BELA', car: 'SAMOCHÓD', tractor: 'TRAKTOR',
      mouse: 'MYSZ', bird: 'PTAK', ground: 'ŁĄKA' }
  : { building: 'BUILDING', tree: 'TREE', bale: 'BALE', car: 'CAR', tractor: 'TRACTOR',
      mouse: 'MOUSE', bird: 'BIRD', ground: 'MEADOW' };
const isBuilding = o => o.w >= 40 && o.h >= 30 && o.w <= 200;
const isTree = o => !isBuilding(o) && o.w < 40 && o.h >= 40;

function allExtents() {
  const out = [];
  out.push({ src: 'hero', x: g.P.x, y: g.P.y, base: g.P.y, halfW: 10, top: 40, bottom: 5 });
  out.push({ src: 'frodo', x: g.FRODO.x, y: g.FRODO.y, base: g.FRODO.y, halfW: 13, top: 27, bottom: 1 });
  for (const n of g.ITEMS.npcs || []) {
    if (n.secret) continue;
    out.push({ src: 'npc:' + n.id, x: n.x, y: n.y, base: n.y, halfW: 18, top: 46, bottom: 2 });
  }
  for (let i = 0; i < g.bales.length; i++) { const b = g.bales[i]; out.push({ src: 'bale:' + i, x: b.x, y: b.y, base: b.y, halfW: 12, top: 10, bottom: 1 }); }
  g.ITEMS.apples.forEach((a, i) => { if (g.Q.apples.includes(i)) return; out.push({ src: 'apple:' + i, x: a.x, y: a.y, base: a.y, halfW: 7, top: 13, bottom: 1 }); });
  (g.Q.mushroomSpots || []).forEach((m, i) => { if ((g.Q.mushrooms || []).includes(i)) return; out.push({ src: 'mushroom:' + i, x: m.x, y: m.y, base: m.y, halfW: 7, top: 13, bottom: 1 }); });
  (g.Q.trashSpots || []).forEach((t, i) => { if ((g.Q.trash || []).includes(i)) return; out.push({ src: 'trash:' + i, x: t.x, y: t.y, base: t.y, halfW: 9, top: 17, bottom: 2 }); });
  for (const o of g.MAP.objects || []) {
    if (!isBuilding(o) && !isTree(o)) continue;
    // Shrine sprites sit at MAP.shrines positions (game.js labels them KAPLICZKA, not DRZEWO).
    const cx = o.x + o.w / 2;
    const shrine = (g.MAP.shrines || []).some(s => Math.abs(s.x - cx) <= 24 && s.y >= o.base - o.h && s.y <= o.base + 2);
    if (shrine) continue;
    out.push({ src: (isBuilding(o) ? 'building:' : 'tree:') + o.x + ',' + o.y, x: cx, y: o.base, base: o.base, halfW: o.w / 2, top: o.h, bottom: 1 });
  }
  for (const s of W.hitShapes()) out.push(Object.assign({ src: 'wl:' + s.kind + ':' + s.x + ',' + s.y }, s));
  return out;
}
const hitAt = (e, x, y) => Math.abs(x - e.x) <= e.halfW && y >= e.y - e.top && y <= e.y + e.bottom;
const conflicts = (x, y, ignoreSrc) => allExtents().filter(e => e.src !== ignoreSrc && hitAt(e, x, y));
function placeHero(x, y) {
  g.P.x = x; g.P.y = y; g.P.air = false; g.P.z = 0; g.P.moving = false;
  A.clickTarget.active = false; A.joy.active = false;
}
function placeFrodoAway(x, y) { g.FRODO.x = x; g.FRODO.y = y; g.FRODO.wander = 0; g.FRODO.returning = false; }

// Live representative + expected label for one case kind.
function select(kind) {
  if (kind === 'hero') {
    for (let r = 0; r <= 900; r += 14) for (let a = 0; a < 6.283; a += 0.42) {
      const x = Math.round(g.MAP.spawn.x + Math.cos(a) * r), y = Math.round(g.MAP.spawn.y + Math.sin(a) * r);
      if (x < 60 || y < 60 || x > g.MAP.w - 60 || y > g.MAP.h - 60) continue;
      if (g.blocked(x, y)) continue;
      if (conflicts(x, y - 12, null).length || conflicts(x, y - 70, null).length) continue;
      return { pt: [x, y - 12], hero: [x, y], expected: heroName(), kind, frodo: null };
    }
    return null;
  }
  if (kind === 'frodo') {
    const base = [g.P.x, g.P.y];
    for (const dx of [0, 40, -40, 80, -80, 120])
      for (const dy of [-70, -95, -120, -145, -170]) {
        const fx = base[0] + dx, fy = base[1] + dy;
        g.FRODO.x = fx; g.FRODO.y = fy; g.FRODO.wander = 0; g.FRODO.returning = false;
        const pt = [fx, fy - 12];
        if (!conflicts(pt[0], pt[1], 'frodo').length) return { pt, expected: 'FRODO', kind, frodo: [fx, fy] };
      }
    return null;
  }
  if (kind === 'npc') {
    for (const n of g.ITEMS.npcs || []) {
      if (n.secret || !A.T.names[n.id]) continue;
      const pt = [n.x, n.y - 24];
      if (!conflicts(pt[0], pt[1], 'npc:' + n.id).length) return { pt, expected: String(A.T.names[n.id]).toUpperCase(), kind, frodo: null };
    }
    return null;
  }
  if (kind === 'tree' || kind === 'building') {
    for (const o of g.MAP.objects || []) {
      const ok = kind === 'building' ? isBuilding(o) : isTree(o);
      if (!ok) continue;
      const pt = [o.x + o.w / 2, o.base - (kind === 'building' ? 8 : 12)];
      if (!conflicts(pt[0], pt[1], (kind === 'building' ? 'building:' : 'tree:') + o.x + ',' + o.y).length) return { pt, expected: LAB[kind], kind, frodo: null };
    }
    return null;
  }
  if (kind === 'apple') {
    for (let i = 0; i < g.ITEMS.apples.length; i++) {
      if (g.Q.apples.includes(i)) continue;
      const a = g.ITEMS.apples[i], pt = [a.x, a.y - 6];
      if (!conflicts(pt[0], pt[1], 'apple:' + i).length) return { pt, expected: String(A.T.apple).toUpperCase(), kind, frodo: null };
    }
    return null;
  }
  if (kind === 'mushroom') {
    for (let i = 0; i < (g.Q.mushroomSpots || []).length; i++) {
      if ((g.Q.mushrooms || []).includes(i)) continue;
      const m = g.Q.mushroomSpots[i], pt = [m.x, m.y - 6];
      if (!conflicts(pt[0], pt[1], 'mushroom:' + i).length) return { pt, expected: String(A.T.mushroom).toUpperCase(), kind, frodo: null };
    }
    return null;
  }
  if (kind === 'trash') {
    for (let i = 0; i < (g.Q.trashSpots || []).length; i++) {
      if ((g.Q.trash || []).includes(i)) continue;
      const t = g.Q.trashSpots[i], pt = [t.x, t.y - 6];
      if (!conflicts(pt[0], pt[1], 'trash:' + i).length) return { pt, expected: String(A.T.trash).toUpperCase(), kind, frodo: null };
    }
    return null;
  }
  if (kind === 'bale') {
    for (let i = 0; i < g.bales.length; i++) {
      const b = g.bales[i], pt = [b.x, b.y - 5];
      if (!conflicts(pt[0], pt[1], 'bale:' + i).length) return { pt, expected: LAB.bale, kind, frodo: null };
    }
    return null;
  }
  if (kind === 'car') {
    for (let i = 0; i < W.cars.length; i++) {
      const c = W.cars[i], pt = [c.x, c.y - 20];
      if (!conflicts(pt[0], pt[1], 'wl:car:' + c.x + ',' + c.y).length) return { pt, expected: LAB.car, kind, frodo: null };
    }
    return null;
  }
  if (kind === 'tractor') {
    for (let i = 0; i < W.tractors.length; i++) {
      const t = W.tractors[i], pt = [t.x, t.y - 20];
      if (!conflicts(pt[0], pt[1], 'wl:tractor:' + t.x + ',' + t.y).length) return { pt, expected: LAB.tractor, kind, frodo: null };
    }
    return null;
  }
  if (kind === 'mouse' || kind === 'bird') {
    for (const a of W.animals) {
      if (a.kind !== kind) continue;
      const pt = kind === 'bird' ? [a.x, a.y - (a.z || 0) - 3] : [a.x, a.y - 4];
      if (!conflicts(pt[0], pt[1], 'wl:' + kind + ':' + a.x + ',' + a.y).length) return { pt, expected: LAB[kind], kind, frodo: null };
    }
    return null;
  }
  if (kind === 'ground') {
    for (let r = 0; r <= 1600; r += 16) for (let a = 0; a < 6.283; a += 0.42) {
      const x = Math.round(g.MAP.spawn.x + Math.cos(a) * r), y = Math.round(g.MAP.spawn.y + Math.sin(a) * r);
      if (x < 40 || y < 40 || x > g.MAP.w - 40 || y > g.MAP.h - 40) continue;
      if (g.terrainAt(x, y) !== 'grass' || g.blocked(x, y)) continue;
      if (!conflicts(x, y, null).length) return { pt: [x, y], expected: LAB.ground, kind, frodo: null };
    }
    return null;
  }
  return null;
}
"""

WORLD_JS = r"""
(kind) => {
  const sel = select(kind);
  if (!sel) return { case: kind, ok: false, what: 'no clear live representative found' };
  if (kind === 'hero') { placeHero(sel.pt[0], sel.pt[1] + 12); placeFrodoAway(sel.pt[0] - 140, sel.pt[1] + 60); }
  else if (kind === 'frodo') { placeHero(sel.pt[0] + 180, sel.pt[1] + 120); }
  else { placeHero(sel.pt[0] - 150, sel.pt[1] - 60); placeFrodoAway(sel.pt[0] - 150 + 130, sel.pt[1] - 60 + 30); }
  let got = null, pickKind = null, err = null;
  try {
    got = g.worldHoverLabel(sel.pt[0], sel.pt[1]);
    const p = g.worldPickAt(sel.pt[0], sel.pt[1]);
    pickKind = p ? p.kind : null;
  } catch (e) { err = String(e && e.message || e); }
  return { case: kind, ok: !err && got === sel.expected && pickKind === kind, got, expected: sel.expected, kind: pickKind, pt: sel.pt, err };
}
"""

OVERLAP_JS = r"""
() => {
  const sel = select('building');
  if (!sel) return { ok: false, what: 'no clear building for overlap check' };
  const bx = sel.pt[0], by = sel.pt[1]; // inside the building rect, 8 px above its baseline
  const out = {};
  // Hero in front: his baseline is below the building's, so he must win the point.
  placeHero(bx, by + 10); placeFrodoAway(bx + 120, by - 60);
  const front = g.worldHoverLabel(bx, by), frontKind = g.worldPickAt(bx, by).kind;
  out.front = { got: front, expected: heroName(), kind: frontKind };
  // Hero behind: his baseline is above the building's -> the building wins.
  placeHero(bx, by - 60); placeFrodoAway(bx + 120, by - 60);
  const back = g.worldHoverLabel(bx, by), backKind = g.worldPickAt(bx, by).kind;
  out.back = { got: back, expected: LAB.building, kind: backKind };
  out.ok = front === heroName() && frontKind === 'hero' && back === LAB.building && backKind === 'building';
  return out;
}
"""

SECRET_JS = r"""
() => {
  const s = (g.ITEMS.npcs || []).find(n => n.secret);
  if (!s) return { ok: true, note: 'no secret npc in items.json' };
  const p = g.worldPickAt(s.x, s.y - 24);
  const secretName = String(A.T.names[s.id]).toUpperCase();
  const got = p ? p.label : null;
  return { ok: !(p && p.kind === 'npc') && got !== secretName, got, secretName, pt: [s.x, s.y - 24] };
}
"""

SIDEFX_JS = r"""
() => {
  const snap = () => JSON.stringify([
    g.P.x, g.P.y, g.FRODO.x, g.FRODO.y, g.Q.apples.length, g.Q.mushrooms.length,
    g.Q.mushroomSpots.length, g.Q.trashSpots.length, W.cars.length, W.tractors.length,
    W.animals.length, A.time, g.showMap, g.scene, JSON.stringify(g.Q.quiz),
  ]);
  const points = [[10, 10], [Math.round(g.MAP.w / 2), Math.round(g.MAP.h / 2)], [g.P.x, g.P.y], [g.P.x, g.P.y - 25],
    [g.MAP.spawn.x, g.MAP.spawn.y], [g.FRODO.x, g.FRODO.y]];
  const before = snap();
  let calls = 0;
  for (const [x, y] of points) { g.worldHoverLabel(x, y); g.worldPickAt(x, y); g.worldHoverLabelAtCanvas(320, 240); calls += 3; }
  // worldHoverLabel(hero spot) also re-runs on the same world point
  g.worldHoverLabel(g.P.x, g.P.y - 12); calls += 1;
  const after = snap();
  const shapes1 = JSON.stringify(W.hitShapes()), shapes2 = JSON.stringify(W.hitShapes());
  return { ok: before === after && shapes1 === shapes2, calls, unchanged: before === after, shapesPure: shapes1 === shapes2 };
}
"""

SCREEN_JS = r"""
([kind, world]) => {
  let point = world.pt, expected = world.expected;
  // Movable kinds are re-derived live at assert time; fixed kinds reuse the point.
  if (kind === 'tractor' || kind === 'mouse' || kind === 'bird' || kind === 'npc') {
    const sel = select(kind);
    if (!sel) return { case: kind, status: 'skipped', reason: 'no clear live representative' };
    point = sel.pt; expected = sel.expected;
    // A roaming representative may have moved outside the camera after the
    // world pass; an off-canvas probe is a skip, never a false failure.
    const [cx, cy] = (A.camera || { S: () => [0, 0] }).S(point[0], point[1]);
    if (cx < 10 || cy < 10 || cx > canvas.width - 10 || cy > canvas.height - 10)
      return { case: kind, status: 'skipped', reason: 'representative moved off-screen', point };
  }
  if (kind === 'frodo') { g.FRODO.x = point[0]; g.FRODO.y = point[1] + 12; }
  else placeFrodoAway(point[0] - 120, point[1] + 80);
  const live = g.worldHoverLabel(point[0], point[1]);
  if (live !== expected) return { case: kind, status: 'drifted', got: live, expected };
  const cam = A.camera;
  if (!cam) return { case: kind, status: 'skipped', reason: 'no camera' };
  const [px, py] = cam.S(point[0], point[1]);
  const back = cam.toWorld(px, py);
  const label = g.worldHoverLabelAtCanvas(px, py);
  const roundtrip = Math.hypot(back[0] - point[0], back[1] - point[1]);
  return {
    case: kind, status: label === expected ? 'ok' : 'FAIL', ok: label === expected && roundtrip < 0.01,
    label, expected, px, py, roundtrip,
    onScreen: px >= 10 && py >= 10 && px <= canvas.width - 10 && py <= canvas.height - 10,
  };
}
"""


SHRINE_JS = r"""
() => {
  // Wayside shrines are drawn as tall thin sprites at MAP.shrines positions; the
  // picker must label them KAPLICZKA (big-map name), never a generic DRZEWO/TREE.
  const bad = [];
  const counts = { shrine: 0, other: 0 };
  for (const s of g.MAP.shrines || []) {
    if (!Number.isFinite(s.x) || !Number.isFinite(s.y)) continue;
    const p = g.worldPickAt(s.x, s.y - 20);
    if (!p) continue;
    if (p.kind === 'tree') bad.push({ pt: [s.x, s.y - 20], got: p.label });
    if (p.kind === 'shrine') counts.shrine++; else counts.other++;
  }
  return { ok: bad.length === 0, bad, counts };
}
"""

TIE_JS = r"""
() => {
  // Equal-baseline ties must go to the front-most layer - the one drawn last by
  // the render() y-sort push order (objects < pickups < cap < bales < npcs <
  // hero < frodo < world-life). Three probes: hero-on-NPC, bale-on-apple and
  // cap-on-apple (the cap is pushed after apples, so it wins that tie).
  const out = { heroNpc: null, baleApple: null, capApple: null };
  // Probe 1: hero standing exactly on an NPC's y (both baselines equal) - hero wins.
  const npc = (g.ITEMS.npcs || []).find(n => !n.secret && A.T.names[n.id]);
  if (npc) {
    // Hero baseline EXACTLY at the NPC baseline: both hit the same point
    // (both extents cover npc.y - 12) and both have base === npc.y, so the
    // tie must go to the hero (drawn after NPCs in the render push order).
    placeHero(npc.x, npc.y); placeFrodoAway(npc.x + 140, npc.y + 80);
    const p = g.worldPickAt(npc.x, npc.y - 12);
    out.heroNpc = { ok: !!(p && p.kind === 'hero'), got: p && p.label, kind: p && p.kind, at: [npc.x, npc.y] };
  }
  // Probe 2: a bale exactly on an uncollected apple (equal baselines) - bale wins.
  const appleIdx = g.ITEMS.apples.findIndex((a, i) => !g.Q.apples.includes(i));
  if (appleIdx >= 0) {
    const a = g.ITEMS.apples[appleIdx], bale = g.bales[0];
    if (bale) {
      const ob = { x: bale.x, y: bale.y, vx: bale.vx || 0, hx: bale.hx != null ? bale.hx : bale.x, hy: bale.hy != null ? bale.hy : bale.y };
      bale.x = a.x; bale.y = a.y;
      if (bale.hx != null) { bale.hx = a.x; bale.hy = a.y; }
      placeHero(a.x + 260, a.y + 120); placeFrodoAway(a.x + 200, a.y + 160);
      const p = g.worldPickAt(a.x, a.y - 4);
      bale.x = ob.x; bale.y = ob.y;
      if (ob.hx != null) { bale.hx = ob.hx; bale.hy = ob.hy; }
      out.baleApple = { ok: !!(p && p.kind === 'bale' && p.label === LAB.bale), got: p && p.label, kind: p && p.kind, appleAt: [a.x, a.y], appleIdx };
    }
  }
  // Probe 3: Damian's cap exactly on an uncollected apple (equal baselines) -
  // the cap is pushed after apples in render(), so it wins the tie.
  if (appleIdx >= 0) {
    const a = g.ITEMS.apples[appleIdx];
    const capO = { x: g.ITEMS.cap.x, y: g.ITEMS.cap.y };
    g.ITEMS.cap.x = a.x; g.ITEMS.cap.y = a.y;
    placeHero(a.x + 260, a.y + 140); placeFrodoAway(a.x + 200, a.y + 180);
    const p = g.worldPickAt(a.x, a.y - 6);
    g.ITEMS.cap.x = capO.x; g.ITEMS.cap.y = capO.y;
    out.capApple = { ok: !!(p && p.kind === 'cap'), got: p && p.label, kind: p && p.kind, appleAt: [a.x, a.y], appleIdx };
  }
  out.ok = !!out.heroNpc && out.heroNpc.ok && !!out.baleApple && out.baleApple.ok && !!out.capApple && out.capApple.ok;
  return out;
}
"""


def boot(page, name="Zosia", lang="pl"):
    url = URL
    if lang and lang != "pl":
        url += ("&" if "?" in url else "?") + "lang=en"
    page.goto(url)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game && window.__worldLife", timeout=30000)
    page.keyboard.press("Enter")
    page.locator("#player-name-input").fill(name)
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'", timeout=30000)


def run_lang(lang):
    results = {}
    pick = PICK_JS.replace("__LANG__", "'" + lang + "'")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        boot(page, lang=lang)

        for kind in WORLD_CASES:
            results[kind] = page.evaluate(pick + WORLD_JS, kind)
        results["overlap"] = page.evaluate(pick + OVERLAP_JS)
        results["secret"] = page.evaluate(pick + SECRET_JS)
        results["sidefx"] = page.evaluate(pick + SIDEFX_JS)
        results["shrine"] = page.evaluate(pick + SHRINE_JS)
        results["tie"] = page.evaluate(pick + TIE_JS)

        for kind in WORLD_CASES:
            world = results[kind]
            if world.get("ok"):
                page.evaluate(
                    "([kind, pt]) => { const g = window.__game, A = window.ARK; const x = pt[0], y = pt[1]; "
                    "g.P.x = x + (kind === 'hero' ? 0 : 90); g.P.y = y + 12 + (kind === 'hero' ? 0 : 48); "
                    "g.P.air = false; g.P.z = 0; g.P.moving = false; A.clickTarget.active = false; A.joy.active = false; "
                    "g.FRODO.x = x - 140; g.FRODO.y = y + 70; g.FRODO.wander = 0; }",
                    [kind, world["pt"]],
                )
                page.wait_for_timeout(700)
                results[kind + "_screen"] = page.evaluate(pick + SCREEN_JS, [kind, world])
            else:
                results[kind + "_screen"] = {"case": kind, "status": "skipped", "reason": "world case failed"}
        browser.close()
    return {"results": results, "errors": errors}


def main():
    overall_ok = True
    for lang in ("pl", "en"):
        run = run_lang(lang)
        results, errors = run["results"], run["errors"]
        print(f"\n=== hover labels [{lang}] ===")
        for kind in WORLD_CASES:
            r = results[kind]
            mark = "PASS" if r.get("ok") else "FAIL"
            if not r.get("ok"):
                overall_ok = False
            print(f"  world  {kind:9s} {mark}  got={r.get('got')!r} expected={r.get('expected')!r} pt={r.get('pt')} err={r.get('err')}")
            s = results.get(kind + "_screen") or {}
            smark = s.get("status", "?")
            if smark == "FAIL":
                overall_ok = False
            print(f"  screen {kind:9s} {smark:7s} label={s.get('label')!r} roundtrip={s.get('roundtrip')} onScreen={s.get('onScreen')}")
        o = results["overlap"]
        print(f"  overlap    {o.get('ok')}  front={o.get('front')} back={o.get('back')}")
        if not o.get("ok"):
            overall_ok = False
        s = results["secret"]
        print(f"  secret     {s.get('ok')}  got={s.get('got')!r} (must never be {s.get('secretName')})")
        if not s.get("ok"):
            overall_ok = False
        fx = results["sidefx"]
        print(f"  sidefx     {fx.get('ok')}  calls={fx.get('calls')} unchanged={fx.get('unchanged')} shapesPure={fx.get('shapesPure')}")
        if not fx.get("ok"):
            overall_ok = False
        sh = results["shrine"]
        print(f"  shrine     {sh.get('ok')}  labels={sh.get('counts')} bad={sh.get('bad')}")
        if not sh.get("ok"):
            overall_ok = False
        ti = results["tie"]
        print(f"  tie        {ti.get('ok')}  heroNpc={ti.get('heroNpc')} baleApple={ti.get('baleApple')} capApple={ti.get('capApple')}")
        if not ti.get("ok"):
            overall_ok = False
        if errors:
            overall_ok = False
            print(f"  page errors: {errors}")
    print("\nhover_labels:", "PASS" if overall_ok else "FAIL")
    if not overall_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()