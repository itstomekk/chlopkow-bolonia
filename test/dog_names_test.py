"""User-visible companion references follow the selected dog, including Polish cases.
Run through isolated_browser_runner against a dedicated local docs server.
"""
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as p:
    browser = p.chromium.launch()
    for dog, expected_nom, expected_gen in [
        ("frodo", "Frodo", "Froda"),
        ("wajper", "Wajper", "Wajpera"),
    ]:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script("""window.__captionTexts=[];
          const fill=CanvasRenderingContext2D.prototype.fillText;
          CanvasRenderingContext2D.prototype.fillText=function(text,...args){window.__captionTexts.push(String(text));return fill.call(this,text,...args);};""")
        page.goto(BASE + "?dog=" + dog)
        page.wait_for_function("window.__game")
        assert page.evaluate("window.CHLOPKOW_DOG.id") == dog
        assert page.evaluate("window.ARK.dogName") == expected_nom
        rendered = page.evaluate("""async () => {
          const A = window.ARK;
          return {
            dialogue: A.heroText(A.T.edytka0[0]),
            after: A.heroText(A.T.edytkaAfter[0]),
            genitive: A.heroText('Pozdrów Froda.'),
            toast: A.heroText('FRODO 2/3'),
            oldForms: A.heroText('FRODO / FRODA / Frodo / Froda'),
            english: A.heroText('Bring Frodo to Edytka'),
            music: A.heroText('FRODO: WĘSZĘ KŁOPOTY.'),
            tunnel: A.heroText((await fetch('data/tunnel-church-cemetery.json').then(r => r.json())).text.en.tunnelFirst[1]),
            quest: A.heroText(A.T.edytkaQuest),
          };
        }""")
        assert rendered["dialogue"].startswith(f"{expected_nom}!"), rendered
        assert rendered["after"].startswith(f"Pozdrów {expected_gen}."), rendered
        assert rendered["genitive"] == f"Pozdrów {expected_gen}.", rendered
        assert rendered["toast"] == f"{expected_nom.upper()} 2/3", rendered
        assert rendered["oldForms"] == f"{expected_nom.upper()} / {expected_gen.upper()} / {expected_nom} / {expected_gen}", rendered
        assert rendered["english"] == f"Bring {expected_nom} to Edytka", rendered
        assert rendered["music"] == f"{expected_nom.upper()}: WĘSZĘ KŁOPOTY.", rendered
        assert f"{expected_nom} walks on four paws" in rendered["tunnel"], rendered
        assert expected_gen in rendered["quest"], rendered
        page.keyboard.press("KeyN")
        page.locator("#player-name-input").fill("Dog name check")
        page.keyboard.press("Enter")
        page.wait_for_function("window.__game.scene === 'play'")
        page.evaluate("""() => { const F=window.__game.FRODO, P=window.__game.P; F.x=P.x; F.y=P.y; F.moving=false; }""")
        page.wait_for_function("n => window.__captionTexts.some(t => t.startsWith(n + ':'))", arg=expected_nom.upper(), timeout=5000)
        assert not errors, errors
        page.close()
    browser.close()
print("PASS dog_names: Frodo/Wajper nominative, genitive, dialogue, toast, quest and music caption")
