"""Yard review sheet (east1): builds, renders real images, decisions persist and export. Never touches the game."""
import json, subprocess, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='yard-review-') as tmp:
    out = Path(tmp) / 'review.html'
    r = subprocess.run([sys.executable, str(ROOT / 'gen/build_yard_review.py'), '--strip', 'east1', '--out', str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(accept_downloads=True); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(out.as_uri())
        assert pg.locator('.house').count() == 5
        n = pg.locator('.card').count(); assert n == 27
        assert pg.locator('.card:not(.house)').count() == 22
        assert pg.locator('.house .map img').count() == 5
        assert pg.locator('#copy').inner_text() == 'Kopiuj JSON'
        pg.wait_for_function('Array.from(document.images).filter(i=>i.src).every(i=>i.complete&&i.naturalWidth>0)')
        assert pg.locator('#progress').inner_text() == f'22 / {n} rozstrzygniętych'
        assert pg.locator('[data-id="house-909989528"] .decision').input_value() == 'regen'
        h = pg.locator('.house').first; h.locator('.decision').select_option('regen'); h.locator('.note').fill('za niski')
        pending = pg.locator('[data-id="east1-23-p3"]'); pending.locator('.decision').select_option('add'); pending.locator('.identification').fill('kupa drewna')
        pg.reload()
        assert pg.locator('#progress').inner_text() == f'23 / {n} rozstrzygniętych'
        assert pg.locator('.house').first.locator('.note').input_value() == 'za niski'
        with pg.expect_download() as d: pg.locator('#export').click()
        data = json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
        assert data['gameChangesApplied'] is False and data['strip'] == 'east1'
        assert sum(v['decision'] != 'pending' for v in data['decisions'].values()) == 23
        assert not errs, errs
        b.close()
print('yard review east1: PASS', n, 'cards')
