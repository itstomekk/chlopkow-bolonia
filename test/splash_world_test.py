"""The startup reveals the real village board and never brings the crest back."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8800/index.html")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="no-preference")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def delay_ground(route):
            await asyncio.sleep(1.0)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        assert await page.locator("#boot-splash").is_visible()
        assert not await page.evaluate("!!window.__game")

        await page.wait_for_function("window.__game && document.querySelector('#boot-splash').dataset.state === 'fading'", timeout=60000)
        await page.wait_for_function("(() => { const a=Number(getComputedStyle(document.querySelector('#boot-splash')).opacity); return a > .35 && a < .65; })()", timeout=3000)
        transition = await page.evaluate("""() => ({
          stage:window.__game.openingStage,
          pixelBlock:window.__openingPixelBlock,
          uiAlpha:window.__openingUiAlpha,
          oldTitleArtRequested:performance.getEntriesByType('resource').some(e=>e.name.includes('/img/splash.png')),
          crestRequested:performance.getEntriesByType('resource').some(e=>e.name.includes('/img/chlopkow-polonia-logo.png'))
        })""")
        assert transition["stage"] == "reveal", transition
        assert isinstance(transition["pixelBlock"], (int, float)) and transition["pixelBlock"] >= 12, f"pixel blocks must be unmistakable during logo fade: {transition}"
        assert transition["uiAlpha"] == 0, f"HUD/instructions stay hidden while logo fades: {transition}"
        assert not transition["oldTitleArtRequested"], f"reveal must use the actual game board, not the static splash illustration: {transition}"
        assert not transition["crestRequested"], f"boot crest must not be loaded for a later duplicate title phase: {transition}"
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-real-board-fade.png", full_page=True)

        await page.wait_for_function("document.querySelector('#boot-splash').dataset.state === 'hidden'", timeout=5000)
        await page.wait_for_function("__game.openingStage === 'selector'", timeout=5000)
        assert await page.locator("#player-name-input").is_visible()
        assert await page.evaluate("__game.scene") == "title"
        await page.wait_for_timeout(5600)
        assert await page.evaluate("__game.openingStage") == "selector", "the crest must not reappear after the selector is on screen"
        assert await page.locator("#player-name-input").is_visible()
        assert not errors, errors
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-real-board-title.png", full_page=True)
        await browser.close()
        print(f"Real-board reveal verified: {transition['pixelBlock']}px cells during fade; no static title art/crest; HUD after logo; selector persists; no auto-start/errors")

asyncio.run(main())
