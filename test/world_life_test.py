"""Standalone browser test for docs/js/world-life.js.

The plugin is loaded after the normal page for isolation, then ark-ready is
redispatched. Production integration should load the script before game.js.
"""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOT_DIR = Path(r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\chlopkow-b02b")
SHOT_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" and "wss://" not in msg.text else None)
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" and "wss://" not in message.text else None)
    page.goto(URL)
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.cars.length === 2 && window.__worldLife.waterPoints.length > 0")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")

    facts = page.evaluate("""(() => {
      const g = __game, wl = __worldLife;
      const ground = wl.animals.filter(a => a.kind !== 'bird');
      const storks = wl.animals.filter(a => a.kind === 'stork');
      const pigs = wl.animals.filter(a => a.kind === 'pig');
      const tractorsField = wl.tractors.length === 2 && wl.tractors.every(t => g.terrainAt(t.x, t.y) === 'field' && !g.blocked(t.x, t.y));
      const buildings = (g.MAP.objects || []).filter(o => o.w >= 40 && o.h >= 30 && o.w <= 200);
      const water = Array.isArray(g.MAP.water) && g.MAP.water.length ? g.MAP.water : wl.waterPoints;
      const riverOnly = water.length > 0 && storks.length === 3 && storks.every(a => water.some(v => Math.hypot(a.x - v.x, a.y - v.y) <= 100));
      const pigsByBuildings = pigs.length === 5 && pigs.every(a => buildings.some(o => Math.hypot(a.x - (o.x + o.w / 2), a.y - o.base) < 180));
      const allValid = wl.cars.length === 2 && wl.cars.every(c => !g.blocked(c.x, c.y)) &&
    wl.animals.length >= 40 && wl.animals.every(a => !g.blocked(a.x, a.y));
      // Birds are intentionally spawned in small flocks, so only require the
      // separation invariant for the non-flocking ground animals.
      const apart = ground.every((a, i) => Math.hypot(a.x - g.P.x, a.y - g.P.y) >= 29 &&
    ground.every((b, j) => i === j || Math.hypot(a.x - b.x, a.y - b.y) >= 23));
      const oldCars = wl.cars.map(c => `${c.x},${c.y}`).join('|');
      wl.resetCars();
      const reset = wl.cars.length === 2 && wl.cars.map(c => `${c.x},${c.y}`).join('|') !== oldCars;
      g.Q.apples = Array.from({length: 10}, (_, i) => i);
      g.Q.worldLife.spentApples = 0;
      wl.buyRide(0);
      const purchased = wl.rideSeconds === 15 && g.Q.worldLife.spentApples === 10 &&
    wl.balance() === 0 && g.Q.apples.length === 10;
      return {allValid, apart, reset, purchased, riverOnly, pigsByBuildings, tractorsField};
    })()""")
    assert facts == {"allValid": True, "apart": True, "reset": True, "purchased": True, "riverOnly": True, "pigsByBuildings": True, "tractorsField": True}, facts
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.cars.length === 2")
    persisted = page.evaluate("[__game.Q.worldLife.spentApples, __worldLife.balance(), __game.Q.apples.length]")
    assert persisted == [10, 0, 10], persisted
    page.evaluate("__game.scene = 'title'")
    page.keyboard.press("KeyR")
    page.locator("#player-name-input").fill("Test")
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play' && __worldLife.cars.length === 2")
    fresh = page.evaluate("[__game.Q.worldLife.spentApples, __game.Q.apples.length, __worldLife.cars.every(c => !__game.blocked(c.x, c.y))]")
    assert fresh == [0, 0, True], fresh
    registry = page.evaluate("""() => {
      const W = __worldLife, types = W.animalTypes || {}, w = __game.Q.worldLife || {};
      const counts = {};
      for (const a of W.animals) counts[a.kind] = (counts[a.kind] || 0) + 1;
      const byKind = {};
      for (const a of W.animals) (byKind[a.kind] = byKind[a.kind] || []).push(a.id);
      const order = W.speciesOrder || [];
      const tableOk = order.length === Object.keys(types).length && order.length === Object.keys(counts).length;
      const idsOk = W.animals.length > 0 &&
            W.animals.every(a => typeof a.id === 'string' && /^[a-z]+:\\d+$/.test(a.id)) &&
            Object.entries(byKind).every(([k, list]) => list.every((id, i) => id === k + ':' + i));
      const countsOk = Object.entries(types).every(([k, d]) => counts[k] === d.count);
      const noMigrate = !('animals' in w) && !('ids' in w);
      return { total: W.animals.length, tableOk, idsOk, countsOk, noMigrate, counts, order };
    }""")
    assert registry["total"] == 81, registry["counts"]
    assert registry["tableOk"], registry
    assert registry["idsOk"], "animals lack stable sequential kind:index ids"
    assert registry["countsOk"], registry["counts"]
    assert registry["noMigrate"], "saved worldLife gained per-animal keys (no migration in B01)"
    # ---- B02: the same mouse object survives flee + former invisibility window
    b02 = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const m = W.animals.find(a => a.kind === 'mouse');
      const id0 = m.id, n0 = W.animals.filter(a => a.kind === 'mouse').length;
      // Deterministic arena: a long clear strip west of a spot around the player,
      // so flee (straight west) and the return-to-home walk can never be blocked
      // by village clutter (assertions below are unchanged from B02).
      const free = (x, y) => x > 80 && x < A.MAP.w - 80 && y > 130 && y < A.MAP.h - 80 && !A.blocked(x, y);
      let spot = null;
      outer:
      for (let r = 260; r < 1100; r += 36) {
        for (let a = 0; a < Math.PI * 2; a += 0.45) {
          const x = A.P.x + Math.cos(a) * r, y = A.P.y + Math.sin(a) * r;
          let ok = free(x, y);
          for (let k = 0; k <= 14 && ok; k++) ok = free(x - 28 * k, y) && free(x - 28 * k, y + 18) && free(x - 28 * k, y - 18);
          ok = ok && free(x + 30, y);
          if (ok) { spot = { x: Math.round(x), y: Math.round(y) }; break outer; }
        }
      }
      if (!spot) throw new Error('B02: no clear runway found for the mouse arena');
      m.x = spot.x; m.y = spot.y; m.homeX = spot.x; m.homeY = spot.y; m.wait = 60;
      let maxHidden = 0, frozen = 0, moved = 0;
      let pc = { x: m.x, y: m.y };
      // Pin Frodo on the mouse long enough that the old hiddenT=2 path would fire.
      for (let i = 0; i < 70; i++) {
        A.FRODO.x = m.x + 30; A.FRODO.y = m.y;
        W.resetInteractionCooldown('mouse');
        W.stepInteractions(0.05);
        maxHidden = Math.max(maxHidden, m.hiddenT || 0);
        const d = Math.hypot(m.x - pc.x, m.y - pc.y);
        if (d < 0.001) frozen++; else moved += d;
        pc.x = m.x; pc.y = m.y;
      }
      // Threat leaves: mouse must keep moving (return home), not freeze invisible.
      const away = Math.min(A.MAP.w - 80, m.x + 1900);
      A.FRODO.x = away; A.FRODO.y = away - 10; A.P.x = away; A.P.y = away - 10;
      const dMid = Math.hypot(m.x - m.homeX, m.y - m.homeY);
      let moved2 = 0, frozen2 = 0, maxHidden2 = 0;
      pc = { x: m.x, y: m.y };
      for (let i = 0; i < 50; i++) {
        W.stepInteractions(0.05);
        maxHidden2 = Math.max(maxHidden2, m.hiddenT || 0);
        const d = Math.hypot(m.x - pc.x, m.y - pc.y);
        if (d < 0.001) frozen2++; else moved2 += d;
        pc.x = m.x; pc.y = m.y;
      }
      const dEnd = Math.hypot(m.x - m.homeX, m.y - m.homeY);
      return {
        sameId: m.id === id0,
        countOk: W.animals.filter(a => a.kind === 'mouse').length === n0,
        maxHidden, frozen, moved, maxHidden2, frozen2, moved2, dMid, dEnd,
      };
    }""")
    assert b02["sameId"], "mouse id changed across flee/invisibility window"
    assert b02["countOk"], "mouse count changed during flee"
    assert b02["maxHidden"] == 0 and b02["maxHidden2"] == 0, f"hiddenT-driven draw suppression still active: {b02}"
    assert b02["frozen"] == 0 and b02["frozen2"] == 0, f"mouse frozen during/after flee: {b02}"
    assert b02["moved"] > 20, f"mouse did not flee: {b02}"
    assert b02["moved2"] > 0, f"mouse stopped after threat left: {b02}"
    assert b02["dEnd"] < b02["dMid"] + 25, f"mouse did not head home after flee: {b02}"

    # ---- B02b: animal identity/location survives save + reload (isolated context).
    # Legacy Q.worldLife with no snapshot was already covered above (baseline spawns).
    # Here: anchor six animals at exact valid spots, flush an ordinary save, verify the
    # payload (size, cars untouched, one save key), tamper the snapshot with malformed
    # entries, prove restore-by-ID ignores them, then prove a full save/reload round-trip
    # restores every animal to the same kind:index id and a validated nearby position.
    controls = ["chicken:0", "dog:2", "pig:0", "fox:0", "hare:1", "stork:0"]
    b02b_boot = page.evaluate("""(controls) => {
      const A = window.ARK, W = window.__worldLife, MAP = A.MAP;
      const free = (x, y) => x > 80 && x < MAP.w - 80 && y > 130 && y < MAP.h - 80 && !A.blocked(x, y);
      A.teleport(MAP.spawn.x, MAP.spawn.y);
      const cands = [];
      for (let r = 60; r < 1500 && cands.length < 500; r += 24) {
        for (let a = 0; a < Math.PI * 2 && cands.length < 500; a += 0.25) {
          const x = Math.round(MAP.spawn.x + Math.cos(a) * r), y = Math.round(MAP.spawn.y + Math.sin(a) * r);
          if (free(x, y)) cands.push({ x, y });
        }
      }
      const spots = [];
      for (const c of cands) {
        if (spots.every(p => Math.hypot(p.x - c.x, p.y - c.y) > 260)) { spots.push(c); if (spots.length === controls.length) break; }
      }
      if (spots.length < controls.length) throw new Error('B02b: too few mutually separated anchor spots: ' + spots.length);
      const anchored = {};
      controls.forEach((id, i) => {
        const a = W.animals.find(v => v.id === id);
        if (!a) throw new Error('B02b: missing ' + id);
        const s = spots[i];
        Object.assign(a, { x: s.x, y: s.y, homeX: s.x, homeY: s.y, tx: s.x + 20, ty: s.y, wait: 99999 });
        anchored[id] = s;
      });
      return { anchored, total: W.animals.length };
    }""", controls)
    assert b02b_boot["total"] == 81
    page.wait_for_timeout(300)
    page.screenshot(path=str(SHOT_DIR / "b02b_save_before.png"))
    b02b_payload = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      W.flushSave();
      const w = A.Q.worldLife;
      const saved = JSON.parse(localStorage.getItem('arek-chlopkow-save-v1'));
      return {
        keyOk: localStorage.getItem('arek-chlopkow-save-v1') !== null,
        keys: Object.keys(localStorage),
        wlKeys: Object.keys(w).sort(),
        animalCount: (w.animals || []).length,
        animalJsonLen: JSON.stringify(w.animals).length,
        fullSaveChars: localStorage.getItem('arek-chlopkow-save-v1').length,
        carsJson: JSON.stringify(w.cars),
        noTractors: !('tractors' in w),
        savedHasAnimals: !!(saved && saved.Q && saved.Q.worldLife && Array.isArray(saved.Q.worldLife.animals)),
      };
    }""")
    assert b02b_payload["keyOk"] and b02b_payload["savedHasAnimals"]
    assert b02b_payload["animalCount"] == 81
    assert b02b_payload["animalJsonLen"] < 12000, f"animal snapshot too large: {b02b_payload['animalJsonLen']}"
    assert b02b_payload["fullSaveChars"] < 20000, f"full save too large: {b02b_payload['fullSaveChars']}"
    assert not any("animal" in k for k in b02b_payload["keys"]), f"new storage key appeared: {b02b_payload['keys']}"
    assert "cars" in b02b_payload["wlKeys"] and "animals" in b02b_payload["wlKeys"] and "tractors" not in b02b_payload["wlKeys"], b02b_payload["wlKeys"]
    assert b02b_payload["carsJson"].startswith('[{"x":') and b02b_payload["carsJson"].endswith('}]') and '"kind"' not in b02b_payload["carsJson"], b02b_payload["carsJson"]
    print(f"B02b payload: full save={b02b_payload['fullSaveChars']} chars, animals={b02b_payload['animalJsonLen']} chars")

    # Malformed snapshot: unknown kind/id, NaN, solid-map and out-of-bounds positions,
    # an id whose prefix does not match its kind, and a duplicated control id.
    b02b_mal = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const w = A.Q.worldLife;
      let solid = null;
      for (let r = 0; r < 2500 && !solid; r += 12) for (let a = 0; a < Math.PI * 2; a += 0.6) {
        const x = A.P.x + Math.cos(a) * r, y = A.P.y + Math.sin(a) * r;
        if (x > 22 && y > 60 && x < A.MAP.w - 22 && y < A.MAP.h - 22 && A.blocked(x, y)) { solid = { x, y }; break; }
      }
      if (!solid) throw new Error('B02b: no blocked map point found');
      const clean = w.animals.map(e => ({ ...e }));
      const orig = {};
      for (const id of ['chicken:3', 'chicken:4', 'chicken:5', 'chicken:6']) orig[id] = clean.find(e => e.id === id);
      const tampered = clean.map(e => {
        if (e.id === 'chicken:1') return { id: 'dragon:0', kind: 'dragon', x: e.x, y: e.y, homeX: e.x, homeY: e.y, tx: e.x, ty: e.y };
        if (e.id === 'chicken:2') return { id: 'alien:0', kind: 'chicken', x: e.x, y: e.y, homeX: e.x, homeY: e.y, tx: e.x, ty: e.y };
        if (e.id === 'chicken:3') return { id: 'chicken:3', kind: 'chicken', x: NaN, y: NaN, homeX: NaN, homeY: NaN, tx: NaN, ty: NaN };
        if (e.id === 'chicken:4') return { id: 'chicken:4', kind: 'chicken', x: solid.x, y: solid.y, homeX: solid.x, homeY: solid.y, tx: solid.x, ty: solid.y };
        if (e.id === 'chicken:5') return { id: 'chicken:5', kind: 'chicken', x: -50, y: -50, homeX: -50, homeY: -50, tx: -50, ty: -50 };
        if (e.id === 'chicken:6') return { id: 'dog:6', kind: 'chicken', x: 400, y: 400, homeX: 400, homeY: 400, tx: 400, ty: 400 };
        return e;
      });
      tampered.push({ ...clean.find(e => e.id === 'chicken:0'), x: 300, y: 300, homeX: 300, homeY: 300, tx: 300, ty: 300 });
      w.animals = tampered;
      W.reloadAnimals();          // rebuild baseline from scratch, restore by id from the malformed snapshot
      const counts = {};
      for (const a of W.animals) counts[a.kind] = (counts[a.kind] || 0) + 1;
      const ids = W.animals.map(a => a.id).sort();
      const restoredIds = W.lastRestored.slice().sort();
      const expected = W.animals.map(a => a.id).filter(id => !['chicken:1', 'chicken:2', 'chicken:3', 'chicken:4', 'chicken:5', 'chicken:6'].includes(id)).sort();
      const ch = W.animals.filter(a => a.kind === 'chicken').map(a => a.id).sort();
      const a0 = W.animals.find(a => a.id === 'chicken:0');
      const dog6 = W.animals.find(a => a.id === 'dog:6');
      return {
        counts, total: W.animals.length, ids, restoredIds, expected, ch,
        a0: { x: Math.round(a0.x), y: Math.round(a0.y), hx: Math.round(a0.homeX), hy: Math.round(a0.homeY) },
        dog6: { id: 'dog:6', restored: restoredIds.includes('dog:6'), x: Math.round(dog6.x), y: Math.round(dog6.y) },
        cur: Object.fromEntries(W.animals.filter(a => a.kind === 'chicken').map(a => [a.id, { x: Math.round(a.x), y: Math.round(a.y) }])),
        orig: Object.fromEntries(Object.entries(orig).map(([k, v]) => [k, { x: Math.round(v.x), y: Math.round(v.y) }])),
      };
    }""")
    EXPECTED_COUNTS = {"chicken": 12, "dog": 7, "bird": 24, "stork": 3, "fox": 2, "boar": 4, "mouse": 10, "hare": 6, "pig": 5, "butterfly": 8}
    assert b02b_mal["total"] == 81 and b02b_mal["counts"] == EXPECTED_COUNTS, b02b_mal["counts"]
    assert set(b02b_mal["ch"]) == {f"chicken:{i}" for i in range(12)}, b02b_mal["ch"]
    assert not any(x in b02b_mal["ids"] for x in ["dragon:0", "alien:0", "chicken:99"]), b02b_mal["ids"]
    assert b02b_mal["restoredIds"] == b02b_mal["expected"], f"restore mismatch: extra={set(b02b_mal['restoredIds']) - set(b02b_mal['expected'])} missing={set(b02b_mal['expected']) - set(b02b_mal['restoredIds'])}"
    assert len(b02b_mal["restoredIds"]) == 75, len(b02b_mal["restoredIds"])
    for cid in controls:
        assert cid in b02b_mal["restoredIds"], (cid, b02b_mal["restoredIds"])
    # anchored chicken:0 came back to its saved home (the duplicated 300,300 copy was
    # ignored); home is pinned forever while x/y may have drifted a few px before flush
    a0 = b02b_boot["anchored"]["chicken:0"]
    assert abs(b02b_mal["a0"]["hx"] - a0["x"]) <= 1 and abs(b02b_mal["a0"]["hy"] - a0["y"]) <= 1, b02b_mal["a0"]
    assert abs(b02b_mal["a0"]["x"] - b02b_mal["a0"]["hx"]) <= 40 and abs(b02b_mal["a0"]["y"] - b02b_mal["a0"]["hy"]) <= 40, b02b_mal["a0"]
    # dog:6 survived via its own valid entry; the fake kind-mismatched 'dog:6' probe at (400,400) was ignored
    assert b02b_mal["dog6"]["restored"], "dog:6 was not restored from its own snapshot entry"
    assert (abs(b02b_mal["dog6"]["x"] - 400) > 8 or abs(b02b_mal["dog6"]["y"] - 400) > 8), b02b_mal["dog6"]
    for i in (3, 4, 5, 6):   # NaN, solid, out-of-bounds, kind-mismatch entries were all ignored
        o, c = b02b_mal["orig"][f"chicken:{i}"], b02b_mal["cur"][f"chicken:{i}"]
        assert abs(c["x"] - o["x"]) > 60 or abs(c["y"] - o["y"]) > 60, (i, o, c)

    # Ordinary save/reload round-trip: clean snapshot, page reload (pagehide final
    # snapshot fires), then every animal must be back by id at a validated position.
    page.evaluate("() => { window.__worldLife.flushSave(); }")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.animals.length === 81")
    reload1 = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const byId = Object.fromEntries(W.animals.map(a => [a.id, { x: a.x, y: a.y, hx: a.homeX, hy: a.homeY }]));
      return { byId, total: W.animals.length, n: W.lastRestored.length, restored: W.lastRestored.slice().sort() };
    }""")
    assert reload1["total"] == 81 and reload1["n"] == 81, reload1["n"]
    assert reload1["restored"] == sorted(f"{k}:{i}" for k, n in EXPECTED_COUNTS.items() for i in range(n)), "reload did not restore the full baseline id set"
    for cid in controls:
        a = b02b_boot["anchored"][cid]
        r = reload1["byId"][cid]
        assert abs(r["hx"] - a["x"]) <= 1 and abs(r["hy"] - a["y"]) <= 1, (cid, r, a)
        assert abs(r["x"] - a["x"]) <= 60 and abs(r["y"] - a["y"]) <= 60, (cid, r, a)
    # The reloaded save already has playerName - a plain Enter resumes play.
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play' && __worldLife.animals.length === 81")
    page.evaluate("(a) => { const A = window.ARK; A.teleport(a.x - 140, a.y); }", b02b_boot["anchored"]["chicken:0"])
    page.wait_for_timeout(300)
    page.screenshot(path=str(SHOT_DIR / "b02b_reload_after.png"))

    # Second ordinary reload: pagehide flushed the first session's final snapshot;
    # the same ids must come back pinned again (no re-randomization, no duplication).
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.add_script_tag(url=URL.rsplit("/", 1)[0] + "/js/world-life.js")
    page.evaluate("window.dispatchEvent(new Event('ark-ready'))")
    page.wait_for_function("window.__worldLife && window.__worldLife.animals.length === 81")
    reload2 = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const byId = Object.fromEntries(W.animals.map(a => [a.id, { x: a.x, y: a.y, hx: a.homeX, hy: a.homeY }]));
      return { byId, total: W.animals.length, n: W.lastRestored.length, carsOk: W.cars.length === 2 && W.cars.every(c => !A.blocked(c.x, c.y)) };
    }""")
    assert reload2["total"] == 81 and reload2["n"] == 81, reload2["n"]
    assert reload2["carsOk"], "cars did not survive the second reload unchanged"
    for cid in controls:
        a = b02b_boot["anchored"][cid]
        r = reload2["byId"][cid]
        assert abs(r["hx"] - a["x"]) <= 1 and abs(r["hy"] - a["y"]) <= 1, (cid, r, a)
        assert abs(r["x"] - a["x"]) <= 60 and abs(r["y"] - a["y"]) <= 60, (cid, r, a)

    # ---- B04: friendly Frodo<->stray-dog greet with cooldown (no endless chase)
    # A pinned dog near Frodo greets once (sniff -> play hop -> return home), the
    # interaction resolves in bounded time, and while the cooldown is active the
    # dog never re-greets or tails Frodo even though he stays in range. Animal
    # ids/counts and the Q.worldLife payload stay byte-identical (no persistence).
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play' && __worldLife.animals.length === 81")
    b04 = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      A.teleport(A.MAP.spawn.x, A.MAP.spawn.y);
      // Build a clear arena around the spawn and park every non-dog far away.
      const free = (x, y) => x > 80 && x < A.MAP.w - 80 && y > 130 && y < A.MAP.h - 80 && !A.blocked(x, y);
      for (const a of W.animals) if (a.kind !== 'dog') { a.x = A.MAP.w - 200; a.y = A.MAP.h - 200; a.homeX = a.x; a.homeY = a.y; }
      const dog = W.animals.find(a => a.kind === 'dog');
      let spot = null;
      outer:
      for (let r = 60; r < 900; r += 24) for (let a = 0; a < Math.PI * 2; a += 0.4) {
        const x = A.MAP.spawn.x + Math.cos(a) * r, y = A.MAP.spawn.y + Math.sin(a) * r;
        if (free(x, y) && free(x + 90, y) && free(x - 90, y)) { spot = { x: Math.round(x), y: Math.round(y) }; break outer; }
      }
      if (!spot) throw new Error('B04: no clear arena spot');
      A.FRODO.x = spot.x; A.FRODO.y = spot.y;
      A.P.x = spot.x; A.P.y = spot.y;
      dog.x = spot.x + 50; dog.y = spot.y; dog.homeX = spot.x + 50; dog.homeY = spot.y;
      dog.tx = dog.x; dog.ty = dog.y; dog.wait = 999999;
      const idsBefore = W.animals.map(a => a.id).sort().join(',');
      const countsBefore = {};
      for (const a of W.animals) countsBefore[a.kind] = (countsBefore[a.kind] || 0) + 1;
      const wlKeysBefore = Object.keys(A.Q.worldLife).sort().join(',');
      W.resetInteractionCooldown('dog');
      let sniffSeen = false, playSeen = false, sayBubble = null, resolveSteps = 0;
      let reGreetPlay = 0, tailed = false, leaveHome = false;
      const startFd = Math.hypot(dog.x - A.FRODO.x, dog.y - A.FRODO.y);
      // Phase 1: 6 s of steps - greet must trigger and fully resolve
      // (sniff -> play -> return home), a bounded interaction.
      for (let i = 0; i < 120; i++) {
        W.stepInteractions(0.05);
        if (dog.sniffT > 0) sniffSeen = true;
        if (dog.playT > 0) playSeen = true;
        if (dog.say && !sayBubble) sayBubble = dog.say;
        if (dog.leaveT > 0 && dog.tx === dog.homeX && dog.ty === dog.homeY) leaveHome = true;
        if (!resolveSteps && !dog.sniffT && !dog.playT && !dog.leaveT && (sniffSeen || playSeen)) resolveSteps = i + 1;
      }
      const cdMid = dog.greetCdT || 0;
      const dMid = Math.hypot(dog.x - dog.homeX, dog.y - dog.homeY);
      // Phase 2: 3 s more with Frodo parked in greet range - the cooldown must
      // hold (no sniff/play restart, no endless tailing toward Frodo).
      const fx = A.FRODO.x, fy = A.FRODO.y;
      let nextFd = Math.hypot(dog.x - fx, dog.y - fy);
      for (let i = 0; i < 60; i++) {
        W.stepInteractions(0.05);
        if (dog.sniffT > 0 || dog.playT > 0) reGreetPlay++;
        const fd = Math.hypot(dog.x - fx, dog.y - fy);
        // tailing means the dog steadily reduced its distance to the parked Frodo
        if (fd < nextFd - 4) tailed = true;
        nextFd = fd;
      }
      const dEnd = Math.hypot(dog.x - dog.homeX, dog.y - dog.homeY);
      // Phase 3: mouse chase priority - a mouse near Frodo must still start and
      // keep a live chase while the dog is simultaneously greeting him.
      W.resetInteractionCooldown('dog');
      W.resetInteractionCooldown('mouse');
      const mouse = W.animals.find(a => a.kind === 'mouse');
      mouse.x = spot.x + 30; mouse.y = spot.y; mouse.homeX = mouse.x; mouse.homeY = mouse.y;
      dog.x = spot.x - 60; dog.y = spot.y; dog.homeX = dog.x; dog.homeY = dog.y; dog.wait = 999999;
      const chaseT0 = (A.FRODO.chase && A.FRODO.chase.t) || 0;
      const mouse0 = { x: mouse.x, y: mouse.y };
      let chased = false, chaseAlive = false, dogGreetedWhileChase = false;
      for (let i = 0; i < 20; i++) {
        W.stepInteractions(0.05);
        if (A.FRODO.chase && A.FRODO.chase.t > 0) chased = true;
        if (dog.sniffT > 0) dogGreetedWhileChase = true;
      }
      chaseAlive = !!(A.FRODO.chase && A.FRODO.chase.t > 0);
      const mouseMoved = Math.hypot(mouse.x - mouse0.x, mouse.y - mouse0.y);
      const idsAfter = W.animals.map(a => a.id).sort().join(',');
      const countsAfter = {};
      for (const a of W.animals) countsAfter[a.kind] = (countsAfter[a.kind] || 0) + 1;
      const wlKeysAfter = Object.keys(A.Q.worldLife).sort().join(',');
      const snapshotClean = !JSON.stringify(A.Q.worldLife.animals).includes('greetC') &&
                            !JSON.stringify(A.Q.worldLife.animals).includes('playT') &&
                            !JSON.stringify(A.Q.worldLife.animals).includes('sniffT');
      return { sniffSeen, playSeen, sayBubble, resolveSteps, cdMid,
               dMid, dEnd, startFd, reGreetPlay, tailed, leaveHome,
               chased, chaseAlive, dogGreetedWhileChase, mouseMoved,
               idsSame: idsBefore === idsAfter,
               countsSame: JSON.stringify(countsBefore) === JSON.stringify(countsAfter),
               wlKeysSame: wlKeysBefore === wlKeysAfter, snapshotClean };
    }""")
    assert b04["sniffSeen"], f"B04: dog never entered the greet (sniff) state: {b04}"
    assert b04["playSeen"], f"B04: greet had no play phase after sniff: {b04}"
    assert b04["sayBubble"], f"B04: no visible speech bubble during greet: {b04}"
    assert 0 < b04["resolveSteps"] <= 130, f"B04: interaction did not resolve in bounded time: {b04}"
    assert b04["cdMid"] > 0, f"B04: cooldown never started: {b04}"
    assert b04["reGreetPlay"] == 0, f"B04: dog re-greeted during cooldown ({b04['reGreetPlay']} frames)"
    assert b04["leaveHome"], f"B04: dog never headed home after the greet: {b04}"
    assert not b04["tailed"], f"B04: dog tailed Frodo during cooldown: {b04}"
    assert b04["dEnd"] <= b04["dMid"] + 40, f"B04: dog did not return home after greet: {b04}"
    assert b04["chased"], f"B04: mouse chase never started while dog was near: {b04}"
    assert b04["chaseAlive"], f"B04: dog greet killed the active mouse chase: {b04}"
    assert b04["dogGreetedWhileChase"], f"B04: dog did not greet during the mouse chase (scenario setup)"
    assert b04["mouseMoved"] > 10, f"B04: mouse did not flee during the chase: {b04}"
    assert b04["idsSame"] and b04["countsSame"], f"B04: animal ids/counts changed: {b04}"
    assert b04["wlKeysSame"] and b04["snapshotClean"], f"B04: Q.worldLife payload changed: {b04}"
    print(f"B04: greet={b04['sayBubble']} resolve={b04['resolveSteps']} steps, cooldown={b04['cdMid']:.1f}s, re-greet={b04['reGreetPlay']}, chaseAlive={b04['chaseAlive']}")
    assert not errors, errors
    print("world life: PASS", facts)
    browser.close()
