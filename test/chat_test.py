"""Smoke-test the always-visible in-play chat overlay.

Run with the same local server used by the other play-tests:
    python -m http.server 8765 --directory docs
    python test/chat_test.py

Use test/isolated_browser_runner.py to disable public relay traffic.
"""
import os

from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(URL)
    if not page.locator("#arek-global-chat").count():
        parsed = urlsplit(URL)
        base_path = parsed.path if parsed.path.endswith("/") else parsed.path.rsplit("/", 1)[0] + "/"
        script_url = urlunsplit((parsed.scheme, parsed.netloc, base_path + "js/chat.js", "", ""))
        page.add_script_tag(url=script_url)
    page.wait_for_function("window.__arekGlobalChat")
    assert page.locator("#arek-chat-panel").evaluate("node => getComputedStyle(node).display") == "block"
    assert page.evaluate("__arekGlobalChat.unicodeLength('😀éa')") == 3

    page.keyboard.press("KeyN")
    page.locator("#player-name-input").fill("ChatTest")
    page.locator("#player-name-submit").click()
    page.wait_for_function("__game.scene === 'play'")
    assert page.locator("#arek-chat-panel").is_visible()
    assert page.locator("#arek-chat-launch").count() == 0
    assert page.locator("#arek-chat-close").count() == 0
    page.locator("#arek-chat-text").fill("😀" * 101)
    assert page.locator("#arek-chat-text").input_value() == "😀" * 100
    assert page.locator("#arek-chat-count").text_content() == "100/100"
    page.wait_for_timeout(1000)
    status = page.locator("#arek-chat-status").text_content()
    assert status and not status.startswith("Message sent")
    assert "unavailable" in status.lower() or "connecting" in status.lower()
    # Optional relay-history assertion is deliberately opt-in; runner isolation disables transport.
    if not os.environ.get("ARK_CHAT_OFFLINE"):
        page.wait_for_function("__arekGlobalChat.isConnected()", timeout=20000)
        n = page.evaluate("__arekGlobalChat.messageCount()")
        assert n >= 1, "no channel history loaded"
        assert page.evaluate("__arekGlobalChat.historySince") <= 1790373600
        days = page.locator(".arek-chat-day").count()
        assert days >= 1, "day separators missing"
        status = page.locator("#arek-chat-status").text_content()
        print("history:", n, "messages,", days, "day(s)")
    assert not errors, errors
    print("chat smoke: PASS - in-play visibility, legacy preference ignored, Unicode limit, no page errors")
    print("status:", status)
    browser.close()
