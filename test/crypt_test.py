"""Headless crypt test: confessional riddle -> counting clues -> cryptex -> crypt -> sign order puzzle -> hidden chamber,
then back up to the church, out to the village, and a reload in the middle of the crypt.

Run (server first: python -m http.server 8770 --directory docs):
    ARK_URL=http://127.0.0.1:8770/index.html python test/isolated_browser_runner.py test/crypt_test.py
Set CRYPT_SHOTS=<dir> to also write the documentation screenshots there (flat files).
"""
import time, os, json
from playwright.sync_api import sync_playwright
EXE = os.environ.get("CHROME")   # optional explicit Chromium path
SHOTS = os.environ.get("CRYPT_SHOTS")
URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SAVE_KEY = "arek-chlopkow-save-v1"
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE) if EXE else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" and "favicon" not in m.text else None)
    pg.goto(URL); pg.wait_for_function("window.__game", timeout=30000)
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_function("window.__game")
    pg.keyboard.press("Enter")
    pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.2)

    def shot(name):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True); time.sleep(1.2); pg.screenshot(path=os.path.join(SHOTS, name))

    def tp(x, y):
        pg.evaluate(f"(()=>{{const g=__game; for(let r=0;r<80;r+=2)for(let a=0;a<6.3;a+=.3){{const X={x}+Math.cos(a)*r,Y={y}+Math.sin(a)*r; if(!g.blocked(X,Y)){{g.P.x=X;g.P.y=Y;return}}}}}})()")
        time.sleep(.3)

    def talk_all():
        n = 0
        for _ in range(30):
            if not pg.evaluate("!!__game.talk"): break
            pg.keyboard.press("Space"); time.sleep(.07); pg.keyboard.press("Space"); time.sleep(.07); n += 1
        return n

    def poi(key, nth=0):
        return pg.evaluate(f"__game.room.pois.filter(p=>p.key==='{key}')[{nth}] || null")

    def read(key, nth=0, who="arek"):
        pt = poi(key, nth); assert pt, f"no POI {key}"
        tp(pt["x"], pt["y"]); pg.keyboard.press("KeyE"); time.sleep(.35)
        t = pg.evaluate("__game.talk && {who:__game.talk.who, n:__game.talk.lines.length, first:__game.talk.lines[0]}")
        check(bool(t) and t["who"] == who, f"read {key}: {t['first'][:60] if t else None}")
        talk_all()
        return t

    def kind(): return pg.evaluate("__game.room && (__game.room.kind || 'church')")
    def Q(k): return pg.evaluate(f"__game.Q.{k}")
    def room_wait(k, timeout=3):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if kind() == k: return True
            time.sleep(.1)
        return False
    def save_pos(): return pg.evaluate(f"(()=>{{const s=JSON.parse(localStorage.getItem('{SAVE_KEY}')); return [s.x,s.y,s.Q]}})()")

    # ---------------- village -> church
    c = pg.evaluate("__game.MAP.pois.find(p=>p.key==='church')"); tp(c["x"], c["y"] + 40)
    out = pg.evaluate("[__game.P.x, __game.P.y]")
    pg.keyboard.press("KeyE"); time.sleep(.8)
    check(kind() == "church", "entered the church")
    talk_all()

    # ---------------- 1. first confessional visit: the whisper (no free door)
    conf = poi("confession")
    tp(conf["x"], conf["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    t = pg.evaluate("__game.talk && {who:__game.talk.who, n:__game.talk.lines.length}")
    check(t and t["who"] == "szept" and t["n"] == 3, f"confessional whispers a riddle first {t}")
    shot("01_church_confessional_hint.png")
    talk_all()
    check(Q("cryptHint") is True and Q("cryptOpen") is False, "hint stored, door still shut")
    check(kind() == "church", "still in the church after the whisper")

    # ---------------- 2. cryptex overlay: wrong code is refused
    pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("!!CRYPT.puzzle()"), "second visit opens the cryptex")
    shot("02a_cryptex_empty_notebook.png")
    for ch in "1111": pg.keyboard.press("Digit" + ch)
    pg.keyboard.press("Enter"); time.sleep(.3)
    check(pg.evaluate("!!CRYPT.puzzle()") and Q("cryptOpen") is False, "wrong code 1111 is refused")
    pg.keyboard.press("Escape"); time.sleep(.2)
    check(not pg.evaluate("!!CRYPT.puzzle()"), "Esc closes the cryptex")

    # ---------------- 3. read the clues in the church (notes only count after the whisper)
    for key, num in [("candles", 4), ("pew", 7), ("glass", 2), ("altar", 3)]:
        t = read(key)
        check(t["n"] >= 2, f"clue {key} has extra counting line")
    check(sorted(Q("cryptNotes")) == ["altar", "candles", "glass", "pew"], f"4 notes recorded {Q('cryptNotes')}")
    read("flowers")
    check(len(Q("cryptNotes")) == 4, "flowers is a red herring (no note)")
    # glass has two windows
    check(pg.evaluate("__game.room.pois.filter(p=>p.key==='glass').length") == 2, "two stained-glass POIs")

    # ---------------- 4. solve with the real keyboard path
    tp(conf["x"], conf["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("!!CRYPT.puzzle()"), "cryptex opens again")
    pg.keyboard.press("ArrowUp"); pg.keyboard.press("ArrowUp"); pg.keyboard.press("ArrowUp"); pg.keyboard.press("ArrowUp")   # ring 0 -> 4 via arrows
    pg.keyboard.press("ArrowRight")
    for ch in "723": pg.keyboard.press("Digit" + ch)
    check(pg.evaluate("CRYPT.puzzle().d.join('')") == "4723", "dials show 4723")
    shot("02_cryptex_puzzle.png")
    pg.keyboard.press("Enter"); time.sleep(.4)
    check(Q("cryptOpen") is True, "4723 opens the confessional")
    check(kind() == "church", "still in the church while the passage opens")
    shot("03_confessional_opened.png")
    n = talk_all(); check(n >= 3, "solved dialogue plays")
    check(room_wait("crypt"), "descended into the crypt after the dialogue")
    time.sleep(.3)
    check(pg.evaluate("__game.parentRoom && !__game.parentRoom.kind") is True, "church is remembered as the parent room")
    # the save must point at the village door, not at crypt coordinates
    sx, sy, _ = save_pos()
    check(abs(sx - out[0]) < 40 and abs(sy - out[1]) < 40, f"save written inside the crypt = village door {sx:.0f},{sy:.0f} vs {out[0]:.0f},{out[1]:.0f}")
    talk_all()   # first-visit line (cryptIn)

    # ---------------- 5. the crypt
    shot("04_crypt_entrance.png")
    read("cryptArch")
    for i in range(4): read("cryptTomb", i)
    read("cryptFloor")
    read("cryptPlaque")
    t = read("cryptDoor"); check(t["n"] == 2, "door says it is shut")
    tp(160, 300); shot("05_crypt_main_hall.png")
    # wrong order first, then the right order from the tablet: CRUX, ROSA, CIRCULUS, LUX
    pt = poi("symLux"); tp(pt["x"], pt["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(pg.evaluate("__game.room.seq") == 0 and pg.evaluate("__game.toastText") is not None, "wrong first sign resets")
    for i, key in enumerate(["symCrux", "symRosa", "symCirculus", "symLux"]):
        pt = poi(key); tp(pt["x"], pt["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
        if i < 3: check(pg.evaluate("__game.room.seq") == i + 1, f"sign {key} accepted ({i + 1}/4)")
    time.sleep(.2)
    check(Q("cryptDoor") is True and pg.evaluate("__game.room.doorOpen"), "four signs in order open the stone door")
    shot("05b_crypt_door_open_dialogue.png")
    talk_all()
    # chamber is reachable now and not before
    read("cryptMap", 0)
    tp(126, 134); shot("06_crypt_final_chamber.png")
    read("cryptBook")
    check(Q("cryptReward") is True, "book found, reward stored")
    read("cryptBook")   # the 'again' text
    shot("06b_crypt_book.png")

    # ---------------- 6. reload in the middle of the crypt: no stranding
    tp(160, 300)
    pg.evaluate("ARK.save()")
    sx, sy, sq = save_pos()
    check(abs(sx - out[0]) < 40 and abs(sy - out[1]) < 40, "save inside crypt = village coordinates")
    check(sq.get("cryptDoor") and sq.get("cryptReward") and sq.get("cryptOpen") and sq.get("cryptHint"), "crypt state is in the save")
    pg.reload(); pg.wait_for_function("window.__game"); time.sleep(.6)
    pg.keyboard.press("Enter"); time.sleep(.6)
    for _ in range(40):
        if pg.evaluate("__game.scene") == "play": break
        time.sleep(.2)
    check(pg.evaluate("__game.scene") == "play", "continues after reload")
    check(not pg.evaluate("!!__game.room"), "after reload Arek is in the village")
    back = pg.evaluate("[__game.P.x, __game.P.y]")
    check(abs(back[0] - out[0]) < 60 and abs(back[1] - out[1]) < 60, f"after reload Arek stands at the church door {back}")
    check(Q("cryptOpen") is True and Q("cryptDoor") is True and Q("cryptReward") is True, "crypt progress survived the reload")

    # ---------------- 7. second descent: no puzzle, door already open, then climb up and leave
    pg.keyboard.press("KeyE"); time.sleep(.8)
    check(kind() == "church", "re-entered the church")
    talk_all()
    check(pg.evaluate("__game.room.pois.length > 0"), "church loaded")
    conf = poi("confession"); tp(conf["x"], conf["y"]); pg.keyboard.press("KeyE"); time.sleep(.3)
    check(not pg.evaluate("!!CRYPT.puzzle()"), "solved confessional goes straight down")
    check(room_wait("crypt"), "second descent works")
    time.sleep(.3)
    check(pg.evaluate("__game.room.doorOpen") is True and poi("cryptBook") is not None, "stone door stays open, chamber present")
    # stairs up
    pg.evaluate("__game.P.x=160; __game.P.y=480")
    pg.keyboard.down("ArrowDown"); time.sleep(.9); pg.keyboard.up("ArrowDown"); time.sleep(.7)
    check(kind() == "church", "stairs lead back up into the church")
    here = pg.evaluate("[__game.P.x, __game.P.y]")
    check(abs(here[0] - conf["x"]) < 30 and abs(here[1] - conf["y"]) < 30, f"Arek stands at the confessional {here}")
    # leave the church: back at the village door
    pg.evaluate("__game.P.x=160; __game.P.y=426"); pg.keyboard.down("ArrowDown"); time.sleep(.6); pg.keyboard.up("ArrowDown"); time.sleep(.7)
    check(not pg.evaluate("!!__game.room"), "left the church")
    back = pg.evaluate("[__game.P.x, __game.P.y]")
    check(abs(back[0] - out[0]) < 60 and abs(back[1] - out[1]) < 60, f"back at the village door {back}")

    # ---------------- 8. English texts exist for every crypt key
    keys = ["confessionHint", "candles", "clue", "cryptNoteNames", "cryptSolved", "cryptIn", "cryptArch", "cryptTomb", "cryptFloor", "cryptPlaque",
            "cryptDoorShut", "cryptDoorOpen", "cryptMap", "cryptBook", "cryptLabel", "cryptQuest", "cryptPuzzleTitle", "cryptRiddle"]
    pg2 = b.new_page(viewport={"width": 800, "height": 500}); pg2.goto(URL.split("?")[0] + "?lang=en"); pg2.wait_for_function("window.__game", timeout=30000)
    miss = pg2.evaluate(f"{json.dumps(keys)}.filter(k=>!ARK.T[k])"); check(not miss, f"EN texts present {miss}")
    pl_en = pg2.evaluate("JSON.stringify([ARK.T.cryptBook, ARK.T.confessionHint, ARK.T.cryptPlaque])")
    check("\u2014" not in pl_en and "\u2013" not in pl_en, "no dashes in EN crypt text")
    pg2.close()
    pgl = pg.evaluate("JSON.stringify(Object.entries(ARK.T).filter(([k])=>k.startsWith('crypt')||k.startsWith('sym')||k==='clue'||k==='confessionHint'))")
    check("\u2014" not in pgl and "\u2013" not in pgl, "no dashes in PL crypt text")

    check(not errs, f"no page errors {errs[:3]}")
    print("crypt", "OK" if not fails else "FAILED", "errors", errs)
    b.close()
if fails:
    raise SystemExit("FAIL " + "; ".join(fails))
