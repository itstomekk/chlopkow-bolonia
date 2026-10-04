"""Sept 28 batch (game.js / music.js / minigames.js side):
hero name everywhere, 5 trash bags, edge-only direction signs, map closes on an outside click + hover labels,
Polka Dziadek follows the walking tempo, Frodo keeps his position (save/reload, no teleport in view),
pushable hay bales, pitch unmown by default (lines only after mowing), pixel apple/mushroom.
Run: python test/sept28_batch_test.py  (dev server on http://127.0.0.1:8765)"""
import os
import sys
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
fails = []


def check(name, ok, info=""):
    if not ok:
        fails.append(f"{name}: {info}")


def start(page, name="ZOSIA", query=""):
    page.goto(URL + query)
    page.wait_for_function("window.__game")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.ARK")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill(name)
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    page.wait_for_timeout(300)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    start(page)

    # 1. hero name replaces "Arek" in dialogue and toasts (all Polish forms, any case)
    hero = page.evaluate("""() => [
      ARK.heroText('Dziękuję, Arek.'), ARK.heroText('FRODO UCIEKŁ DO AREKA!'), ARK.heroText('Daj to Arkowi, z Arkiem, o Arku'),
      ARK.heroText('arek-chlopkow-save-v1'), ARK.heroText('Marek i Jarek')]""")
    check("heroText", hero == ["Dziękuję, ZOSIA.", "FRODO UCIEKŁ DO ZOSIA!", "Daj to ZOSIA, z ZOSIA, o ZOSIA", "arek-chlopkow-save-v1", "Marek i Jarek"], hero)
    page.evaluate("ARK.popToast('Arek dostaje oranżadę!')")
    check("toast name", page.evaluate("__game.toastText") == "ZOSIA dostaje oranżadę!", page.evaluate("__game.toastText"))

    # 2. trash: exactly 5 bags on the board
    check("trash 5", page.evaluate("__game.Q.trashSpots.length") == 5, page.evaluate("__game.Q.trashSpots.length"))

    # 3. direction signs only at the board's edges
    mid = page.evaluate("ARK.teleport(__game.MAP.w / 2, __game.MAP.h / 2)")
    page.wait_for_timeout(250)
    vis_mid = page.evaluate("__game.directionSignVisibility")
    check("signs hidden mid-map", vis_mid["left"] == 0 and vis_mid["right"] == 0, vis_mid)
    page.evaluate("""() => { const M = __game.MAP; for (let x = 40; x < 600; x += 8) for (let y = M.h / 2; y < M.h - 50; y += 24) if (!__game.blocked(x, y)) { ARK.teleport(x, y); return; } }""")
    page.wait_for_timeout(400)
    vis_w = page.evaluate("__game.directionSignVisibility")
    check("DUŃCY at west edge", vis_w["left"] > .9 and vis_w["right"] == 0, vis_w)
    page.evaluate("""() => { const M = __game.MAP; for (let x = M.w - 40; x > M.w - 600; x -= 8) for (let y = M.h / 2; y < M.h - 50; y += 24) if (!__game.blocked(x, y)) { ARK.teleport(x, y); return; } }""")
    page.wait_for_timeout(400)
    vis_e = page.evaluate("__game.directionSignVisibility")
    check("LITWA at east edge", vis_e["right"] > .9 and vis_e["left"] == 0, vis_e)

    # 4. map overlay: hover labels + click outside closes it
    page.evaluate("ARK.teleport(__game.MAP.football_pitch.cx + 80, __game.MAP.football_pitch.cy + 120)")
    page.keyboard.press("KeyM")
    check("map open", page.evaluate("__game.showMap") is True)
    labels = page.evaluate("""() => { const f = __game.MAP.football_pitch, r = __game.ITEMS.npcs.find(n => n.id === 'renik');
      return [__game.mapHoverLabel(__game.P.x, __game.P.y), __game.mapHoverLabel(f.cx, f.cy - 60), __game.mapHoverLabel(r.x, r.y, 20), __game.mapHoverLabel(__game.MAP.w / 2, __game.MAP.h / 2)] }""")
    check("hover labels", labels[0] == "ZOSIA" and labels[1] == "BOISKO" and labels[2] == "DJ RENIK" and bool(labels[3]), labels)
    page.mouse.click(15, 360)   # left margin, outside the map
    page.wait_for_timeout(100)
    check("click outside closes map", page.evaluate("__game.showMap") is False)

    # 5. Polka Dziadek is the entrance screen only; the village playlist slows to a 0.5x floor
    rate = page.evaluate("MUSIC.MAIN_RATE_MIN")
    check("main track rate floor", rate == .5, rate)

    # 6. Frodo keeps his position across save/reload and never jumps while on screen
    page.evaluate("ARK.teleport(__game.MAP.football_pitch.cx + 80, __game.MAP.football_pitch.cy + 120)")
    page.wait_for_function("Math.hypot(ARK.FRODO.x - ARK.P.x, ARK.FRODO.y - ARK.P.y) < 90", timeout=15000)
    page.wait_for_timeout(500)
    before = page.evaluate("[ARK.FRODO.x, ARK.FRODO.y]")
    page.evaluate("ARK.save()")
    page.reload()
    page.wait_for_function("window.ARK && ARK.FRODO")
    after = page.evaluate("[ARK.FRODO.x, ARK.FRODO.y]")
    check("frodo restored after reload", abs(before[0] - after[0]) < 1 and abs(before[1] - after[1]) < 1, (before, after))
    page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    jumps = page.evaluate("""() => new Promise(done => {
      let last = [ARK.FRODO.x, ARK.FRODO.y], maxStep = 0, n = 0;
      const keys = ['KeyD', 'KeyS', 'KeyA', 'KeyW'];
      const tick = () => {
        const f = ARK.FRODO, d = Math.hypot(f.x - last[0], f.y - last[1]); maxStep = Math.max(maxStep, d); last = [f.x, f.y];
        if (++n % 45 === 0) { ARK.keys.clear(); ARK.keys.add(keys[(n / 45) % 4 | 0]); }
        if (n < 360) requestAnimationFrame(tick); else { ARK.keys.clear(); done(maxStep); }
      };
      ARK.keys.add('KeyD'); requestAnimationFrame(tick);
    })""")
    check("frodo moves continuously", jumps < 12, jumps)

    # 7. Frodo chase contract used by world-life.js
    chased = page.evaluate("""() => new Promise(done => {
      const f = ARK.FRODO, tx = f.x + 60, ty = f.y; const d0 = Math.hypot(tx - f.x, ty - f.y);
      f.chase = { x: tx, y: ty, t: 2 };
      setTimeout(() => { const d1 = Math.hypot(tx - f.x, ty - f.y); f.chase = null; done([d0, d1]); }, 500);
    })""")
    check("frodo chases target", chased[1] < chased[0] - 20, chased)

    # 8. hay bales: dynamic, pushed by walking into them
    bales = page.evaluate("ARK.MAP.bales ? ARK.MAP.bales.length : -1")
    if bales > 0:
        page.evaluate("""() => new Promise(done => {
          const M = ARK.MAP.bales[0];
          ARK.teleport(M.x - 30, M.y); ARK.P.dir = 'right'; ARK.keys.add('KeyD');
          setTimeout(() => { ARK.keys.clear(); done(true); }, 900);
        })""")
        dist = page.evaluate("__game.baleMoved()")
        check("bale pushed", dist > 5, dist)
    else:
        check("MAP.bales exported", False, bales)

    # 9. pitch: unmown by default, mown + lines only after the mowing minigame is won
    pitch = page.evaluate("__game.pitchState()")
    check("pitch default unmown", pitch == "unmown", pitch)
    page.evaluate("ARK.Q.mg.mowing = { tries: 1, won: true, medal: 1, best: 30 }")
    check("pitch mown after win", page.evaluate("__game.pitchState()") == "mown")

    check("no page errors", not errors, errors)
    browser.close()

if fails:
    print("sept28 batch: FAIL")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("sept28 batch: PASS")
