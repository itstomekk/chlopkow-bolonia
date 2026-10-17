"""BIJATYKA (LF2-style local brawler) regression.

Run: python test/isolated_browser_runner.py test/brawl_test.py [URL] [SHOT_DIR]
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SHOTS = sys.argv[2] if len(sys.argv) > 2 else None
FAILS = []


def check(ok, msg):
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok:
        FAILS.append(msg)


FAKE_PAD = """
window.__fakePad = null;
const realPads = navigator.getGamepads ? navigator.getGamepads.bind(navigator) : () => [];
navigator.getGamepads = () => window.__fakePad ? [window.__fakePad, null, null, null] : realPads();
"""


def pad(page, **btn):
    idx = {"jump": 0, "defend": 1, "attack": 2, "up": 12, "down": 13, "left": 14, "right": 15}
    pressed = [False] * 17
    for k, v in btn.items():
        pressed[idx[k]] = v
    page.evaluate("p => { window.__fakePad = { axes: [0, 0], buttons: p.map(x => ({ pressed: x })) }; }", pressed)


def ev(page, js, arg=None):
    return page.evaluate(js, arg) if arg is not None else page.evaluate(js)


F = "window.ARK.brawl.fight"
RESET_PAIR = f"""() => {{ const F = {F}.fighters; for (const f of F) {{ f.st = 'stand'; f.t = 0; f.inv = 0; f.fall = 0; f.bdef = 0; f.vx = f.vy = f.vz = 0; f.y = 0; f.hold = null; f.grabbing = null; f.grabbedBy = null; f.hitstop = 0; f.running = 0; f.hist = []; f.ko = false; f.ammo = 0; f.hp = f.hpMax; f.hpDark = f.hpMax; }}
  F[0].x = 300; F[0].z = 100; F[0].face = 1; F[1].x = 345; F[1].z = 100; F[1].face = -1; for (const f of F.slice(2)) {{ f.x = 900; f.z = 0; }} {F}.items = []; {F}.balls = []; }}"""


def step(page, ms):
    page.evaluate("n => window.ARK.brawl.step(n)", max(1, round(ms * 60 / 1000)))


def tap(page, key, wait=70):
    page.keyboard.press(key)
    step(page, wait)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.add_init_script(FAKE_PAD)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    bad = []
    page.on("response", lambda r: bad.append(r.url) if "/brawl/" in r.url and r.status >= 400 else None)
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_function("window.ARK && window.ARK.brawl && window.ARK.brawl.venue")
    ev(page, "localStorage.removeItem('ark_brawl_keys_v1'); localStorage.removeItem('ark_brawl_slots_v1'); localStorage.removeItem('ark_brawl_opts_v1')")
    if ev(page, "window.ARK.scene") != "play":
        page.keyboard.press("KeyN")
        page.locator("#player-name-input").fill("Pilot")
        page.keyboard.press("Enter")
        page.wait_for_function("window.ARK.scene === 'play'")

    v = ev(page, "({...window.ARK.brawl.venue, w: window.ARK.MAP.w, h: window.ARK.MAP.h, blocked: window.ARK.blocked(window.ARK.brawl.venue.x, window.ARK.brawl.venue.y), reach: window.__game.isSpawnReachable(window.ARK.brawl.venue.x, window.ARK.brawl.venue.y)})")
    check(v["x"] < v["w"] * .4 and v["y"] > v["h"] * .6, f"venue is in the south-west ({v['x']},{v['y']})")
    check(not v["blocked"] and v["reach"], "venue is walkable and reachable from spawn")

    ev(page, "v => window.ARK.teleport(v.x + 14, v.y + 4)", v)
    page.wait_for_timeout(1200)
    page.keyboard.press("KeyE")
    check(page.locator("#brawl-overlay").is_visible(), "flag interaction opens the brawl lobby")
    before = ev(page, "[window.ARK.P.x, window.ARK.P.y]")
    page.keyboard.down("KeyD"); page.wait_for_timeout(300); page.keyboard.up("KeyD")
    check(ev(page, "[window.ARK.P.x, window.ARK.P.y]") == before, "lobby keys never move the village player")
    check(page.locator(".brawl-slot").count() == 4, "lobby has four player slots")
    ev(page, "window.ARK.brawl.loaded()")
    page.wait_for_timeout(400)
    check(ev(page, "[...document.querySelectorAll('canvas[data-portrait]')].every(c => c.getContext('2d').getImageData(0,0,c.width,c.height).data.some(v => v > 0))"), "fighter portraits render in the lobby")

    # Rebinding.
    page.locator("#brawl-controls summary").click()
    page.locator('[data-rebind="kb1:attack"]').click()
    page.keyboard.press("KeyZ")
    check(ev(page, "window.ARK.brawl.keys.kb1.attack") == "KeyZ", "real key press rebinds kb1 attack")
    page.locator('[data-rebind="kb1:jump"]').click()
    page.keyboard.press("KeyZ")
    k = ev(page, "window.ARK.brawl.keys.kb1")
    check(k["jump"] == "KeyZ" and k["attack"] == "KeyG", f"duplicate binding swaps ({k})")
    page.locator("#brawl-reset-keys").click()
    check(ev(page, "window.ARK.brawl.keys.kb1.attack") == "KeyF", "reset restores default keys")

    # Validation.
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'human',fighter:'edytka',ctrl:'kb1',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    check(bool(ev(page, "window.ARK.brawl.validate()")), "two humans on one scheme is rejected")
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:'A'},{type:'cpu',fighter:'edytka',ctrl:'kb2',team:'A'},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    check(bool(ev(page, "window.ARK.brawl.validate()")), "one-team fight is rejected")

    # 2 keyboards + gamepad + CPU on the shop stage, items off for deterministic checks.
    ev(page, "window.ARK.brawl.setOpts({stage:'shop', items:false, sound:false})")
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'human',fighter:'edytka',ctrl:'kb2',team:''},{type:'human',fighter:'renik',ctrl:'pad1',team:''},{type:'cpu',fighter:'edytka',ctrl:'kb3',team:''}])")
    page.locator("#brawl-start").click()
    check(page.locator("#brawl-canvas").is_visible(), "fight canvas shows")
    page.wait_for_function(f"{F} && {F}.phase === 'fight'")
    check(ev(page, f"{F}.stage") == "shop", "chosen stage is used")
    ev(page, f"{F}.fighters[3].cpu = false; {F}.fighters[3].ctrl = 'none'")   # freeze the CPU for input checks
    xs = ev(page, f"{F}.fighters.map(f => f.x)")
    page.keyboard.down("KeyD"); page.keyboard.down("ArrowLeft"); pad(page, right=True)
    page.wait_for_timeout(400)
    page.keyboard.up("KeyD"); page.keyboard.up("ArrowLeft"); pad(page)
    xs2 = ev(page, f"{F}.fighters.map(f => f.x)")
    check(xs2[0] > xs[0] + 20 and xs2[1] < xs[1] - 20 and xs2[2] > xs[2] + 20, f"three players move at once: WASD, arrows, gamepad ({[round(a) for a in xs]} -> {[round(a) for a in xs2]})")
    check(ev(page, "[window.ARK.P.x, window.ARK.P.y]") == before, "fight keys never move the village player")

    ev(page, f"{F}.paused = true")   # deterministic from here: the test drives ticks itself
    # Hit pause: both fighters freeze on impact (the victim longer), and a press during the freeze is buffered, not lost.
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[1].fall = 0")
    hp0 = ev(page, f"{F}.fighters[1].hp")
    page.keyboard.press("KeyF")
    for _ in range(40):
        step(page, 16)
        if ev(page, f"{F}.fighters[1].hp") < hp0: break
    hs = ev(page, f"[{F}.fighters[0].hitstop, {F}.fighters[1].hitstop]")
    # LF2: the attacker stalls hit_stop = 3 TU (0.1 s) and the victim's effect also lasts 3 TU, so the pauses are equal (the victim is read one tick later)
    check(abs(hs[0] - 0.1) < 0.001 and 0.08 <= hs[1] <= 0.1001, f"a light hit pauses attacker and victim 3 TU each (attacker {hs[0]:.3f}s, victim {hs[1]:.3f}s)")
    page.keyboard.press("KeyF"); step(page, 16)
    check(ev(page, f"{F}.fighters[0].hitstop") > 0 and ev(page, f"{F}.fighters[0].buf ? {F}.fighters[0].buf.has('attack') : false"), "a button pressed during the hit pause is buffered, not lost")
    step(page, 120)
    check(ev(page, f"{F}.fighters[0].buf ? {F}.fighters[0].buf.size : 0") == 0, "the buffer is empty again once the pause ends")

    # LF2 fall meter: punch fall 20 -> hurt, hurt, dizzy on the 3rd hit (40 < meter <= 60) -> super punch knocks down.
    ev(page, RESET_PAIR)
    hp = ev(page, f"{F}.fighters[1].hp")
    tap(page, "KeyF", 330)
    st1 = ev(page, f"({{hp:{F}.fighters[1].hp, st:{F}.fighters[1].st}})")
    check(st1["hp"] < hp, f"punch damages ({hp}->{st1['hp']})")
    ev(page, f"{F}.fighters[1].x = {F}.fighters[0].x + 45")
    tap(page, "KeyF", 330)
    st2 = ev(page, f"{F}.fighters[1].st")
    check(st2 == "hurt", f"second punch only hurts (LF2 fall meter 20+20 <= 40; got {st2})")
    ev(page, f"{F}.fighters[1].x = {F}.fighters[0].x + 45")
    tap(page, "KeyF", 330)
    st3 = ev(page, f"{F}.fighters[1].st")
    check(st3 == "dizzy", f"third punch makes the target dizzy (got {st3})")
    ev(page, f"{F}.fighters[1].x = {F}.fighters[0].x + 45")
    tap(page, "KeyF", 330)   # a punch lasts 8 TU plus the 3 TU hit pause (LF2), so the press is chained after the recovery
    check(ev(page, f"{F}.fighters[0].st") == "super", "punching a dizzy target becomes a super punch")
    step(page, 300)
    check(ev(page, f"{F}.fighters[1].st") in ("fall", "lying"), "super punch knocks down")

    # Block.
    ev(page, RESET_PAIR)
    page.keyboard.down("ShiftRight"); step(page, 100)
    hp = ev(page, f"{F}.fighters[1].hp")
    tap(page, "KeyF", 300)
    page.keyboard.up("ShiftRight")
    hp2 = ev(page, f"{F}.fighters[1].hp")
    check(0 < hp - hp2 <= 3, f"DEFEND reduces a frontal punch to chip damage ({hp}->{hp2})")

    # Grab + throw: walk into a dizzy enemy.
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[1].x = {F}.fighters[0].x + 60; {F}.fighters[1].st = 'dizzy'; {F}.fighters[1].t = 0")
    page.keyboard.down("KeyD"); step(page, 250); page.keyboard.up("KeyD")
    g = ev(page, f"[{F}.fighters[0].st, {F}.fighters[1].st]")
    check(g == ["grab", "held"], f"walking into a dizzy enemy grabs it ({g})")
    hp = ev(page, f"{F}.fighters[1].hp")
    tap(page, "KeyF", 300)
    check(ev(page, f"{F}.fighters[1].hp") < hp and ev(page, f"{F}.fighters[0].st") == "grab", "ATTACK punches the held enemy")
    page.keyboard.down("KeyD"); tap(page, "KeyF", 200); page.keyboard.up("KeyD")
    check(ev(page, f"{F}.fighters[1].st") == "fall" and ev(page, f"!!{F}.fighters[1].thrownBy"), "direction + ATTACK throws the held enemy")
    step(page, 900)

    # Flip (rowing) while falling.
    ev(page, RESET_PAIR)
    ev(page, f"const v = {F}.fighters[0]; v.st = 'fall'; v.t = .2; v.y = 60; v.vy = 200; v.vx = -100")
    tap(page, "KeyG", 30)
    check(ev(page, f"{F}.fighters[0].st") == "flip", "JUMP while falling performs a flip")
    step(page, 700)
    check(ev(page, f"{F}.fighters[0].st") in ("stand", "land", "walk"), "flip lands on the feet")

    # Items: pick pitchfork, swing, throw; milk heals.
    ev(page, RESET_PAIR)
    ev(page, f"window.ARK.brawl.spawnItem('widly', {F}.fighters[0].x + 5, {F}.fighters[0].z); {F}.fighters[1].x = 500")
    tap(page, "KeyF", 320)
    check(ev(page, f"{F}.fighters[0].hold && {F}.fighters[0].hold.type") == "widly", "ATTACK on a pitchfork picks it up")
    check(ev(page, f"window.ARK.brawl.frameName({F}.fighters[0])") == "w_stand", "holding the pitchfork uses weapon frames")
    ev(page, f"{F}.fighters[1].x = {F}.fighters[0].x + 85; {F}.fighters[1].st = 'stand'; {F}.fighters[1].fall = 0")
    hp = ev(page, f"{F}.fighters[1].hp")
    tap(page, "KeyF", 380)
    check(ev(page, f"{F}.fighters[1].hp") < hp, "pitchfork reaches farther than a punch and hits")
    ev(page, f"{F}.fighters[1].x = 700; {F}.fighters[1].st = 'stand'; {F}.fighters[0].st = 'stand'")
    page.keyboard.down("KeyD"); tap(page, "KeyF", 160); page.keyboard.up("KeyD")
    check(ev(page, f"{F}.items.some(i => i.type === 'widly' && i.state === 'flying')") and not ev(page, f"!!{F}.fighters[0].hold"), "forward + ATTACK throws the pitchfork")
    ev(page, RESET_PAIR)
    ev(page, f"const f = {F}.fighters[0]; f.hp = 200; f.hpDark = 300; f.mp = 0; window.ARK.brawl.spawnItem('lomza', f.x, f.z)")
    tap(page, "KeyF", 1400)
    m = ev(page, f"({{hp:{F}.fighters[0].hp, mp:{F}.fighters[0].mp}})")
    check(m["hp"] > 250 and m["mp"] > 150, f"picking up a Łomża drinks it: HP and MP rise ({m})")

    # Specials.
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[0].mp = 500; {F}.fighters[1].z = 230")
    for kk in ("KeyH", "KeyD", "KeyF"):
        tap(page, kk, 50)
    step(page, 150)
    b = ev(page, f"({{balls:{F}.balls.map(b => b.item), mp:{F}.fighters[0].mp}})")
    check(b["balls"] == ["apple"] and b["mp"] < 500, f"Arek D>A throws an apple ({b})")
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, "brawl_fight.png"))
    step(page, 500)
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[0].mp = 500; {F}.fighters[1].x = {F}.fighters[0].x + 100")
    for kk in ("KeyH", "KeyW", "KeyF"):
        tap(page, kk, 50)
    check(ev(page, f"{F}.fighters[0].st") == "spin" and ev(page, f"window.ARK.brawl.frameName({F}.fighters[0])") == "w_thrust", "Arek D^A is the pitchfork lunge (widły frame)")
    step(page, 500)
    check(ev(page, f"{F}.fighters[1].hp") < 480, "pitchfork lunge hits at long range")
    step(page, 500)
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[1].mp = 500; {F}.fighters[0].z = 230")
    for kk in ("ShiftRight", "ArrowLeft", "Period"):
        tap(page, kk, 50)
    step(page, 100)
    e = ev(page, f"({{balls:{F}.balls.map(b => b.item), st:{F}.fighters[1].st, mp:{F}.fighters[1].mp, face:{F}.fighters[1].face}})")
    check(e["balls"] == ["mushroom"] or (e["mp"] < 500 and e["st"] in ("cast", "stand")), f"Edytka D>A throws a mushroom ({e})")
    step(page, 600)

    # Renik: vinyl ball and breakdance hitting both sides.
    ev(page, RESET_PAIR)
    ev(page, f"const r = {F}.fighters[2]; r.x = 600; r.z = 40; r.face = -1; r.mp = 500; r.st = 'stand'")
    pad(page, defend=True); step(page, 60); pad(page); step(page, 40)
    pad(page, left=True); step(page, 60); pad(page); step(page, 40)
    pad(page, attack=True); step(page, 60); pad(page); step(page, 160)
    check(ev(page, f"{F}.fighters[2].key") == "renik" and "vinyl" in ev(page, f"{F}.balls.map(b => b.item)"), "Renik (gamepad) D<A throws a vinyl record")
    step(page, 700)
    ev(page, RESET_PAIR)
    ev(page, f"const r = {F}.fighters[2]; r.x = 600; r.z = 100; r.face = 1; r.mp = 500; r.st = 'stand'; {F}.fighters[1].x = 555; {F}.fighters[1].z = 100; {F}.fighters[0].x = 645; {F}.fighters[0].z = 100")
    pad(page, defend=True); step(page, 60); pad(page); step(page, 40)
    pad(page, up=True); step(page, 60); pad(page); step(page, 40)
    pad(page, attack=True); step(page, 60); pad(page); step(page, 600)
    hp = ev(page, f"[{F}.fighters[0].hp, {F}.fighters[0].hpMax, {F}.fighters[1].hp, {F}.fighters[1].hpMax]")
    check(hp[0] < hp[1] and hp[2] < hp[3], f"Renik breakdance hits both sides ({hp})")
    step(page, 500)

    # New fighters: atlases load, specials work.
    for i, (fid, sp) in enumerate([("damian", "football"), ("wesoly", "hammer"), ("soltys", "teczka"), ("michal", "kulka"), ("ernest", "cytryna"), ("felcu", "kluczyk"), ("artur", "smartfon"), ("urban", "deska")]):
        ev(page, RESET_PAIR)
        ev(page, f"const f = {F}.fighters[0]; f.def = window.ARK.brawl.FIGHTERS['{fid}']; f.key = '{fid}'; f.mp = 500; {F}.fighters[1].z = 230")
        for kk in ("KeyH", "KeyD", "KeyF"):
            tap(page, kk, 50)
        step(page, 200)
        check(sp in ev(page, f"{F}.balls.map(b => b.item)"), f"{fid} D>A throws {sp}")
        ev(page, RESET_PAIR)
        ev(page, f"const f = {F}.fighters[0]; f.def = window.ARK.brawl.FIGHTERS['{fid}']; f.key = '{fid}'; f.mp = 500; {F}.fighters[1].x = f.x + 60")
        for kk in ("KeyH", "KeyW", "KeyF"):
            tap(page, kk, 50)
        step(page, 700)
        res_ = ev(page, f"[{F}.fighters[1].hp, {F}.fighters[1].hpMax, {F}.fighters[1].st]")
        check(res_[0] < res_[1], f"{fid} D^A special hits ({res_})")
        step(page, 1500)

    # Held weapons: the paintball pistol shoots orange balls, a frying pan is swung.
    ev(page, RESET_PAIR)
    ev(page, f"window.ARK.brawl.spawnItem('pistol', {F}.fighters[0].x + 5, {F}.fighters[0].z); {F}.fighters[1].x = 700")
    tap(page, "KeyF", 400)
    check(ev(page, f"{F}.fighters[0].hold && {F}.fighters[0].hold.type") == "pistol", "the paintball pistol can be picked up")
    tap(page, "KeyF", 120)
    check(ev(page, f"{F}.balls.some(b => b.item === 'kulka') && {F}.fighters[0].hold.ammo === 11"), "ATTACK with the pistol shoots an orange ball")
    step(page, 800)
    ev(page, RESET_PAIR)
    ev(page, f"window.ARK.brawl.spawnItem('pan', {F}.fighters[0].x + 5, {F}.fighters[0].z)")
    tap(page, "KeyF", 400)
    hp0 = ev(page, f"{F}.fighters[1].hp")
    tap(page, "KeyF", 400)
    check(ev(page, f"{F}.fighters[0].hold && {F}.fighters[0].hold.type") == "pan" and ev(page, f"{F}.fighters[1].hp") < hp0, "a frying pan is held and hits")
    step(page, 800)

    # Pieczarki: picking up gives ammo, ATTACK throws them.
    ev(page, RESET_PAIR)
    ev(page, f"window.ARK.brawl.spawnItem('pieczarki', {F}.fighters[0].x + 5, {F}.fighters[0].z); {F}.fighters[1].x = 600")
    tap(page, "KeyF", 400)
    check(ev(page, f"{F}.fighters[0].ammo") == 5, "picking up pieczarki gives 5 throws")
    tap(page, "KeyF", 150)
    check(ev(page, f"{F}.balls.some(b => b.item === 'pieczarka') && {F}.fighters[0].ammo === 4"), "ATTACK throws one pieczarka")
    step(page, 800)

    # Rural throwable: carry a tyre overhead, throw it, it rolls.
    ev(page, RESET_PAIR)
    ev(page, f"window.ARK.brawl.spawnItem('tyre', {F}.fighters[0].x + 5, {F}.fighters[0].z); {F}.fighters[1].x = 860")
    tap(page, "KeyF", 400)
    check(ev(page, f"{F}.fighters[0].hold && {F}.fighters[0].hold.type") == "tyre", "a tyre can be picked up")
    tap(page, "KeyF", 900)
    t_ = ev(page, f"(() => {{ const t = {F}.items.find(i => i.type === 'tyre'); return t && [t.state, Math.round(t.x), Math.round(t.y)]; }})()")
    check(bool(t_) and t_[1] > 450 and t_[2] == 0, f"thrown tyre rolls along the ground ({t_})")
    step(page, 1500)

    # Run and roll.
    ev(page, RESET_PAIR)
    ev(page, f"{F}.fighters[1].x = 800")
    tap(page, "KeyD", 60); tap(page, "KeyD", 150)
    check(ev(page, f"{F}.fighters[0].st") == "run", "double-tap runs")
    tap(page, "KeyH", 40)
    check(ev(page, f"{F}.fighters[0].st") == "roll", "run + DEFEND rolls")
    step(page, 500)

    page.keyboard.press("Escape")
    check(page.locator("#brawl-lobby").is_visible() and ev(page, F) is None, "ESC returns from fight to lobby")

    # Scrolling arena: the camera follows the fighters along the road and keeps everybody in view.
    ev(page, "window.ARK.brawl.setOpts({stage:'road', items:false, sound:false})")
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:''},{type:'cpu',fighter:'edytka',ctrl:'kb2',team:''},{type:'off',fighter:'arek',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    page.locator("#brawl-start").click()
    page.wait_for_function(f"{F} && {F}.stage === 'road'")
    check(ev(page, f"{F}.ww") > 4000 and ev(page, f"{F}.cam") == 0, "road stage is a wide world, camera starts at the west end")
    ev(page, f"{F}.fighters[1].cpu = false; {F}.fighters[1].ctrl = 'none'")
    step(page, 2000)
    page.keyboard.down("KeyD")
    step(page, 4000)
    page.keyboard.up("KeyD")
    r_ = ev(page, f"({{cam: {F}.cam, x: {F}.fighters.map(f => f.x)}})")
    check(r_["cam"] > 150, f"camera scrolls east after the player ({round(r_['cam'])})")
    check(all(r_["cam"] + 20 <= x <= r_["cam"] + 940 for x in r_["x"]), f"nobody leaves the view ({[round(x) for x in r_['x']]} cam {round(r_['cam'])})")
    ev(page, f"{F}.cam = {F}.ww - 1300; {F}.fighters[0].x = {F}.cam + 600; {F}.fighters[1].x = {F}.cam + 700")
    page.keyboard.down("KeyD")
    step(page, 5000)
    page.keyboard.up("KeyD")
    r_ = ev(page, f"({{cam: {F}.cam, ww: {F}.ww, x: {F}.fighters.map(f => f.x)}})")
    check(abs(r_["cam"] - (r_["ww"] - 960)) < 2 and max(r_["x"]) <= r_["ww"], f"camera stops at the hall end ({round(r_['cam'])} of {r_['ww']})")
    page.keyboard.press("Escape")

    # Full CPU fight with items to a result screen.
    ev(page, "window.ARK.brawl.setOpts({stage:'farmyard', items:true})")
    ev(page, "window.ARK.brawl.setSlots([{type:'human',fighter:'arek',ctrl:'kb1',team:'B'},{type:'cpu',fighter:'arek',ctrl:'kb2',team:''},{type:'cpu',fighter:'renik',ctrl:'kb3',team:''},{type:'off',fighter:'arek',ctrl:'pad1',team:''}])")
    page.locator("#brawl-start").click()
    ev(page, f"{F}.fighters[0].hp = 1; {F}.fighters[0].hpDark = 1; {F}.fighters[0].x = {F}.fighters[1].x - 40; {F}.fighters[0].z = {F}.fighters[1].z")
    res = ev(page, """() => { const b = window.ARK.brawl; let n = 0;
        while (b.fight && b.fight.phase !== 'over' && n < 60 * 300) { b.step(60); n += 60; }
        b.step(80);
        const f = b.fight; return { phase: f.phase, secs: n / 60, winner: f.winner.map(x => x.id), stats: f.fighters.map(x => x.stats), states: f.fighters.map(x => x.st) }; }""")
    check(res["phase"] == "over", f"CPU fighters fight to a result in {res['secs']} s ({res['winner']})")
    check(sum(s["dealt"] for s in res["stats"][1:]) > 300, "CPUs land hits")
    check(any(s == "win" for s in res["states"]), f"winner strikes the victory pose ({res['states']})")
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, "brawl_over.png"))
    page.keyboard.press("Escape")
    if SHOTS:
        page.screenshot(path=os.path.join(SHOTS, "brawl_lobby.png"))
    page.keyboard.press("Escape")
    check(page.locator("#brawl-overlay").count() == 0 and not ev(page, "window.ARK.HOOKS.busy.some(f => f())"), "ESC from lobby closes the brawl")
    page.keyboard.down("KeyD"); page.wait_for_timeout(300); page.keyboard.up("KeyD")
    check(ev(page, "window.ARK.P.x") != before[0], "village controls work again after closing")
    # regression: a re-rendered lobby with the controls <details> open fires `toggle` asynchronously; closing in
    # the same task used to throw "Cannot set properties of null (setting 'controlsOpen')"
    ev(page, "window.ARK.brawl.open()")
    page.click("#brawl-controls summary")
    ev(page, "() => { window.ARK.brawl.setOpts({}); window.ARK.brawl.close(); }")
    page.wait_for_timeout(300)
    # page CSS `canvas{display:block}` must not show the (hidden) fight canvas over the lobby
    ev(page, "window.ARK.brawl.open()")
    check(ev(page, "getComputedStyle(document.getElementById('brawl-canvas')).display") == "none", "fight canvas hidden while the lobby is shown")
    ev(page, "window.ARK.brawl.close()")
    check(not errs, f"no page errors ({errs})")
    check(not bad, f"all brawl assets load ({bad})")

    m = browser.new_page(viewport={"width": 390, "height": 844})
    m.goto(URL, wait_until="domcontentloaded")
    m.wait_for_function("window.ARK && window.ARK.brawl")
    m.evaluate("window.ARK.brawl.open()")
    box = m.locator("#brawl-start").bounding_box()
    check(box and box["y"] + box["height"] <= 844 and box["x"] >= 0, f"lobby start button visible on a phone ({box})")
    if SHOTS:
        m.screenshot(path=os.path.join(SHOTS, "brawl_lobby_mobile.png"))

    # Effects option (screen shake + white hit flash): on by default, saved, and off by default for reduced-motion users.
    check(ev(page, "window.ARK.brawl.opts.effects") is True, "effects (shake, flash) are on by default")
    ev(page, "window.ARK.brawl.open()")
    check(page.locator("#brawl-effects").is_checked(), "lobby has an EFFECTS checkbox, checked by default")
    page.locator("#brawl-effects").uncheck()
    check(ev(page, "window.ARK.brawl.opts.effects") is False and ev(page, "JSON.parse(localStorage.getItem('ark_brawl_opts_v1')).effects") is False, "unchecking EFFECTS turns them off and saves it")
    ev(page, "window.ARK.brawl.close(); window.ARK.brawl.setOpts({effects: true})")
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, reduced_motion="reduce")
    rm = ctx.new_page()
    rm.goto(URL, wait_until="domcontentloaded")
    rm.wait_for_function("window.ARK && window.ARK.brawl")
    check(ev(rm, "window.ARK.brawl.opts.effects") is False, "with reduced motion requested, effects start off")
    ctx.close()
    browser.close()

print("\nRESULT:", "PASS" if not FAILS else f"FAIL ({len(FAILS)})")
sys.exit(1 if FAILS else 0)
