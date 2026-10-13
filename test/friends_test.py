"""KOSTEK, PAWEŁ, DAREK, PIEKARZ, MAREK, WALDEK: selector, pixel walk sheets, fixed reachable NPCs and dialogue."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8847/index.html")
CHARACTER_KEY = "arek-chlopkow-character-v1"
FRIENDS = ("kostek", "pawel", "darek", "piekarz", "marek", "waldek")
ALL = ("arek", "marcin", "damian", "edytka", "renik", "bercik", "wiesio", "iwona") + FRIENDS
OFFSETS = [[-28, 0], [28, 0], [0, -28], [0, 28], [-24, -18], [24, -18]]
LINE = {"kostek": "Kostek", "pawel": "Paweł", "darek": "Darek", "piekarz": "Piekarz", "marek": "Marek", "waldek": "Waldek"}


def wait_ready(page):
    page.wait_for_function("window.__game", timeout=30000)
    page.wait_for_function("window.__friends && window.__friends.installed", timeout=30000)
    # The boot overlay sits above the selector until it has faded out.
    page.wait_for_function("(() => { const s = document.querySelector('#boot-splash'); return !s || getComputedStyle(s).display === 'none'; })()", timeout=30000)


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

    # Every selector button inside the viewport and distinct.
    centers = {c: center(page, c) for c in ALL}
    assert len({tuple(v) for v in centers.values()}) == len(ALL), centers
    for c, (x, y) in centers.items():
        assert 0 < x < 1280 and 0 < y < 720, (c, x, y)
    page.screenshot(path=os.path.join(os.environ.get("ARK_SHOTS", "."), "friends_selector_desktop.png"))

    for friend in FRIENDS:
        page.mouse.click(*center(page, friend))
        assert page.evaluate("key => localStorage.getItem(key)", CHARACTER_KEY) == friend

    # Mobile tap hits the same buttons and stays on the title screen.
    mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    mobile.goto(URL)
    wait_ready(mobile)
    for friend in FRIENDS:
        x, y = center(mobile, friend)
        assert 0 < x < 390 and 0 < y < 844, (friend, x, y)
        mobile.touchscreen.tap(x, y)
        assert mobile.evaluate(f"localStorage.getItem('{CHARACTER_KEY}')") == friend
    assert mobile.evaluate("__game.scene") == "title"
    mobile.screenshot(path=os.path.join(os.environ.get("ARK_SHOTS", "."), "friends_selector_mobile.png"))
    mobile.close()

    # Play as DAREK; the player uses his own pixel sheet.
    page.mouse.click(*center(page, "darek"))
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("Test")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate("__game.playerCharacter") == "darek"
    assert page.evaluate("__game.playerSheetName") == "darek_sheet.png"

    placed = page.evaluate("__friends.placed")
    positions = {}
    for friend in FRIENDS:
        npc = page.evaluate("id => __game.ITEMS.npcs.filter(n => n.id === id)", friend)
        assert len(npc) == 1, (friend, npc)
        pos = npc[0]
        target = placed[friend]["target"]
        assert ((pos["x"] - target["x"]) ** 2 + (pos["y"] - target["y"]) ** 2) ** .5 <= 160, (friend, pos, target)
        assert page.evaluate("({x, y}) => __game.isSpawnReachable(x, y)", pos), friend
        if friend == "waldek":
            # Tomek's spot: the gap between the two barns behind the house by the bus shelter (x 2127-2159).
            assert 2134 <= pos["x"] <= 2152 and abs(pos["y"] - target["y"]) <= 24, pos
        positions[friend] = pos
        print(friend.upper(), "placed at", page.evaluate("id => __friends.position(id)", friend), "near", placed[friend]["anchor"])

    # Each NPC is drawn from its own sheet without smoothing, and Space opens his dialogue.
    for friend in FRIENDS:
        pos = positions[friend]
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
        assert stand is not None, (friend, "no adjacent walkable interaction point")
        page.evaluate("({x, y}) => window.ARK.teleport(x, y)", stand)
        page.evaluate("""name => {
            const ctx = ARK.ctx, draw = ctx.__origDraw || ctx.drawImage.bind(ctx);
            ctx.__origDraw = draw; window.__friendDraws = [];
            ctx.drawImage = (...args) => {
                if (args[0] && args[0].src && args[0].src.endsWith('/' + name + '_sheet.png'))
                    __friendDraws.push({smooth: ctx.imageSmoothingEnabled});
                return draw(...args);
            };
        }""", friend)
        # (DAREK is the player here, so his NPC slot shows AREK; his own sheet is the hero.)
        page.wait_for_function("() => __friendDraws.length > 3", timeout=10000)
        draws = page.evaluate("__friendDraws")
        assert draws and all(not d["smooth"] for d in draws), (friend, draws[:3])
        page.screenshot(path=os.path.join(os.environ.get("ARK_SHOTS", "."), f"friends_{friend}_ingame.png"))
        page.keyboard.press("Space")
        page.wait_for_function("id => __game.talk && __game.talk.who === id", arg=friend)
        assert LINE[friend] in page.evaluate("__game.talk.lines.join(' ')"), friend
        page.keyboard.press("Escape")
        for _ in range(6):
            if not page.evaluate("!!__game.talk"):
                break
            page.keyboard.press("Space")
            page.wait_for_timeout(250)
        assert not page.evaluate("!!__game.talk"), (friend, "dialogue did not close")

    # Reload keeps one fixed NPC each at the same deterministic spot.
    page.reload()
    wait_ready(page)
    for friend in FRIENDS:
        restored = page.evaluate("id => __game.ITEMS.npcs.filter(n => n.id === id)", friend)
        pos = positions[friend]
        assert len(restored) == 1 and restored[0]["x"] == pos["x"] and restored[0]["y"] == pos["y"], (friend, restored, pos)
    assert not errors, errors

    browser.close()
    print(f"FRIENDS regression passed: {len(ALL)}-button selector desktop/mobile, DAREK playable sheet, {len(FRIENDS)} fixed reachable NPCs, unsmoothed draws, dialogues, reload")
