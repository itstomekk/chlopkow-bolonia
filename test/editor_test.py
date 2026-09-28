"""Map editor smoke/integration test: server API + UI in a real browser.

Uses a temporary edits file, so osm/edits.json and the game are never touched. Rebuild stays disabled.

    python test/editor_test.py
"""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'osm'))
import geo  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


tmpd = tempfile.mkdtemp()
EDITS = os.path.join(tmpd, 'edits.json')
PORT = free_port()
BASE = f'http://127.0.0.1:{PORT}'
srv = subprocess.Popen([sys.executable, os.path.join(ROOT, 'editor', 'server.py'), '--port', str(PORT), '--edits', EDITS],
                       cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + '/api/geo', timeout=1); break
        except Exception:
            time.sleep(.2)

    # ---------------------------------------------------------------- API
    code, body = req('GET', '/api/geo'); g = json.loads(body)
    check(code == 200 and g['w'] == geo.W and g['h'] == geo.H, 'GET /api/geo matches osm/geo.py')
    code, body = req('GET', '/api/edits')
    check(code == 200 and json.loads(body)['layers'] == {}, 'missing edits file -> empty document')
    code, body = req('PUT', '/api/edits', {'version': 1, 'layers': {'trees': {'add': [{'lat': 'bad', 'lon': 1}]}}})
    check(code == 400 and not os.path.exists(EDITS), 'invalid PUT rejected, nothing written')
    code, _ = req('GET', '/game/../osm/edits.py')
    check(code == 404, 'path traversal out of docs/ blocked')
    code, _ = req('GET', '/game/%2e%2e/osm/geo.py')
    check(code == 404, 'encoded path traversal blocked')
    code, _ = req('POST', '/api/rebuild')
    check(code == 403, 'rebuild disabled by default')
    code, body = req('GET', '/game/map.json')
    check(code == 200 and json.loads(body)['w'] == geo.W, 'game map served read-only from docs/')
    code, body = req('GET', '/api/basemap/0/1/9.jpg?src=esri')
    check(code in (200, 502) and (code != 200 or body[:2] == b'\xff\xd8'), f'basemap tile answers (HTTP {code})')
    online = code == 200
    code, _ = req('GET', '/api/basemap/0/999/0.jpg?src=esri')
    check(code == 404, 'tile outside map rejected')

    # ---------------------------------------------------------------- UI
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1400, 'height': 850})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + '/#949,4665,1')
        page.wait_for_function("window.Editor && Editor.img.ground && Editor.entities && Editor.entities.length > 5", timeout=60000)
        check(page.evaluate("Editor.tools.map(t => t.id).join(',')") == 'pan,trees,clear,forest+,forest-,water,block,free,zones,entities,buildings,ref',
              'all tools registered')
        # JS geo parity with Python
        pts = [(0, 0), (949, 4665), (3000, 120), (1234.5, 2345.25)]
        js = page.evaluate("pts => pts.map(([x, y]) => GEO.toLL(x, y))", pts)
        py = [geo.to_latlon(x, y) for x, y in pts]
        check(all(abs(a[0] - b_[0]) < 1e-9 and abs(a[1] - b_[1]) < 1e-9 for a, b_ in zip(js, py)), 'JS geo.toLL == Python geo.to_latlon')
        check(page.evaluate("GEO.sector(949, 4665)") == 'B10', 'sector readout (949,4665) = B10')

        box = page.locator('#cv').bounding_box()
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2

        # tree tool: click adds a tree at the clicked map position
        page.keyboard.press('2')
        page.mouse.click(cx, cy)
        t = page.evaluate("Editor.edits.layers.trees.add[0]")
        wx, wy = geo.P(t['lat'], t['lon'])
        check(abs(wx - 949) < 2 and abs(wy - 4665) < 2, f'tree added under cursor ({wx:.1f},{wy:.1f})')
        page.keyboard.press('Control+z')
        check(page.evaluate("!Editor.edits.layers.trees"), 'undo removes the tree')
        page.keyboard.press('Control+y')
        check(page.evaluate("Editor.edits.layers.trees.add.length") == 1, 'redo restores the tree')

        # zone polygon (music) with Enter to close
        page.keyboard.press('9')
        page.fill('#z-id', 'jazz-w-stodole')
        page.fill('#z-props', '{"track": "jazz"}')
        for dx, dy in [(-80, -60), (80, -60), (80, 60), (-80, 60)]:
            page.mouse.click(cx + dx, cy + dy)
        page.keyboard.press('Enter')
        z = page.evaluate("Editor.edits.layers.zones.items[0]")
        check(z['kind'] == 'music' and z['id'] == 'jazz-w-stodole' and z['props'] == {'track': 'jazz'} and len(z['poly']) == 4,
              'music zone polygon created with props')

        # forest polygon closed by double click
        page.keyboard.press('Escape')
        page.keyboard.press('4')
        page.mouse.click(cx + 150, cy + 100); page.mouse.click(cx + 250, cy + 100); page.mouse.dblclick(cx + 200, cy + 180)
        check(len(page.evaluate("Editor.edits.layers.forest.add")) == 1, 'forest polygon closed with double click')

        # entity drag
        page.keyboard.press('Escape')
        page.keyboard.press('0') if False else page.evaluate("Editor.setTool('entities')")
        ent = page.evaluate("(() => { const e = Editor.entities.find(e => e.key === 'npc:marcin'); return [e.x, e.y]; })()")
        page.evaluate("([x, y]) => Editor.centerOn(x, y, 1)", ent)
        page.wait_for_timeout(100)
        page.mouse.move(cx, cy); page.mouse.down(); page.mouse.move(cx + 40, cy + 30, steps=5); page.mouse.up()
        m = page.evaluate("Editor.edits.layers.entities && Editor.edits.layers.entities['npc:marcin']")
        if m:
            mx, my = geo.P(m['lat'], m['lon'])
            check(abs(mx - ent[0] - 40) < 3 and abs(my - ent[1] - 30) < 3, f'Marcin dragged by (+40,+30) -> ({mx:.0f},{my:.0f})')
        else:
            check(False, 'Marcin dragged')

        # buildings: draw a new rectangle, then select an OSM building and move it, then delete another
        page.evaluate("Editor.setTool('buildings')")
        page.wait_for_function("Editor.tools.find(t => t.id === 'buildings') && document.querySelector('#tool-panel').textContent.includes('OSM: ') && !document.querySelector('#tool-panel').textContent.includes('OSM: 0')", timeout=20000)
        page.evaluate("Editor.centerOn(20, 20, 2)")  # map corner: empty ground
        page.wait_for_timeout(100)
        page.mouse.move(cx - 20, cy - 10); page.mouse.down(); page.mouse.move(cx + 20, cy + 10, steps=5); page.mouse.up()
        nb = page.evaluate("Editor.edits.layers.buildings && Editor.edits.layers.buildings.add[0]")
        check(bool(nb) and abs(nb['len'] - 40 / 2 / 2) < .6 and abs(nb['wid'] - 20 / 2 / 2) < .6,
              f'new building rectangle drawn (len {nb and nb["len"]} m, wid {nb and nb["wid"]} m)')
        ob = page.evaluate("fetch('/api/buildings').then(r => r.json()).then(j => j.buildings.find(b => !b.landmark && b.len > 8))")
        bx, by = geo.P(ob['lat'], ob['lon'])
        page.evaluate("([x, y]) => Editor.centerOn(x, y, 2)", [bx, by])
        page.wait_for_timeout(100)
        page.mouse.move(cx, cy); page.mouse.down(); page.mouse.move(cx + 30, cy, steps=5); page.mouse.up()
        mod = page.evaluate("id => Editor.edits.layers.buildings.modify && Editor.edits.layers.buildings.modify[id]", ob['id'])
        if mod:
            mx, my = geo.P(mod['lat'], mod['lon'])
            check(abs(mx - bx - 15) < 1.5 and abs(my - by) < 1.5 and abs(mod['len'] - ob['len']) < .01, f'OSM building moved by 15 px, size kept')
        else:
            check(False, 'OSM building moved')
        page.keyboard.press('Delete')
        check(page.evaluate("id => Editor.edits.layers.buildings.remove.includes(id) && !(Editor.edits.layers.buildings.modify || {})[id]", ob['id']),
              'Delete removes the OSM building (and drops its modify entry)')

        # save via Ctrl+S -> server validates and writes the temp edits file
        page.keyboard.press('Control+s')
        page.wait_for_function("!Editor.dirty", timeout=10000)
        saved = json.load(open(EDITS, encoding='utf-8'))
        check(set(saved['layers']) == {'trees', 'zones', 'forest', 'entities', 'buildings'} and saved['meta'].get('updated'), 'Ctrl+S saved all layers')
        sys.path.insert(0, os.path.join(ROOT, 'osm'))
        import edits
        check(edits.validate(saved) == [], 'saved file passes osm/edits.py validation')

        # basemap layer + grid render without errors
        page.evaluate("Editor.vis.basemap = true; Editor.vis.grid = true; Editor.vis.collide = true; Editor.centerOn(949, 4665, .5)")
        page.wait_for_timeout(4000 if online else 500)
        shot = os.path.join(tmpd, 'editor.png'); page.screenshot(path=shot)
        check(not errors, 'no page errors ' + '; '.join(errors[:3]))
        print('screenshot:', shot)
        b.close()
finally:
    srv.terminate()

print('\nFAILED:', len(fails)) if fails else print('\nALL PASSED')
sys.exit(1 if fails else 0)
