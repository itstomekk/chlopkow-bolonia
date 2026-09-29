"""
A06 — transparent right-side chat overlay (layout/behaviour regression).

Asserts the product contract for the optional Nostr chat as a transparent overlay:
  * right-aligned to the viewport edge, open by default for a fresh visitor,
    minimized preference persisted in localStorage and reopenable via the launch chip;
  * panel itself transparent and borderless (readable text comes from shadow/colour,
    never from an enclosing box); day separators stay hidden by CSS;
  * form/send/minimize controls present and visible; text input never leaks game keys
    (WASD/arrows/Space/jump/map) while focused;
  * no overlap with the top-right minimap or the right-side touch zones
    (map toggle above 30% height, jump/interact below 60%), and the overlay steps
    aside while a dialogue box or the big M-map is open, returning without losing
    the draft input or the loaded messages.

Never publishes to a Nostr relay: wss:// and the nostr-tools CDN are both aborted in
the page, so the panel renders with the relay connection failed and everything below
is pure DOM/CSS layout. Run against the worktree server:

    python -m http.server 8790 --directory docs
    ARK_URL=http://127.0.0.1:8790/index.html python test/chat_overlay_test.py
"""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8790/index.html")
CHAT_MINIMIZED_KEY = "arek-chlopkowie-chat-minimized-v1"

VIEWPORTS = [{"width": 1280, "height": 720}, {"width": 390, "height": 844}]

# Transparent background computed by Chromium.
TRANSPARENT = ("rgba(0, 0, 0, 0)", "transparent")


def new_page(browser, viewport):
    """Fresh context: no chat preference, no guest key, no real relay traffic."""
    page = browser.new_page(viewport=viewport)
    # Keep the test fully offline/mock: the layout must not depend on Nostr at all.
    page.route("wss://**", lambda route: route.abort())
    page.route("https://esm.sh/**", lambda route: route.abort())
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL + "?debug=1")
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    page.errors = errors
    return page


def start_game(page):
    """Title -> player-name overlay -> scene 'play' (same flow as other tests)."""
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("A06")
    page.locator("#player-name-submit").click()
    page.wait_for_function("window.__game && window.__game.scene === 'play'")


def rects(page):
    """Chat/panel rects + game geometry, all in CSS pixels (dpr=1 headless)."""
    data = page.evaluate("""() => {
        const b = r => { const x = r.getBoundingClientRect();
            return { left: x.left, top: x.top, right: x.right, bottom: x.bottom,
                     width: x.width, height: x.height }; };
        const W = innerWidth, H = innerHeight, U = Math.min(W, H * 1.6) / 100;
        const mw = U * 16, mh = mw * window.__game.MAP.h / window.__game.MAP.w;
        return {
            root: b(document.getElementById('arek-global-chat')),
            panel: b(document.getElementById('arek-chat-panel')),
            launch: b(document.getElementById('arek-chat-launch')),
            minimap: { left: W - mw - U * 2, top: U * 2, right: W - U * 2, bottom: U * 2 + mh },
            mapZone: { left: W * .78, top: 0, right: W, bottom: H * .3 },
            jumpZone: { left: W * .78, top: H * .6, right: W, bottom: H },
            W, H, U,
        };
    }""")
    data["panelBg"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).backgroundColor")
    data["panelBorder"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-panel')).borderWidth")
    data["launchBg"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-launch')).backgroundColor")
    data["launchBorder"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-launch')).borderWidth")
    # .arek-chat-day only exists while history messages render; probe the CSS rule directly.
    data["dayDisplay"] = page.evaluate("""(() => {
        const d = document.createElement('div');
        d.className = 'arek-chat-day';
        document.body.appendChild(d);
        const s = getComputedStyle(d).display;
        d.remove();
        return s;
    })()""")
    data["msgColor"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-messages')).color")
    data["msgShadow"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-messages')).textShadow")
    data["msgFont"] = page.evaluate("getComputedStyle(document.querySelector('#arek-chat-messages')).fontSize")
    return data


def intersects(a, b):
    return not (a["right"] <= b["left"] or a["left"] >= b["right"]
                or a["bottom"] <= b["top"] or a["top"] >= b["bottom"])


def close_talk(page):
    """Advance any open dialogue (single space on canvas) until it closes."""
    for _ in range(8):
        if not page.evaluate("window.__game.talk"):
            return
        page.locator("#game").click(position={"x": 1, "y": 1})
        page.wait_for_timeout(150)
    assert not page.evaluate("window.__game.talk"), "dialogue would not close"


def check_open_chat(page, viewport, r):
    """Default-open, transparent, borderless, right-aligned, controls visible."""
    W, H = r["W"], r["H"]
    assert page.locator("#arek-chat-panel").is_visible(), "chat is not open for a fresh visitor"
    assert page.evaluate(f"localStorage.getItem('{CHAT_MINIMIZED_KEY}')") is None, \
        "fresh visitor must not have a minimize preference"
    assert not page.locator("#arek-chat-launch").is_visible(), "launch chip must hide while open"
    assert r["panelBg"] in TRANSPARENT, f"panel background must be transparent, got {r['panelBg']}"
    assert r["panelBorder"] == "0px", f"panel must have no enclosing border, got {r['panelBorder']}"
    # Right-aligned: the panel hugs the right edge of the viewport.
    assert r["panel"]["right"] >= W - 40, f"panel not right-aligned (right={r['panel']['right']} of {W})"
    # Readable without a box: light text, ≥12px font, real text shadow, no border-box chrome.
    assert r["msgColor"] == "rgb(255, 247, 214)", f"message text colour off: {r['msgColor']}"
    assert r["msgShadow"] != "none", "message text must carry a shadow for readability"
    assert float(r["msgFont"].removesuffix("px")) >= 12, f"message font too small: {r['msgFont']}"
    assert r["dayDisplay"] == "none", "day separators must stay hidden"
    # Form / send / minimize controls exist and are visible.
    for sel in ("#arek-chat-form", "#arek-chat-text", "#arek-chat-send", "#arek-chat-close"):
        assert page.locator(sel).is_visible(), f"{sel} not visible"
    assert page.locator("#arek-chat-text").get_attribute("aria-label") == "Message"
    assert page.locator("#arek-chat-close").get_attribute("aria-label") == "Close global chat"
    # No overlap with the minimap or the right-side touch zones (desktop + mobile).
    assert not intersects(r["panel"], r["minimap"]), "chat overlaps the minimap"
    assert not intersects(r["panel"], r["mapZone"]), "chat overlaps the top-right map touch zone"
    assert not intersects(r["panel"], r["jumpZone"]), "chat overlaps the bottom-right jump/interact touch zone"
    # The panel is pinned into the free corridor between the minimap bottom and the
    # jump/interact touch zone, so the minimap and both right-side zones stay clear.
    assert r["panel"]["bottom"] <= r["jumpZone"]["top"] + 4, \
        f"panel bottom too low ({r['panel']['bottom']}) vs jump zone at {r['jumpZone']['top']}"
    assert r["panel"]["top"] >= r["minimap"]["bottom"] - 4, \
        f"panel still covers the minimap (top {r['panel']['top']} < minimap bottom {r['minimap']['bottom']})"
    # Default-open must not steal keyboard focus.
    assert page.evaluate("document.activeElement !== document.querySelector('#arek-chat-text')")


def check_keyboard_isolation(page):
    """Typing in the chat must never fire game keys (move/jump/map)."""
    before = page.evaluate("[__game.P.x, __game.P.y]")
    page.locator("#arek-chat-text").focus()
    for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight",
                "KeyW", "KeyA", "KeyS", "KeyD", "KeyJ", "KeyX", "KeyM", "Space", "KeyE"):
        page.keyboard.press(key)
    page.wait_for_timeout(300)
    after = page.evaluate("[__game.P.x, __game.P.y, __game.showMap]")
    assert after[:2] == before and after[2] is False, \
        f"chat input leaked game keys: {before} -> {after}"
    assert page.evaluate("document.activeElement === document.querySelector('#arek-chat-text')"), \
        "chat input lost focus while typing"


def check_map_dialogue_adaptation(page):
    """Chat steps aside for the M-map and a dialogue, then returns intact."""
    # Big M-map: hidden while open (even with a draft in the input), restored after.
    page.locator("#arek-chat-text").fill("draft kept")
    page.locator("#arek-chat-text").blur()   # while typing the chat stays visible by design
    before_msgs = page.evaluate("__arekGlobalChat.messageCount()")
    page.evaluate("__game.showMap = true")
    page.wait_for_function("document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
    assert page.evaluate("getComputedStyle(document.getElementById('arek-global-chat')).visibility") == "hidden"
    page.evaluate("__game.showMap = false")
    page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
    assert page.locator("#arek-chat-text").input_value() == "draft kept", "draft input lost after map"
    assert page.evaluate("__arekGlobalChat.messageCount()") == before_msgs, "messages lost after map"

    # Dialogue: same step-aside, same intact restore.
    page.evaluate("__game.talkTo('wesoly_swiat')")
    page.wait_for_function("document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
    assert not page.locator("#arek-chat-panel").is_visible(), "chat must hide during dialogue"
    close_talk(page)
    page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
    assert page.locator("#arek-chat-text").input_value() == "draft kept", "draft input lost after dialogue"
    assert page.evaluate("__arekGlobalChat.messageCount()") == before_msgs, "messages lost after dialogue"


def check_minimize_cycle(page, tag=None):
    """Close -> launch chip visible -> reopen; preference survives reload."""
    page.locator("#arek-chat-close").click()
    assert not page.locator("#arek-chat-panel").is_visible(), "chat did not minimise"
    assert page.locator("#arek-chat-launch").is_visible(), "launch chip missing while minimised"
    assert page.evaluate(f"localStorage.getItem('{CHAT_MINIMIZED_KEY}')") == "1"
    if tag:
        # Minimised: only the transparent launch chip remains on the right side.
        page.screenshot(path=os.path.join(SHOTS, f"chat-minimized-{tag}.png"))
    page.reload()
    page.wait_for_function("window.__arekGlobalChat")
    assert not page.locator("#arek-chat-panel").is_visible(), "minimised preference lost on reload"
    assert page.locator("#arek-chat-launch").is_visible()
    page.locator("#arek-chat-launch").click()
    assert page.locator("#arek-chat-panel").is_visible(), "launch chip did not reopen the chat"
    assert page.evaluate(f"localStorage.getItem('{CHAT_MINIMIZED_KEY}')") is None
    page.locator("#arek-chat-close").click()


def run_viewport(browser, viewport, tag):
    page = new_page(browser, viewport)
    try:
        # The overlay opens by default once the game runs (scene 'play'): on the
        # title screen it would sit over the character selector / name prompt on
        # touch layouts, so a fresh visitor starts the game before the open-state
        # contract is asserted. Minimize preference must still be absent.
        start_game(page)
        check_open_chat(page, viewport, rects(page))
        page.screenshot(path=os.path.join(SHOTS, f"transparent-right-chat-open-{tag}.png"))
        check_keyboard_isolation(page)
        check_map_dialogue_adaptation(page)
        # M-map open: the chat is gone from the right side (proof of no overlap).
        page.evaluate("__game.showMap = true")
        page.wait_for_function("document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
        page.screenshot(path=os.path.join(SHOTS, f"chat-map-{tag}.png"))
        page.evaluate("__game.showMap = false")
        page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
        # Dialogue box open: chat steps aside; screenshot shows the dialogue.
        page.evaluate("__game.talkTo('wesoly_swiat')")
        page.wait_for_function("document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
        page.screenshot(path=os.path.join(SHOTS, f"chat-dialogue-{tag}.png"))
        close_talk(page)
        page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')", timeout=3000)
        # Minimised: only the transparent launch chip remains on the right side.
        check_minimize_cycle(page, f"{viewport['width']}")
        assert not page.errors, page.errors
        print(f"PASS chat overlay @ {viewport['width']}x{viewport['height']}")
    finally:
        page.close()


SHOTS = r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\chlopkow-a06"
os.makedirs(SHOTS, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for viewport in VIEWPORTS:
        run_viewport(browser, viewport, f"{viewport['width']}")
    browser.close()
print("chat overlay: PASS")