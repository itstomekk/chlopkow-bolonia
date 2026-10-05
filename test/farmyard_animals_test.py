"""Focused regression for domestic animal preference around real farmyard buildings.

Run with a docs server on port 8796, or set ARK_URL explicitly.
"""
import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8796/index.html")
SEED_JS = """
  let s = 246813579;
  Math.random = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
"""

INSPECT_JS = """
() => {
  const A = window.ARK, W = window.__worldLife;
  const buildings = (A.MAP.objects || []).filter(o => o.kind === 'yard_building');
  const domestic = W.animals.filter(a => a.kind === 'chicken' || a.kind === 'dog');
  const centers = [[4870, 5710], [5000, 6060]];
  const nearYard = a => centers.some(([x, y]) => Math.hypot(a.x - x, a.y - y) <= 280);
  const insideExpandedBuilding = a => buildings.some(o =>
    a.x >= o.x - 20 && a.x <= o.x + o.w + 20 &&
    a.y >= o.y - 20 && a.y <= o.base + 20);
  const awayFromBuildingFront = a => buildings.every(o =>
    Math.hypot(a.x - (o.x + o.w / 2), a.y - o.base) >= 20);
  const valid = a => Number.isFinite(a.x) && Number.isFinite(a.y) &&
    a.x >= 18 && a.x <= A.MAP.w - 18 && a.y >= (A.MAP.top || 40) + 18 &&
    a.y <= A.MAP.h - 18 && !A.blocked(a.x, a.y) &&
    !['road', 'track', 'forest'].includes(A.terrainAt(a.x, a.y));
  return {
    yardBuildingCount: buildings.length,
    domestic: domestic.map(a => ({ id: a.id, kind: a.kind, x: a.x, y: a.y })),
    nearYard: domestic.filter(nearYard).map(a => a.id),
    nearByKind: Object.fromEntries(['chicken', 'dog'].map(k => [k, domestic.filter(a => a.kind === k && nearYard(a)).length])),
    invalid: domestic.filter(a => !valid(a)).map(a => a.id),
    insideExpandedBuilding: domestic.filter(insideExpandedBuilding).map(a => a.id),
    atBuildingFront: domestic.filter(a => !awayFromBuildingFront(a)).map(a => a.id),
  };
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script(SEED_JS)
    page.goto(URL + ("&" if "?" in URL else "?") + "x=3606&y=1326")
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.ARK && window.__game", timeout=30000)
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Farmyard")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play' && window.__worldLife", timeout=30000)

    result = page.evaluate(INSPECT_JS)
    assert result["yardBuildingCount"] >= 10, result
    assert len(result["domestic"]) == 19, result
    assert len(result["nearYard"]) >= 4, result
    assert result["nearByKind"]["chicken"] >= 1, result
    assert result["nearByKind"]["dog"] >= 1, result
    assert not result["invalid"], result
    assert not result["insideExpandedBuilding"], result
    assert not result["atBuildingFront"], result
    assert len(result["nearYard"]) < 19, "domestic animals lost their rural scatter"

    saved = page.evaluate("""() => {
      const W = window.__worldLife, A = window.ARK;
      const animal = W.animals.find(a => a.kind === 'chicken' || a.kind === 'dog');
      A.save();
      W.flushSave();
      return { id: animal.id, x: animal.x, y: animal.y };
    }""")
    restored = page.evaluate("""(saved) => {
      const W = window.__worldLife;
      W.reloadAnimals();
      const animal = W.animals.find(a => a.id === saved.id);
      return { id: animal.id, x: animal.x, y: animal.y, restored: W.lastRestored.includes(saved.id) };
    }""", saved)
    assert restored["id"] == saved["id"]
    assert restored["restored"]
    assert restored["x"] == int(saved["x"]) and restored["y"] == int(saved["y"]), (saved, restored)
    assert not errors, errors
    print("farmyard animals: PASS", {
        "yardBuildings": result["yardBuildingCount"],
        "domestic": len(result["domestic"]),
        "nearDenseJ12": len(result["nearYard"]),
        "nearByKind": result["nearByKind"],
        "saveRestored": saved["id"],
    })
    browser.close()
