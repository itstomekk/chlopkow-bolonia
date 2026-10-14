"""After the reveal the real village board is under the selector; no static title art, crest or pixel-reveal comes back."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8800/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "C:/Users/Lenovo/AppData/Local/hermes/cache/scratch")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="no-preference")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(URL, wait_until="domcontentloaded")
        await page.wait_for_function("window.__game && __arkBoot.stage === 'ready'", timeout=60000)
        info = await page.evaluate("""() => {
          const c = document.querySelector('#game'), x = c.getContext('2d'), colors = new Set();
          const d = x.getImageData(0, 0, c.width, c.height).data;
          for (let y = 0; y < c.height; y += Math.max(1, Math.floor(c.height / 24)))
            for (let px = 0; px < c.width; px += Math.max(1, Math.floor(c.width / 24))) {
              const i = (y * c.width + px) * 4; colors.add(d[i] + ',' + d[i + 1] + ',' + d[i + 2]);
            }
          const res = performance.getEntriesByType('resource').map(e => e.name);
          return {colors: colors.size, stage: __game.openingStage, scene: __game.scene,
            oldArt: res.some(n => n.includes('/img/splash.png')),
            crest: res.some(n => n.includes('/img/chlopkow-polonia-logo.png')),
            pixelReveal: window.__openingPixelBlock !== undefined || window.__openingUiAlpha !== undefined,
            overlayGone: getComputedStyle(document.querySelector('#boot-splash')).display === 'none'};
        }""")
        assert info["colors"] > 20, f"the live village board must be visible under the selector: {info}"
        assert info["stage"] == "selector" and info["scene"] == "title", info
        assert not info["oldArt"], f"the static splash illustration must not load: {info}"
        assert not info["crest"], f"the full-size crest must not load (the compact boot logo is the only logo): {info}"
        assert not info["pixelReveal"], f"the canvas pixel reveal is gone: {info}"
        assert info["overlayGone"]
        await page.screenshot(path=f"{SHOTS}/splash-real-board-title.png")
        await page.wait_for_timeout(5600)
        assert await page.evaluate("__game.openingStage") == "selector", "no timed crest phase after the selector is up"
        assert await page.locator("#player-name-input").is_visible() and await page.locator("#player-name-submit").is_visible()
        assert await page.evaluate("__game.scene") == "title"
        assert not errors, errors
        await browser.close()
        print("Splash world: live board under the selector, no static art/crest/pixel reveal, selector persists, no auto-start")

asyncio.run(main())
