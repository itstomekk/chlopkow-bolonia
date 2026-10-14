"""prefers-reduced-motion keeps the same order (logo -> black -> map) with zero-length transitions."""
import asyncio
import os
from playwright.async_api import async_playwright

STAGE_RECORDER = """(() => {
  window.__bootStages = [];
  const t0 = performance.now();
  new MutationObserver(records => records.forEach(r => {
    const s = r.target.dataset.bootStage;
    if (s) window.__bootStages.push({stage: s, t: performance.now() - t0, game: !!window.__game,
      logo: getComputedStyle(document.querySelector('#boot-splash-logo')).opacity,
      overlay: getComputedStyle(r.target).opacity});
  })).observe(document, {subtree: true, attributes: true, attributeFilter: ['data-boot-stage']});
})()"""

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8800/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "C:/Users/Lenovo/AppData/Local/hermes/cache/scratch")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.add_init_script(STAGE_RECORDER)

        async def delay_ground(route):
            await asyncio.sleep(1.0)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        assert await page.evaluate("__arkBoot.stage") == "loading" and await page.locator("#boot-splash").is_visible()
        assert await page.evaluate("getComputedStyle(document.querySelector('#boot-splash')).transitionDuration") == "0s"
        assert await page.evaluate("getComputedStyle(document.querySelector('#boot-splash-logo')).transitionDuration") == "0s"
        await page.screenshot(path=f"{SHOTS}/splash-reduced-motion-loading.png")
        await page.wait_for_function("__arkBoot.stage === 'ready'", timeout=60000)
        stages = await page.evaluate("__bootStages")
        order = [s["stage"] for s in stages]
        assert order == ["logo-out", "black", "map-in", "ready"], order
        black = next(s for s in stages if s["stage"] == "black")
        assert black["logo"] == "0" and black["overlay"] == "1", black
        assert stages[-1]["t"] - stages[0]["t"] < 1500, f"reduced motion must be near-instant: {stages}"
        assert await page.evaluate("__game.scene") == "title" and await page.locator("#player-name-input").is_visible()
        assert not errors, errors
        await browser.close()
        print(f"Reduced-motion startup: {order} with zero-length transitions; selector ready; no errors")

asyncio.run(main())
