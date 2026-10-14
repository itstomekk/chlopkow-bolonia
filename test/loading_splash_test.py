"""Standalone boot splash contract; never contacts public Nostr relays.

Run against the local project server (typically port 8799):
    ARK_URL=http://127.0.0.1:8799/index.html python test/isolated_browser_runner.py test/loading_splash_test.py
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8799/index.html")
ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [{"width": 1280, "height": 720}, {"width": 390, "height": 844}]
SHOTS = Path(os.environ.get("ARK_SPLASH_SHOTS", "C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/chlopkow-loading-splash"))
SHOTS.mkdir(parents=True, exist_ok=True)


def isolate(page):
    page.route('https://esm.sh/**', lambda route: route.fulfill(
        status=200, content_type='application/javascript', body='export {};'))
    page.route_web_socket('wss://**', lambda socket: socket.close())


def assert_centered_logo(page, expect_no_game=True):
    data = page.evaluate("""() => {
      const overlay = document.querySelector('#boot-splash');
      const logo = document.querySelector('#boot-splash-logo');
      const r = logo ? logo.getBoundingClientRect() : {left: 0, top: 0, width: 0, height: 0};
      return {exists: !!overlay, visible: !!overlay && getComputedStyle(overlay).visibility !== 'hidden',
        bg: getComputedStyle(document.body).backgroundColor,
        htmlBg: getComputedStyle(document.documentElement).backgroundColor,
        left: r.left, top: r.top, width: r.width, height: r.height,
        vw: innerWidth, vh: innerHeight, complete: !!logo && logo.complete && logo.naturalWidth > 0,
        logoOpacity: logo ? getComputedStyle(logo).opacity : "missing",
        pointer: overlay ? getComputedStyle(overlay).pointerEvents : "missing"};
    }""")
    assert data["exists"] and data["visible"], "static splash overlay must be visible before game initialization"
    assert data["bg"] == data["htmlBg"] == "rgb(0, 0, 0)", f"page must remain pure black: {data}"
    assert data["complete"], "existing logo must be loaded before boot continues"
    assert abs((data["left"] + data["width"] / 2) - data["vw"] / 2) < 2, f"logo is not horizontally centered: {data}"
    assert abs((data["top"] + data["height"] / 2) - data["vh"] / 2) < 2, f"logo is not vertically centered: {data}"
    assert data["pointer"] == "auto", "splash must block pointer input while loading"
    if expect_no_game:
        assert data["logoOpacity"] == "1", "logo must remain visible until initialization finishes"
        assert not page.evaluate("!!window.__game"), "game must not be exposed while map.json is delayed"
        assert page.evaluate("window.__arkBoot && window.__arkBoot.stage") == "loading"


def test_viewport(browser, viewport):
    page = browser.new_page(viewport=viewport)
    isolate(page)
    if viewport["width"] == 390:
        page.emulate_media(reduced_motion="reduce")
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    map_payload = (ROOT / "docs" / "map.json").read_bytes()
    page.add_init_script("""(() => {
      window.__bootStages = []; window.__bootBlackFrames = [];
      new MutationObserver(records => records.forEach(record => {
        if (record.target.dataset.bootStage) window.__bootStages.push(record.target.dataset.bootStage);
        if (record.target.dataset.bootStage === 'black') {
          window.__bootBlackFrames.push({logo: getComputedStyle(document.querySelector('#boot-splash-logo')).opacity,
            overlay: getComputedStyle(record.target).opacity, background: getComputedStyle(record.target).backgroundColor});
        }
      })).observe(document, {subtree: true, attributes: true, attributeFilter: ['data-boot-stage']});
      const nativeFetch = window.fetch.bind(window);
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      window.__releaseBootMap = () => { window.__bootMapReleased = true; release(); };
      window.__bootMapRequested = false;
      window.fetch = (input, ...args) => {
        const url = typeof input === 'string' ? input : input.url;
        if (!window.__bootMapReleased && String(url).includes('map.json')) {
          window.__bootMapRequested = true;
          return gate.then(() => nativeFetch(input, ...args));
        }
        return nativeFetch(input, ...args);
      };
    })()""")
    page.route("**/map.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body=map_payload))
    try:
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("window.__bootMapRequested === true", timeout=10000)
        assert_centered_logo(page)
        page.keyboard.press('Enter')
        page.keyboard.press('Tab')
        assert page.evaluate("__arkBoot.stage") == 'loading'
        if viewport["width"] == 390:
            assert page.evaluate("getComputedStyle(document.querySelector('#boot-splash')).transitionDuration") == "0s"
            assert page.evaluate("getComputedStyle(document.querySelector('#boot-splash-logo')).transitionDuration") == "0s"
        page.screenshot(path=str(SHOTS / f"loading-{viewport['width']}.png"))
        # During the loading barrier, no game object or partially visible map may leak.
        assert page.evaluate("getComputedStyle(document.querySelector('#game')).opacity") in ("0", "1"), \
            "canvas must be covered by the full-screen splash"

        page.evaluate("window.__releaseBootMap()")
        page.wait_for_function("window.__game", timeout=15000)
        assert_centered_logo(page, expect_no_game=False)
        # Only real game initialization may trigger finish; never force it from this test.
        page.wait_for_function("window.__arkBoot.stage === 'ready'", timeout=10000)
        observed = page.evaluate("window.__bootStages")
        stages = [stage for index, stage in enumerate(observed) if index == 0 or stage != observed[index - 1]]
        expected = ["logo-out", "black", "map-in", "ready"]
        assert stages[-4:] == expected, f"boot stages out of order: {stages}"
        black_frames = page.evaluate('__bootBlackFrames')
        assert black_frames == [{'logo': '0', 'overlay': '1', 'background': 'rgb(0, 0, 0)'}], f'The black stage must hide the logo and cover the map: {black_frames}'
        assert page.locator("#boot-splash-logo").evaluate("e => getComputedStyle(e).opacity") == "0", \
            "crest/logo must remain absent through the map reveal"
        page.wait_for_function("getComputedStyle(document.querySelector('#boot-splash')).display === 'none'")
        assert not page_errors, page_errors
        assert page.evaluate("__game.scene") == 'title', 'Loading must not auto-start the game'
        page.screenshot(path=str(SHOTS / f"ready-{viewport['width']}.png"))
    finally:
        page.close()


def test_failed_logo_uses_accessible_fallback(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    isolate(page)
    page.route("**/boot-logo.png", lambda route: route.abort())
    try:
        page.goto(URL, wait_until="domcontentloaded")
        fallback = page.locator("#boot-splash-title")
        assert fallback.is_visible(), "missing logo must leave an accessible visible title"
        assert fallback.get_attribute("role") == "img"
        assert page.evaluate("window.__arkBoot.stage") == "loading"
        page.evaluate("window.__arkBoot.fail('Unable to initialize <script>')")
        assert page.locator("#boot-splash-error").is_visible(), "init failure must be visible"
        assert "<script>" in page.locator("#boot-splash-error").inner_text(), "failure text must be rendered as text, not HTML"
        assert page.locator("#boot-splash-reload").is_visible(), "failure state must offer reload"
        assert page.evaluate("window.__arkBoot.stage") == "error"
    finally:
        page.close()


def test_delayed_logo_and_missing_logo_reveal(browser):
    for missing in (False, True):
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        isolate(page)
        held = []
        page.route('**/boot-logo.png', lambda route: held.append(route))
        try:
            page.goto(URL, wait_until='domcontentloaded')
            page.wait_for_function('window.__game', timeout=20000)
            assert held and page.evaluate('__arkBoot.stage') == 'loading', 'Loaded game must still await the logo'
            if missing:
                held[0].abort()
            else:
                held[0].fulfill(status=200, content_type='image/png', body=(ROOT / 'docs/img/boot-logo.png').read_bytes())
            page.wait_for_function("__arkBoot.stage === 'black'")
            target = '#boot-splash-title' if missing else '#boot-splash-logo'
            assert page.locator(target).evaluate('e => getComputedStyle(e).opacity') == '0'
            assert page.locator('#boot-splash').evaluate('e => getComputedStyle(e).opacity') == '1'
            page.wait_for_function("__arkBoot.stage === 'ready'")
            assert page.locator(target).evaluate('e => getComputedStyle(e).opacity') == '0'
            assert page.evaluate('__game.scene') == 'title'
        finally:
            page.close()


def test_real_initialization_failure(browser):
    page = browser.new_page(viewport={'width': 390, 'height': 844})
    isolate(page)
    page.route('**/map.json', lambda route: route.fulfill(status=503, content_type='application/json', body='invalid-json'))
    try:
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function("__arkBoot.stage === 'error'")
        assert page.locator('#boot-splash-error').is_visible()
        assert page.locator('#boot-splash-error').inner_text()
        assert page.locator('#boot-splash-reload').is_visible()
        assert not page.evaluate('Boolean(window.__game)')
    finally:
        page.close()


with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    for size in VIEWPORTS:
        test_viewport(browser, size)
    test_failed_logo_uses_accessible_fallback(browser)
    test_delayed_logo_and_missing_logo_reveal(browser)
    test_real_initialization_failure(browser)
    browser.close()
print("loading splash: PASS")
