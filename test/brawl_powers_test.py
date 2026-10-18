"""BIJATYKA elemental powers (DEFEND, down, ATTACK): fire burns, ice freezes and shatters, kamehameha beam,
Ernest's captain's cap boomerang (bald until he catches it).

Run: ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/brawl_powers_test.py [SHOT_DIR]
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("http") else (sys.argv[2] if len(sys.argv) > 2 else None)
FAILS = []


def check(ok, msg):
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


F = "window.ARK.brawl.fight"
RESET = f"""fid => {{ const F = {F}.fighters; for (const f of F) {{ f.st = 'stand'; f.t = 0; f.inv = 0; f.fall = 0; f.bdef = 0; f.vx = f.vy = f.vz = 0; f.y = 0; f.hold = null; f.grabbing = null; f.grabbedBy = null; f.hitstop = 0; f.running = 0; f.hist = []; f.ko = false; f.ammo = 0; f.hp = f.hpMax; f.hpDark = f.hpMax; f.burn = 0; f.mp = 500; f.capless = false; f.cap = null; }}
  const a = F[0]; a.def = window.ARK.brawl.FIGHTERS[fid]; a.key = fid;
  a.x = 200; a.z = 100; a.face = 1; F[1].x = 520; F[1].z = 100; F[1].face = -1; {F}.items = []; {F}.balls = []; }}"""


def step(page, ms):
    page.evaluate("n => window.ARK.brawl.step(n)", max(1, round(ms * 60 / 1000)))


def power(page):
    for k in ("KeyH", "KeyS", "KeyF"):
        page.keyboard.press(k)
        step(page, 50)


def render_srcs(page):
    """Names of the atlas images drawImage receives during one render() (which atlas the renderer really uses)."""
    return page.evaluate(f"""(() => {{ const seen = new Set(), o = CanvasRenderingContext2D.prototype.drawImage;
      CanvasRenderingContext2D.prototype.drawImage = function (im, ...r) {{ if (im && im.src) seen.add(im.src.split('/').pop().split('?')[0]); return o.call(this, im, ...r); }};
      const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; CanvasRenderingContext2D.prototype.drawImage = o; return [...seen]; }})()""")


def target(page):
    return page.evaluate(f"(() => {{ const o = {F}.fighters[1]; return {{ st: o.st, hp: o.hp, max: o.hpMax, burn: o.burn || 0 }}; }})()")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errs, bad = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("response", lambda r: bad.append(r.url) if r.status >= 400 else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_function("window.ARK && window.ARK.brawl && window.ARK.brawl.venue")
    page.evaluate("localStorage.removeItem('ark_brawl_keys_v1')")
    if page.evaluate("window.ARK.scene") != "play":
        page.keyboard.press("KeyN")
        page.locator("#player-name-input").fill("Pilot")
        page.keyboard.press("Enter")
        page.wait_for_function("window.ARK.scene === 'play'")

    fd = page.evaluate("Object.fromEntries(Object.entries(window.ARK.brawl.FIGHTERS).map(([k, f]) => [k, f.power && f.power.el]))")
    check(all(fd.values()) and set(fd.values()) == {"fire", "ice", "beam", "cap"}, f"every fighter has a power, all four elements used ({fd})")
    check(fd["ernest"] == "cap" and list(fd.values()).count("cap") == 1, "Ernest's power is the captain's cap (no ice any more)")

    page.evaluate("window.ARK.brawl.open()")
    page.evaluate("window.ARK.brawl.setOpts({stage:'shop', items:false, sound:false})")
    page.evaluate("window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'human',fighter:'edytka',ctrl:'kb2',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    page.evaluate("window.ARK.brawl.loaded()")
    page.locator("#brawl-start").click()
    page.wait_for_function(f"{F} && {F}.phase === 'fight'")
    page.evaluate(f"{F}.paused = true")

    # FIRE: Arek fireball knocks down and burns.
    page.evaluate(RESET, "arek")
    power(page)
    step(page, 200)
    st = page.evaluate(f"({{ st: {F}.fighters[0].st, mp: {F}.fighters[0].mp, balls: {F}.balls.map(b => b.el) }})")
    check(st["mp"] <= 500 - 120 + 10 and "fire" in st["balls"], f"D v A as Arek fires a fireball ({st})")
    for _ in range(30):
        step(page, 50)
        if target(page)["burn"] > 0:
            break
    if SHOTS:
        page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
        page.screenshot(path=os.path.join(SHOTS, "brawl_power_fire.png"))
    t = target(page)
    check(t["st"] in ("fall", "lying") and t["burn"] > 0 and t["hp"] < t["max"], f"fireball knocks down and sets burning ({t})")
    hp_burning = t["hp"]
    step(page, 1900)
    t = target(page)
    check(t["hp"] < hp_burning and t["burn"] == 0, f"burning deals damage over time then stops ({hp_burning}->{t['hp']})")

    # ICE: Edytka freezes, next hit shatters.
    page.evaluate(RESET, "edytka")
    power(page)
    for _ in range(14):
        step(page, 50)
        if target(page)["st"] == "frozen":
            break
    if SHOTS:
        page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
        page.screenshot(path=os.path.join(SHOTS, "brawl_power_ice.png"))
    t = target(page)
    check(t["st"] == "frozen", f"ice shard freezes the target ({t})")
    x_before = page.evaluate(f"{F}.fighters[1].x")
    page.keyboard.down("ArrowLeft"); step(page, 300); page.keyboard.up("ArrowLeft")
    check(target(page)["st"] == "frozen" and abs(page.evaluate(f"{F}.fighters[1].x") - x_before) < 20, "frozen fighter cannot walk")
    page.evaluate(f"{F}.fighters[0].x = {F}.fighters[1].x - 45; {F}.fighters[0].face = 1; {F}.fighters[0].st = 'stand'")
    hp0 = target(page)["hp"]
    page.keyboard.press("KeyF"); step(page, 300)
    t = target(page)
    check(t["st"] in ("fall", "lying") and hp0 - t["hp"] >= 30, f"punching a frozen fighter shatters the ice for bonus damage ({hp0}->{t['hp']}, {t['st']})")
    page.evaluate(RESET, "edytka")
    power(page)
    for _ in range(14):
        step(page, 50)
        if target(page)["st"] == "frozen":
            break
    step(page, 2000)
    check(target(page)["st"] == "frozen", "ice holds for 91 TU (3.03 s) in LF2: still frozen after 2 s")
    step(page, 1300)
    check(target(page)["st"] in ("fall", "lying", "getup", "stand"), "ice shatters by itself after 91 TU: the fighter is thrown back and falls (LF2 frame 202)")

    # BEAM: Renik kamehameha, long range, multi-hit, knocks down; z dodge avoids it.
    page.evaluate(RESET, "renik")
    page.evaluate(f"{F}.fighters[1].x = 800")
    hp0 = target(page)["hp"]
    power(page)
    check(page.evaluate(f"{F}.fighters[0].st") == "power", "D v A as Renik starts the kamehameha charge")
    step(page, 400)
    if SHOTS:
        page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
        page.screenshot(path=os.path.join(SHOTS, "brawl_power_beam.png"))
    blen = page.evaluate(f"{F}.fighters[0].beamLen")
    step(page, 700)
    t = target(page)
    check(blen > 500 and hp0 - t["hp"] >= 28 and t["st"] in ("fall", "lying"), f"beam reaches across the screen, hits several times and knocks down (len {blen}, {hp0}->{t['hp']}, {t['st']})")
    # TOMEK: orange kamehameha (HODL-HAMEHA!) that hits and knocks down.
    page.evaluate(RESET, "tomek")
    page.evaluate(f"{F}.fighters[1].x = 800")
    hp0 = target(page)["hp"]
    power(page)
    step(page, 400)
    tp = page.evaluate(f"(() => {{ const d = {F}.fighters[0].def; return {{ el: d.power.el, color: d.power.color, name: d.power.name, len: {F}.fighters[0].beamLen }}; }})()")
    r_, g_, b_ = (int(tp["color"][i:i + 2], 16) for i in (1, 3, 5))
    check(tp["el"] == "beam" and r_ > 200 and 100 < g_ < 180 and b_ < 60, f"TOMEK's kamehameha is bitcoin orange ({tp})")
    step(page, 700)
    t = target(page)
    check(tp["len"] > 500 and hp0 - t["hp"] >= 28 and t["st"] in ("fall", "lying"), f"TOMEK's orange beam hits several times and knocks down ({hp0}->{t['hp']}, {t['st']})")
    page.evaluate(RESET, "michal")
    page.evaluate(f"{F}.fighters[1].x = 700; {F}.fighters[1].z = 180")
    power(page)
    step(page, 1200)
    t = target(page)
    check(t["hp"] == t["max"], f"beam misses a fighter on a different depth line ({t})")
    # ARTUR: black small kamehameha (same beam element, thinner, black core) still travels and hits.
    page.evaluate(RESET, "artur")
    page.evaluate(f"{F}.fighters[1].x = 800")
    hp0 = target(page)["hp"]
    pw = page.evaluate("(() => { const p = window.ARK.brawl.FIGHTERS.artur.power; return { el: p.el, size: p.size, core: p.core }; })()")
    check(pw["el"] == "beam" and pw["size"] < 1 and pw["core"] == "#0b0b10", f"ARTUR power is a smaller black beam ({pw})")
    power(page)
    step(page, 400)
    if SHOTS:
        page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
        page.screenshot(path=os.path.join(SHOTS, "brawl_power_artur_beam.png"))
    blen = page.evaluate(f"{F}.fighters[0].beamLen")
    step(page, 700)
    t = target(page)
    check(blen > 500 and hp0 - t["hp"] >= 28, f"ARTUR black beam renders and hits (len {blen}, {hp0}->{t['hp']}, {t['st']})")

    # ERNEST: captain's cap boomerang. Bald (atlas ernest_bald) while it is away, hits on the way out, comes back, caught.
    CAP = f"{F}.balls.filter(b => b.el === 'cap')"
    page.evaluate(RESET, "ernest")
    pn = page.evaluate("(() => { const p = window.ARK.brawl.FIGHTERS.ernest.power; return { el: p.el, name: p.name }; })()")
    check(pn["el"] == "cap" and ("CZAPKA" in pn["name"].upper() or "CAP" in pn["name"].upper()), f"ERNEST power is named after the cap ({pn})")
    check(page.evaluate(f"window.ARK.brawl.atlasOf({F}.fighters[0])") == "ernest", "ERNEST wears his cap before the throw (atlas ernest)")
    hp0 = target(page)["hp"]
    srcs0 = render_srcs(page)
    check("ernest_bald.webp" not in srcs0, f"before the throw the renderer does not touch ernest_bald.webp ({srcs0})")
    power(page)
    step(page, 120)
    st = page.evaluate(f"({{ st: {F}.fighters[0].st, mp: {F}.fighters[0].mp, caps: {CAP}.length, capless: {F}.fighters[0].capless }})")
    check(st["st"] == "power" and st["caps"] == 0 and not st["capless"], f"cap is still on his head while he winds up ({st})")
    step(page, 200)
    st = page.evaluate(f"({{ mp: {F}.fighters[0].mp, caps: {CAP}.length, capless: {F}.fighters[0].capless, atlas: window.ARK.brawl.atlasOf({F}.fighters[0]), frame: window.ARK.brawl.frameName({F}.fighters[0]) }})")
    check(st["caps"] == 1 and st["capless"] and st["mp"] <= 500 - 100 + 10, f"D v A as Ernest throws a cap and costs MP ({st})")
    check(st["atlas"] == "ernest_bald", f"while the cap flies Ernest is drawn from atlas ernest_bald ({st['atlas']})")
    # the renderer really uses the bald atlas for Ernest's sprite (the HUD portrait always stays capped, so compare with a render before the throw)
    srcs = render_srcs(page)
    check("ernest_bald.webp" in srcs and "items.webp" in srcs, f"renderer draws ernest_bald.webp for the capless Ernest and the cap sprite from items.webp ({srcs})")
    step(page, 150)
    if SHOTS:
        page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
        page.screenshot(path=os.path.join(SHOTS, "brawl_power_cap_out.png"))
    got = None
    for _ in range(30):
        step(page, 50)
        t = target(page)
        if t["st"] in ("fall", "lying"):
            got = t; break
    check(got is not None and hp0 - got["hp"] >= 35, f"flying cap hits the target in front and knocks it down ({hp0}->{got and got['hp']}, {got and got['st']})")
    seen_back = False
    for _ in range(80):
        step(page, 50)
        if page.evaluate(f"{CAP}.some(b => b.phase === 'back')"):
            seen_back = True
            if SHOTS and not os.path.exists(os.path.join(SHOTS, "brawl_power_cap_back.png")):
                page.evaluate(f"(() => {{ const p = {F}.paused; {F}.paused = false; window.ARK.brawl.render(); {F}.paused = p; }})()")
                page.screenshot(path=os.path.join(SHOTS, "brawl_power_cap_back.png"))
        if not page.evaluate(f"{F}.fighters[0].capless"):
            break
    check(seen_back, "the cap turns round and flies back (phase 'back')")
    st = page.evaluate(f"({{ capless: {F}.fighters[0].capless, caps: {CAP}.length, atlas: window.ARK.brawl.atlasOf({F}.fighters[0]) }})")
    check(not st["capless"] and st["caps"] == 0 and st["atlas"] == "ernest", f"Ernest catches the cap: no cap ball left, atlas ernest again ({st})")

    # cannot throw again while the cap is away
    page.evaluate(RESET, "ernest")
    page.evaluate(f"{F}.fighters[1].x = 900")
    power(page)
    step(page, 400)
    mp1 = page.evaluate(f"{F}.fighters[0].mp")
    check(page.evaluate(f"{F}.fighters[0].capless") and page.evaluate(f"{CAP}.length") == 1, "second throw test: first cap is out")
    page.evaluate(f"{F}.fighters[0].st = 'stand'; {F}.fighters[0].t = 0")
    power(page)
    step(page, 400)
    st = page.evaluate(f"({{ caps: {CAP}.length, mp: {F}.fighters[0].mp, st: {F}.fighters[0].st }})")
    check(st["caps"] == 1 and st["mp"] >= mp1 - 5, f"no second cap and no MP spent while capless ({st})")
    # a cap that cannot return in time drops and he picks it up himself
    page.evaluate(f"{F}.balls.find(b => b.el === 'cap').t = 2.49")
    for _ in range(30):
        step(page, 50)
        if not page.evaluate(f"{F}.fighters[0].capless"):
            break
    check(not page.evaluate(f"{F}.fighters[0].capless") and page.evaluate(f"{CAP}.length") == 0, "after the max flight time the cap drops and Ernest recovers it by himself")

    # Block: a defended fireball does chip damage only, no burn.
    page.evaluate(RESET, "arek")
    page.keyboard.down("ShiftRight"); step(page, 100)
    power(page)
    step(page, 700)
    page.keyboard.up("ShiftRight")
    t = target(page)
    check(t["burn"] == 0 and t["max"] - t["hp"] <= 6, f"blocked fireball: chip damage, no burn ({t})")

    # CPU uses the power.
    page.evaluate(f"window.ARK.brawl.end()")
    page.evaluate("window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'cpu',fighter:'michal',ctrl:'kb2',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    page.evaluate("window.ARK.brawl.setOpts({level:'hard'})")
    page.locator("#brawl-start").click()
    page.wait_for_function(f"{F} && {F}.phase === 'fight'")
    page.evaluate(f"{F}.paused = true")
    used = False
    for _ in range(120):
        page.evaluate(f"(() => {{ const F = {F}.fighters; F[0].x = 150; F[0].z = 100; F[0].hp = F[0].hpMax; F[1].mp = 500; F[1].z = 100; if (F[1].st !== 'power') F[1].x = 600; }})()")
        step(page, 250)
        if page.evaluate(f"{F}.fighters[1].st === 'power'"):
            used = True
            break
    check(used, "CPU Michał uses the kamehameha")
    page.evaluate(f"window.ARK.brawl.end()")
    page.evaluate("window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'cpu',fighter:'ernest',ctrl:'kb2',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    page.locator("#brawl-start").click()
    page.wait_for_function(f"{F} && {F}.phase === 'fight'")
    page.evaluate(f"{F}.paused = true")
    used = False
    for _ in range(160):
        page.evaluate(f"(() => {{ const F = {F}.fighters; F[0].x = 150; F[0].z = 100; F[0].hp = F[0].hpMax; F[1].mp = 500; F[1].z = 100; if (!F[1].capless && F[1].st !== 'power') F[1].x = 430; }})()")
        step(page, 250)
        if page.evaluate(f"{F}.fighters[1].capless"):
            used = True
            break
    check(used, "CPU Ernest throws his captain's cap")

    check(not errs, f"no page errors ({errs[:3]})")
    check(not bad, f"no failed requests ({bad[:3]})")
    browser.close()

print("RESULT:", "PASS" if not FAILS else f"FAIL {len(FAILS)}")
if not FAILS:
    print("PASS brawl_powers_test")
sys.exit(1 if FAILS else 0)
