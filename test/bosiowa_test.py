"""BOSIOWA selector, 4-frame pixel walk sheet, fixed NPC beside the buildings at Kasia's home and dialogue regression."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"
OFFSETS = [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]]


def wait_ready(page):
    page.wait_for_function("window.__game", timeout=30000)
    page.wait_for_function("window.__bosiowa && window.__bosiowa.installed", timeout=30000)


def center(page, character):
    point = page.evaluate("character => __game.characterButtonCenter(character)", character)
    assert point is not None, f"missing selector button: {character}"
    return point


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    wait_ready(page)

    # Her selector button exists next to the older ones and BOSIOWA persists on desktop.
    for character in ("arek", "bercik", "wiesio", "iwona", "bosiowa"):
        center(page, character)
    page.mouse.click(*center(page, "bosiowa"))
    assert page.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == "bosiowa"
    page.reload()
    wait_ready(page)
    assert page.evaluate("__game.playerCharacter") == "bosiowa"
    page.mouse.click(*center(page, "bosiowa"))

    # Mobile tap hits the same button and stays on the title screen.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    wait_ready(mobile)
    mobile.touchscreen.tap(*center(mobile, "bosiowa"))
    assert mobile.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == "bosiowa"
    assert mobile.evaluate("__game.scene") == "title"
    mobile.close()

    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "bosiowa"
    assert page.evaluate("__game.playerSheetName") == "bosiowa_sheet.png"

    # Exactly one fixed BOSIOWA, reachable, beside the buildings next to Kasia's home.
    npc = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'bosiowa')")
    assert len(npc) == 1, npc
    pos = npc[0]
    target = page.evaluate("__bosiowa.target")
    assert target == {"x": 3790, "y": 4950}, target
    home = page.evaluate("__bosiowa.kasiaHome")
    assert ((pos["x"] - home["x"]) ** 2 + (pos["y"] - home["y"]) ** 2) ** .5 <= 240, (pos, home)
    assert page.evaluate("__bosiowa.position().terrain") not in ("field", "forest")
    assert ((pos["x"] - target["x"]) ** 2 + (pos["y"] - target["y"]) ** 2) ** .5 <= 140, (pos, target)
    assert page.evaluate("({x, y}) => __game.isSpawnReachable(x, y)", pos)
    info = page.evaluate("__bosiowa.position()")
    print("BOSIOWA placed at", info)

    # The player renderer uses all four distinct frames per row, without smoothing.
    page.evaluate("() => { const n = __bosiowa.position(); ARK.teleport(n.x - 40, n.y); }")
    page.wait_for_function("!('heroShade' in __game) || __game.heroShade < .01")
    page.evaluate("""() => {
        const ctx = ARK.ctx, draw = ctx.drawImage.bind(ctx);
        window.__bosiowaDraws = [];
        ctx.drawImage = (...args) => {
            if (args[0] && args[0].src && args[0].src.endsWith('/bosiowa_sheet.png'))
                __bosiowaDraws.push({x: args[1], y: args[2], smooth: ctx.imageSmoothingEnabled});
            return draw(...args);
        };
    }""")
    # Walk with real key presses; every direction must cycle through all four frames.
    origin = page.evaluate("() => ({x: __game.P.x, y: __game.P.y})")
    expected_rows = {"ArrowDown": 0, "ArrowUp": 170, "ArrowLeft": 340, "ArrowRight": 510}
    for key, row in expected_rows.items():
        page.evaluate("({x, y}) => ARK.teleport(x, y)", origin)
        page.evaluate("() => { __bosiowaDraws.length = 0; }")
        page.keyboard.down(key)
        page.wait_for_timeout(1600)
        page.keyboard.up(key)
        draws = page.evaluate("__bosiowaDraws")
        assert draws and all(not d["smooth"] for d in draws), (key, draws[:5])
        frames = {d["x"] for d in draws if d["y"] == row}
        assert frames == {0, 130, 260, 390}, (key, sorted(frames), sorted({(d["x"], d["y"]) for d in draws})[:12])

    # Space next to him opens his dialogue.
    stand = page.evaluate(
        """({x, y}) => {
            for (const [dx, dy] of %s) {
                const sx = x + dx, sy = y + dy;
                if (!__game.blocked(sx, sy)) return {x: sx, y: sy};
            }
            return null;
        }""" % OFFSETS,
        pos,
    )
    assert stand is not None, "no adjacent walkable interaction point"
    page.evaluate("({x, y}) => window.ARK.teleport(x, y)", stand)
    page.keyboard.press("Space")
    page.wait_for_function("__game.talk && __game.talk.who === 'bosiowa'")
    lines = page.evaluate("__game.talk.lines.join(' ')")
    assert "królowa pieczarek" in lines, lines

    # Reload keeps one fixed BOSIOWA at the same deterministic spot.
    page.reload()
    wait_ready(page)
    restored = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'bosiowa')")
    assert len(restored) == 1 and restored[0]["x"] == pos["x"] and restored[0]["y"] == pos["y"], (restored, pos)
    assert not errors, errors

    browser.close()
    print("BOSIOWA regression passed: selector desktop/mobile, 4-frame pixel sheet, fixed reachable NPC by Kasia's home, Space dialogue, reload")
