"""Capture BERCIK in the actual game and verify PL/EN interactions."""
import json
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

URL = 'http://127.0.0.1:8848/index.html'
OUT = Path(__file__).resolve().parent
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    errors, requested = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: requested.append({'url': r.url, 'status': r.status}) if '/bercik' in r.url else None)
    page.goto(URL + '?music=0')
    page.wait_for_function('window.__game && window.__bercik.installed')
    page.evaluate('localStorage.clear()')
    page.reload()
    page.wait_for_function('window.__game && window.__bercik.installed')
    page.mouse.click(*page.evaluate("__game.characterButtonCenter('bercik')"))
    page.screenshot(path=str(OUT / 'title_desktop.png'))
    # Start as Arek so the visitable NPC itself is rendered as BERCIK.
    page.mouse.click(*page.evaluate("__game.characterButtonCenter('arek')"))
    page.keyboard.press('KeyN')
    page.locator('#player-name-input').fill('Arek')
    page.locator('#player-name-submit').click()
    page.wait_for_function("__game.scene === 'play'")
    pos = page.evaluate('__bercik.position()')
    assert pos['sector'] == 'J12' and pos['reachable'], pos
    page.evaluate('n => ARK.teleport(n.x - 28, n.y)', pos)
    page.wait_for_function("!('heroShade' in __game) || __game.heroShade < .01")
    # Teleport changes the player instantly, but the camera eases over many frames.
    # Wait for its actual map position, not a guessed delay or the HUD sector.
    page.wait_for_function('''() => {
        const c = ARK.camera, p = __game.P, m = ARK.MAP, canvas = ARK.ctx.canvas;
        if (!c) return false;
        const vw = canvas.width / c.zoom, vh = canvas.height / c.zoom;
        const x = m.w < vw ? m.w / 2 : Math.max(vw / 2, Math.min(m.w - vw / 2, p.x));
        const y = m.h < vh ? m.h / 2 : Math.max(vh / 2, Math.min(m.h - vh / 2, p.y - 16));
        const actual = c.toWorld(canvas.width / 2, canvas.height / 2);
        return Math.abs(actual[0] - x) < 2 && Math.abs(actual[1] - y) < 2;
    }''')
    page.screenshot(path=str(OUT / 'in_game.png'))
    page.keyboard.press('Space')
    page.wait_for_function("ARK.talk && ARK.talk.who === 'bercik'")
    assert 'Bercik' in page.evaluate('ARK.talk.lines.join(" ")')
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / 'dialogue_pl.png'))
    page.goto(URL + '?lang=en&music=0')
    page.wait_for_function('window.__game && window.__bercik.installed')
    page.keyboard.press('Enter')
    page.wait_for_function("__game.scene === 'play'")
    page.evaluate('n => ARK.teleport(n.x - 28, n.y)', pos)
    page.keyboard.press('Space')
    page.wait_for_function("ARK.talk && ARK.talk.who === 'bercik'")
    assert 'friendly traveller' in page.evaluate('ARK.talk.lines.join(" ")')
    mobile = browser.new_page(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
    mobile.goto(URL + '?music=0')
    mobile.wait_for_function('window.__game && window.__bercik.installed')
    mobile.touchscreen.tap(*mobile.evaluate("__game.characterButtonCenter('bercik')"))
    mobile.screenshot(path=str(OUT / 'title_mobile.png'))
    assert not errors, errors
    for item in requested:
        assert item['status'] in (200, 304), item  # reload may reuse validated cached assets
    for asset in ('js/bercik.js', 'img/bercik_sheet.png', 'img/bercik_sheet.json', 'img/bercik.png'):
        with urlopen('http://127.0.0.1:8848/' + asset) as response:
            assert response.status == 200 and response.read(), asset
    report = {'position':pos, 'page_errors':errors, 'asset_responses':requested,
              'pl_dialogue':True,'en_dialogue':True,'screenshots':['in_game.png','dialogue_pl.png','title_desktop.png','title_mobile.png']}
    (OUT / 'browser_evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
    browser.close()
