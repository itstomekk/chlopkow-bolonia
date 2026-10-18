"""ZOSIA: NPC-only wide pixel sheet (bike), placed ~1 km north of the cemetery near JAZZ W STODOLE,
wanders around her home, Space dialogue, reload keeps one ZOSIA."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
OFFSETS = [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]]


def wait_ready(page):
    page.wait_for_function("window.__game", timeout=30000)
    page.wait_for_function("window.__zosia && window.__zosia.installed", timeout=30000)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    http_errors = []
    page.on("response", lambda response: http_errors.append((response.status, response.url)) if response.status >= 400 else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function("window.__game", timeout=30000)
    page.evaluate("localStorage.clear()")
    page.reload()
    wait_ready(page)

    # NPC only: no selector button.
    assert page.evaluate("__game.characterButtonCenter('zosia')") is None

    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")

    npc = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'zosia')")
    assert len(npc) == 1, npc
    target = page.evaluate("__zosia.target")
    assert target == {"x": 2600, "y": 1616}, target  # cemetery (2558, 3616) + 1 km north, nudged east
    home = page.evaluate("__zosia.home")
    assert ((home["x"] - target["x"]) ** 2 + (home["y"] - target["y"]) ** 2) ** .5 <= 220, (home, target)
    jazz = page.evaluate("__game.MAP.jazz")
    assert ((home["x"] - jazz["x"]) ** 2 + (home["y"] - jazz["y"]) ** 2) ** .5 < 500, (home, jazz)
    assert page.evaluate("({x, y}) => __game.isSpawnReachable(x, y)", home)
    print("ZOSIA home", home, page.evaluate("__zosia.position()"))

    # She wanders: within ~6 s she moves, and stays inside her wander radius (+ slack).
    start = page.evaluate("__zosia.position()")
    page.wait_for_function(
        "({x, y}) => { const p = __zosia.position(); return Math.hypot(p.x - x, p.y - y) > 4; }",
        arg=start, timeout=12000)
    for _ in range(6):
        page.wait_for_timeout(500)
        pos = page.evaluate("__zosia.position()")
        assert ((pos["x"] - home["x"]) ** 2 + (pos["y"] - home["y"]) ** 2) ** .5 <= 130, (pos, home)

    # Drawn from the wide (160 px) sheet without smoothing.
    page.evaluate("() => { const n = __zosia.position(); ARK.teleport(n.x - 60, n.y); }")
    page.evaluate("""() => {
        const ctx = ARK.ctx, draw = ctx.drawImage.bind(ctx);
        window.__zosiaDraws = [];
        ctx.drawImage = (...args) => {
            if (args[0] && args[0].src && args[0].src.endsWith('/zosia_sheet.png'))
                __zosiaDraws.push({x: args[1], y: args[2], w: args[3], smooth: ctx.imageSmoothingEnabled});
            return draw(...args);
        };
    }""")
    page.wait_for_timeout(1500)
    draws = page.evaluate("__zosiaDraws")
    assert draws and all(not d["smooth"] and d["w"] == 160 for d in draws), draws[:5]

    # Space next to her opens her dialogue (freeze her first so she does not walk off).
    page.evaluate("() => { const n = ARK.ITEMS.npcs.find(v => v.id === 'zosia'); n.x = __zosia.home.x; n.y = __zosia.home.y; }")
    pos = page.evaluate("__zosia.home")
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
    page.wait_for_function("__game.talk && __game.talk.who === 'zosia'")
    lines = page.evaluate("__game.talk.lines.join(' ')")
    assert "Zosia" in lines and "grzyby" in lines, lines

    page.reload()
    wait_ready(page)
    restored = page.evaluate("__game.ITEMS.npcs.filter(n => n.id === 'zosia')")
    assert len(restored) == 1, restored
    assert page.evaluate("__zosia.home") == home
    assert not errors, errors
    assert not http_errors, http_errors

    browser.close()
    print("ZOSIA regression passed: NPC-only wide sheet, home north of the cemetery near JAZZ, wandering, dialogue, reload")
