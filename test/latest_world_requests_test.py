"""Regression checks for the latest NPC, venue, weather and vehicle requests."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
items = json.loads((ROOT / "docs/items.json").read_text(encoding="utf-8"))
map_data = json.loads((ROOT / "docs/map.json").read_text(encoding="utf-8"))
npcs = {n["id"]: n for n in items["npcs"]}
jazz = map_data["jazz"]
assert (npcs["edytka"]["x"], npcs["edytka"]["y"]) == (120, 3869)
assert (npcs["wesoly_swiat"]["x"], npcs["wesoly_swiat"]["y"]) == (1692, 650)
# DJ Renik stands by the football pitch POI.
pitch = map_data["football_pitch"]
assert abs(npcs["renik"]["x"] - pitch["cx"]) < 200 and abs(npcs["renik"]["y"] - pitch["cy"]) < 200, (npcs["renik"], pitch)
assert 2850 <= jazz["x"] <= 3150 and 2500 <= jazz["y"] <= 2800 and jazz["r"] == 140

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game && window.__worldLife")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.__worldLife")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Nowosci")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    facts = page.evaluate("""() => ({
      forest: __game.terrainAt(1692, 650),
      npcCount: __game.ITEMS.npcs.filter(n => ['michal','patryk','wesoly_swiat'].includes(n.id)).length,
      noTrashNpc: !__game.ITEMS.npcs.some(n => n.id === 'mateusz'),
      trashSpots: (__game.Q.trashSpots || []).length,
      trashFixed: ['cemetery', 'southshop'].every(k => { const t = __game.ITEMS.trash.find(v => v.id === k); return (__game.Q.trashSpots || []).some(p => p.x === t.x && p.y === t.y); }),
      trashReachable: (__game.Q.trashSpots || []).every(p => __game.isSpawnReachable(p.x, p.y)),
      cloudCount: __game.cloudCount,
      tractors: __worldLife.tractors.length,
      // blocked() also counts NPC bodies (±12,±6), so probe just below his feet; plus flood-fill reachability
      renikBlocked: (() => { const r = __game.ITEMS.npcs.find(n => n.id === 'renik'); return __game.blocked(r.x, r.y + 10) || !__game.isSpawnReachable(r.x, r.y); })(),
      renikTalk: (() => { __game.talkTo('renik'); const t = __game.talk; return !!(t && JSON.stringify(t).toLowerCase().includes('disco polo')); })()
    })""")
    assert facts == {"forest": "forest", "npcCount": 3, "noTrashNpc": True, "trashSpots": 12, "trashFixed": True, "trashReachable": True,
                     "cloudCount": 7, "tractors": 2, "renikBlocked": False, "renikTalk": True}, facts

    # Trash bags are collected by walking over them, exactly like apples and mushrooms.
    for _ in range(6):   # close DJ Renik's dialogue (Space advances / closes, as in mushroom_test.py)
        if not page.evaluate("!!__game.talk"): break
        page.keyboard.press("Space"); page.wait_for_timeout(120)
    assert not page.evaluate("!!__game.talk")
    page.evaluate("const t = __game.Q.trashSpots[0]; __game.P.x = t.x; __game.P.y = t.y")
    page.wait_for_function("__game.Q.trash.length === 1", timeout=3000)
    page.evaluate("const t = __game.Q.trashSpots[1]; __game.P.x = t.x; __game.P.y = t.y")
    page.wait_for_function("__game.Q.trash.length === 2", timeout=3000)
    saved = page.evaluate("JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).Q.trash")
    assert saved == [0, 1], saved
    # Reload keeps the collected bags and the same spots.
    spots = page.evaluate("JSON.stringify(__game.Q.trashSpots)")
    page.reload()
    page.wait_for_function("window.__game && window.__game.Q")
    assert page.evaluate("JSON.stringify(__game.Q.trashSpots)") == spots
    assert page.evaluate("__game.Q.trash") == [0, 1]
    assert not errors, errors
    browser.close()
print("latest world requests: PASS", facts)
