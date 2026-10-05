"""HUD corners (2026-10-04, Tomek): chat is left-aligned at the bottom-left; the music note and
the position/sector readout sit at the bottom-right; maps mark only the player's own position.

Run: ARK_URL=http://127.0.0.1:8795/index.html python test/hud_corners_test.py
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8795/index.html")
SHOTS = Path(__file__).resolve().parents[1] / "asset-review" / "hud-corners"
SHOTS.mkdir(parents=True, exist_ok=True)
ALLOWED_MAP_MARKS = {"#ff3b30", "#ffffff"}   # the blinking player dot only

TRACER = r"""
(() => {
  window.__hud = { text: [], rects: [] };
  const ft = CanvasRenderingContext2D.prototype.fillText, fr = CanvasRenderingContext2D.prototype.fillRect;
  CanvasRenderingContext2D.prototype.fillText = function (t, x, y) {
    if (typeof t === 'string' && t) { window.__hud.text.push({ t, x: +x, y: +y, a: this.textAlign }); if (window.__hud.text.length > 4000) window.__hud.text.splice(0, 2000); }
    return ft.apply(this, arguments);
  };
  CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
    window.__hud.rects.push({ x: +x, y: +y, w: +w, h: +h, c: String(this.fillStyle) });
    if (window.__hud.rects.length > 20000) window.__hud.rects.splice(0, 10000);
    return fr.apply(this, arguments);
  };
})();
"""


def boot(page):
    page.add_init_script(TRACER)
    page.goto(URL)
    page.wait_for_function("window.__game && window.ARK && window.MUSIC", timeout=60000)
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="load")
    page.wait_for_function("window.__game && window.MUSIC", timeout=60000)
    page.keyboard.press("Enter")
    if page.locator("#player-name-input").count():
        page.locator("#player-name-input").fill("Test")
        page.keyboard.press("Enter")
    page.wait_for_function("__game.scene === 'play'", timeout=30000)
    page.wait_for_timeout(500)


def check_chat(page):
    page.wait_for_function("!document.getElementById('arek-global-chat').classList.contains('arek-chat-away')")
    for state in ("open", "minimized"):
        if state == "minimized":
            page.locator("#arek-chat-close").click()
        g = page.evaluate("""() => {
            const root = document.getElementById('arek-global-chat'), r = root.getBoundingClientRect();
            const vis = ['#arek-chat-panel', '#arek-chat-launch'].map(s => document.querySelector(s)).find(e => e.offsetParent);
            const q = getComputedStyle(root), v = vis.getBoundingClientRect();
            return { left: r.left, right: r.right, bottom: r.bottom, align: q.textAlign, vw: innerWidth, vh: innerHeight,
                     visLeft: v.left, visAlign: getComputedStyle(vis).textAlign };
        }""")
        assert g["left"] <= 16 and g["right"] < g["vw"] * .75, f"chat ({state}) must sit at the left edge: {g}"
        assert g["align"] == "left" and g["visAlign"] == "left", f"chat ({state}) text must be left-aligned: {g}"
    page.locator("#arek-chat-launch").click()


def check_corner(page):
    W, H = page.evaluate("[ARK.ctx.canvas.width, ARK.ctx.canvas.height]")
    U = min(W, H * 1.6) / 100
    page.evaluate("window.__hud.text.length = 0")
    page.wait_for_timeout(300)
    name = page.evaluate("__game.playerName")
    lines = [e for e in page.evaluate("window.__hud.text") if e["t"].startswith(f"{name} ") and e["y"] > H - U * 4]
    assert lines, "position/sector readout not painted"
    e = lines[-1]
    assert e["a"] == "right", f"readout must be right-aligned, got {e}"
    assert W * .5 < e["x"] <= W - U, f"readout must sit at the bottom-right: {e} (W={W})"
    icon = page.evaluate("MUSIC.iconRect")
    assert icon, "music icon not painted"
    assert icon["x"] > W * .5 and icon["x"] + icon["s"] <= W, f"music icon must sit at the right: {icon} (W={W})"
    assert icon["y"] > H * .7, f"music icon must sit at the bottom: {icon} (H={H})"
    # the note is clickable where it is drawn, and no longer at the old left spot
    before = page.evaluate("MUSIC.muted")
    page.evaluate("([x, y]) => ARK.HOOKS.pointer.forEach(f => f(x, y))", [icon["x"] + icon["s"] / 2, icon["y"] + icon["s"] / 2])
    assert page.evaluate("MUSIC.muted") != before, "right-hand music icon did not toggle mute"
    page.evaluate("([x, y]) => ARK.HOOKS.pointer.forEach(f => f(x, y))", [icon["x"] + icon["s"] / 2, icon["y"] + icon["s"] / 2])
    assert page.evaluate("MUSIC.muted") == before


def map_marks(page, big):
    W, H = page.evaluate("[ARK.ctx.canvas.width, ARK.ctx.canvas.height]")
    U = min(W, H * 1.6) / 100
    MW, MH = page.evaluate("[__game.MAP.w, __game.MAP.h]")
    mw = min(W * .8, H * .8 * MW / MH) if big else U * 16
    mh = mw * MH / MW
    mx, my = ((W - mw) / 2, (H - mh) / 2) if big else (W - mw - U * 2, U * 2)
    page.evaluate("window.__hud.rects.length = 0")
    page.wait_for_timeout(400)
    rects = page.evaluate("window.__hud.rects")
    marks = [r for r in rects if mx <= r["x"] and r["x"] + r["w"] <= mx + mw and my <= r["y"] and r["y"] + r["h"] <= my + mh
             and r["w"] < mw / 4 and r["h"] < mh / 4]
    assert marks, "no player marker painted on the map"
    return {r["c"] for r in marks}


def check_maps(page):
    # make sure plugin markers would exist: a car, race flags, quest boards, NPCs
    colours = map_marks(page, big=False)
    assert colours <= ALLOWED_MAP_MARKS, f"minimap shows more than the player: {colours}"
    page.evaluate("__game.showMap = true")   # keyboard focus may sit in the chat box
    page.wait_for_timeout(300)
    colours = map_marks(page, big=True)
    assert colours <= ALLOWED_MAP_MARKS, f"big map shows more than the player: {colours}"
    page.evaluate("__game.showMap = false")


with sync_playwright() as p:
    browser = p.chromium.launch()
    for vp in ({"width": 1280, "height": 720}, {"width": 820, "height": 640}):
        page = browser.new_page(viewport=vp)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        boot(page)
        check_chat(page)
        check_corner(page)
        check_maps(page)
        page.screenshot(path=str(SHOTS / f"corners-{vp['width']}.png"))
        assert not errors, errors
        page.close()
    browser.close()
print("HUD corners: PASS chat left, music + sector right, maps show only the player")
