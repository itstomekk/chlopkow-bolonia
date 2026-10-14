"""Selected card label becomes an editable player name; blank uses the character default."""
import ast
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get('ARK_URL', 'http://127.0.0.1:8799/index.html')
fixture = ast.parse(Path(__file__).with_name('arrival_log_test.py').read_text(encoding='utf-8'))
STUB = next(ast.literal_eval(n.value) for n in fixture.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'STUB' for t in n.targets))
OUT = Path('C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/chlopkow-inline-identity')
OUT.mkdir(parents=True, exist_ok=True)
TRACE = """window.__labels = [];
const ft = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function(text) {
  if (__labels.length > 2000) __labels.length = 0;
  __labels.push(text); return ft.apply(this, arguments);
};
window.__nostrHarness = {nextId:0, failures:0, calls:[], accepted:[], history:[], subscriptions:[]};
"""


def boot(browser, width, height):
    page = browser.new_page(viewport={'width': width, 'height': height}, is_mobile=width < 480, has_touch=width < 480)
    page.add_init_script(TRACE)
    page.route('https://esm.sh/nostr-tools@2.25.2?bundle&target=es2020',
               lambda route: route.fulfill(status=200, content_type='application/javascript', body=STUB))
    page.route_web_socket('wss://**', lambda socket: socket.close())
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL + '?music=0')
    page.wait_for_function('window.__game && window.__arekGlobalChat')
    page.wait_for_function("!window.__arkBoot || window.__arkBoot.stage === 'ready'")
    return page, errors


def choose(page, char):
    center = page.evaluate('(id) => __game.characterButtonCenter(id)', char)
    if page.viewport_size['width'] < 480:
        page.touchscreen.tap(*center)
    else:
        page.mouse.click(*center)
    assert page.evaluate('__game.playerCharacter') == char
    return center


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height in ((1280, 720), (390, 844), (844, 390)):
        for value, expected in (('   ', 'Edytka'), ('  Żaneta <img>  ', 'Żaneta img')):
            page, errors = boot(browser, width, height)
            center = choose(page, 'edytka')
            field = page.locator('#player-name-input')
            assert field.input_value() == ''
            assert field.get_attribute('placeholder') == 'Edytka', 'Default name must follow the selected character'
            box = field.bounding_box()
            assert box and abs(box['x'] + box['width'] / 2 - center[0]) < 2, 'Name must replace the selected card label, not sit beside the grid'
            assert box['y'] > center[1] and box['y'] - center[1] < 70, box
            assert box['x'] >= 0 and box['x'] + box['width'] <= width, box
            page.evaluate('__labels.length = 0')
            page.wait_for_timeout(100)
            assert 'EDYTKA' not in page.evaluate('__labels'), 'Selected canvas label must disappear'
            assert page.evaluate('__game.scene') == 'title', 'Choice must not auto-start'
            if width >= 480:
                page.keyboard.type('Zosia')
                assert field.input_value() == 'Zosia', 'A desktop card click must focus its inline editor'
            else:
                field.fill('Zosia')
            choose(page, 'damian')
            assert field.input_value() == '' and field.get_attribute('placeholder') == 'Damian'
            choose(page, 'edytka')
            start = page.locator('#player-name-submit').bounding_box()
            disclosure = page.locator('#player-name-disclosure').bounding_box()
            assert start and disclosure and start['y'] + start['height'] <= disclosure['y'] and disclosure['y'] + disclosure['height'] <= height, (start, disclosure)
            page.screenshot(path=str(OUT / f'selector-{width}.png'))
            field.fill(value)
            page.locator('#player-name-submit').click()
            page.wait_for_function("__game.scene === 'play'")
            page.wait_for_function('__nostrHarness.accepted.length === 1')
            event = page.evaluate('__nostrHarness.accepted[0]')
            assert next(t[1] for t in event['tags'] if t[0] == 'name') == expected, event
            assert expected in event['content'], event
            assert page.evaluate('__game.playerName') == expected
            assert page.evaluate('__game.playerCharacter') == 'edytka'
            assert page.evaluate('__game.playerSheetName') == 'edytka_sheet.png'
            page.wait_for_function("document.querySelector('.arek-chat-arrival')")
            assert expected in page.locator('.arek-chat-arrival').inner_text()
            page.evaluate('__labels.length = 0')
            page.wait_for_timeout(100)
            assert any(t.startswith(expected + ' ') for t in page.evaluate('__labels')), 'HUD must use the submitted name'
            assert not errors, errors
            page.close()
    # A virtual keyboard / shortened viewport must preserve the draft and keep Start reachable.
    page, errors = boot(browser, 1280, 720)
    choose(page, 'edytka')
    page.keyboard.type('Ada')
    page.set_viewport_size({'width': 390, 'height': 320})
    page.wait_for_timeout(100)
    assert page.locator('#player-name-input').input_value() == 'Ada'
    start = page.locator('#player-name-submit').bounding_box()
    disclosure = page.locator('#player-name-disclosure').bounding_box()
    assert start['y'] + start['height'] <= disclosure['y'] and disclosure['y'] + disclosure['height'] <= 320, (start, disclosure)
    page.mouse.click(5, 310)
    assert page.evaluate('__game.scene') == 'title' and page.locator('#player-name-input').input_value() == 'Ada', 'Background clicks cannot bypass a pending Start'
    page.screenshot(path=str(OUT / 'selector-short-resize.png'))
    page.locator('#player-name-input').focus()
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.id') == 'player-name-submit'
    page.keyboard.press('Enter')
    page.wait_for_function("__game.scene === 'play'")
    assert page.evaluate('__game.playerName') == 'Ada'
    assert not errors, errors
    page.close()
    browser.close()
print('Inline character identity: PASS default/custom names, label geometry, click-to-type/touch, switching, HUD/arrival, desktop/mobile/landscape')
