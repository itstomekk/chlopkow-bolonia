"""Boot brand remains visible while game assets/init are pending, then hands off to the pixel reveal."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8799/index.html")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def delay_ground(route):
            await asyncio.sleep(3.5)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        boot = page.locator("#boot-splash")
        assert await boot.count() == 1, "HTML must paint a boot splash before game.js finishes init"
        assert await boot.is_visible(), "boot logo layer must cover the blank canvas during loading"
        assert not await page.evaluate("!!window.__game"), "game must still be initializing while the boot logo is visible"
        assert await page.locator("#boot-splash img").evaluate("i => i.complete && i.naturalWidth > 0"), "small boot logo asset must have loaded"
        transparent_corner = await page.locator("#boot-splash img").evaluate("""i => { const c=document.createElement('canvas'); c.width=i.naturalWidth; c.height=i.naturalHeight; const x=c.getContext('2d'); x.drawImage(i,0,0); return x.getImageData(0,0,1,1).data[3] === 0; }""")
        assert transparent_corner, "the compact logo must preserve transparent pixels, not show a black rectangle"
        await page.wait_for_timeout(1300)
        chat_hidden = await page.evaluate("getComputedStyle(document.querySelector('#arek-global-chat')).visibility === 'hidden'")
        assert chat_hidden, "global chat label must stay hidden underneath the boot logo until the game is ready"
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\boot-loading-mobile.png", full_page=True)

        await page.wait_for_function("window.__game", timeout=60000)
        await page.wait_for_function("document.querySelector('#boot-splash').dataset.state === 'hidden'", timeout=5000)
        await page.wait_for_function("__game.openingStage === 'selector'", timeout=8000)
        assert await page.locator("#player-name-input").is_visible()
        assert await page.locator("#player-name-submit").is_visible()
        assert await page.evaluate("__game.scene") == "title", "opening sequence must not auto-start"
        assert not errors, errors
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-local-mobile.png", full_page=True)
        await browser.close()
        print("Splash handoff: boot logo covers loading, then pixel reveal + selector; no auto-start; no page errors")

asyncio.run(main())
