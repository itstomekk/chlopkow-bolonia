"""Record a short real-time BIJATYKA demo (all fighters CPU-driven) for visual review.

Run: python test/isolated_browser_runner.py gen/brawl/record_demo.py URL OUT_DIR [seconds] [f1,f2,f3,f4] [stage] [start_x]
Writes OUT_DIR/demo.webm and numbered PNG snapshots.
"""
import os, sys, glob, shutil
from playwright.sync_api import sync_playwright

URL, OUT = sys.argv[1], sys.argv[2]
SECS = float(sys.argv[3]) if len(sys.argv) > 3 else 14
FIGHT = (sys.argv[4] if len(sys.argv) > 4 else 'arek,edytka,arek,edytka').split(',')
STAGE = sys.argv[5] if len(sys.argv) > 5 else 'farmyard'
START = float(sys.argv[6]) if len(sys.argv) > 6 else 0   # scrolling stages: left edge of the view at the start (game px)
os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
    page = ctx.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_function("window.ARK && window.ARK.brawl")
    page.evaluate("window.ARK.brawl.open()")
    page.evaluate("window.ARK.brawl.loaded()")
    page.evaluate("window.ARK.brawl.setOpts({stage:'%s', items:true, sound:false, level:'hard'})" % STAGE + "")
    page.evaluate("f => window.ARK.brawl.setSlots([{type:'human',fighter:f[0],ctrl:'kb1',team:''},{type:'cpu',fighter:f[1],ctrl:'kb2',team:''},{type:'cpu',fighter:f[2],ctrl:'kb3',team:''},{type:'cpu',fighter:f[3],ctrl:'pad1',team:''}])", FIGHT)
    page.wait_for_timeout(600)
    page.locator("#brawl-start").click()
    page.evaluate("const f = window.ARK.brawl.fight.fighters[0]; f.cpu = true")
    if START:
        page.evaluate("s => { const F = window.ARK.brawl.fight; F.cam = s; F.fighters.forEach((f, i) => { f.x = s + 220 + i * 170; }); }", START)
    n = int(SECS * 2)
    for i in range(n):
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT, f"snap_{i:02d}.png"))
        if page.evaluate("window.ARK.brawl.fight.phase") == "over" and i > 4:
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUT, f"snap_{i + 1:02d}.png"))
            break
    vid = page.video.path()
    ctx.close(); b.close()
    shutil.move(vid, os.path.join(OUT, "demo.webm"))
print("ok", OUT)
