"""Arrival-log contract with an isolated, deterministic nostr-tools transport.

No CDN or relay is contacted. The controlled pool records signed payloads and can
reject or accept publication, allowing safe coverage of retry and echo handling.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8797/index.html")
SHOTS = Path(r"C:\Users\Lenovo\AppData\Local\hermes\cache\scratch\chlopkow-arrival-log")
SHOTS.mkdir(parents=True, exist_ok=True)

STUB = r"""
export function generateSecretKey() { return new Uint8Array(32).fill(7); }
export function getPublicKey() { return 'b'.repeat(64); }
export function finalizeEvent(event) {
  return {...event, id: 'c'.repeat(62) + String(++window.__nostrHarness.nextId).padStart(2, '0'), pubkey: 'b'.repeat(64), sig: 'd'.repeat(128)};
}
export class SimplePool {
  subscribeMany(relays, filter, handlers) {
    window.__nostrHarness.subscriptions.push(handlers);
    setTimeout(() => { handlers.oneose(); for (const ev of window.__nostrHarness.history) handlers.onevent(ev); }, 5);
    return { close() {} };
  }
  publish(relays, event) {
    const h = window.__nostrHarness;
    h.calls.push(JSON.parse(JSON.stringify(event)));
    if (h.failures > 0) { h.failures--; return relays.map(() => Promise.reject(new Error('controlled rejection'))); }
    h.accepted.push(JSON.parse(JSON.stringify(event)));
    h.history.push(JSON.parse(JSON.stringify(event)));
    localStorage.setItem('__arrivalHarness', JSON.stringify({nextId:h.nextId, calls:h.calls, accepted:h.accepted, history:h.history}));
    for (const sub of h.subscriptions) sub.onevent(event);
    return relays.map(() => Promise.resolve());
  }
  listConnectionStatus() { return new Map([['test', true]]); }
  close() {}
}
"""


def setup(page):
    page.add_init_script("const s=JSON.parse(localStorage.getItem('__arrivalHarness')||'{}'); window.__nostrHarness = {nextId:s.nextId||0, failures:0, calls:s.calls||[], accepted:s.accepted||[], history:s.history||[], subscriptions:[]};")
    page.route("https://esm.sh/nostr-tools@2.25.2?bundle&target=es2020", lambda route: route.fulfill(status=200, content_type="application/javascript", body=STUB))
    page.route("wss://**", lambda route: route.abort())
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL + "?debug=1&music=0")
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    return errors


def submit_name(page, name):
    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill(name)
    page.locator("#player-name-submit").click()


def start_chat(page):
    page.wait_for_function("window.__arekGlobalChat.isConnected()")


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = setup(page)
    assert page.evaluate("__nostrHarness.calls.length") == 0, "title screen must never announce"
    page.keyboard.press("KeyN")
    disclosure = page.locator("#player-name-disclosure")
    assert disclosure.is_visible() and "public" in disclosure.inner_text().lower() and "nostr" in disclosure.inner_text().lower()
    page.locator("#player-name-input").fill("   ")
    page.locator("#player-name-submit").click()
    assert page.locator("#player-name-input").is_visible(), "blank name must not enter play"
    assert page.evaluate("__nostrHarness.calls.length") == 0
    page.locator("#player-name-input").fill("  Żaneta <img>  ")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    start_chat(page)
    page.wait_for_function("__nostrHarness.accepted.length === 1")
    assert page.evaluate("__nostrHarness.calls.length") == 1, "one signed arrival per document visit"
    event = page.evaluate("__nostrHarness.accepted[0]")
    assert event["kind"] == 42 and event["content"]
    assert [tag[0] for tag in event["tags"]].count("arrival") == 1
    assert [tag[0] for tag in event["tags"]].count("session") == 1
    assert next(tag[1] for tag in event["tags"] if tag[0] == "name") == "Żaneta img"
    assert page.locator("#arek-chat-panel").is_visible()
    page.wait_for_function("document.querySelectorAll('.arek-chat-arrival').length === 1")
    assert page.locator(".arek-chat-arrival").inner_text().find("Żaneta") >= 0
    assert page.locator(".arek-chat-arrival img").count() == 0, "arrival text must not become HTML"
    assert page.locator(".arek-chat-arrival > div").count() == 0, "arrival must be one compact line, not repeated name/header rows"
    arrival_color = page.locator(".arek-chat-arrival").evaluate("e => getComputedStyle(e).color")
    assert arrival_color not in ("rgb(255, 247, 214)", "rgba(0, 0, 0, 0)"), arrival_color

    # Reopening and dialogue/map visibility do not publish again; arrival and regular chat coexist.
    page.locator("#arek-chat-close").click()
    page.evaluate("__arekGlobalChat.open()")
    page.evaluate("""() => __arekGlobalChat.injectEvent({kind:42,id:'f'.repeat(64),created_at:Math.floor(Date.now()/1000),content:'Zwykła wiadomość',pubkey:'a'.repeat(64),tags:[['e',__arekGlobalChat.channelId,'','root'],['name','Sąsiad']]})""")
    page.evaluate("""() => __arekGlobalChat.injectEvent({kind:42,id:'2'.repeat(64),created_at:Math.floor(Date.now()/1000),content:'Do Chłopkowa zagląda Mira.',pubkey:'a'.repeat(64),tags:[['e',__arekGlobalChat.channelId,'','root'],['name','Mira']]})""")
    page.evaluate("""() => __arekGlobalChat.injectEvent({kind:42,id:'3'.repeat(64),created_at:Math.floor(Date.now()/1000),content:'invalid arrival',pubkey:'a'.repeat(64),tags:[['e',__arekGlobalChat.channelId,'','root'],['arrival','v1'],['name','No session']]})""")
    page.wait_for_function("document.querySelectorAll('.arek-chat-arrival').length === 1 && document.querySelectorAll('.arek-chat-regular').length === 2")
    assert page.locator(".arek-chat-arrival").count() == 1
    assert page.locator(".arek-chat-regular").count() == 2
    assert page.locator(".arek-chat-regular").filter(has_text="Do Chłopkowa zagląda Mira.").count() == 1, "ordinary text must not be guessed as an arrival"
    assert page.evaluate("__arekGlobalChat.messageCount()") == 3, "invalid arrival tags must be rejected"
    page.evaluate("__nostrHarness.subscriptions[0].onevent(__nostrHarness.accepted[0])")
    page.wait_for_timeout(50)
    assert page.locator(".arek-chat-arrival").count() == 1, "relay echo must deduplicate by event ID"
    assert page.evaluate("__nostrHarness.calls.length") == 1
    page.screenshot(path=str(SHOTS / "arrival-desktop.png"))

    # Reload is a new visit: previous arrival is replayed but a fresh signed event is made.
    page.reload()
    page.wait_for_function("window.__game && window.__arekGlobalChat")
    assert page.evaluate("__nostrHarness.accepted.length") == 1
    submit_name(page, "Żaneta")
    page.wait_for_function("__nostrHarness.accepted.length === 2")
    page.wait_for_function("__arekGlobalChat.messageCount() >= 2")
    assert page.locator(".arek-chat-arrival").count() == 2, "accepted arrivals must replay from channel history"
    assert page.evaluate("__nostrHarness.calls.length") == 2
    assert page.evaluate("__nostrHarness.accepted[0].id !== __nostrHarness.accepted[1].id")

    # A saved-name continuation enters without the form and still creates one arrival.
    page.evaluate("localStorage.removeItem('arek-chlopkow-save-v1')")

    # Existing save with a valid name continues directly and announces only upon Enter.
    saved = browser.new_page(viewport={"width": 1280, "height": 720})
    saved_errors = setup(saved)
    saved.evaluate("localStorage.setItem('arek-chlopkow-save-v1', JSON.stringify({v:2,Q:{playerName:'Saved'},x:1200,y:4050}))")
    saved.reload()
    saved.wait_for_function("window.__game && window.__arekGlobalChat")
    assert saved.evaluate("__nostrHarness.calls.length") == 0, "saved title must not announce before continuation"
    saved.keyboard.press("Enter")
    saved.wait_for_function("__game.scene === 'play'")
    saved.wait_for_function("__nostrHarness.accepted.length === 1")
    assert saved.evaluate("__nostrHarness.accepted[0].tags.find(t => t[0] === 'name')[1]") == "Saved"
    assert not saved_errors, saved_errors

    legacy = browser.new_page(viewport={"width": 1280, "height": 720})
    legacy_errors = setup(legacy)
    legacy.evaluate("localStorage.setItem('arek-chlopkow-save-v1', JSON.stringify({Q:{playerName:'',apples:[1,2]},x:1200,y:4050}))")
    legacy.reload()
    legacy.wait_for_function("window.__game && window.__arekGlobalChat")
    legacy.keyboard.press("Enter")
    assert legacy.locator("#player-name-input").is_visible(), "legacy unnamed save must ask once"
    assert legacy.evaluate("__nostrHarness.calls.length") == 0
    legacy.locator("#player-name-input").fill("Legacy")
    legacy.locator("#player-name-submit").click()
    legacy.wait_for_function("__nostrHarness.accepted.length === 1")
    assert legacy.evaluate("__nostrHarness.calls.length") == 1
    assert legacy.evaluate("__nostrHarness.accepted[0].tags.find(t => t[0] === 'name')[1]") == "Legacy"
    assert legacy.evaluate("__game.Q.apples.length") == 2, "name continuation must keep existing progress"
    assert not legacy_errors, legacy_errors

    # A failed first write stays out of history; minimized UI remains closed, then online retries the same signature.
    offline = browser.new_page(viewport={"width": 1280, "height": 720})
    offline_errors = setup(offline)
    offline.evaluate("localStorage.setItem('arek-chlopkowie-chat-minimized-v1','1')")
    offline.reload()
    offline.wait_for_function("window.__game && window.__arekGlobalChat")
    offline.evaluate("__nostrHarness.failures=1")
    submit_name(offline, "Retry")
    offline.wait_for_function("__nostrHarness.calls.length === 1")
    offline.wait_for_timeout(30)
    assert offline.evaluate("__nostrHarness.accepted.length") == 0
    assert offline.evaluate("__arekGlobalChat.messageCount()") == 0, "failed arrival must not appear as persisted"
    assert not offline.locator("#arek-chat-panel").is_visible(), "arrival publishing must not reopen minimized chat"
    offline.evaluate("__arekGlobalChat.open()")
    offline.wait_for_function("__nostrHarness.accepted.length === 1")
    offline.evaluate("__arekGlobalChat.close()")
    calls = offline.evaluate("__nostrHarness.calls")
    assert len(calls) == 2 and calls[0] == calls[1], "retry must reuse the exact signed event"
    assert offline.evaluate("__arekGlobalChat.messageCount()") == 1
    offline.evaluate("dispatchEvent(new Event('online'))")
    offline.wait_for_timeout(30)
    assert offline.evaluate("__nostrHarness.calls.length") == 2, "accepted visit must not republish"
    assert not offline_errors, offline_errors

    capped = browser.new_page(viewport={"width": 1280, "height": 720})
    capped_errors = setup(capped)
    capped.evaluate("__nostrHarness.failures=10")
    submit_name(capped, "Limit")
    capped.wait_for_function("__nostrHarness.calls.length === 1")
    for _ in range(4):
        capped.evaluate("dispatchEvent(new Event('online'))")
        capped.wait_for_timeout(50)
    cap_calls = capped.evaluate("__nostrHarness.calls")
    assert len(cap_calls) == 3, f"arrival retries must stop at three attempts, got {len(cap_calls)}"
    assert len({event['id'] for event in cap_calls}) == 1, "all bounded retries must reuse one signed event"
    assert capped.evaluate("__arekGlobalChat.messageCount()") == 0
    assert not capped_errors, capped_errors
    capped.close()
    legacy.close()
    offline.close()
    saved.close()
    browser.close()

# Mobile form/disclosure fit and screenshot; transport stays controlled.
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    errors = setup(page)
    page.keyboard.press("KeyN")
    assert page.locator("#player-name-disclosure").is_visible()
    assert float(page.locator("#player-name-disclosure").evaluate("e => getComputedStyle(e).fontSize").removesuffix("px")) >= 12
    box = page.locator("#player-name-overlay").bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390
    page.screenshot(path=str(SHOTS / "arrival-mobile-form.png"))
    page.locator("#player-name-input").fill("Ada")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__nostrHarness.accepted.length === 1")
    assert not errors, errors
    browser.close()
print("arrival log: controlled publish, disclosure, title/blank gating, safe tagged rendering, coexistence, dedupe, reload, mobile: PASS")
