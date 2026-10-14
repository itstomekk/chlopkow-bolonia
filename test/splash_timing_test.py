"""Reveal order: logo fades out only after init -> full black frame -> map + selector fade in -> ready (overlay gone)."""
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
  window.__logoSamples = [];
  const sample = () => {
    const l = document.querySelector('#boot-splash-logo');
    if (l) window.__logoSamples.push(Number(getComputedStyle(l).opacity));
    if (!window.__bootDone) requestAnimationFrame(sample);
  };
  requestAnimationFrame(sample);
})()"""

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8799/index.html")
SHOTS = os.environ.get("ARK_SHOTS", "C:/Users/Lenovo/AppData/Local/hermes/cache/scratch")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        await page.emulate_media(reduced_motion="no-preference")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.add_init_script(STAGE_RECORDER)

        async def delay_ground(route):
            await asyncio.sleep(1.0)
            await route.continue_()

        await page.route("**/img/map_ground.png", delay_ground)
        await page.goto(URL, wait_until="domcontentloaded")
        assert await page.locator("#boot-splash").is_visible()
        assert not await page.evaluate("!!window.__game"), "logo appears before the game is ready"

        await page.wait_for_function("__arkBoot.stage === 'logo-out'", timeout=60000)
        await page.wait_for_function("__arkBoot.stage === 'black'", timeout=3000)
        black = await page.evaluate("""() => ({logo: getComputedStyle(document.querySelector('#boot-splash-logo')).opacity,
          overlay: getComputedStyle(document.querySelector('#boot-splash')).opacity,
          bg: getComputedStyle(document.querySelector('#boot-splash')).backgroundColor})""")
        assert black == {"logo": "0", "overlay": "1", "bg": "rgb(0, 0, 0)"}, f"full black frame must contain no logo: {black}"
        await page.screenshot(path=f"{SHOTS}/splash-black-mobile.png")

        await page.wait_for_function("__arkBoot.stage === 'map-in'", timeout=3000)
        mid = await page.evaluate("""() => {
          const o = document.querySelector('#boot-splash'), input = document.querySelector('#player-name-input');
          const r = input.getBoundingClientRect(), top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
          return {logo: getComputedStyle(document.querySelector('#boot-splash-logo')).opacity, blocked: o.contains(top), game: !!window.__game};
        }""")
        assert mid["logo"] == "0" and mid["game"], f"the logo must not return during the map reveal: {mid}"
        assert mid["blocked"], "the reveal overlay must still block clicks on the selector"
        await page.wait_for_function("__arkBoot.stage === 'ready'", timeout=5000)
        assert await page.evaluate("getComputedStyle(document.querySelector('#boot-splash')).display") == "none"
        await page.evaluate("window.__bootDone = true")
        samples = await page.evaluate("__logoSamples")
        assert samples[0] == 1 and any(.1 < s < .9 for s in samples), f"the logo must fade out smoothly, not cut: {samples[:4]}...{samples[-4:]}"
        stages = await page.evaluate("__bootStages")
        order = [s["stage"] for s in stages]
        assert order == ["logo-out", "black", "map-in", "ready"], order
        assert stages[0]["game"], "the logo may only start fading after real game init finished"
        assert [round(s["t"]) for s in stages] == sorted(round(s["t"]) for s in stages)
        assert await page.evaluate("__game.scene") == "title" and await page.locator("#player-name-input").is_visible()
        assert not errors, errors
        await browser.close()
        print(f"Splash timing: {order} (logo-out starts only after init), black frame without logo, overlay blocks input until ready")

asyncio.run(main())
