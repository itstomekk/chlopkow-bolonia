"""Headless test for the hidden Sołtys encounter by the Białka woodland path."""
import time
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_function("window.__game && window.CHURCH_ART?.soltys", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.CHURCH_ART?.soltys")
    page.keyboard.press("Enter")
    time.sleep(.2)

    npc = page.evaluate("__game.ITEMS.npcs.find(n => n.id === 'soltys' && n.secret)")
    assert npc, "the secret Sołtys should be listed as hidden data, not a marked quest NPC"
    assert (npc["x"], npc["y"]) == (1760, 1600), npc
    assert page.evaluate("""n => { for (let r = 24; r <= 38; r += 2) for (let a = 0; a < 6.28; a += .3) if (!__game.blocked(n.x + Math.cos(a) * r, n.y + Math.sin(a) * r)) return true; return false; }""", npc), "the chosen path point must have a walkable interaction tile"

    # Stand beside him using a collision-free neighboring tile, then interact.
    page.evaluate("""n => {
      const g = __game;
      for (let r = 24; r <= 38; r += 2) for (let a = 0; a < 6.28; a += .3) {
        const x = n.x + Math.cos(a) * r, y = n.y + Math.sin(a) * r;
        if (!g.blocked(x, y)) { g.P.x = x; g.P.y = y; return; }
      }
      throw new Error('no walkable interaction tile beside the secret Sołtys');
    }""", npc)
    page.keyboard.press("KeyE")
    page.wait_for_function("__game.talk && __game.talk.who === 'soltys'", timeout=5000)
    line = page.evaluate("__game.talk.lines[0]")
    assert line, "the secret encounter should have an optional dialogue line"
    assert page.evaluate("!!window.CHURCH_ART.soltys"), "the generated church Sołtys sprite should be reused"
    page.screenshot(path="C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/soltys_surprise.png")
    assert not errors, errors
    print("secret Sołtys OK", npc, line, "errors", errors)
    browser.close()
