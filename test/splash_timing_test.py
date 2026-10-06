"""Verify the logo-to-pixel-reveal handoff and delayed title HUD."""
import asyncio
import os
from playwright.async_api import async_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8799/index.html")

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
        boot = page.locator("#boot-splash")
        assert await boot.is_visible()
        assert not await page.evaluate("!!window.__game"), "boot logo should appear before game readiness"
        await page.wait_for_function("(() => { const i=document.querySelector('#boot-splash img'); const a=Number(getComputedStyle(i).opacity); return i.classList.contains('loaded') && a > .25 && a < .75; })()", timeout=3000)
        intro = await page.evaluate("""() => ({opacity:Number(getComputedStyle(document.querySelector('#boot-splash img')).opacity),
          state:document.querySelector('#boot-splash').dataset.state, revealStarted:window.__bootRevealStarted})""")
        assert intro["state"] is None and intro["revealStarted"] is False, f"logo must emerge from black before the handoff: {intro}"
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-logo-in-mobile.png", full_page=True)

        await page.wait_for_function("window.__game && document.querySelector('#boot-splash').dataset.state === 'fading'", timeout=60000)
        await page.wait_for_function("(() => { const a=Number(getComputedStyle(document.querySelector('#boot-splash')).opacity); return a > .35 && a < .65; })()", timeout=3000)
        midpoint = await page.evaluate("""() => {
          const boot=document.querySelector('#boot-splash'), c=document.querySelector('canvas'), x=c.getContext('2d');
          const d=x.getImageData(0,0,c.width,c.height).data, colors=new Set();
          for(let y=0;y<c.height;y+=Math.max(1,Math.floor(c.height/24)))
            for(let px=0;px<c.width;px+=Math.max(1,Math.floor(c.width/24))) {
              const i=(y*c.width+px)*4; colors.add(`${d[i]},${d[i+1]},${d[i+2]}`);
            }
          return {opacity:Number(getComputedStyle(boot).opacity), stage:window.__game.openingStage,
            uiAlpha:window.__openingUiAlpha, scene:window.__game.scene, sampledColors:colors.size,
            nameField:!!document.querySelector('#player-name-input')};
        }""")
        assert midpoint["stage"] == "reveal", midpoint
        assert midpoint["scene"] == "title", midpoint
        assert midpoint["sampledColors"] > 20, f"village should already be pixel-revealing under the fading logo: {midpoint}"
        assert midpoint["uiAlpha"] == 0, f"HUD/instructions must remain hidden during the logo fade: {midpoint}"
        assert not midpoint["nameField"], "name prompt/HUD must not appear while logo is still fading"
        await page.screenshot(path=r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\splash-fade-mobile.png", full_page=True)

        await page.wait_for_function("document.querySelector('#boot-splash').dataset.state === 'hidden'", timeout=3000)
        assert await page.evaluate("__game.openingStage") == "reveal", "logo should finish fading before the selector/HUD phase"
        assert not await page.locator("#player-name-input").count(), "name prompt must wait until after the logo disappears"
        await page.wait_for_function("window.__openingUiAlpha > 0", timeout=3000)
        assert await page.locator("#boot-splash").get_attribute("data-state") == "hidden", "HUD must begin only after the logo is gone"
        await page.wait_for_function("__game.openingStage === 'selector'", timeout=3000)
        assert await page.locator("#player-name-input").is_visible()
        assert await page.evaluate("__game.scene") == "title", "the opening must not auto-start"
        assert not errors, errors
        await browser.close()
        print(f"Fade overlap verified: logo opacity {midpoint['opacity']:.2f}, pixelated board visible, UI delayed until after logo, no auto-start/errors")

asyncio.run(main())
