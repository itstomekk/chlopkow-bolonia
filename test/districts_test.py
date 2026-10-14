"""District names: real canvas output and outdoor/map visibility, no public events."""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get('ARK_URL', 'http://127.0.0.1:8823/index.html')
SHOTS = ROOT / 'asset-review' / 'districts'
SHOTS.mkdir(parents=True, exist_ok=True)
TRACE = """window.__districtText = [];
const original = CanvasRenderingContext2D.prototype.fillText;
CanvasRenderingContext2D.prototype.fillText = function(text, x, y) {
  window.__districtText.push({text:String(text),x,y});
  if (window.__districtText.length > 3000) window.__districtText.splice(0,1500);
  return original.apply(this, arguments);
};"""


def boot(browser, viewport, failure=False, lang='pl'):
    page = browser.new_page(viewport=viewport, has_touch=viewport['width'] <= 480)
    page.add_init_script(TRACE)
    page.route('https://esm.sh/**', lambda r: r.fulfill(content_type='application/javascript', body='export {};'))
    page.route_web_socket('wss://**', lambda s: s.close())
    page.route('https://chlopkow-scores.kolotom.workers.dev/**', lambda r: r.fulfill(
        content_type='application/json', body='{"ok":false,"top":[],"avg":null,"count":0}'))
    if failure:
        page.route('**/data/districts.json', lambda r: r.fulfill(status=503, body='unavailable'))
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(URL + '?music=0&lang=' + lang)
    page.wait_for_function("window.__game && (!window.__arkBoot || __arkBoot.stage === 'ready')", timeout=60000)
    assert page.evaluate('Boolean(window.__districts)'), 'District plugin is not integrated'
    page.wait_for_function("__districts.status !== 'loading'", timeout=30000)
    assert not page.evaluate('__districts.badge.shown')
    assert page.evaluate('__districts.mapLabels') == []
    page.locator('#player-name-input').fill('Tester')
    page.locator('#player-name-submit').click()
    page.wait_for_function("__game.scene === 'play'")
    return page, errors


def move_to(page, point, expected):
    page.evaluate('([x,y]) => { ARK.P.x=x; ARK.P.y=y; ARK.P.moving=false; }', point)
    page.wait_for_function('(id) => (__districts.current && __districts.current.id) === id', arg=expected, timeout=10000)
    page.wait_for_function("""() => {
      const A=ARK, c=A.camera, W=A.ctx.canvas.width, H=A.ctx.canvas.height;
      const vw=W/A.zoom, vh=H/A.zoom;
      const x=A.MAP.w<vw ? A.MAP.w/2 : Math.max(vw/2,Math.min(A.MAP.w-vw/2,A.P.x));
      const y=A.MAP.h<vh ? A.MAP.h/2 : Math.max(vh/2,Math.min(A.MAP.h-vh/2,A.P.y-16));
      const actual=c.toWorld(W/2,H/2);
      return Math.abs(actual[0]-x)<3 && Math.abs(actual[1]-y)<3;
    }""", timeout=10000)


def assert_drawn(page, text):
    page.evaluate('window.__districtText.length=0')
    page.wait_for_function('(t) => __districtText.some(e => e.text === t)', arg=text)


def check(page, viewport, errors):
    assert page.evaluate('__districts.status') == 'ready'
    regions = page.evaluate('__districts.regions')
    assert len(regions) >= 9, 'Missing source areas'
    assert len({r['id'] for r in regions}) == len(regions)
    # Every authored label remains in its own geographic polygon and is painted on M.
    for r in regions:
        assert page.evaluate('(r) => ARK_DISTRICTS.contains(r.polygon,...r.label)', r), r['name']
    targets = page.evaluate("""() => __districts.regions.map(r => {
      for(let y=r.bounds[1]+8;y<r.bounds[3];y+=12) for(let x=r.bounds[0]+8;x<r.bounds[2];x+=12)
        if(__districts.at(x,y)?.id===r.id && !ARK.blocked(x,y)) return {id:r.id,name:r.name,point:[x,y]};
      return null;
    }).filter(Boolean)""")
    assert len(targets) >= 2, 'No clear area points'
    first, second = targets[:2]
    move_to(page, first['point'], first['id'])
    page.wait_for_function('__districts.badge.shown')
    assert_drawn(page, first['name'])
    badge = page.evaluate('__districts.badge')
    assert 0 <= badge['x'] and badge['x'] + badge['w'] <= viewport['width'] + 1
    assert 0 <= badge['y'] and badge['y'] + badge['h'] <= viewport['height'] + 1
    page.screenshot(path=str(SHOTS / f"walk-{viewport['width']}.png"))
    direction = page.evaluate("""() => {
      for (const [key,dx,dy] of [['ArrowRight',18,0],['ArrowLeft',-18,0],['ArrowDown',0,18],['ArrowUp',0,-18]])
        if(!ARK.blocked(ARK.P.x+dx,ARK.P.y+dy) && __districts.at(ARK.P.x+dx,ARK.P.y+dy)?.id===__districts.current.id) return key;
      throw new Error('No clear short walking direction');
    }""")
    origin = page.evaluate('[ARK.P.x,ARK.P.y]')
    page.keyboard.down(direction)
    try:
        page.wait_for_function('([x,y])=>Math.hypot(ARK.P.x-x,ARK.P.y-y)>4', arg=origin, timeout=5000)
    finally:
        page.keyboard.up(direction)
    assert page.evaluate('__districts.current.id') == first['id']
    # Exercise every available district and the longest badge, not only two names.
    for target in targets:
        page.evaluate('([x,y])=>{ARK.P.x=x;ARK.P.y=y;}', target['point'])
        page.wait_for_function('(id)=>__districts.current?.id===id && __districts.badge.shown', arg=target['id'])
        b = page.evaluate('__districts.badge')
        assert b['text'] == target['name'] and b['x'] >= 0 and b['x']+b['w'] <= viewport['width']+1, b
    move_to(page, second['point'], second['id'])
    page.wait_for_function('(name) => __districts.badge.text === name', arg=second['name'])
    # Dialogue and a real existing busy hook suppress the outdoor badge.
    page.evaluate("ARK.say('arek',['Test visibility'])")
    page.wait_for_function('!__districts.badge.shown')
    for _ in range(12):
        if not page.evaluate('Boolean(ARK.talk)'):
            break
        page.keyboard.press('Space')
        page.wait_for_timeout(100)
    page.wait_for_function('!ARK.talk')
    page.wait_for_function('__districts.badge.shown')
    page.evaluate('window.__districtBusy=()=>true; ARK.HOOKS.busy.push(__districtBusy)')
    page.wait_for_function('!__districts.badge.shown')
    page.evaluate('ARK.HOOKS.busy.splice(ARK.HOOKS.busy.indexOf(__districtBusy),1)')
    page.wait_for_function('__districts.badge.shown')
    # Real M key, not just a diagnostic setter.
    if viewport['width'] <= 480:
        page.touchscreen.tap(viewport['width']-20, 30)
    else:
        page.locator('#game').click(position={'x': viewport['width'] // 2, 'y': viewport['height'] // 2})
        page.keyboard.press('KeyM')
    page.wait_for_function('__game.showMap && !__districts.badge.shown')
    page.wait_for_function('(n)=>__districts.mapLabels.length===n', arg=len(regions))
    for r in regions:
        for line in page.evaluate('(id)=>__districts.mapLabels.find(l=>l.id===id).lines', r['id']):
            assert_drawn(page, line)
    labels = page.evaluate('__districts.mapLabels')
    bounds = page.evaluate('__districts.mapBounds')
    for label in labels:
        assert bounds['x'] <= label['x'] and label['x'] + label['w'] <= bounds['x'] + bounds['w'] + .1, label
        assert bounds['y'] <= label['y'] and label['y'] + label['h'] <= bounds['y'] + bounds['h'] + .1, label
    for i, a in enumerate(labels):
        for b in labels[i+1:]:
            assert a['x']+a['w'] <= b['x'] or b['x']+b['w'] <= a['x'] or a['y']+a['h'] <= b['y'] or b['y']+b['h'] <= a['y'], (a,b)
    assert page.evaluate("__districtText.some(e=>e.text.includes('ORIENTACYJNE') || e.text.includes('APPROXIMATE'))")
    page.screenshot(path=str(SHOTS / f"map-{viewport['width']}.png"))
    page.set_viewport_size({'width':390,'height':320})
    page.wait_for_function('(n)=>__districts.mapLabels.length===n && ARK.ctx.canvas.height===320',arg=len(regions))
    assert not errors, errors
    page.screenshot(path=str(SHOTS / 'map-short.png'))
    page.set_viewport_size(viewport)
    page.keyboard.press('KeyM')
    page.wait_for_function('!__game.showMap')
    outside = page.evaluate("""() => {
      for(let y=400;y<ARK.MAP.h-400;y+=80) for(let x=400;x<ARK.MAP.w-400;x+=80)
        if(!__districts.at(x,y) && !ARK.blocked(x,y)) return [x,y];
      throw new Error('No clear uncovered point');
    }""")
    page.evaluate('([x,y])=>{ARK.P.x=x;ARK.P.y=y;}', outside)
    page.wait_for_function('__districts.current === null && !__districts.badge.shown')
    assert page.evaluate('__districts.at(-100,-100)') is None
    assert page.evaluate('__districts.at(NaN,NaN)') is None
    page.evaluate("__game.scene='end'")
    assert not page.evaluate('__districts.badge.shown')
    assert page.evaluate('__districts.mapLabels') == []
    page.evaluate("__game.scene='play'")
    # Interiors and title/end scenes never inherit outdoor names.
    page.evaluate('__game.enterChurch()')
    page.wait_for_function('Boolean(ARK.room)', timeout=10000)
    page.wait_for_function('!__districts.badge.shown && __districts.mapLabels.length===0')
    assert not errors, errors
    print(f"District browser: PASS {viewport['width']}x{viewport['height']} ({len(regions)} names)")


with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        if '--failure-only' not in sys.argv:
            page, errors = boot(browser, {'width':1280,'height':720})
            check(page, {'width':1280,'height':720}, errors)
            page.close()
            page, errors = boot(browser, {'width':390,'height':844}, lang='en')
            check(page, {'width':390,'height':844}, errors)
            page.close()
        page, errors = boot(browser, {'width':1280,'height':720}, failure=True)
        assert page.evaluate('__districts.status') == 'error'
        assert page.evaluate('__game.scene') == 'play'
        page.evaluate('__game.showMap=true')
        page.wait_for_function("__districtText.some(e=>e.text.includes('NIEDOSTĘPNE'))")
        assert not page.evaluate('__districts.badge.shown')
        assert not errors, errors
        page.close()
        print('District data failure: PASS nonblocking boot, honest map notice')
    finally:
        browser.close()
print('RESULT: PASS')
