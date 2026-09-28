"""Enter the live shop, shop at the counter, save the result and leave through the door."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get('ARK_URL', 'http://127.0.0.1:8765/index.html')

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(URL)
    page.wait_for_function('window.__game')
    assert page.evaluate("typeof window.buildShop === 'function'"), 'shop.js must load before game.js'
    page.evaluate('localStorage.clear()')
    page.reload()
    page.wait_for_function('window.__game')
    page.keyboard.press('Enter')
    page.locator('#player-name-input').fill('Kupujący')
    page.locator('#player-name-submit').click()
    page.wait_for_function("__game.scene === 'play'")
    shop = page.evaluate("__game.MAP.pois.find(p => p.key === 'shop')")
    assert shop, 'shop location missing'
    page.evaluate("p => { __game.P.x=p.x; __game.P.y=p.y; }", shop)
    page.keyboard.press('KeyE')
    page.wait_for_function("__game.room && __game.room.kind === 'shop'")
    page.evaluate("() => { __game.Q.marcin=1; ARK.save(); }")
    page.evaluate("() => {__game.P.x=160; __game.P.y=342;}")
    page.keyboard.press('KeyE')
    page.locator('[data-shop-game]').wait_for()
    assert page.evaluate("__game.scene === 'play' && __game.room.kind === 'shop'")
    page.locator('[data-shop-start]').click()
    for answer in ['600', '1270', '730']:
        page.locator('[data-shop-answer]').fill(answer)
        page.locator('[data-shop-submit]').click()
    assert page.locator('[data-shop-game]').get_attribute('data-phase') == 'complete'
    page.locator('[data-shop-close]').click()
    assert page.evaluate("__game.Q.shopGames >= 1 && !!JSON.parse(localStorage.getItem('arek-chlopkow-save-v1')).Q.shopGames")
    assert page.evaluate("__game.Q.orange === true"), 'shopping should still provide Marcin’s orangeade'
    page.evaluate("() => { __game.P.x=160; __game.P.y=426; }")
    page.keyboard.down('ArrowDown')
    page.wait_for_function('!__game.room', timeout=5000)
    page.keyboard.up('ArrowDown')
    assert not errors, errors
    print('Shop integration OK: enter, arithmetic game, persisted result, exit')
    browser.close()
