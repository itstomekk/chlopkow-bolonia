"""Browser regression test for pixel critters and animal interactions."""
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

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
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
    print("animals: PASS", {"animalRows": len(required_rows), "vehicleRows": len(VEHICLE_META["rows"]), "storksNearWater": facts["storksNearWater"], "mouseChase": facts["chase"], "interactions": len(facts["interactions"])})
    browser.close()
