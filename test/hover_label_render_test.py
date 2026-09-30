"""A03 render regression: the small world hover label beside the bottom-left
coordinate HUD.

The A02 picker answers *which* label a world point gets; this suite pins down
*that the label is actually rendered*, and only under the right conditions:

- one small strip directly above the coordinate readout (same left margin,
  same translucent box colour, separate from the large M-map floating box);
- correct text after the pointer moves between objects;
- hidden on pointerleave (and never redrawn stale), hidden in title / during
  dialogue / over the big M-map, hidden for touch-only input (no stuck mouse
  label);
- hovering never triggers click-to-move or any other input side effect;
- the strip and its text stay fully inside the viewport at 1280x720 and
  390x844 (measured width, clamped with an ellipsis).

Truth comes from the live render state accessor __game.worldHoverLabelState()
(the same function drawCoords paints from), plus a fillText tracer (A01
convention) proving the text is really painted on the canvas and that the
coordinate line still paints itself.

Run: ARK_URL=http://127.0.0.1:8790/index.html python test/hover_label_render_test.py
"""
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

import hover_labels_test
from hover_labels_test import boot, PICK_JS

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8790/index.html")
hover_labels_test.URL = URL

_home = Path(os.environ.get("HERMES_HOME", r"C:\Users\Lenovo\AppData\Local\hermes"))
SCRATCH = Path(os.environ.get("HERMES_SCRATCH", str(_home / "cache" / "scratch" / "chlopkow-a03")))
SCRATCH.mkdir(parents=True, exist_ok=True)

PICK_PL = PICK_JS.replace("__LANG__", "'pl'")
PICK_EN = PICK_JS.replace("__LANG__", "'en'")

# Records every canvas fillText so the suite can prove the label is painted next
# to the coordinates and the coordinate line still paints itself. Installed
# before the game scripts (same convention as the A01 direction-sign tracer).
TRACER = r"""
(() => {
  window.__a3trace = [];
  const orig = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, x, y) {
    if (typeof text === 'string' && text) {
      window.__a3trace.push({ t: text, x: +x, y: +y, f: String(this.font) });
      if (window.__a3trace.length > 20000) window.__a3trace.splice(0, 5000);
    }
    return orig.apply(this, arguments);
  };
})();
"""

# Live representative + hero parked so the camera settles with the target on
# screen, yet the hero's own hit box never covers the hovered point.
PLACE_JS = """
(kind) => {
  const s = select(kind);
  if (!s) return { ok: false, why: 'no clear live representative' };
  const A = window.ARK, g = window.__game;
  window.__a3tgt = { pt: s.pt, expected: s.expected, kind };
  if (kind === 'hero') placeHero(s.pt[0], s.pt[1] + 12);
  else placeHero(s.pt[0] - 30, s.pt[1] + 15);
  // Freeze Frodo EXACTLY at the spot he is heading to (42 px behind Arek's
  // facing): dist becomes 0, so he idles in place instead of walking a line
  // across the hovered point mid-dance. Resetting chase/wander/trail keeps
  // the follow logic from picking another heading.
  const dv = { down: [0, 1], up: [0, -1], left: [-1, 0], right: [1, 0] }[(g.P.dir || 'down')];
  placeFrodoAway(g.P.x - dv[0] * 42, g.P.y - dv[1] * 42);
  A.FRODO.chase = null; A.FRODO.wander = 0; A.FRODO.returning = false;
  A.FRODO.visit = null; A.FRODO.trailI = -1;
  return { ok: true, expected: s.expected, pt: s.pt };
}
"""

READ_CANVAS = """
() => {
  const [px, py] = A.camera.S(window.__a3tgt.pt[0], window.__a3tgt.pt[1]);
  return {
    canvas: [Math.round(px), Math.round(py)],
    visible: px >= 8 && py >= 8 && px <= A.ctx.canvas.width - 8 && py <= A.ctx.canvas.height - 8,
  };
}
"""

U_JS = "() => Math.min(window.ARK.ctx.canvas.width, window.ARK.ctx.canvas.height * 1.6) / 100"


def new_page(browser, viewport, mobile=False):
    kw = {"viewport": viewport}
    if mobile:
        kw.update(has_touch=True, is_mobile=True)
    page = browser.new_page(**kw)
    page.add_init_script(TRACER)
    return page


def lbl(page):
    return page.evaluate("() => window.__game.worldHoverLabelState()")


def painted(page, text):
    return page.evaluate("(t) => window.__a3trace.filter(e => e.t === t).length", text)


def clear_trace(page):
    page.evaluate("() => { window.__a3trace.length = 0; }")


def place_and_point(page, pick_js, kind, settle_ms=1000):
    r = page.evaluate(pick_js + PLACE_JS, kind)
    if not r or not r.get("ok"):
        return {"ok": False, "why": r and r.get("why")}
    page.wait_for_timeout(settle_ms)
    c = page.evaluate(pick_js + READ_CANVAS)
    r.update(c)
    return r


def hover(page, pick_js, kind):
    info = place_and_point(page, pick_js, kind)
    assert info.get("ok"), f"no live {kind} representative: {info}"
    assert info["visible"], f"{kind} target off-screen at {info['canvas']}: {info['pt']}"
    page.mouse.move(info["canvas"][0], info["canvas"][1])
    page.wait_for_timeout(250)
    return info


def assert_label(page, info, expected, why):
    st = lbl(page)
    assert st["shown"], f"{why}: label not shown (state={st})"
    assert st["text"] == expected, f"{why}: text {st['text']!r} != {expected!r}"


def assert_no_label(page, why):
    st = lbl(page)
    assert not st["shown"], f"{why}: label unexpectedly shown (state={st})"


def assert_near_coords(page, st):
    """The strip sits directly above the coordinate box: same left margin, its
    bottom touching the box top (H - 2.4*U), fully inside the viewport."""
    W, H = page.evaluate("() => [window.ARK.ctx.canvas.width, window.ARK.ctx.canvas.height]")
    U = page.evaluate(U_JS)
    assert abs(st["x"] - U * 1.2) <= 0.01, f"label left margin {st['x']} != {U*1.2}"
    assert abs((st["y"] + st["h"]) - (H - U * 2.4)) <= U * 0.4, \
        f"label bottom {st['y']+st['h']} not above the coordinate box (H-2.4U={H-U*2.4})"
    assert st["x"] >= 0 and st["x"] + st["w"] <= W, f"label box outside viewport: {st}"


def run_desktop(page, lang, out):
    """Label beside coordinates, correct text after pointer moves, pointerleave,
    title/dialogue/M-map gates and no input interference - one fresh context."""
    name = "Zosia"
    boot(page, name=name, lang=lang)
    pick = PICK_PL if lang == "pl" else PICK_EN

    # --- 1. label near the bottom-left coordinates, really painted ---
    info = hover(page, pick, "building")
    st = lbl(page)
    assert_label(page, info, info["expected"], "building hover")
    assert_near_coords(page, st)
    assert painted(page, info["expected"]) > 0, f"{info['expected']} never painted on canvas"
    # the coordinate line itself still paints (hero name + grid sector, P04)
    hn = page.evaluate("() => window.__game.playerName")
    coord_re = re.compile(rf"^{re.escape(str(hn))} [A-K]\d{{1,2}}$")
    coords_painted = [e["t"] for e in page.evaluate("() => window.__a3trace") if coord_re.match(e["t"])]
    assert coords_painted, f"coordinate readout line not painted: {page.evaluate('() => window.__a3trace')[:20]}"
    assert not re.search(r"\d+,\d+", coords_painted[-1]), f"raw pixels still in the readout: {coords_painted[-1]}"
    page.screenshot(path=SCRATCH / f"1280x720_{lang}_hover_building.png")

    # --- 2. correct text after the pointer moves ---
    clear_trace(page)
    info2 = hover(page, pick, "apple")
    st2 = lbl(page)
    assert_label(page, info2, info2["expected"], "apple hover after building")
    assert painted(page, info2["expected"]) > 0, "apple label never painted"
    # once settled, the previous object's label is gone (no stale draw)
    clear_trace(page)
    page.wait_for_timeout(250)
    assert painted(page, info["expected"]) == 0, \
        f"stale {info['expected']} label while hovering the apple"
    assert painted(page, info2["expected"]) > 0, "apple label not repainted after settling"
    # and back to the building: text follows the pointer (fresh placement so the
    # camera is settled on the building again)
    info3 = hover(page, pick, "building")
    st3 = lbl(page)
    assert_label(page, info3, info3["expected"], "building again")
    assert st3["text"] != st2["text"]
    # --- 3. hide on pointerleave, no stale redraw, recovery on re-enter ---
    page.evaluate("""() => {
      const c = document.getElementById('game');
      c.dispatchEvent(new PointerEvent('pointerleave', { pointerType: 'mouse', bubbles: true }));
    }""")
    page.wait_for_timeout(200)
    assert_no_label(page, "after pointerleave")
    clear_trace(page)
    page.wait_for_timeout(200)
    assert painted(page, info["expected"]) == 0, "label redrawn stale after pointerleave"
    page.screenshot(path=SCRATCH / f"1280x720_{lang}_pointerleave.png")
    page.mouse.move(info["canvas"][0], info["canvas"][1])
    page.wait_for_timeout(250)
    assert_label(page, info, info["expected"], "after re-entering the canvas")

    # --- 4. title, dialogue and big M-map gates ---
    # big M-map: hidden while showMap, back when closed
    page.keyboard.press("KeyM")
    page.wait_for_timeout(250)
    assert_no_label(page, "while the big M-map is open")
    clear_trace(page)
    page.wait_for_timeout(200)
    assert painted(page, info["expected"]) == 0, "label painted over the big M-map"
    page.screenshot(path=SCRATCH / f"1280x720_{lang}_map_open.png")
    page.keyboard.press("KeyM")
    page.wait_for_timeout(250)
    assert_label(page, info, info["expected"], "after closing the M-map")
    # dialogue: hidden while talk is open, back when the line is closed
    page.evaluate("() => window.ARK.say('arek', ['Testowa linia'])")
    page.wait_for_timeout(150)
    assert_no_label(page, "during dialogue")
    clear_trace(page)
    page.wait_for_timeout(200)
    assert painted(page, info["expected"]) == 0, "label painted during dialogue"
    page.keyboard.press("Space")
    page.wait_for_timeout(200)
    assert_label(page, info, info["expected"], "after the dialogue closed")
    # title scene: hidden, and back after re-entering play
    page.keyboard.press("Escape")
    page.wait_for_function("window.__game.scene === 'title'")
    page.wait_for_timeout(150)
    assert_no_label(page, "in the title scene")
    page.keyboard.press("Enter")
    page.wait_for_function("window.__game.scene === 'play'")
    page.wait_for_timeout(350)
    assert_label(page, info, info["expected"], "after returning to play")

    # --- 5. no pointer/click-to-move interference ---
    px, py = page.evaluate("() => [window.__game.P.x, window.__game.P.y]")
    for dx in range(4):  # arbitrary hover moves across the canvas
        page.mouse.move(200 + dx * 90, 150 + dx * 40)
        page.wait_for_timeout(60)
    page.mouse.move(info["canvas"][0], info["canvas"][1])
    page.wait_for_timeout(150)
    moved = page.evaluate("""() => {
      const g = window.__game, A = window.ARK;
      return { px: g.P.x, py: g.P.y, moving: g.P.moving, click: A.clickTarget.active,
               keys: A.keys.size, map: g.showMap, joy: A.joy.active };
    }""")
    assert moved["px"] == px and moved["py"] == py, f"hover moved the hero: {moved}"
    assert not moved["moving"] and not moved["click"] and moved["keys"] == 0 \
        and not moved["map"] and not moved["joy"], f"hover leaked into input: {moved}"
    # a real click-to-move still works afterwards
    spot = page.evaluate(pick + """
    () => {
      const g = window.__game, A = window.ARK;
      const cx = g.P.x, cy = g.P.y;
      for (let r = 30; r <= 900; r += 5) for (let a = 0; a < 6.283; a += 0.25) {
        const x = Math.round(cx + Math.cos(a) * r), y = Math.round(cy + Math.sin(a) * r);
        if (x < 8 || y < 8 || x > g.MAP.w - 8 || y > g.MAP.h - 8) continue;
        if (g.terrainAt(x, y) !== 'grass' || g.blocked(x, y)) continue;
        const [px, py] = A.camera.S(x, y);
        if (px < 8 || py < 8 || px > A.ctx.canvas.width * .75 || py > A.ctx.canvas.height * .55) continue;
        if (Math.hypot(x - cx, y - cy) < 60) continue;   // far enough that the walk is still ongoing
        return [Math.round(px), Math.round(py)];
      }
      return null;
    }
    """)
    assert spot, "no clear grass click spot found"
    page.mouse.click(spot[0], spot[1])
    page.wait_for_timeout(150)
    ok_click = page.evaluate("() => window.ARK.clickTarget.active")
    assert ok_click, "click-to-move broken by the hover label"
    print(f"  desktop [{lang}] PASS")


def run_clamp(page, viewport, out):
    """Viewport clamping at 1280x720 and 390x844: the label strip always stays
    inside the canvas; an absurdly long hero name is clamped with an ellipsis."""
    W, H = viewport["width"], viewport["height"]
    boot(page, lang="pl")
    info = hover(page, PICK_PL, "hero")
    st = lbl(page)
    assert_label(page, info, info["expected"], f"{W}x{H} hero hover")
    assert_near_coords(page, st)
    page.screenshot(path=SCRATCH / f"{W}x{H}_hover_hero.png")
    page.evaluate("""() => {
      window.__game.Q.playerName =
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    }""")
    page.wait_for_timeout(200)
    # A genuinely long label overflows the measured budget; the clamp must truncate
    # instead of letting the strip leave the viewport. The game caps the hero name
    # at 20 chars, so force the width by replacing ctx.measureText (game.js wraps it
    # as an own property, bypassing prototype patches) - restored right after.
    page.evaluate("""() => {
      const A = window.ARK;
      window.__origCtxMeasure = A.ctx.measureText;
      A.ctx.measureText = function (t) {
        return { width: window.__origCtxMeasure.call(A.ctx, t).width + 4000 };
      };
    }""")
    page.wait_for_timeout(150)
    st2 = lbl(page)
    assert st2["shown"], f"{W}x{H}: long hero label not shown ({st2})"
    assert st2["text"].endswith("…") and st2["text"].startswith("A"), \
        f"{W}x{H}: long label not clamped: {st2['text']!r}"
    assert len(st2["text"]) < 20, f"{W}x{H}: truncation loop did not cut: {st2!r}"
    page.screenshot(path=SCRATCH / f"{W}x{H}_long_label_clamped.png")
    # restore the real measure: the label returns to full width and fits the viewport
    page.evaluate("""() => {
      window.ARK.ctx.measureText = window.__origCtxMeasure;
    }""")
    page.evaluate("() => { window.__game.Q.playerName = 'Zosia'; }")
    page.wait_for_timeout(250)
    st3 = lbl(page)
    assert st3["shown"] and st3["text"] == "ZOSIA", f"{W}x{H}: label not restored: {st3}"
    assert st3["x"] + st3["w"] <= W and st3["y"] >= 0, \
        f"{W}x{H}: restored label outside viewport: {st3}"
    # a normal object label also clamps inside the narrow viewport
    info4 = hover(page, PICK_PL, "building")
    st4 = lbl(page)
    assert_label(page, info4, info4["expected"], f"{W}x{H} building hover")
    assert st4["x"] + st4["w"] <= W and st4["y"] >= 0, f"{W}x{H}: building label outside: {st4}"
    page.screenshot(path=SCRATCH / f"{W}x{H}_hover_building.png")
    print(f"  clamp [{W}x{H}] PASS")


def run_touch(browser, out):
    """Touch-only context (has_touch + is_mobile): a real tap must never show a
    stuck mouse label, and the pointer guard must record the touch type."""
    page = new_page(browser, {"width": 390, "height": 844}, mobile=True)
    boot(page, lang="pl")
    info = place_and_point(page, PICK_PL, "building")
    assert info.get("ok"), f"touch: no building representative: {info}"
    assert info["visible"], f"touch: target off-screen: {info}"
    page.touchscreen.tap(info["canvas"][0], info["canvas"][1])
    page.wait_for_timeout(300)
    st = lbl(page)
    assert not st["shown"], f"touch-only: stuck mouse label shown: {st}"
    kind = page.evaluate("() => window.ARK.pointer.kind")
    assert kind in (None, "touch"), f"touch pointer recorded as {kind!r}"
    clear_trace(page)
    page.wait_for_timeout(200)
    assert painted(page, "BUDYNEK") == 0, "touch tap painted the world label"
    page.screenshot(path=SCRATCH / "390x844_touch_tap.png")
    page.close()
    print("  touch-only [390x844] PASS")


def main():
    overall_ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for lang in ("pl", "en"):
            page = new_page(browser, {"width": 1280, "height": 720})
            try:
                run_desktop(page, lang, SCRATCH)
            except AssertionError as e:
                overall_ok = False
                print(f"  desktop [{lang}] FAIL: {e}")
            except Exception as e:  # RED: missing accessor / page errors surface here
                overall_ok = False
                print(f"  desktop [{lang}] ERROR: {type(e).__name__}: {e}")
            finally:
                page.close()
        for viewport in ({"width": 1280, "height": 720}, {"width": 390, "height": 844}):
            page = new_page(browser, viewport)
            try:
                run_clamp(page, viewport, SCRATCH)
            except AssertionError as e:
                overall_ok = False
                print(f"  clamp {viewport} FAIL: {e}")
            except Exception as e:
                overall_ok = False
                print(f"  clamp {viewport} ERROR: {type(e).__name__}: {e}")
            finally:
                page.close()
        try:
            run_touch(browser, SCRATCH)
        except AssertionError as e:
            overall_ok = False
            print(f"  touch-only FAIL: {e}")
        except Exception as e:
            overall_ok = False
            print(f"  touch-only ERROR: {type(e).__name__}: {e}")
        browser.close()
    print("\nhover_label_render:", "PASS" if overall_ok else "FAIL")
    if not overall_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()