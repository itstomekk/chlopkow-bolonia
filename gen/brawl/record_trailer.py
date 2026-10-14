"""Record a trailer of the whole game: Polonia splash, title, village walk, map, church, a minigame, then BIJATYKA.

Run: python gen/brawl/record_trailer.py URL OUT_DIR
Writes OUT_DIR/trailer.webm and OUT_DIR/marks.json (seconds from the start of the video for each scene).
"""
import json, os, shutil, sys, time
from playwright.sync_api import sync_playwright

URL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
marks = {}
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
    pg = ctx.new_page()
    t0 = time.time()
    mark = lambda k: marks.__setitem__(k, round(time.time() - t0, 2))
    pg.route('https://esm.sh/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body='export {};'))
    pg.goto(URL)
    mark("splash")
    pg.wait_for_function("window.__game && window.__game.scene === 'title'", timeout=60000)
    mark("title")
    time.sleep(2.6)
    pg.keyboard.press("Enter")
    pg.locator("#player-name-input").fill("Arek"); time.sleep(.4); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    mark("play"); time.sleep(.6)
    pg.keyboard.down("ArrowRight"); time.sleep(1.6); pg.keyboard.up("ArrowRight")
    pg.keyboard.down("ArrowDown"); time.sleep(1.4); pg.keyboard.up("ArrowDown")
    mark("map"); pg.keyboard.press("KeyM"); time.sleep(2.6); pg.keyboard.press("KeyM"); time.sleep(.3)

    def tp(x, y):
        pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()")
    c = pg.evaluate("__game.MAP.pois.find(p=>p.key==='church')")
    tp(c["x"] - 160, c["y"] + 90); time.sleep(.3)
    mark("church_out")
    pg.keyboard.down("ArrowRight"); time.sleep(1.2); pg.keyboard.up("ArrowRight")
    tp(c["x"], c["y"] + 40); time.sleep(.3)
    pg.keyboard.press("KeyE"); time.sleep(.9)
    mark("church_in")
    for _ in range(6):
        if not pg.evaluate("!!__game.talk"): break
        pg.keyboard.press("Space"); time.sleep(.15)
    pg.keyboard.down("ArrowUp"); time.sleep(1.6); pg.keyboard.up("ArrowUp"); time.sleep(.6)
    pg.evaluate("__game.P.x=160; __game.P.y=426"); pg.keyboard.down("ArrowDown"); time.sleep(.6); pg.keyboard.up("ArrowDown"); time.sleep(.5)
    for _ in range(6):
        if not pg.evaluate("!!__game.talk"): break
        pg.keyboard.press("Space"); time.sleep(.15)
    mark("race")
    pg.evaluate("__features.startMG('race')"); time.sleep(3.3)
    tr = pg.evaluate("__game.MAP.track")
    import math
    for k in range(1, 30):
        a = math.pi / 2 + k * 2 * math.pi / 30
        pg.evaluate(f"__game.P.x={tr['cx'] + math.cos(a) * tr['rx']}; __game.P.y={tr['cy'] + math.sin(a) * tr['ry']}"); time.sleep(.09)
    mark("race_end"); time.sleep(.5)
    pg.keyboard.press("Escape"); time.sleep(.3)
    for _ in range(4):
        if not pg.evaluate("!!__game.talk"): break
        pg.keyboard.press("Space"); time.sleep(.15)
    # BIJATYKA on the village road
    pg.evaluate("window.ARK.brawl.open(); window.ARK.brawl.loaded()")
    pg.evaluate("window.ARK.brawl.setOpts({stage:'road', items:true, sound:false, level:'hard'})")
    pg.evaluate("window.ARK.brawl.setSlots([{type:'human',fighter:'damian',ctrl:'kb1',team:''},{type:'cpu',fighter:'soltys',ctrl:'kb2',team:''},{type:'cpu',fighter:'michal',ctrl:'kb3',team:''},{type:'cpu',fighter:'edytka',ctrl:'pad1',team:''}])")
    mark("lobby"); time.sleep(1.4)
    pg.locator("#brawl-start").click()
    pg.evaluate("""() => { const B = window.ARK.brawl, F = B.fight; F.fighters[0].cpu = true; const s = 2500; F.cam = s;
      F.fighters.forEach((f, i) => { f.x = s + 220 + i * 170; });
      const give = (f, w) => { const it = B.spawnItem(w, f.x, f.z, false); it.state = 'held'; it.owner = f; f.hold = it; };
      give(F.fighters[0], 'scythe'); give(F.fighters[3], 'pan');
      ['club', 'broom', 'picket', 'rollpin', 'shovel', 'pistol'].forEach((w, i) => B.spawnItem(w, s + 120 + i * 140, 40 + (i % 3) * 60, false)); }""")
    mark("fight")
    time.sleep(22)
    mark("end")
    vid = pg.video.path()
    ctx.close(); b.close()
    shutil.move(vid, os.path.join(OUT, "trailer.webm"))
json.dump(marks, open(os.path.join(OUT, "marks.json"), "w"), indent=1)
print("ok", marks)
