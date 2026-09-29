"""Frodo remains with Arek during ordinary exploration."""
import os
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.add_init_script("""
        window.__frodoDraws = 0;
        const drawImage = CanvasRenderingContext2D.prototype.drawImage;
        CanvasRenderingContext2D.prototype.drawImage = function (image, ...args) {
            if (image && image.src && image.src.includes('/img/frodo.png')) window.__frodoDraws++;
            return drawImage.call(this, image, ...args);
        };
    """)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html"))
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game")
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")

    initial = page.evaluate("__game.FRODO && [__game.FRODO.x, __game.FRODO.y]")
    assert initial, "Frodo must be initialized when a new game starts"
    page.wait_for_function("window.__frodoDraws > 0")
    page.keyboard.down("ArrowRight")
    time.sleep(1.0)
    page.keyboard.up("ArrowRight")
    time.sleep(1.0)
    result = page.evaluate("({dog:[__game.FRODO.x,__game.FRODO.y], arek:[__game.P.x,__game.P.y]})")
    moved = ((result["dog"][0] - initial[0]) ** 2 + (result["dog"][1] - initial[1]) ** 2) ** .5
    gap = ((result["dog"][0] - result["arek"][0]) ** 2 + (result["dog"][1] - result["arek"][1]) ** 2) ** .5
    assert moved > 5, f"Frodo should move with Arek; moved {moved:.1f} map pixels"
    assert gap < 100, f"Frodo should stay nearby; distance is {gap:.1f} map pixels"

    # ---- B04: a dog greeting in a live session must not freeze Frodo, block the
    # Frodo->mouse chase, or change animal identity/count. Run in the open world
    # before the church check below (rooms are exited by walking, not by API).
    b04 = page.evaluate("""() => {
      const A = window.ARK, W = window.__worldLife;
      const free = (x, y) => x > 80 && x < A.MAP.w - 80 && y > 130 && y < A.MAP.h - 80 && !A.blocked(x, y);
      const dog = W.animals.find(a => a.kind === 'dog');
      const mouse = W.animals.find(a => a.kind === 'mouse');
      const idsBefore = W.animals.map(a => a.id).sort().join(',');
      const nBefore = W.animals.length;
      let spot = null;
      for (let r = 40; r < 600; r += 24) for (let a = 0; a < Math.PI * 2; a += 0.5) {
        const x = A.P.x + Math.cos(a) * r, y = A.P.y + Math.sin(a) * r;
        if (free(x, y) && free(x + 70, y) && free(x - 70, y)) { spot = { x: Math.round(x), y: Math.round(y) }; break; }
      }
      if (!spot) throw new Error('B04: no arena near player');
      A.teleport(spot.x, spot.y);        // Arek must stay near Frodo for the chase/routines to run
      A.FRODO.x = spot.x; A.FRODO.y = spot.y;
      dog.x = spot.x + 40; dog.y = spot.y; dog.homeX = spot.x + 40; dog.homeY = spot.y; dog.wait = 1e9;
      mouse.x = spot.x + 24; mouse.y = spot.y - 6; mouse.homeX = mouse.x; mouse.homeY = mouse.y; mouse.wait = 1e9;
      W.resetInteractionCooldown('dog');
      W.resetInteractionCooldown('mouse');
      return { ids: idsBefore, n: nBefore, spot };
    }""")
    # Live frames: the dog's greet and the mouse chase both play out; sample a few
    # times because the mouse flees and the chase window (2.4 s) is short.
    sample = []
    for _ in range(4):
        page.wait_for_timeout(400)
        sample.append(page.evaluate(
            """() => {
      const A = window.ARK, W = window.__worldLife;
      const dog = W.animals.find(a => a.kind === 'dog');
      return {
        dogGreeted: (dog.sayT || 0) > 0 || (dog.playT > 0) || (dog.greetCdT > 0) || dog.say === 'hau!',
        mouseChase: !!(A.FRODO.chase && A.FRODO.chase.t > 0),
        stillFollowing: Math.hypot(A.FRODO.x - A.P.x, A.FRODO.y - A.P.y) < 200,
      };
    }"""))
    livecheck = page.evaluate(
        """(data) => {
      const A = window.ARK, W = window.__worldLife;
      const idsNow = W.animals.map(a => a.id).sort().join(',');
      return { idsSame: idsNow === data.ids, nSame: W.animals.length === data.n };
    }""", {"ids": b04["ids"], "n": b04["n"]})
    assert livecheck["idsSame"] and livecheck["nSame"], f"B04 live: animal ids/count changed: {livecheck}"
    assert any(s["dogGreeted"] for s in sample), f"B04 live: dog never greeted Frodo: {sample}"
    assert any(s["mouseChase"] for s in sample), f"B04 live: Frodo->mouse chase did not start: {sample}"
    assert all(s["stillFollowing"] for s in sample), f"B04 live: Frodo left Arek: {sample}"
    # original church-follow check, kept last (rooms are exited by walking)
    page.evaluate("__game.enterChurch()")
    page.wait_for_function("__game.room")
    room_gap = page.evaluate("Math.hypot(__game.FRODO.x-__game.P.x,__game.FRODO.y-__game.P.y)")
    assert room_gap < 100, f"Frodo should enter the church with Arek; distance is {room_gap:.1f} map pixels"
    assert not errors, f"Browser errors: {errors}"
    print(f"Frodo follow check passed: moved {moved:.1f}px, outdoor gap {gap:.1f}px, church gap {room_gap:.1f}px; "
          f"B04 dog greet ✓ mouse chase ✓ Frodo stays with Arek ✓")
    browser.close()
