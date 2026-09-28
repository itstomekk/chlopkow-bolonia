"""Music: the engine starts on the first key press, picks the track by scene, K mutes/unmutes, and every
song arranges and plays without errors."""
import os, time
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.add_init_script("""
    (() => {
        const realNow = performance.now.bind(performance);
        let extra = 0;
        Object.defineProperty(performance, 'now', { configurable: true, value: () => realNow() + extra });
        window.__advanceMusicClock = ms => { extra += ms; };
    })();
    """)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game && window.MUSIC", timeout=30000)
    pg.evaluate("localStorage.removeItem('arek-music-muted')")
    pg.keyboard.press("Enter")
    if pg.locator("#player-name-input").count():
        pg.locator("#player-name-input").fill("Test"); pg.keyboard.press("Enter")
    pg.wait_for_function("__game.scene === 'play'")
    time.sleep(.6)
    st = pg.evaluate("[MUSIC.state, MUSIC.current, MUSIC.muted]")
    print("after start", st)
    assert st[0] == 'running' and st[1] in ('krakowiak', 'mazurka') and not st[2], st

    # outdoor tempo contract: slower acceleration, a 0.2x floor, and no fast asymmetric catch-up
    tempo = pg.evaluate("({ ...MUSIC.TEMPO })")
    print("tempo settings", tempo)
    assert tempo['idle'] == .2, tempo
    assert tempo['rampUp'] > 20 and tempo['rampRun'] > 10, tempo
    assert tempo['rampDown'] >= tempo['rampRun'], tempo
    assert tempo.get('glideUp', 1) == tempo.get('glideDown', 1), tempo

    time.sleep(2.5); idle = pg.evaluate("MUSIC.tempo"); print("idle tempo", round(idle, 2)); assert idle < .5, idle
    pg.keyboard.down("ShiftLeft")
    for k in ["ArrowLeft", "ArrowRight"] * 3: pg.keyboard.down(k); time.sleep(.8); pg.keyboard.up(k)
    pg.keyboard.up("ShiftLeft")
    fast = pg.evaluate("MUSIC.tempo"); print("after running", round(fast, 2)); assert fast > idle + .25, fast
    assert fast <= 1.31, fast

    # stopping should spend comparable time in comparable linear energy intervals
    time.sleep(.5); first_calm = pg.evaluate("MUSIC.tempo")
    time.sleep(1.5); second_calm = pg.evaluate("MUSIC.tempo")
    drop1, drop2 = fast - first_calm, first_calm - second_calm
    print("calm drops", round(drop1, 3), round(drop2, 3))
    assert drop1 > 0 and abs(drop1 - drop2) < max(.08, drop1 * .6), (drop1, drop2)

    # a long standing-still period must not select pastoralka; village tracks may still alternate normally
    for _ in range(32):
        pg.evaluate("window.__advanceMusicClock(1000)"); time.sleep(.08)
    idle_track = pg.evaluate("MUSIC.current")
    print("long-idle track", idle_track)
    assert idle_track in ('krakowiak', 'mazurka'), idle_track

    # touching Frodo barks
    pg.evaluate("(() => { const g = __game; g.P.x = g.FRODO.x; g.P.y = g.FRODO.y; })()"); time.sleep(.3)
    print("barks", pg.evaluate("MUSIC.barks")); assert pg.evaluate("MUSIC.barks") >= 1
    pg.screenshot(path="test/music_hau.png")

    # cemetery -> nokturn
    cem = pg.evaluate("__game.MAP.pois.find(p => p.key === 'cemetery')")
    pg.evaluate(f"__game.P.x = {cem['x']}; __game.P.y = {cem['y']} + 60"); time.sleep(.8)
    print("cemetery", pg.evaluate("MUSIC.current")); assert pg.evaluate("MUSIC.current") == 'nokturn'
    pg.evaluate(f"__game.P.x = {cem['x']} + 600"); time.sleep(.8)
    assert pg.evaluate("MUSIC.current") in ('krakowiak', 'mazurka'), pg.evaluate("MUSIC.current")

    # church -> choral
    pg.evaluate("__game.enterChurch()"); time.sleep(1.2)
    print("church", pg.evaluate("MUSIC.current")); assert pg.evaluate("MUSIC.current") == 'choral'

    # K toggles mute and is remembered
    pg.keyboard.press("KeyK"); time.sleep(.2)
    assert pg.evaluate("MUSIC.muted") and pg.evaluate("localStorage.getItem('arek-music-muted')") == '1'
    pg.keyboard.press("KeyK"); time.sleep(.2)
    assert not pg.evaluate("MUSIC.muted")

    # each song plays for a moment
    for s in pg.evaluate("MUSIC.SONGS"):
        pg.evaluate(f"MUSIC.play('{s}')"); time.sleep(.2)
        # the scene picker overrides play() every frame, so just check that arranging/playing throws nothing
    pg.evaluate("MUSIC.jingle(); MUSIC.ding()"); time.sleep(.5)
    pg.screenshot(path="test/music_hud.png")
    b.close()

print("errors", errors)
assert not errors
print("music ok")
