"""Music: the engine starts on the first key press, picks the track by scene, K mutes/unmutes, and every
song arranges and plays without errors."""
import os, time
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={"width": 1280, "height": 720})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")); pg.wait_for_function("window.__game && window.MUSIC", timeout=30000)
    pg.evaluate("localStorage.removeItem('arek-music-muted')")
    pg.keyboard.press("Enter"); time.sleep(.6)
    st = pg.evaluate("[MUSIC.state, MUSIC.current, MUSIC.muted]")
    print("after start", st)
    assert st[0] == 'running' and st[1] in ('krakowiak', 'mazurka') and not st[2], st

    # tempo follows the player: idle drifts toward 0.5x, running builds it up, standing still calms it again
    time.sleep(2.5); idle = pg.evaluate("MUSIC.tempo"); print("idle tempo", round(idle, 2)); assert idle < .62, idle
    pg.keyboard.down("ShiftLeft")
    for k in ["ArrowLeft", "ArrowRight"] * 3: pg.keyboard.down(k); time.sleep(.8); pg.keyboard.up(k)
    pg.keyboard.up("ShiftLeft")
    fast = pg.evaluate("MUSIC.tempo"); print("after running", round(fast, 2)); assert fast > idle + .25, fast
    time.sleep(4); calm = pg.evaluate("MUSIC.tempo"); print("calmed", round(calm, 2)); assert calm < fast - .2, calm

    # church -> pastoralka
    pg.evaluate("__game.enterChurch()"); time.sleep(1.2)
    print("church", pg.evaluate("MUSIC.current")); assert pg.evaluate("MUSIC.current") == 'pastoralka'

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
