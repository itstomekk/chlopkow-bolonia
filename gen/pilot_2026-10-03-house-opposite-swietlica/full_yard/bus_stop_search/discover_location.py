"""Public pano metadata discovery in a driver-owned headless Chromium."""
import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent
PANOS=['FwXCydlXslK6XYsWNsaaFw','d1exMEfDQSY24_dp_stAuw','x6Y_xD3hv503c0IX3yAAag']
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--enable-unsafe-swiftshader'])
    ctx=browser.new_context(locale='en-US',viewport={'width':1280,'height':800})
    page=ctx.new_page()
    records=[]
    captures=[]
    def response(r):
        if 'photometa' in r.url:
            try:
                text=r.text(); captures.append({'url':r.url,'text':text})
            except Exception: pass
    page.on('response',response)
    for pano in PANOS:
        captures.clear()
        page.goto(f'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=52.26428,22.87490&heading=298',wait_until='domcontentloaded',timeout=60000)
        page.wait_for_timeout(6500)
        rec={'panoid':pano,'final_url':page.url,'text':page.inner_text('body')[:1000],'captures':list(captures)}
        records.append(rec)
        (OUT/'pano_metadata.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print(pano, page.url, len(captures), flush=True)
    browser.close()
