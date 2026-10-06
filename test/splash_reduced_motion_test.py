"""prefers-reduced-motion shortens, but does not erase, the requested startup sequence."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8800/index.html")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def delay_ground(route):
            await asyncio.sleep(1.0)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_function("document.querySelector('#boot-splash img').classList.contains('loaded')")
        await page.wait_for_function("(() => { const o=Number(getComputedStyle(document.querySelector('#boot-splash img')).opacity); return o > .2 && o < .9; })()", timeout=2500)
        await page.wait_for_function("document.querySelector('#boot-splash').dataset.state === 'fading'", timeout=60000)
        await page.wait_for_function("(() => { const o=Number(getComputedStyle(document.querySelector('#boot-splash')).opacity); return o > .35 && o < .65; })()", timeout=2500)
        mid_fade = await page.evaluate("""() => ({
          stage:window.__game.openingStage,
          pixelBlock:window.__openingPixelBlock,
          uiAlpha:window.__openingUiAlpha
        })""")
        assert mid_fade["stage"] == "reveal", mid_fade
        assert isinstance(mid_fade["pixelBlock"], (int, float)) and mid_fade["pixelBlock"] >= 12, f"reduced-motion mode still needs a visible short pixel reveal: {mid_fade}"
        assert mid_fade["uiAlpha"] == 0, f"HUD/instructions must wait until the shortened logo fade finishes: {mid_fade}"
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-reduced-motion-fade.png", full_page=True)
        await page.wait_for_function("document.querySelector('#boot-splash').dataset.state === 'hidden'", timeout=2500)
        await page.wait_for_function("__game.openingStage === 'selector'", timeout=2500)
        assert await page.locator("#player-name-input").is_visible()
        assert await page.evaluate("__game.scene") == "title"
        assert not errors, errors
        await browser.close()
        print(f"Reduced-motion startup verified: shortened logo fades with {mid_fade['pixelBlock']}px board blocks; HUD waits until logo is gone; selector works; no errors")

asyncio.run(main())
