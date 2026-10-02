"""E02: minimal two-lane local key-mash race prototype.

Run: python test/local_competition_race_test.py [URL]
Tests both 1280x720 and 390x844.
"""
import os, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
FAILS = []


def check(ok, msg):
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok: FAILS.append(msg)


def key_edge(page, code, repeat=False):
    page.evaluate("c => document.dispatchEvent(new KeyboardEvent('keydown',{code:c,repeat:" + str(repeat).lower() + ",bubbles:true}))", code)
    if not repeat:
        page.evaluate("c => document.dispatchEvent(new KeyboardEvent('keyup',{code:c,bubbles:true}))", code)


with sync_playwright() as p:
    browser = p.chromium.launch()
    for viewport in ({"width": 1280, "height": 720}, {"width": 390, "height": 844}):
        page = browser.new_page(viewport=viewport)
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("window.ARK && window.ARK.localCompetition")
        if page.evaluate("window.ARK.scene") != "play":
            page.keyboard.press("KeyN")
            page.locator("#player-name-input").fill("Pilot")
            page.keyboard.press("Enter")
            page.wait_for_function("window.ARK.scene === 'play'")

        # Activate the authored race marker as a real near interaction would.
        point = page.evaluate("window.ARK.localCompetition.racePoint")
        check(bool(point), f"{viewport}: local race has a world launch point")
        if not point:
            page.close(); continue
        page.evaluate("p => { window.ARK.P.x = p.x; window.ARK.P.y = p.y; }", point)
        page.keyboard.press("KeyE")
        check(page.locator("#local-race-overlay").is_visible(), f"{viewport}: race lobby opens from world interaction")
        check(page.locator("#local-race-start").count() == 1, f"{viewport}: start control is available")
        page.locator("#local-race-start").click()
        state = page.evaluate("window.ARK.localCompetition.race.state")
        check(state == "running", f"{viewport}: start opens one simultaneous race (got {state})")
        start_xy = page.evaluate("[window.ARK.P.x, window.ARK.P.y]")

        # Repeat and unrelated keys cannot score. Each player has an independent lane.
        key_edge(page, "KeyA")
        key_edge(page, "KeyA", repeat=True)
        key_edge(page, "KeyZ")
        prog = page.evaluate("window.ARK.localCompetition.race.participants.map(p=>p.result)")
        check(prog == [1, 0], f"{viewport}: lane A counts one real edge only (got {prog})")
        key_edge(page, "KeyL")
        prog = page.evaluate("window.ARK.localCompetition.race.participants.map(p=>p.result)")
        check(prog == [1, 1], f"{viewport}: lane L is independent (got {prog})")

        # Race A finishes first; both lanes run the same target distance.
        target = page.evaluate("window.ARK.localCompetition.race.target")
        for _ in range(target - 1): key_edge(page, "KeyA")
        key_edge(page, "KeyA")
        check(page.evaluate("window.ARK.localCompetition.race.participants[0].finishedAt !== null"),
              f"{viewport}: lane A finishes at the shared distance {target}")
        page.wait_for_timeout(160)  # a true lead, beyond the tie-resolution bucket
        for _ in range(target - 1): key_edge(page, "KeyL")
        key_edge(page, "KeyL")
        result = page.evaluate("({state:window.ARK.localCompetition.race.state,winner:window.ARK.localCompetition.race.winner,progress:window.ARK.localCompetition.race.participants.map(p=>p.result)})")
        check(result["state"] == "finished" and result["winner"] == "p1" and result["progress"] == [target, target],
              f"{viewport}: equal distance, earlier finish wins (got {result})")
        check(page.evaluate("[window.ARK.P.x,window.ARK.P.y]") == start_xy,
              f"{viewport}: race input never moves the single overworld player")

        # Exact same 100 ms finish bucket resolves deterministically as a tie.
        page.locator("#local-race-retry").click()
        page.locator("#local-race-start").click()
        page.evaluate("window.ARK.localCompetition.race.target=1; window.ARK.localCompetition.race.startAt=performance.now()")
        page.evaluate("""() => { for (const code of ['KeyA','KeyL']) {
          document.dispatchEvent(new KeyboardEvent('keydown',{code,bubbles:true}));
          document.dispatchEvent(new KeyboardEvent('keyup',{code,bubbles:true}));
        }}""")
        tie = page.evaluate("({winner:window.ARK.localCompetition.race.winner,finishedAt:window.ARK.localCompetition.race.participants.map(p=>p.finishedAt)})")
        check(tie["winner"] == "tie" and tie["finishedAt"][0] == tie["finishedAt"][1],
              f"{viewport}: identical finish time gives deterministic tie (got {tie})")

        # Restart resets both lanes; Escape aborts and stores no result.
        page.locator("#local-race-retry").click()
        reset = page.evaluate("({state:window.ARK.localCompetition.race.state,p:window.ARK.localCompetition.race.participants.map(p=>p.result),winner:window.ARK.localCompetition.race.winner})")
        check(reset == {"state":"ready","p":[0,0],"winner":None}, f"{viewport}: retry fully resets both lanes (got {reset})")
        page.locator("#local-race-start").click()
        key_edge(page, "KeyA")
        page.keyboard.press("Escape")
        aborted = page.evaluate("({state:window.ARK.localCompetition.race.state,p:window.ARK.localCompetition.race.participants.map(p=>p.result),winner:window.ARK.localCompetition.race.winner})")
        check(aborted == {"state":"cancelled","p":[0,0],"winner":None}, f"{viewport}: Escape aborts without result (got {aborted})")
        page.evaluate("window.__e02Player = window.ARK.P")
        page.locator("#local-race-leave").click()
        after_close = page.evaluate("({closed:window.ARK.localCompetition.race===null,samePlayer:window.ARK.P===window.__e02Player})")
        check(after_close == {"closed":True,"samePlayer":True}, f"{viewport}: leave restores the same single overworld player (got {after_close})")
        check(not errs, f"{viewport}: no page errors {errs}")
        page.close()
    browser.close()

print("\nFAILED:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)
