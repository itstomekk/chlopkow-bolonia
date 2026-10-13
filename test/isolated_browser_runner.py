"""Run a browser regression without polluting public Nostr arrival/chat history.

Usage: python test/isolated_browser_runner.py test/branding_flow_test.py [args...]
Tests can override the disabled CDN module with their own controlled module route.
"""
import runpy
import sys
from playwright.sync_api import Browser, BrowserContext


EMPTY_BOARD = ('{"ok":true,"best":[],"recent":[],"average":{"score":null,"count":0},'
               '"cpu":{"score":null,"count":0,"trace":null},"players":0}')


def isolate(original):
    def new_page(self, *args, **kwargs):
        page = original(self, *args, **kwargs)
        # A valid but disabled module avoids network-error console noise; chat stays unavailable.
        page.route('https://esm.sh/**', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='export {};'))
        page.route_web_socket('wss://**', lambda socket: socket.close())
        # Global scores: tests read an empty board and never write to production.
        page.route('https://chlopkow-api.kolotom.workers.dev/**', lambda route: route.fulfill(
            status=200, content_type='application/json',
            body=EMPTY_BOARD if route.request.method == 'GET' else '{"ok":false,"error":"test isolation"}'))
        return page
    return new_page


if __name__ == '__main__':
    Browser.new_page = isolate(Browser.new_page)
    BrowserContext.new_page = isolate(BrowserContext.new_page)
    target = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(target, run_name='__main__')
