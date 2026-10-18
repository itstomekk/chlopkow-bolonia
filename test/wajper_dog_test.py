"""WAJPER: ?dog=wajper swaps the companion dog's sprites, label and idle routines; ?dog=frodo switches back.
Run: python test/isolated_browser_runner.py test/wajper_dog_test.py   (needs the docs/ server on :8765)"""
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
OUT = os.path.join(os.path.dirname(__file__), "wajper_dog.png")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.add_init_script("""
        window.__dogDraws = {};
        const drawImage = CanvasRenderingContext2D.prototype.drawImage;
        CanvasRenderingContext2D.prototype.drawImage = function (image, ...args) {
            const m = image && image.src && image.src.match(/img\\/(frodo[^/]*|wajper[^/]*)\\.png/);
            if (m) { window.__dogDraws[m[1]] = (window.__dogDraws[m[1]] || 0) + 1;
                     const t = this.getTransform(); window.__dogAt = [t.a * args[4] + t.e, t.d * args[5] + t.f, Math.abs(t.a * args[6])]; }
            return drawImage.call(this, image, ...args);
        };
    """)
    page.goto(BASE)
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?dog=wajper")
    page.wait_for_function("window.__game")
    assert page.evaluate("window.CHLOPKOW_DOG.id") == "wajper"
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test"); page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'")
    page.wait_for_function("(window.__dogDraws.wajper_walk4 || 0) > 0", timeout=15000)
    assert not page.evaluate("window.__dogDraws.frodo"), "Frodo's walk sheet must not be drawn when WAJPER is chosen"

    # every WAJPER idle routine draws from the pose strip; screenshot a few around the dog
    shots = []
    for action in ["pant", "yawn", "tilt", "shake", "dig", "wag", "sleep", "belly"]:
        page.evaluate("""a => { const F = __game.FRODO; F.x = __game.P.x; F.y = __game.P.y + 42; __game.P.dir = 'up'; F.chase = null; F.routine = a; F.routineT = 99;
                         F.idleAnim = 1; F.action = a; F.dir = 'right'; F.moving = false; F.wander = 0; F.wanderWait = 99; }""", action)
        before = page.evaluate("window.__dogDraws.wajper_poses || 0")
        page.wait_for_timeout(350)
        now = page.evaluate("[window.__dogDraws.wajper_poses || 0, __game.FRODO.action]")
        assert now[0] > before, f"{action}: pose strip not drawn ({now})"
        at = page.evaluate("window.__dogAt")
        box = page.evaluate("(() => { const r = document.getElementById('game').getBoundingClientRect(); const c = document.getElementById('game'); return [r.left, r.top, r.width / c.width]; })()")
        x = box[0] + (at[0] + at[2] / 2) * box[2]; y = box[1] + (at[1] + at[2] / 2) * box[2]
        page.screenshot(path=OUT.replace('.png', f'_{action}.png'), clip={"x": x - 70, "y": y - 70, "width": 140, "height": 140})
        shots.append(action)
    page.screenshot(path=OUT)

    page.goto(BASE + "?dog=frodo")
    page.wait_for_function("window.__game")
    assert page.evaluate("window.CHLOPKOW_DOG.id") == "frodo"
    assert page.evaluate("localStorage.getItem('chlopkow_dog')") == "frodo"
    assert not errors, errors
    print("WAJPER dog check passed: walk4 + poses drawn for", ", ".join(shots), "; ?dog=frodo switches back")
    browser.close()
