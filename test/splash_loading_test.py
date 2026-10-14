"""Logo on pure black stays up while the game assets are still loading; only a finished init reveals the selector."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8799/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "C:/Users/Lenovo/AppData/Local/hermes/cache/scratch")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="no-preference")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def delay_ground(route):
            await asyncio.sleep(3.5)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        boot = page.locator("#boot-splash")
        assert await boot.count() == 1, "HTML must paint the boot splash before game.js finishes init"
        assert await boot.is_visible(), "the logo layer must cover the blank canvas during loading"
        assert not await page.evaluate("!!window.__game"), "game must still be initializing while the logo is visible"
        assert await page.evaluate("__arkBoot.stage") == "loading"
        assert await page.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(0, 0, 0)", "loading screen is pure black"
        assert await page.evaluate("getComputedStyle(document.querySelector('#boot-splash')).backgroundColor") == "rgb(0, 0, 0)"
        assert await page.locator("#boot-splash-logo").evaluate("i => i.complete && i.naturalWidth > 0"), "compact boot logo must have loaded"
        assert (await page.locator("#boot-splash-logo").get_attribute("src")).endswith("img/boot-logo.png")
        transparent_corner = await page.locator("#boot-splash-logo").evaluate(
            """i => { const c=document.createElement('canvas'); c.width=i.naturalWidth; c.height=i.naturalHeight; const x=c.getContext('2d'); x.drawImage(i,0,0); return x.getImageData(0,0,1,1).data[3] === 0; }""")
        assert transparent_corner, "the compact logo must keep its transparent pixels, not show a black rectangle"
        await page.wait_for_timeout(1300)
        assert await page.evaluate("getComputedStyle(document.querySelector('#boot-splash-logo')).opacity") == "1", "logo stays at full opacity until init finishes"
        assert await page.evaluate("getComputedStyle(document.querySelector('#arek-global-chat')).visibility") == "hidden", "chat must stay hidden under the logo"
        await page.keyboard.press("Enter")
        await page.keyboard.press("KeyN")
        assert not await page.evaluate("!!window.__game"), "input during loading cannot start anything"
        await page.screenshot(path=f"{SHOTS}/splash-loading-mobile.png")

        await page.wait_for_function("window.__game", timeout=60000)
        await page.wait_for_function("__arkBoot.stage === 'ready'", timeout=10000)
        assert await page.locator("#player-name-input").is_visible()
        assert await page.locator("#player-name-submit").is_visible()
        assert await page.evaluate("__game.scene") == "title", "loading must not auto-start the game"
        assert not errors, errors
        await page.screenshot(path=f"{SHOTS}/splash-ready-mobile.png")
        await browser.close()
        print("Splash loading: logo on black while init is pending, input blocked, selector after init, no auto-start, no page errors")

asyncio.run(main())
