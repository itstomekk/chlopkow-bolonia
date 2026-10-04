"""Regression: a save whose hero is named 'Arek' must stay loadable (CONTINUE), not be hidden
and later overwritten by a new game. Legacy v1 'AREK' saves keep progress and only re-ask the name.

    python test/save_name_test.py [URL]
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ARK_URL', 'http://localhost:8765/')
KEY = 'arek-chlopkow-save-v1'


def run(page, payload):
    page.goto(URL + '?music=0')
    page.evaluate('([k, v]) => localStorage.setItem(k, v)', [KEY, json.dumps(payload)])
    page.reload()
    page.wait_for_function('window.__game && window.__game.Q', timeout=60000)
    return page.evaluate('() => ({ name: window.__game.Q.playerName, apples: window.__game.Q.apples.length, x: window.__game.P.x })')


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': 1280, 'height': 720})
    page.goto(URL + '?music=0')
    page.wait_for_function('window.__game && window.__game.Q', timeout=60000)
    key = page.evaluate("() => Object.keys(localStorage).find(k => k.includes('save')) || null")
    if key:
        KEY = key
    q = page.evaluate('() => JSON.parse(JSON.stringify(window.__game.Q))')
    q.update(playerName='Arek', apples=[0, 1, 2])
    ok = True
    r = run(page, {'v': 2, 'Q': q, 'x': 1200, 'y': 4050})
    print('v2 Arek:', r)
    ok &= r['name'] == 'Arek' and r['apples'] == 3 and r['x'] == 1200
    q['playerName'] = 'AREK'
    r = run(page, {'Q': q, 'x': 1210, 'y': 4050})
    print('v1 AREK:', r)
    ok &= r['name'] == '' and r['apples'] == 3 and r['x'] == 1210
    r = run(page, {'v': 2, 'Q': q, 'x': 'bad', 'y': None})
    print('bad coords:', r)
    ok &= isinstance(r['x'], (int, float))
    b.close()
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
