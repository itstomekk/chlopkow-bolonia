"""Focused browser checks for the standalone shop interior and groszowy shopping game.
Usage: python test/shop_test.py [URL] (serve docs on port 8765 first)."""
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    script_url = URL.rsplit("/", 1)[0] + "/js/shop.js"
    response = page.request.get(script_url)
    assert response.ok, f"shop.js is missing or unreadable: HTTP {response.status}"
    page.add_script_tag(url=script_url)
    page.wait_for_function("typeof window.buildShop === 'function' && !!window.ShopGame")

    room = page.evaluate("""() => {
      const r = buildShop(), required = ['w','h','top','ground','obj','objects','solid','pois','spawn','exit'];
      return {r, keys: required.every(k => Object.hasOwn(r,k)),
        sizes: r.ground.width === r.w && r.ground.height === r.h && r.obj.width === r.w && r.obj.height === r.h && r.solid.length === r.w*r.h,
        allPois: r.pois.map(p => p.key), solid: r.solid};
    }""")
    assert room["keys"], "buildShop must return all room fields expected by buildChurch/game.js"
    assert room["sizes"], "room canvases and solid map must use matching dimensions"
    assert all(key in room["allPois"] for key in ["bread", "produce", "scale", "bitcoin"]), room["allPois"]
    assert room["r"]["w"] <= 640 and room["r"]["h"] >= 320
    assert room["r"]["spawn"]["y"] < room["r"]["exit"]["y"]
    assert room["r"]["exit"]["x0"] < room["r"]["exit"]["x1"]
    assert room["solid"][int(room["r"]["spawn"]["y"]) * room["r"]["w"] + int(room["r"]["spawn"]["x"])] == 0, "spawn must be walkable"
    assert room["solid"][432 * room["r"]["w"] + 160] == 0, "door opening must remain clear"
    assert any(v == 2 for v in room["solid"]), "shelves/counter should block walking"

    api = page.evaluate("""() => ({
      quote: ShopGame.quote({tomatoesGrams: 750, tomatoPricePerKgGrosz: 800,
        breadGrosz: 320, beerGrosz: 350, cashGrosz: 2000}),
      create: typeof ShopGame.create,
      })""")
    assert api["create"] == "function", "ShopGame.create should mount a playable overlay"
    assert api["quote"]["tomatoesGrosz"] == 600
    assert api["quote"]["totalGrosz"] == 1270
    assert api["quote"]["changeGrosz"] == 730
    assert page.evaluate("ShopGame.quote({tomatoesGrams:751}).tomatoesGrosz") == 601, "tomato multiplication must round to a whole grosz"

    game = page.evaluate("""() => {
      const game = ShopGame.create({timeLimitMs: 12000});
      document.body.appendChild(game.element);
      game.start();
      return {prompt: game.element.querySelector('[data-shop-question]').textContent,
        input: !!game.element.querySelector('[data-shop-answer]'),
        submit: !!game.element.querySelector('[data-shop-submit]'),
        credit: !!game.element.querySelector('[data-shop-credit]'),
        negotiated: !!game.element.querySelector('[data-shop-credit-amount]')};
    }""")
    assert "pomn" in game["prompt"].lower() or "razy" in game["prompt"].lower(), game["prompt"]
    assert game["input"] and game["submit"] and game["credit"] and game["negotiated"], "game needs touch-friendly answer and credit controls"

    # Solve the exact integer-grosz steps: weighted tomato price, basket sum, cash change.
    for answer in ["600", "1270", "730"]:
        page.locator('[data-shop-answer]').fill(answer)
        page.locator("[data-shop-submit]").click()
    result = page.evaluate("""() => {
      const root = document.querySelector('[data-shop-game]');
      return {text: root.innerText, state: root.dataset.phase,
        credit: root.querySelector('[data-shop-credit-status]').textContent};
    }""")
    assert result["state"] == "complete", result
    assert "730" in result["text"] and "grosz" in result["text"].lower(), result
    assert "0" in result["credit"], result

    # A player can negotiate game-only store credit, without creating a real debt.
    page.evaluate("""() => { const g=ShopGame.create({timeLimitMs:12000}); document.body.appendChild(g.element); g.start(); g.element.querySelector('[data-shop-credit-amount]').value='217'; g.element.querySelector('[data-shop-credit]').click(); }""")
    credit = page.evaluate("""() => { const root = [...document.querySelectorAll('[data-shop-game]')].at(-1); return {phase: root.dataset.phase,
      amount: root.dataset.creditGrosz,
      copy: root.innerText}; }""")
    assert credit["phase"] == "complete" and int(credit["amount"]) == 217, credit
    assert "grze" in credit["copy"].lower() and "dług" in credit["copy"].lower(), credit

    page.evaluate("""() => { const g=ShopGame.create({timeLimitMs:1000}); document.body.appendChild(g.element); g.start(); }""")
    page.wait_for_function("[...document.querySelectorAll('[data-shop-game]')].at(-1).dataset.phase === 'timeout'", timeout=3000)
    assert page.evaluate("[...document.querySelectorAll('[data-shop-game]')].at(-1).dataset.phase") == "timeout"
    assert not errors, errors
    print("shop OK — room geometry, collision/art POIs, exact grosz math, mobile inputs, store-credit completion; errors", errors)
    browser.close()
