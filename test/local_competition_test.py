"""E01: isolated session-only participants and keyboard-edge behavior.

Checks two identities/names/keys/results; one result per true key edge;
repeat/unrelated keys ignored; focused input and Escape never score; Escape
cancels without a result; explicit hit/time comparators; no Q.mg mutation.

Run: python test/local_competition_test.py [URL]
"""
import os, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
FAILS = []


def check(ok, msg):
    print(("OK   " if ok else "FAIL ") + msg)
    if not ok: FAILS.append(msg)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_function("window.ARK && window.ARK.Q")

    api = page.evaluate("!!(window.ARK && window.ARK.localCompetition)")
    check(api, "local competition API registered without altering normal game boot")
    if api:
        baseline = page.evaluate("JSON.stringify(window.ARK.Q.mg)")
        page.evaluate("""() => {
          window.__e01 = window.ARK.localCompetition.createSession({
            id: 'e01-test', scoreKind: 'hits',
            participants: [
              { id: 'p1', name: 'Ada', key: 'KeyA' },
              { id: 'p2', name: 'Bela', key: 'KeyL' },
            ],
          });
        }""")
        rows = page.evaluate("window.__e01.participants.map(p => [p.id,p.name,p.key,p.result])")
        check(rows == [["p1", "Ada", "KeyA", 0], ["p2", "Bela", "KeyL", 0]], f"two distinct participants initialized (got {rows})")

        page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyA',bubbles:true}))")
        page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyA',repeat:true,bubbles:true}))")
        page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyZ',bubbles:true}))")
        r = page.evaluate("window.__e01.participants.map(p => p.result)")
        check(r == [1, 0], f"first press scores once; repeat/unrelated key ignored (got {r})")
        page.evaluate("document.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyA',bubbles:true})); document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyA',bubbles:true}))")
        r = page.evaluate("window.__e01.participants.map(p => p.result)")
        check(r == [2, 0], f"press-release-press gives exactly two edges (got {r})")
        page.evaluate("document.dispatchEvent(new KeyboardEvent('keyup',{code:'KeyL',bubbles:true})); document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyL',bubbles:true}))")
        r = page.evaluate("window.__e01.participants.map(p => p.result)")
        check(r == [2, 1], f"second participant key scores only second participant (got {r})")

        page.evaluate("""() => {
          window.__e01.reset();
          const input = document.createElement('input'); input.id = 'e01-focus'; document.body.appendChild(input); input.focus();
          input.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyA',bubbles:true}));
        }""")
        r = page.evaluate("window.__e01.participants.map(p => p.result)")
        check(r == [0, 0], f"focused text input cannot score (got {r})")
        page.evaluate("document.getElementById('e01-focus').remove(); document.body.focus()")

        page.evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{code:'Escape',bubbles:true}))")
        state = page.evaluate("({cancelled:window.__e01.cancelled,results:window.__e01.participants.map(p=>p.result)})")
        check(state == {"cancelled": True, "results": [0, 0]}, f"Escape cancels without score/result (got {state})")

        page.evaluate("""() => {
          const config = kind => ({id:kind,scoreKind:kind,participants:[{id:'a',name:'A',key:'KeyA'},{id:'b',name:'B',key:'KeyL'}]});
          const hits = window.ARK.localCompetition.createSession(config('hits'));
          hits.setResult('a', 7); hits.setResult('b', 5);
          const hitWinner = hits.winner();
          const time = window.ARK.localCompetition.createSession(config('time'));
          time.setResult('a', 12.2); time.setResult('b', 13.1);
          window.__e01comparators = [hitWinner, time.winner()];
        }""")
        winners = page.evaluate("window.__e01comparators")
        check(winners == ["a", "a"], f"explicit hits-high/time-low comparators select the right winner (got {winners})")
        page.evaluate("""() => {
          const s = window.ARK.localCompetition.createSession({id:'tie',scoreKind:'time',participants:[{id:'a',name:'A',key:'KeyA'},{id:'b',name:'B',key:'KeyL'}]});
          s.participants.forEach(p => p.result=10); window.__e01tie=s.winner();
        }""")
        tie = page.evaluate("window.__e01tie")
        check(tie is None, f"equal results produce a deterministic tie (got {tie})")
        after = page.evaluate("JSON.stringify(window.ARK.Q.mg)")
        check(after == baseline, f"session-only results leave legacy Q.mg unchanged ({baseline} -> {after})")
        page.evaluate("window.__e01.cancel()")

    # Ordinary game still boots and single-player legacy API remains available.
    single = page.evaluate("!!(window.__features && typeof window.__features.startMG === 'function')")
    check(single, "existing single-player minigame entry point remains present")
    check(not errors, f"no page errors {errors}")
    browser.close()

print("\nFAILED:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)
