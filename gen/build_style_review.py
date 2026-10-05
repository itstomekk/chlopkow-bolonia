"""Style-match review sheet for everything except characters and buildings.

Every asset is shown at its IN-GAME size (world px x ZOOM, same resampling the
game uses) next to Arek and on map grass, so mismatched scale/resolution/palette
is visible at a glance. Procedural code-drawn art (pickups, bales, minigame
props) is re-drawn from the same pixel data/rects as docs/js. Optional live
screenshots from the running game show things in context (Playwright).

Reads only docs/, gen/ sources and plans/asset-labels-*.json. Never references/.

    python gen/build_style_review.py [--no-shots] [YYYY-MM-DD]

Output: asset-review/<date>-style/review.html (+ assets.json). Tomek labels each
card; "Wyślij" sends the JSON to Hermes, "Pobierz" saves it as a file.
"""
import base64
import datetime
import html
import io
import json
import os
import re
import socket
import subprocess
import sys
import time

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'osm'))
IMG = os.path.join(ROOT, 'docs', 'img')
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
SHOTS = '--no-shots' not in sys.argv
DATE = ARGS[0] if ARGS else datetime.date.today().isoformat()
OUT = os.path.join(ROOT, 'asset-review', f'{DATE}-style')
Z = 3                      # display zoom: screen px per world px (game default zoom = 3)
CHAR_H = 40                # game.js CHAR_H
GRASS = (110, 150, 74, 255)

cards = []
GAME_JS = open(os.path.join(ROOT, 'docs', 'js', 'game.js'), encoding='utf-8').read()


def load(rel):
    return Image.open(os.path.join(ROOT, rel)).convert('RGBA')


def b64(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def to_screen(im, world_w, world_h, smooth=False):
    """Art -> how the game paints it at zoom Z (smooth = game uses imageSmoothingEnabled)."""
    w, h = max(1, round(world_w * Z)), max(1, round(world_h * Z))
    return im.resize((w, h), Image.LANCZOS if smooth else Image.NEAREST)


def native(im, cap=300):
    """Source art at an integer zoom, for the 'źródło' view."""
    big = max(im.width, im.height, 1)
    if big > cap * 1.5:    # huge raw sources: shrink for the sheet (the file itself is untouched)
        k = cap * 1.5 / big
        return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    k = max(1, min(8, cap // big))
    return im.resize((im.width * k, im.height * k), Image.NEAREST) if k > 1 else im


# ------------------------------------------------------------------ Arek (scale reference)
_meta = json.load(open(os.path.join(IMG, 'arek_sheet_8dir.json'), encoding='utf-8'))
_fr = _meta['anims']['walk_down']['frames'][0]
_sheet = load('docs/img/arek_sheet_8dir.png')
_ak = CHAR_H / (_fr['h'] - _meta['foot'] - 14)            # world px per art px (drawArek)
AREK = to_screen(_sheet.crop((_fr['x'], _fr['y'], _fr['x'] + _fr['w'], _fr['y'] + _fr['h'])),
                 _fr['w'] * _ak, _fr['h'] * _ak, smooth=True)
AREK_FOOT = round(_meta['foot'] * _ak * Z)                 # rows below the feet line


def with_arek(frames, gap=6, bg=None):
    """Lay screen-space frames on one baseline, Arek last. frames: [(img, foot_rows)]."""
    items = list(frames) + [(AREK, AREK_FOOT)]
    above = max(im.height - f for im, f in items)
    below = max(f for _, f in items)
    W = sum(im.width for im, _ in items) + gap * (len(items) + 1)
    H = above + below + 2 * gap
    out = Image.new('RGBA', (W, H), bg or (0, 0, 0, 0))
    x = gap
    for im, f in items:
        out.alpha_composite(im, (x, gap + above - (im.height - f)))
        x += im.width + gap
    return out


def card(aid, cat, title, game, src=None, info='', note=''):
    cards.append(dict(id=aid, cat=cat, title=title, game=b64(game), src=b64(native(src)) if src else None,
                      info=info, note=note, span=min(3, max(1, -(-game.width // 330)))))


def sheet_cells(im, cw, ch, row, n):
    return [im.crop((i * cw, row * ch, (i + 1) * cw, (row + 1) * ch)) for i in range(n)]


def frames_card(aid, cat, title, cells, ww, wh, foot_art, ch, smooth=False, src=None, info='', note=''):
    foot = round(foot_art / ch * wh * Z)
    shown = [(to_screen(c, ww, wh, smooth), foot) for c in cells if c.getbbox()]
    card(aid, cat, title, with_arek(shown), src, info, note)


# ------------------------------------------------------------------ animals
CAT = 'Zwierzęta'
frodo = load('docs/img/frodo.png')
frames_card('animal.frodo.walk', CAT, 'Frodo - chód (dół, góra, prawo, lewo)',
            [c for r in range(4) for c in sheet_cells(frodo, 32, 32, r, 2)], 27, 27, 3, 32,
            src=frodo, info='docs/img/frodo.png · 32 px -> 27 world px · game.js drawFrodo')
fi = load('docs/img/frodo_idle.png')
frames_card('animal.frodo.idle', CAT, 'Frodo - pozy (siad, dyszenie, drapanie, węszenie, leżenie, lizanie)',
            sheet_cells(fi, 32, 32, 0, 10), 27, 27, 3, 32, src=fi, info='docs/img/frodo_idle.png · 27 world px')

# ANIMAL_TYPES atlas sizes from world-life.js
WL = open(os.path.join(ROOT, 'docs', 'js', 'world-life.js'), encoding='utf-8').read()
ATLAS = {m[0]: (int(m[1]), int(m[2]), int(m[3]))
         for m in re.findall(r"(\w+): \{ category: '\w+', atlas: \{ row: (\d+), px: (\d+), h: (\d+) \}", WL)}
crit = load('docs/img/critters.png')
cmeta = json.load(open(os.path.join(IMG, 'critters.json'), encoding='utf-8'))
TYPE_OF_ROW = {'hen': 'chicken', 'stray': 'dog'}
PL = {'hen': 'kura', 'stray': 'pies wiejski', 'bird': 'ptak (wróbel)', 'stork': 'bocian', 'fox': 'lis',
      'boar': 'dzik', 'mouse': 'mysz', 'hare': 'zając', 'pig': 'świnia', 'butterfly': 'motyl'}
for k, r in cmeta['rows'].items():
    t = TYPE_OF_ROW.get(k, k)
    row, px, h = ATLAS.get(t, (r['row'], 64, 32))
    size = 64 * h / px
    cells = sheet_cells(crit, 64, 64, r['row'], 4)
    frames_card(f'animal.critter.{k}', CAT, f'{PL.get(k, k)} ({k})', cells, size, size, 2, 64,
                src=crit.crop((0, r['row'] * 64, 256, r['row'] * 64 + 64)),
                info=f'critters.png rząd {r["row"]} · {round(size, 1)} world px · klatki: {", ".join(r["frames"])}')

anim = load('docs/img/animals.png')
for row, (k, t) in enumerate([('pig', 'świnia (minigra "złap świnię")'), ('dog', 'psy (minigra "jajka i psy")')]):
    frames_card(f'animal.minigame.{k}', CAT, t, sheet_cells(anim, 110, 90, row, 4), 110 / 90 * 24, 24, 4, 90,
                smooth=True, src=anim.crop((0, row * 90, 440, row * 90 + 90)),
                info='docs/img/animals.png · 110x90 -> 29x24 world px · rysowane Z wygładzaniem (minigames.js drawAnimal)')

bison = load('docs/img/bison.png')
K_B = 21 / 44 * 1.3
frames_card('animal.bison', CAT, 'żubr', sheet_cells(bison, 96, 80, 0, 4), 96 * K_B, 80 * K_B, 80 - 77, 80,
            src=bison, info=f'docs/img/bison.png · {round(96 * K_B)}x{round(80 * K_B)} world px · bison.js')

# ------------------------------------------------------------------ vehicles
CAT = 'Pojazdy'
veh = load('docs/img/vehicles.png')
vmeta = json.load(open(os.path.join(IMG, 'vehicles.json'), encoding='utf-8'))
VSIZE = {'car': (60, 38, 'auto (jedyna klatka, zawsze bokiem)')}
for k, r in vmeta['rows'].items():
    ww, wh, t = VSIZE.get(k, (60, 42, f'traktor - {r["view"]}'))
    frames_card(f'vehicle.{k}', CAT, t, sheet_cells(veh, 64, 64, r['row'], 1 if k == 'car' else 4), ww, wh, 6, 64,
                src=veh.crop((0, r['row'] * 64, 256, r['row'] * 64 + 64)),
                info=f'vehicles.png rząd {r["row"]} · 64 px -> {ww}x{wh} world px (nieproporcjonalnie) · world-life.js')
car_red = load('docs/img/car_red.png')
frames_card('vehicle.car_red', CAT, 'czerwone auto (stary plik, tylko awaryjnie)', [car_red], 56, 38, 3, car_red.height,
            src=car_red, info='docs/img/car_red.png · rysowany tylko gdy vehicles.png się nie wczyta')


# ------------------------------------------------------------------ pickups / items (pixel runs from game.js)
def js_const(name):
    m = re.search(r'const ' + name + r'\s*=\s*(\[\[.*?\]\]);', GAME_JS, re.S)
    return json.loads(m.group(1))


PAL = json.loads(re.search(r'const PICK_PAL = (\{.*?\});', GAME_JS).group(1))
PAL.update(json.loads(re.search(r'Object\.assign\(PICK_PAL,\s*//[^\n]*\n\s*(\{.*?\})\);', GAME_JS, re.S).group(1)))


def runs_img(runs, u):
    w = max(x + rw for x, y, rw, c in runs)
    h = max(y for x, y, rw, c in runs) + 1
    k = u * Z
    im = Image.new('RGBA', (max(1, round(w * k)), max(1, round(h * k))))
    d = ImageDraw.Draw(im)
    for x, y, rw, c in runs:
        d.rectangle([round(x * k), round(y * k), round(x * k) + int(-(-rw * k // 1)) - 1, round(y * k) + int(-(-k // 1)) - 1],
                    fill=PAL[c])
    return im


CAT = 'Znajdźki i przedmioty'
card('item.apple', CAT, 'jabłko', with_arek([(runs_img(js_const('APPLE_PX'), .85), 0)]),
     info='procedural · game.js APPLE_PX · 13x12 art px x0.85')
card('item.mushroom', CAT, 'grzyb', with_arek([(runs_img(js_const('MUSH_PX'), .8), 0)]),
     info='procedural · game.js MUSH_PX · 13x12 art px x0.8')
card('item.bale', CAT, 'bela siana', with_arek([(runs_img(js_const('BALE_PX'), 1), 0)]),
     info='procedural · game.js BALE_PX · 1 art px = 1 world px')
trash = load('docs/img/trash.png')
frames_card('item.trash', CAT, 'śmieci (butelka, puszka, worek, papier, opona)', sheet_cells(trash, 32, 32, 0, 5),
            16, 16, 2, 32, src=trash, info='docs/img/trash.png · 32 px -> 16 world px')


class Rects:
    """Tiny fillRect emulator in world units (origin = feet), for code-drawn props."""
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = x0, y0
        self.im = Image.new('RGBA', (round((x1 - x0) * Z), round((y1 - y0) * Z)))
        self.d = ImageDraw.Draw(self.im)
        self.foot = round(y1 * Z)

    def r(self, x, y, w, h, c):
        X, Y = (x - self.x0) * Z, (y - self.y0) * Z
        self.d.rectangle([round(X), round(Y), round(X + w * Z) - 1, round(Y + h * Z) - 1], fill=c)

    def circle(self, cx, cy, rad, c):
        X, Y = (cx - self.x0) * Z, (cy - self.y0) * Z
        self.d.ellipse([X - rad * Z, Y - rad * Z, X + rad * Z, Y + rad * Z], fill=c)


cap = Rects(-5, -10, 7, 1)
for a in [(-4, -5, 7, 4, '#1f5fd1'), (-3, -6, 5, 1, '#1f5fd1'), (2, -2, 4, 1.5, '#163f8c'), (-2, -5, 2, 1, '#6fa3ff'),
          (5, -9, 1, 1, '#ffffff')]:
    cap.r(*a)
card('item.cap', CAT, 'czapka Damiana', with_arek([(cap.im, cap.foot)]), info='procedural · game.js drawCap (fillRect)')

# ------------------------------------------------------------------ minigame props (minigames.js)
CAT = 'Minigry - rekwizyty'
b = Rects(-11, -20, 11, 1)
b.r(-9, -14, 18, 14, '#6b4526'); b.r(-8, -13, 16, 12, '#8a5a2c')
for i in range(5):
    b.r(-10 + i * 4, -19, 4, 5, '#f5f0e0' if i % 2 else '#d8262c')
b.r(-4, -9, 8, 5, '#1b1b1b')
card('minigame.booth', CAT, 'budka strzelnicy', with_arek([(b.im, b.foot)]), info='procedural · minigames.js drawBooth')
m = Rects(-7, -7, 8, 4)
for a in [(-5, -2, 9, 5, '#1d2230'), (-6, -1, 2, 3, '#1d2230'), (3, -5, 3, 4, '#1d2230'), (5, -4, 2, 1.5, '#d8262c'),
          (4, -6, 1.5, 1.5, '#d8262c'), (-6, -1, 1.5, 1.5, '#f5f0e0'), (-3, 0, 5, 1, '#3a4256'), (4, -4, 1, 1, '#f5f0e0')]:
    m.r(*a)
card('minigame.moorhen', CAT, 'blaszana kurka wodna (cel)', with_arek([(m.im, 0)]), info='procedural · minigames.js drawMoorhen')
t = Rects(-10, -25, 10, 21)
t.r(-2, -4, 4, 24, '#6a4229'); t.r(-9, -24, 18, 24 * .78, '#e7dfcb')
for rad, c in [(7, '#d8262c'), (4.5, '#f5f0e0'), (2, '#d8262c')]:
    t.circle(0, -24 * .61, rad, c)
card('minigame.target', CAT, 'tarcza', with_arek([(t.im, round(21 * Z))]), info='procedural · minigames.js drawTarget')
mw = Rects(-9, -14, 9, 3)
mw.r(-8, -10, 16, 9, '#c8342c'); mw.r(-5, -13, 10, 3, '#2b542d'); mw.r(-7, -1, 4, 3, '#24232b'); mw.r(3, -1, 4, 3, '#24232b')
card('minigame.mower', CAT, 'kosiarka', with_arek([(mw.im, mw.foot)]), info='procedural · minigames.js drawMower')
fl = Rects(-2, -31, 14, 1)
fl.r(-1, -30, 2, 30, '#5a3a1e')
for i in range(12):
    fl.r(1 + i, -29 + i * .35, 1, 8 - i * .6, '#d8262c')
card('minigame.flag', CAT, 'flaga minigry (bez napisu)', with_arek([(fl.im, fl.foot)]), info='procedural · minigames.js drawFlag')
bf = Rects(-8, -8, 8, 3)
for a in [(-7, -7, 5, 6, '#ff5a8a'), (2, -7, 5, 6, '#ff5a8a'), (-1, -7, 2, 8, '#402b4f'), (-2, 0, 4, 2, '#402b4f')]:
    bf.r(*a)
card('animal.butterfly_fallback', 'Zwierzęta', 'motyl - wersja awaryjna (kod)', with_arek([(bf.im, bf.foot)]),
     info='procedural · world-life.js drawButterfly, tylko gdy critters.png się nie wczyta')

# ------------------------------------------------------------------ map crops (trees, small objects, terrain)
from geo import legacy_i  # noqa: E402

MAP = json.load(open(os.path.join(ROOT, 'docs', 'map.json'), encoding='utf-8'))
ground = Image.open(os.path.join(IMG, 'map_ground.png')).convert('RGBA')
objs = Image.open(os.path.join(IMG, 'map_objects.png')).convert('RGBA')


def world_crop(x0, y0, w, h):
    x0 = max(0, min(MAP['w'] - w, int(x0)))
    y0 = max(0, min(MAP['h'] - h, int(y0)))
    box = (x0, y0, x0 + w, y0 + h)
    im = ground.crop(box)
    im.alpha_composite(objs.crop(box))
    return im, x0, y0


def map_card(aid, cat, title, cx, cy, w, h, info, arek_at=None, src=None, note=''):
    im, x0, y0 = world_crop(cx - w / 2, cy - h / 2, w, h)
    im = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
    if arek_at:
        ax, ay = arek_at
        im.alpha_composite(AREK, (round((ax - x0) * Z - AREK.width / 2), round((ay - y0) * Z - AREK.height + AREK_FOOT)))
    card(aid, cat, title, im, src, info, note)


CAT = 'Drzewa i roślinność'
oak_src = load('gen/trees_src/oak.png')
frames_card('tree.oak.source', CAT, 'dąb (nowy, zatwierdzony w pilocie A2)', [oak_src], oak_src.width, oak_src.height,
            0, oak_src.height, src=oak_src, info='gen/trees_src/oak.png · 1 art px = 1 world px',
            note='zatwierdzony 2026-10-02 - punkt odniesienia dla innych drzew')
seen = {}
for o in MAP['objects']:
    sp = o.get('species')
    if sp and seen.get(sp, 0) < 2:
        seen[sp] = seen.get(sp, 0) + 1
        n = seen[sp]
        pad = 26
        map_card(f'tree.{sp}.{n}', CAT, f'{ {"oak": "dąb", "deciduous": "liściaste"}.get(sp, sp)} na mapie #{n}',
                 o['x'] + o['w'] / 2, o['y'] + o['h'] / 2, o['w'] + 2 * pad + 40, o['h'] + 2 * pad,
                 'osm/render_map.py · map_objects.png', arek_at=(o['x'] + o['w'] + pad + 4, o['y'] + o['h']))

# terrain samples: find a uniform patch for each class (map_terrain.png is 1/4 scale)
ter = Image.open(os.path.join(IMG, 'map_terrain.png'))
TK = MAP['w'] / ter.width
tw, th = ter.size
tp = ter.load()


def find_patch(val, size=18, near=None):
    best = None
    step = 6
    for y in range(size, th - size, step):
        for x in range(size, tw - size, step):
            if tp[x, y] != val:
                continue
            if all(tp[x + dx, y + dy] == val for dx in (-size, 0, size) for dy in (-size, 0, size)):
                d = 0 if near is None else (x - near[0]) ** 2 + (y - near[1]) ** 2
                if best is None or d < best[0]:
                    best = (d, x, y)
                    if near is None:
                        return x * TK, y * TK
    return (best[1] * TK, best[2] * TK) if best else None


SP = (MAP['spawn']['x'] / TK, MAP['spawn']['y'] / TK)
CAT = 'Teren i las'
for val, key, title, size in [(220, 'forest', 'las (drzewa w warstwie ziemi)', 30), (160, 'field', 'pole uprawne', 18),
                              (0, 'grass', 'trawa / łąka', 14), (100, 'track', 'droga gruntowa', 3), (60, 'road', 'asfalt', 3)]:
    p = find_patch(val, size, SP)
    if p:
        map_card(f'terrain.{key}', CAT, title, p[0], p[1], 240, 150, 'map_ground.png (osm/render_map.py)', arek_at=p)
riv = next(p for p in MAP['pois'] if p['key'] == 'river')
map_card('terrain.river', CAT, 'rzeka Melioranka', riv['x'], riv['y'], 260, 160, 'map_ground.png', arek_at=(riv['x'] + 60, riv['y'] + 50))
bl = MAP['bales'][0]
map_card('terrain.bales_field', CAT, 'bele na polu (tło mapy)', bl['x'], bl['y'], 240, 150, 'map_ground.png + bele z game.js (tu bez bel)')
fp = MAP.get('football_pitch')
if fp:
    map_card('terrain.football_pitch', CAT, 'boisko (nieskoszone)', fp['cx'], fp['cy'], 320, 200, 'map_ground.png')
cem = next(p for p in MAP['pois'] if p['key'] == 'cemetery')
map_card('terrain.cemetery', CAT, 'cmentarz (tło mapy, bez nagrobków z cemetery-art.js)', cem['x'], cem['y'], 300, 230,
         'map_ground + map_objects')

CAT = 'Małe obiekty mapy'
LM_PL = {'cross_iron': 'krzyż żelazny', 'shrine_stone': 'kapliczka kamienna', 'shrine_white': 'kapliczka biała',
         'shrine_fenced': 'kapliczka za płotkiem', 'kapliczka': 'kapliczka (z mapy)'}
for s in MAP['shrines']:
    k = s['kind']
    src_rel = f'gen/lm_{k}.png'
    src = load(src_rel) if os.path.exists(os.path.join(ROOT, src_rel)) else None
    aid = f'landmark.{k}' if k in ('cross_iron', 'shrine_stone', 'shrine_white', 'shrine_fenced') else f'landmark.{s["spot"]}'
    map_card(aid, CAT, LM_PL.get(k, k), s['x'], s['y'] - 14, 150, 100, f'{src_rel if src else "map_objects.png"} · {s["spot"]}',
             arek_at=(s['x'] + 34, s['y']), src=src)
sx_, sb_ = legacy_i(1150, 2405)
map_card('landmark.village_sign', CAT, 'tablica "Chłopków"', sx_, sb_ - 30, 220, 120,
         'gen/lm_village_sign.png -> 110 px szer. (LANCZOS) · render_map.py', arek_at=(sx_ + 70, sb_),
         src=load('gen/lm_village_sign.png'))
del ground, objs

# ------------------------------------------------------------------ church interior props, memories, UI
CAT = 'Kościół - rekwizyty wnętrza'
for k in json.load(open(os.path.join(IMG, 'church', 'manifest.json'), encoding='utf-8')):
    if k in ('soltys', 'font'):
        continue
    im = load(f'docs/img/church/{k}.png')
    card(f'church.{k}', CAT, k, native(im, 260), None, f'docs/img/church/{k}.png · {im.width}x{im.height} · church.js (skala pokoju)')
CAT = 'Wspomnienia i UI'
for k in ['procession', 'memorial', 'wooden_cross']:
    im = load(f'docs/img/memories/{k}.png')
    card(f'memory.{k}', CAT, f'wspomnienie: {k}', native(im, 300), None, f'docs/img/memories/{k}.png · {im.width}x{im.height}')
for k, t in [('splash', 'ekran tytułowy'), ('sokol_watermark', 'Sokół - znak w trawie')]:
    im = load(f'docs/img/{k}.png')
    card(f'ui.{k}', CAT, t, native(im, 320), None, f'docs/img/{k}.png · {im.width}x{im.height}')


# ------------------------------------------------------------------ live screenshots (optional)
def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def live_shots():
    from playwright.sync_api import sync_playwright
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1', '--directory',
                            os.path.join(ROOT, 'docs')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shots = []
    try:
        time.sleep(1.0)
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={'width': 1280, 'height': 720})
            pg.goto(f'http://127.0.0.1:{port}/index.html')
            pg.wait_for_function('window.__game && window.__worldLife', timeout=40000)
            pg.evaluate('localStorage.clear()')
            pg.reload(wait_until='load')
            pg.wait_for_function('window.__game && window.__worldLife', timeout=40000)
            pg.keyboard.press('KeyN')
            pg.locator('#player-name-input').fill('Review')
            pg.locator('#player-name-submit').click()
            pg.wait_for_function("__game.scene === 'play'", timeout=30000)
            time.sleep(1.5)
            items = json.load(open(os.path.join(ROOT, 'docs', 'items.json'), encoding='utf-8'))
            apple = items['apples'][0]
            cl = pg.evaluate('__game.clouds()[0]')
            spots = [('village', 'wieś przy starcie', MAP['spawn']['x'], MAP['spawn']['y']),
                     ('cemetery', 'cmentarz (z nagrobkami)', cem['x'], cem['y'] + 70),
                     ('bales', 'bele siana', bl['x'], bl['y'] - 40),
                     ('apple', 'jabłko w terenie', apple['x'], apple['y'] + 20),
                     ('river', 'rzeka', riv['x'], riv['y'] + 30),
                     ('range', 'strzelnica', MAP['range']['x'], MAP['range']['y']),
                     ('cloud', 'cień chmury', cl['x'], cl['y'])]
            fpatch = find_patch(220, 30, SP)
            if fpatch:
                spots.insert(1, ('forest', 'las', fpatch[0], fpatch[1]))
            for key, title, x, y in spots:
                pg.evaluate(f'window.ARK.teleport({x}, {y})')
                time.sleep(1.4)
                png = pg.screenshot(clip={'x': 240, 'y': 120, 'width': 800, 'height': 480})
                shots.append((key, title, Image.open(io.BytesIO(png)).convert('RGBA')))
            br.close()
    finally:
        srv.terminate()
    return shots


if SHOTS:
    try:
        for key, title, im in live_shots():
            card(f'context.{key}', 'W grze - kontekst (zrzuty)', title, im, None,
                 'zrzut z działającej gry 1280x720 (zoom ~2.2) · do oceny "czy to razem pasuje"')
    except Exception as e:  # screenshots are a bonus; the sheet still works without them
        print('live screenshots skipped:', type(e).__name__, e)

# ------------------------------------------------------------------ prior labels
prior = {}
for f in sorted(os.listdir(os.path.join(ROOT, 'plans'))):
    if f.startswith('asset-labels-') and f.endswith('.json'):
        prior.update(json.load(open(os.path.join(ROOT, 'plans', f), encoding='utf-8')).get('labels', {}))
PRIOR_ALIAS = {'animal.minigame.pig': 'animal.minigame_sheet', 'animal.minigame.dog': 'animal.minigame_sheet',
               'tree.oak.1': 'tree.tree.oak', 'tree.oak.2': 'tree.tree.oak',
               'tree.deciduous.1': 'tree.tree.deciduous', 'tree.deciduous.2': 'tree.tree.deciduous'}
DONE = {'animal.critter.boar': 'przerobiony w pilocie A2 (zatwierdzony)', 'tree.oak.1': 'nowy dąb A2 (zatwierdzony)',
        'tree.oak.2': 'nowy dąb A2 (zatwierdzony)'}
for c in cards:
    p = prior.get(c['id']) or prior.get(PRIOR_ALIAS.get(c['id'], ''))
    c['prior'] = (p['label'] + (': ' + p['note'] if p.get('note') else '')) if p else ''
    if c['id'] in DONE:
        c['note'] = (c['note'] + ' · ' if c['note'] else '') + DONE[c['id']]

# ------------------------------------------------------------------ html
os.makedirs(OUT, exist_ok=True)
json.dump([{k: v for k, v in c.items() if k not in ('game', 'src', 'span')} for c in cards],
          open(os.path.join(OUT, 'assets.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

LABELS = [('anchor', 'wzór stylu'), ('keep', 'pasuje'), ('adjust', 'dopasuj'), ('regen', 'od nowa'), ('retire', 'usuń')]
ISSUES = [('too_detailed', 'za szczegółowe / za drobne piksele'), ('too_crude', 'za prymitywne'),
          ('size', 'zły rozmiar vs Arek'), ('palette', 'inne kolory / paleta'), ('outline', 'brak / inny obrys'),
          ('blurry', 'rozmyte'), ('perspective', 'zła perspektywa / kąt'), ('animation', 'animacja / kierunki')]
groups = {}
for c in cards:
    groups.setdefault(c['cat'], []).append(c)

parts = []
for cat, items in groups.items():
    parts.append(f'<h2>{html.escape(cat)} <span class=n>{len(items)}</span></h2><div class=grid>')
    for c in items:
        btns = ''.join(f'<button class=lb data-v="{v}">{t}</button>' for v, t in LABELS)
        chips = ''.join(f'<button class=ch data-v="{v}">{t}</button>' for v, t in ISSUES)
        src = (f'<details><summary>źródło (natywne piksele)</summary><div class=pic><img src="{c["src"]}"></div></details>'
               if c['src'] else '')
        parts.append(
            f'<div class=card style="grid-column:span {c["span"]}" data-id="{c["id"]}" data-cat="{html.escape(cat)}">'
            f'<div class="pic game"><img src="{c["game"]}"></div>{src}'
            f'<b>{html.escape(c["title"])}</b><code>{c["id"]}</code><small>{html.escape(c["info"])}</small>'
            + (f'<small class=note>{html.escape(c["note"])}</small>' if c['note'] else '')
            + (f'<small class=prior>poprzednio: {html.escape(c["prior"])}</small>' if c['prior'] else '')
            + f'<div class=btns>{btns}</div><div class="btns chips">{chips}</div>'
            f'<textarea rows=1 placeholder="uwaga (opcjonalnie)"></textarea></div>')
    parts.append('</div>')

page = f"""<!doctype html><meta charset=utf-8><title>Bolonia - spójność stylu assetów {DATE}</title>
<style>
body{{margin:0;padding:8px;font-family:system-ui,sans-serif}} h1{{font-size:18px;margin:4px 0}} h2{{font-size:15px;margin:18px 0 6px}}
.n{{color:var(--muted-foreground,#888);font-weight:normal}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px}}
.card{{border:1px solid var(--border,#ccc);border-radius:6px;padding:6px;display:flex;flex-direction:column;gap:3px;background:var(--card,transparent)}}
.card.done{{border-color:#2a7}} .card.hide{{display:none}}
.pic{{display:flex;justify-content:center;align-items:center;min-height:90px;max-height:420px;overflow:auto;border-radius:4px}}
body.bg-grass .pic{{background:rgb{GRASS[:3]}}} body.bg-check .pic{{background:repeating-conic-gradient(#8883 0 25%,#0000 0 50%) 0 0/12px 12px}}
body.bg-dark .pic{{background:#1c1f27}} body.bg-light .pic{{background:#f3efe4}}
.pic img{{image-rendering:pixelated;max-width:100%}} body.fit .pic img{{max-width:100%}} body:not(.fit) .game img{{max-width:none}}
details summary{{font-size:11px;cursor:pointer;color:var(--muted-foreground,#777)}}
code{{font-size:11px}} small{{font-size:11px;color:var(--muted-foreground,#777)}} .note{{color:#2a7}} .prior{{color:var(--accent,#b60)}}
.btns{{display:flex;flex-wrap:wrap;gap:3px}} button{{font:inherit;font-size:11px;padding:2px 6px;border:1px solid var(--border,#aaa);border-radius:4px;background:none;color:inherit;cursor:pointer}}
.ch{{font-size:10px;padding:1px 5px;opacity:.75}} .ch.on{{background:#557;color:#fff;opacity:1}}
.lb.on[data-v=anchor]{{background:#2a7}} .lb.on[data-v=keep]{{background:#6a6}} .lb.on[data-v=adjust]{{background:#c90}}
.lb.on[data-v=regen]{{background:#c55}} .lb.on[data-v=retire]{{background:#777}} .lb.on{{color:#fff}}
textarea{{font:inherit;font-size:11px;padding:2px 4px;border:1px solid var(--border,#aaa);border-radius:4px;background:none;color:inherit;resize:vertical}}
#bar{{position:sticky;top:0;z-index:2;padding:6px 0;background:var(--card,#fff);display:flex;flex-wrap:wrap;gap:6px;align-items:center;border-bottom:1px solid var(--border,#ddd)}}
#bar select{{font:inherit;font-size:12px}} #send{{font-size:13px;padding:4px 10px;background:#2a7;color:#fff;border:0}}
#global{{width:100%;box-sizing:border-box;margin:6px 0}}
</style>
<body class="bg-grass">
<h1>Chłopków Bolonia - spójność stylu: zwierzęta, drzewa, przedmioty, teren ({len(cards)}) · {DATE}</h1>
<div id=bar>
 <button id=send>Wyślij do Hermesa</button><button id=copy>Kopiuj JSON</button><button id=dl>Pobierz JSON</button>
 <label><small>tło</small> <select id=bg><option value=grass>trawa</option><option value=check>szachownica</option><option value=dark>ciemne</option><option value=light>jasne</option></select></label>
 <label><small>pokaż</small> <select id=flt><option value=all>wszystkie</option><option value=todo>nieocenione</option><option value=done>ocenione</option></select></label>
 <button id=clr>Wyczyść</button><span id=cnt></span>
</div>
<p><small>Wszystko pokazane w skali gry (zoom {Z}x), z Arkiem obok dla porównania. Wzorce stylu do tej pory: Arek, ptak, kapliczka kamienna, krzyż żelazny + nowy dąb i dzik z pilota A2.
Oceń tyle, ile chcesz - postęp zapisuje się w przeglądarce. Tagi problemów można łączyć.</small></p>
<textarea id=global rows=2 placeholder="uwagi ogólne do całego stylu (np. kierunek palety, jasność, obrys...)"></textarea>
{''.join(parts)}
<script>
const KEY='bolonia-style-review-{DATE}';
let S={{}}, G='';
try{{const o=JSON.parse(localStorage.getItem(KEY)||'{{}}'); S=o.labels||{{}}; G=o.global_note||'';}}catch(e){{}}
const clean=id=>{{const v=S[id]; if(v&&!v.label&&!(v.issues||[]).length&&!v.note) delete S[id];}};
function data(){{return {{review:'style-{DATE}',scope:'zwierzęta, drzewa, przedmioty, teren, obiekty, rekwizyty (bez postaci i budynków)',global_note:G,labels:S}};}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(data()));}}catch(e){{}} upd();}}
function upd(){{let n=0;document.querySelectorAll('.card').forEach(c=>{{const d=!!S[c.dataset.id];c.classList.toggle('done',d);if(d)n++;}});
  document.getElementById('cnt').textContent=n+' / {len(cards)} ocenionych'; filt();}}
function filt(){{const f=document.getElementById('flt').value;document.querySelectorAll('.card').forEach(c=>{{const d=!!S[c.dataset.id];
  c.classList.toggle('hide',(f==='todo'&&d)||(f==='done'&&!d));}});}}
document.querySelectorAll('.card').forEach(c=>{{
  const id=c.dataset.id, st=S[id]||{{}};
  c.querySelectorAll('.lb').forEach(b=>{{ if(st.label===b.dataset.v) b.classList.add('on');
    b.onclick=()=>{{const on=b.classList.contains('on'); c.querySelectorAll('.lb').forEach(x=>x.classList.remove('on'));
      S[id]=S[id]||{{}}; if(on) delete S[id].label; else {{b.classList.add('on'); S[id].label=b.dataset.v;}} clean(id); save();}};}});
  c.querySelectorAll('.ch').forEach(b=>{{ if((st.issues||[]).includes(b.dataset.v)) b.classList.add('on');
    b.onclick=()=>{{b.classList.toggle('on'); S[id]=S[id]||{{}};
      S[id].issues=[...c.querySelectorAll('.ch.on')].map(x=>x.dataset.v); if(!S[id].issues.length) delete S[id].issues; clean(id); save();}};}});
  const ta=c.querySelector('textarea'); ta.value=st.note||'';
  ta.oninput=()=>{{S[id]=S[id]||{{}}; if(ta.value.trim()) S[id].note=ta.value; else delete S[id].note; clean(id); save();}};
}});
const g=document.getElementById('global'); g.value=G; g.oninput=()=>{{G=g.value; save();}};
const out=()=>JSON.stringify(data(),null,1);
document.getElementById('send').onclick=()=>{{
  save(); navigator.clipboard&&navigator.clipboard.writeText(out()).catch(()=>{{}});
  if(window.hermes&&window.hermes.send) {{window.hermes.send('Oceny stylu assetów Bolonia ({DATE}): '+JSON.stringify(data())); document.getElementById('cnt').textContent+=' - wysłane';}}
  else document.getElementById('cnt').textContent+=' - skopiowane (wklej w czat)';}};
document.getElementById('copy').onclick=()=>navigator.clipboard.writeText(out());
document.getElementById('dl').onclick=()=>{{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([out()],{{type:'application/json'}}));
  a.download='asset-style-labels-{DATE}.json';a.click();}};
document.getElementById('clr').onclick=()=>{{if(confirm('Wyczyścić wszystkie oceny?')){{S={{}};G='';localStorage.removeItem(KEY);location.reload();}}}};
document.getElementById('bg').onchange=e=>{{document.body.className='bg-'+e.target.value;}};
document.getElementById('flt').onchange=filt;
upd();
</script>"""
with open(os.path.join(OUT, 'review.html'), 'w', encoding='utf-8') as f:
    f.write(page)
print(len(cards), 'cards ->', os.path.join(OUT, 'review.html'), round(len(page) / 1e6, 1), 'MB')
