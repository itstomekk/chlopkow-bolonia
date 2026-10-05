"""Portable satellite uncertainty sheet: real imagery, no game writes, decisions round-trip."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'gen/build_yard_evidence_review.py'
with tempfile.TemporaryDirectory(prefix='yard-review-') as tmp:
    output = Path(tmp) / 'review.html'
    result = subprocess.run([sys.executable, str(BUILDER), '--out', str(output)], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, 'review builder missing or failed: ' + result.stderr
    assert output.is_file()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(output.as_uri())
        assert page.locator('.candidate').count() == 6
        page.wait_for_function('Array.from(document.querySelectorAll("img[src]")).every(i => i.complete && i.naturalWidth > 0)')
        assert page.locator('img[src]').count() == 8
        assert page.evaluate('Array.from(document.querySelectorAll("img[src]")).every(i => i.src.startsWith("data:image/"))')
        assert page.locator('.candidate[data-id="j12-15-object"] .confidence').text_content() == 'Niska'
        assert page.locator('#progress').inner_text() == '0 / 6 rozstrzygniętych'
        card = page.locator('.candidate').first
        card.locator('.decision').select_option('add')
        card.locator('.identification').fill('krzewy')
        card.locator('.note').fill('Zostaw przejście do domu.')
        assert page.locator('#progress').inner_text() == '1 / 6 rozstrzygniętych'
        page.reload()
        assert page.locator('.candidate').first.locator('.decision').input_value() == 'add'
        assert page.locator('.candidate').first.locator('.note').input_value() == 'Zostaw przejście do domu.'
        page.locator('#filter').select_option('pending')
        assert page.locator('.candidate:visible').count() == 5
        page.locator('#filter').select_option('all')
        with page.expect_download() as download:
            page.locator('#export').click()
        payload = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
        assert payload['review'] == 'yard-evidence-j12-v1'
        assert len(payload['decisions']) == 6
        assert payload['decisions']['j12-15-vegetation'] == {
            'decision': 'add', 'identification': 'krzewy', 'note': 'Zostaw przejście do domu.'}
        assert payload['decisions']['j12-15-object']['decision'] == 'pending'
        assert payload['gameChangesApplied'] is False
        assert 'denseFarmyards' in payload['policy']
        # Copy and download must carry the same schema and current choices.
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:async text=>{window.__copiedJSON=text;}}})")
        page.locator('#copy').click()
        page.wait_for_function('window.__copiedJSON')
        assert json.loads(page.evaluate('window.__copiedJSON')) == payload
        # file:// and denied clipboard permissions need an honest manual fallback.
        page.evaluate("navigator.clipboard.writeText=async()=>{throw Error('denied')}; document.execCommand=()=>false")
        page.locator('#copy').click()
        page.wait_for_function('document.querySelector("#copy-json").hidden === false')
        assert json.loads(page.locator('#copy-json').input_value()) == payload
        assert page.locator('#copy-json').evaluate('(el)=>el.selectionEnd-el.selectionStart') > 0
        good = Path(tmp) / 'import.json'
        payload['decisions']['j12-15-vegetation']['decision'] = 'skip'
        good.write_text(json.dumps(payload), encoding='utf-8')
        page.locator('#import').set_input_files(str(good))
        page.wait_for_function('document.querySelector("#notice").textContent.startsWith("Wczytano decyzje.")')
        assert page.locator('.candidate').first.locator('.decision').input_value() == 'skip'
        bad = Path(tmp) / 'bad.json'
        bad.write_text('{"review":"wrong","decisions":{}}', encoding='utf-8')
        page.locator('#import').set_input_files(str(bad))
        page.wait_for_function('document.querySelector("#notice").textContent.startsWith("Nie wczytano:")')
        assert page.locator('#notice').inner_text().startswith('Nie wczytano:')
        assert page.locator('.candidate').first.locator('.decision').input_value() == 'skip'
        seeded = Path(tmp) / 'seeded.html'
        # Seed load ignores old pending answers, but edits after loading persist.
        seed_payload = dict(payload)
        for entry in seed_payload['decisions'].values():
            entry['decision'] = 'skip'
        good.write_text(json.dumps(seed_payload), encoding='utf-8')
        result = subprocess.run([sys.executable, str(BUILDER), '--out', str(seeded), '--decisions', str(good)],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        page.goto(seeded.as_uri())
        assert page.locator('#progress').inner_text() == '6 / 6 rozstrzygniętych'
        page.locator('.candidate').first.locator('.decision').select_option('better-photo')
        page.reload()
        assert page.locator('.candidate').first.locator('.decision').input_value() == 'better-photo'
        assert not errors, errors
        browser.close()
print('yard evidence review: PASS (6 real crops, persistence, filter, import/export, copy/fallback, seeded decisions)')
