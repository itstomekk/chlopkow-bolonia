"""Yard review sheet (east1): renders sources, map context, seeded decisions and working copy/export. No game writes."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="yard-review-") as tmp:
    out = Path(tmp) / "review.html"
    r = subprocess.run([sys.executable, str(ROOT / "gen/build_yard_review.py"), "--strip", "east1", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(accept_downloads=True); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.add_init_script("Object.defineProperty(navigator,'clipboard',{value:undefined,configurable:true})")
        pg.goto(out.as_uri())
        assert pg.locator(".house").count() == 5
        assert pg.locator(".card:not(.house)").count() == 22
        assert pg.locator("#copy").inner_text() == "Kopiuj JSON"
        assert pg.locator(".house .map img").count() == 5
        pg.wait_for_function("Array.from(document.images).filter(i=>i.src).every(i=>i.complete&&i.naturalWidth>0)")
        assert pg.evaluate("[...document.querySelectorAll('.house .map img')].every(i=>i.naturalWidth>100)")
        assert pg.locator("#progress").inner_text() == "22 / 27 rozstrzygniętych"
        assert pg.locator('[data-id="house-909989528"] .decision').input_value() == "regen"
        assert pg.locator('[data-id="house-909988586"] .note').input_value().startswith("zostaje, ale")
        assert pg.locator('[data-id="east1-19-p5"] .identification').input_value() == "drzewka iglaste po prawej a po lewej czeresnie"
        pg.locator("#copy").click()
        pg.wait_for_function("document.querySelector('#notice').textContent.includes('JSON')")
        copied = json.loads(pg.locator("#copyFallback").input_value())
        assert copied["review"] == "yard-review-east1-v3" and copied["gameChangesApplied"] is False
        assert copied["decisions"]["east1-19-p5"]["identification"] == "drzewka iglaste po prawej a po lewej czeresnie"
        pending = pg.locator('[data-id="east1-23-p3"]')
        pending.locator(".decision").select_option("add"); pending.locator(".identification").fill("śliwa")
        pg.reload()
        assert pg.locator("#progress").inner_text() == "23 / 27 rozstrzygniętych"
        assert pg.locator('[data-id="east1-23-p3"] .identification').input_value() == "śliwa"
        with pg.expect_download() as d:
            pg.locator("#export").click()
        data = json.loads(Path(d.value.path()).read_text(encoding="utf-8"))
        assert data["gameChangesApplied"] is False and data["strip"] == "east1"
        assert data["decisions"]["east1-19-p5"]["identification"] == "drzewka iglaste po prawej a po lewej czeresnie"
        assert len(data["decisions"]) == 27 and not errs, errs
        b.close()
print("yard review east1 v3: PASS — 5 map-context houses, 22 unique prop questions, exact JSON copy/export/import")
