"""BERCIK selector, playable sprite directions, fixed J12 NPC and dialogue regression."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"
J12 = {"x0": 4608, "x1": 5119, "y0": 5632, "y1": 6143}


def wait_ready(page):
    page.wait_for_function("window.__game", timeout=30000)


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

    # Desktop selector persistence, including all normal existing choices.
    for character in ("arek", "marcin", "damian", "edytka", "renik", "bercik"):
        page.mouse.click(*center(page, character))
        assert page.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == character
    page.reload()
    wait_ready(page)
    assert page.evaluate("__game.playerCharacter") == "bercik"
    page.mouse.click(*center(page, "bercik"))

    # Mobile tap persistence must use the same selector hit targets and remain on title.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    wait_ready(mobile)
    mobile.touchscreen.tap(*center(mobile, "damian"))
    assert mobile.evaluate("localStorage.getItem('arek-chlopkow-character-v1')") == "damian"
    assert mobile.evaluate("__game.scene") == "title"
    mobile.touchscreen.tap(*center(mobile, "bercik"))
    assert mobile.evaluate("localStorage.getItem('arek-chlopkow-character-v1')") == "bercik"
    assert mobile.evaluate("__game.scene") == "title"
    mobile.close()

    # Fresh game uses the canonical Bercik sheet, including exact cardinal and diagonal fallback.
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "bercik"
    assert page.evaluate("__game.playerSheetName") == "bercik_sheet.png"
    assert page.evaluate("__bercik.directionFrames()") == {
        "down": "walk_down",
        "up": "walk_up",
        "left": "walk_left",
        "right": "walk_right",
        "down_right": "walk_right",
        "down_left": "walk_down",
        "up_right": "walk_up",
        "up_left": "walk_left",
    }

    # Observe the actual renderer on the open J12 track (not the forest-tint canvas).
    page.evaluate("() => { const n = __bercik.position(); ARK.teleport(n.x - 28, n.y); }")
    page.wait_for_function("!('heroShade' in __game) || __game.heroShade < .01")
    page.evaluate("""() => {
        const ctx = ARK.ctx, draw = ctx.drawImage.bind(ctx);
        window.__bercikDraws = [];
        ctx.drawImage = (...args) => {
            if (args[0] && args[0].src && args[0].src.endsWith('/bercik_sheet.png'))
                __bercikDraws.push({x: args[1], y: args[2], smooth: ctx.imageSmoothingEnabled});
            return draw(...args);
        };
    }""")
    expected_rows = {"down": 0, "up": 170, "left": 340, "right": 510,
                     "down_right": 510, "down_left": 0, "up_right": 170, "up_left": 340}
    for direction, row in expected_rows.items():
        page.evaluate("d => { __game.P.dir = d; __bercikDraws.length = 0; }", direction)
        page.wait_for_function("__bercikDraws.length > 0")
        draws = page.evaluate("__bercikDraws")
        assert all(d["y"] == row and not d["smooth"] for d in draws), (direction, draws)

    # There is exactly one fixed Bercik in J12, on walkable terrain reachable from spawn.
    npc = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'bercik')")
    assert len(npc) == 1, npc
    pos = npc[0]
    assert J12["x0"] <= pos["x"] <= J12["x1"] and J12["y0"] <= pos["y"] <= J12["y1"], pos
    assert page.evaluate("({x, y}) => [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]].some(([dx, dy]) => !__game.blocked(x + dx, y + dy))", {"x": pos["x"], "y": pos["y"]})
    assert page.evaluate("({x, y}) => __game.isSpawnReachable(x, y)", {"x": pos["x"], "y": pos["y"]})
    assert page.evaluate("__bercik.position().sector") == "J12"

    # Move to a real adjacent walkable point and use the game's Space interaction path.
    stand = page.evaluate(
        """({x, y}) => {
            for (const [dx, dy] of [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]]) {
                const sx = x + dx, sy = y + dy;
                if (!__game.blocked(sx, sy) && Math.hypot(sx - x, sy - y) < 42) return {x: sx, y: sy};
            }
            return null;
        }""",
        {"x": pos["x"], "y": pos["y"]},
    )
    assert stand is not None, "no adjacent walkable interaction point"
    page.evaluate("({x, y}) => window.ARK.teleport(x, y)", stand)
    page.keyboard.press("Space")
    page.wait_for_function("__game.talk && __game.talk.who === 'bercik'")
    assert page.evaluate("__game.talk.lines.join(' ')")

    # A reload cannot restore or wander the fixed NPC outside J12.
    page.reload()
    wait_ready(page)
    restored = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'bercik')")
    assert len(restored) == 1, restored
    assert page.evaluate("__bercik.position().sector") == "J12"
    assert page.evaluate("({x, y}) => [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]].some(([dx, dy]) => !__game.blocked(x + dx, y + dy))", restored[0])
    assert not errors, errors

    browser.close()
    print("BERCIK regression passed: desktop/mobile selector, sheet directions, fixed reachable J12 NPC, Space dialogue, reload persistence")
