"""Smoke-test the opt-in chat overlay.

Run with the same local server used by the other play-tests:
    python -m http.server 8765 --directory docs
    python test/chat_test.py

The test intentionally does not publish a message. Opening the panel may read
public channel history from Nostr relays.
"""
import os
import re
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

URL = os.environ.get("ARK_URL", "http://127.0.0.1:8765/index.html")
SECRET_KEY = "arek-chlopkowie-nostr-guest-secret-v1"

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
    page.evaluate(f"localStorage.removeItem('{SECRET_KEY}')")
    assert page.locator("#arek-chat-panel").evaluate("node => getComputedStyle(node).display") == "none"
    assert page.evaluate(f"localStorage.getItem('{SECRET_KEY}')") is None
    assert page.evaluate("__arekGlobalChat.unicodeLength('😀éa')") == 3

    page.click("#arek-chat-launch")
    page.wait_for_function(f"localStorage.getItem('{SECRET_KEY}')")
    page.locator("#arek-chat-text").fill("😀" * 101)
    assert page.locator("#arek-chat-text").input_value() == "😀" * 100
    assert page.locator("#arek-chat-count").text_content() == "100/100"
    page.wait_for_timeout(1000)
    status = page.locator("#arek-chat-status").text_content()
    assert status and not status.startswith("Message sent")
    assert re.fullmatch(r"[0-9a-f]{64}", page.evaluate(f"localStorage.getItem('{SECRET_KEY}')"))
    # History since 26 Sep must actually arrive (the channel has public messages from 27 Sep on).
    # Needs network; set ARK_CHAT_OFFLINE=1 to skip this part.
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
    print("chat smoke: PASS - opt-in, local guest key, Unicode limit, and no page errors")
    print("status:", status)
    browser.close()
