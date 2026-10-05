"""Accepted J12 objects: source provenance, hard pixel art, runtime rendering/collision."""
import json
import os
from pathlib import Path
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'asset-review/yard-evidence-j12'
OUT.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('ARK_URL', 'http://127.0.0.1:8795/index.html')
DATA = json.loads((ROOT / 'docs/data/j12-yard-props.json').read_text(encoding='utf-8'))
DECISIONS = json.loads((ROOT / 'plans/yard-evidence-j12-decisions.json').read_text(encoding='utf-8'))
accepted = {key for key, value in DECISIONS['decisions'].items() if value['decision'] == 'add'}
assert {p['candidate'] for p in DATA['props']} == accepted
assert len(DATA['props']) == 10
assert len({p['id'] for p in DATA['props']}) == 10
assert not any(p['candidate'] == 'j12-18-object' for p in DATA['props'])
assert DATA['identificationSource'] == 'user-review-not-independent-satellite-confirmation'
objects = np.array(Image.open(ROOT / 'docs/img/map_objects.png').convert('RGBA'))[..., 3]
terrain = Image.open(ROOT / 'docs/img/map_terrain.png').convert('L')
for asset in DATA['assets'].values():
    im = Image.open(ROOT / 'docs' / asset['src'])
    assert im.mode == 'RGBA' and im.size == tuple(asset['size'])
    ar = np.array(im)
    assert set(np.unique(ar[..., 3])) == {0, 255}
    assert not ((ar[..., 0] > 150) & (ar[..., 2] > 150) & (ar[..., 1] < 100) & (ar[..., 3] > 0)).any()
    assert len(im.convert('RGB').getcolors(maxcolors=1000)) <= 41
for prop in DATA['props']:
    w, h = DATA['assets'][prop['kind']]['size']
    x, y = prop['x'], prop['y']
    assert 4608 <= x < 5120 and 5632 <= y < 6144
    assert abs(x-prop['sourcePoint'][0]) <= 70 and abs(y-prop['sourcePoint'][1]) <= 70
    assert not objects[y-h:y+1, x-w//2:x+(w+1)//2].any(), prop
    assert terrain.getpixel((x//4,y//4)) not in (60,100,220), prop

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':1280,'height':900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.add_init_script("""window.__propDraws=[]; const old=CanvasRenderingContext2D.prototype.drawImage;
      CanvasRenderingContext2D.prototype.drawImage=function(im,...args){if(im.src?.includes('j12_prop_'))window.__propDraws.push({src:im.src,args,smooth:this.imageSmoothingEnabled});return old.call(this,im,...args);};""")
    page.goto(URL)
    page.wait_for_function('window.__game && window.__yardProps?.ready', timeout=60000)
    assert page.evaluate('window.__yardProps.error') is None
    assert page.evaluate('__yardProps.props.length') == 10
    page.keyboard.press('Enter')
    if page.locator('#player-name-input').count():
        page.locator('#player-name-input').fill('TEST')
        page.keyboard.press('Enter')
    page.wait_for_function('__game.scene === "play"')
    for x,y in [(4870,5735),(5060,6040)]:
        page.evaluate('([x,y])=>{ARK.teleport(x,y);window.__propDraws.length=0;}', [x,y])
        page.wait_for_function('''() => { const A=ARK,c=document.querySelector('canvas'),z=A.zoom,center=A.camera.toWorld(c.width/2,c.height/2);
          const ex=Math.max(c.width/z/2,Math.min(A.MAP.w-c.width/z/2,A.P.x));
          const ey=Math.max(c.height/z/2,Math.min(A.MAP.h-c.height/z/2,A.P.y-16));
          return Math.abs(center[0]-ex)<2 && Math.abs(center[1]-ey)<2; }''', timeout=15000)
        page.wait_for_function('window.__propDraws.length > 0', timeout=15000)
        page.screenshot(path=str(OUT / ('props-north.png' if y < 5900 else 'props-south.png')))
        draws = page.evaluate('window.__propDraws.splice(0)')
        assert all(d['smooth'] is False for d in draws)
        assert any('j12_prop_' in d['src'] for d in draws)
    # Test the shared physics hook rather than an unused diagnostic claim.
    result = page.evaluate("""() => __yardProps.props.map(p=>({kind:p.kind,
      ground:__yardProps.solidAt(p.x,p.y-2,false), air:__yardProps.solidAt(p.x,p.y-2,true),
      engine:ARK.blocked(p.x,p.y-2), outside:__yardProps.solidAt(p.x+40,p.y-2,false)}))""")
    assert all(r['ground'] and r['engine'] and not r['outside'] for r in result), result
    assert all(r['air'] == (r['kind'] in ('truck','silo')) for r in result), result
    assert not page.evaluate('ARK.HOOKS.solidAt.some(f=>f(4883,5756,false))'), 'silo must not be put on an existing roof'
    # The hook is outdoor-only; no courtyard blockers in church interiors.
    page.evaluate('__game.enterChurch()')
    page.wait_for_function('__game.room !== null')
    assert page.evaluate('__game.room') is not None
    assert not page.evaluate('ARK.HOOKS.solidAt.some(f=>f(__yardProps.props[0].x,__yardProps.props[0].y-2,false))')
    assert not errors, errors
    browser.close()
print('J12 yard props: PASS (5 accepted/1 skipped, 10 sprites, hard alpha, placements, real rendering, ground/air/interior collision)')
