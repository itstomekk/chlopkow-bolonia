"""Player names belong to a new game, not the selected sprite or a rename action.
Controlled relay transport only: no test visitors are published to public Nostr.
"""
import ast
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get('ARK_URL', 'http://127.0.0.1:8799/index.html')
# Reuse the existing controlled transport without importing its executing test script.
fixture = ast.parse(Path(__file__).with_name('arrival_log_test.py').read_text(encoding='utf-8'))
STUB = next(ast.literal_eval(node.value) for node in fixture.body if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'STUB' for t in node.targets))
TRACE = """window.__labels = [];
const original = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function(text) {
  if (!window.__labels.includes(text)) window.__labels.push(text);
  return original.apply(this, arguments);
};
window.__nostrHarness = {nextId:0, failures:0, calls:[], accepted:[], history:[], subscriptions:[]};
"""


def page_for(browser, saved=False):
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    page.add_init_script(TRACE)
    page.route('https://esm.sh/nostr-tools@2.25.2?bundle&target=es2020',
               lambda route: route.fulfill(status=200, content_type='application/javascript', body=STUB))
    page.route_web_socket('wss://**', lambda socket: socket.close())
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL + '?music=0')
    page.wait_for_function('window.__game && window.__arekGlobalChat')
    if saved:
        page.evaluate("localStorage.setItem('arek-chlopkow-save-v1', JSON.stringify({v:2,Q:{playerName:'Mira',apples:[1,2,3]},x:1200,y:4050}))")
        page.reload()
        page.wait_for_function("window.__game && __game.Q.playerName === 'Mira'")
    page.wait_for_function("!window.__arkBoot || __arkBoot.stage === 'ready'")
    return page, errors


def enter(page, name):
    page.locator('#player-name-input').fill(name)
    page.locator('#player-name-submit').click()
    page.wait_for_function("__game.scene === 'play'")
    page.wait_for_function('__nostrHarness.accepted.length === 1')
    event = page.evaluate('__nostrHarness.accepted[0]')
    assert next(t[1] for t in event['tags'] if t[0] == 'name') == name, event
    assert name in event['content'], event
    assert page.evaluate('__game.playerName') == name
    page.wait_for_function("document.querySelector('.arek-chat-arrival')")
    assert name in page.locator('.arek-chat-arrival').inner_text()


with sync_playwright() as p:
    browser = p.chromium.launch()
    only = sys.argv[1] if len(sys.argv) > 1 else ''
    if not only or only == 'selector':
        page, errors = page_for(browser)
        page.wait_for_function("__game.openingStage !== 'reveal'")
        page.wait_for_timeout(150)
        labels = page.evaluate('__labels')
        assert page.locator('#player-name-input').get_attribute('placeholder') == 'Arek' and 'BOHATER' not in labels, f'Arek sprite mislabeled: {labels}'
        enter(page, 'Żaneta')
        page.keyboard.press('KeyN')
        assert page.locator('#player-name-input').count() == 0, 'No rename prompt during play'
        assert page.evaluate('__game.playerName') == 'Żaneta'
        assert not errors, errors
        page.close()
    if not only or only == 'en':
        page, errors = page_for(browser)
        page.goto(URL + '?music=0&lang=en')
        page.wait_for_function("window.__game && __game.openingStage !== 'reveal'")
        page.wait_for_function("!window.__arkBoot || __arkBoot.stage === 'ready'")
        page.wait_for_timeout(150)
        labels = page.evaluate('__labels')
        assert page.locator('#player-name-input').get_attribute('placeholder') == 'Arek' and 'PLAYER' not in labels, f'English selector mislabeled: {labels}'
        enter(page, 'Ada')
        assert not errors, errors
        page.close()
    if not only or only == 'new':
        page, errors = page_for(browser, saved=True)
        page.wait_for_timeout(150)
        labels = page.evaluate('__labels')
        assert not any('ZMIEŃ IMIĘ' in text or 'CHANGE NAME' in text for text in labels), labels
        page.keyboard.press('Enter')
        page.wait_for_function("__game.scene === 'play'")
        assert page.evaluate('__game.Q.apples.length') == 3
        assert page.evaluate('__game.playerName') == 'Mira', 'Continue keeps the saved name'
        page.keyboard.press('Escape')
        page.wait_for_function("__game.scene === 'title'")
        page.keyboard.press('KeyN')
        assert page.locator('#player-name-input').input_value() == '', 'New game asks a fresh name'
        # Existing progress is safe until a valid new name is submitted.
        assert page.evaluate('__game.Q.apples.length') == 3
        page.locator('#player-name-input').fill('Tomek')
        page.locator('#player-name-submit').click()
        page.wait_for_function("__game.scene === 'play'")
        assert page.evaluate('__game.Q.apples.length') == 0, 'N must start a new game, not rename the old save'
        assert page.evaluate('__game.playerName') == 'Tomek'
        assert not errors, errors
        page.close()
    browser.close()
print('Player identity: PASS Arek label, entered-name arrival, fixed save name, N starts fresh')
