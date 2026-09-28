"""Procedural 16-bit style game map of Chłopków (gmina Platerów) from OpenStreetMap data.

Outputs (docs/img/ + docs/map.json):
  map_ground.png   ground layer (grass, fields, roads, river, shadows, flat details)
  map_objects.png  y-sorted layer (buildings, trees) — drawn by the game per object rect, sorted with Arek
  map_collide.png  255 = tall/solid (buildings, ponds, woods, trunks), 128 = low/jumpable (streams, fences, bales)
  map.json         size, objects [x,y,w,h,base], POIs, minigame venues, spawn

Geometry (bbox, scale, legacy-coordinate conversion) lives in osm/geo.py.

1 m = A art pixels. Buildings are exaggerated around their centroid (RPG convention).
Map data © OpenStreetMap contributors (ODbL).
"""
import json, math, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, 'osm'); sys.path.insert(0, 'gen')
from geo import A, BBOX, W, H, P, to_latlon, legacy_i, pre_expansion_i, REAL_POIS, PRE_EXPANSION_ADDITIONS
from slice_sheet import key as chroma_key

OSM = 'osm/chlopkow.json'
rnd = random.Random(7)
np.random.seed(7)


data = json.load(open(OSM, encoding='utf-8'))
ways = [e for e in data['elements'] if e['type'] == 'way' and 'geometry' in e]
nodes = [e for e in data['elements'] if e['type'] == 'node']
pts = lambda e: [P(g['lat'], g['lon']) for g in e['geometry']]


def hexc(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def noise2(w, h, cell, seed):
    r = np.random.RandomState(seed)
    gw, gh = w // cell + 2, h // cell + 2
    g = r.rand(gh, gw)
    ys = np.arange(h) / cell; xs = np.arange(w) / cell
    y0 = ys.astype(int); x0 = xs.astype(int); fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def mask_of(polys, lines=None, width=1):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for p in polys:
        if len(p) > 2: d.polygon(p, fill=255)
    for l, w in (lines or []):
        d.line(l, fill=255, width=int(w), joint='curve')
        for x, y in l: d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
    return np.array(m) > 0


def mask_win(poly, pad=2):
    """Polygon mask on its own bounding window: returns (x0, y0, bool array). Much cheaper than a full-map mask."""
    arr = np.array(poly); x0 = max(0, int(arr[:, 0].min()) - pad); y0 = max(0, int(arr[:, 1].min()) - pad)
    x1 = min(W, int(arr[:, 0].max()) + pad + 1); y1 = min(H, int(arr[:, 1].max()) + pad + 1)
    if x1 <= x0 or y1 <= y0: return x0, y0, np.zeros((0, 0), bool)
    m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in poly], fill=255)
    return x0, y0, np.array(m) > 0


# ---------------------------------------------------------------- ground base
g = np.zeros((H, W, 3), np.float32)
n1 = noise2(W, H, 18, 1); n2 = noise2(W, H, 5, 2); speck = np.random.rand(H, W)
grass_a, grass_b = np.array(hexc('#6fae45')), np.array(hexc('#5f9c3b'))
t = (n1 * .7 + n2 * .3)[..., None]
g[:] = grass_a * (1 - t) + grass_b * t
g[speck < .035] *= .86
g[speck > .996] = hexc('#f4f1d8')
g[(speck > .993) & (speck <= .996)] = hexc('#f2d34a')

classes = {}
for e in ways:
    tg = e['tags']
    k = tg.get('landuse') or tg.get('natural') or tg.get('leisure') or tg.get('amenity')
    if 'building' in tg or 'highway' in tg or 'waterway' in tg or not k: continue
    classes.setdefault(k, []).append(pts(e))

collide = np.zeros((H, W), bool)
low = np.zeros((H, W), bool)   # jumpable: streams, ditches, fences, hay bales


def fill(mask, col_a, col_b, cell=12, seed=0, jitter=.08):
    nn = noise2(W, H, cell, seed)[..., None]
    c = np.array(hexc(col_a)) * (1 - nn) + np.array(hexc(col_b)) * nn
    c = c * (1 + (np.random.rand(H, W, 1) - .5) * jitter)
    g[mask] = c[mask]


# residential / farmyard / religious
for k, a_, b_ in [('residential', '#7ab84c', '#6aa843'), ('religious', '#86c05a', '#76b04e'), ('farmyard', '#b89a6c', '#a8895e'), ('grass', '#78b64b', '#68a642'), ('meadow', '#80bb50', '#70ab46')]:
    if k in classes: fill(mask_of(classes[k]), a_, b_, seed=len(k))

# farmland: oriented furrow stripes, one crop per field
CROPS = [('#dcb64c', '#c9a13d'), ('#d4ad44', '#be973a'), ('#86b24c', '#739f3f'), ('#9c724a', '#86603d'), ('#e6d24a', '#d2bd3b'), ('#a8c060', '#94ab50')]
for i, p in enumerate(classes.get('farmland', [])):
    ox_, oy_, m = mask_win(p, pad=1)
    ca, cb = CROPS[rnd.randrange(len(CROPS))]
    if not m.size: continue
    arr = np.array(p); c = arr.mean(0); u, s, vt = np.linalg.svd(arr - c); ang = math.atan2(vt[0][1], vt[0][0])
    yy, xx = np.nonzero(m); yy = yy + oy_; xx = xx + ox_
    proj = (xx * -math.sin(ang) + yy * math.cos(ang))
    stripe = (np.floor(proj / 5) % 2).astype(bool)
    colA, colB = np.array(hexc(ca)), np.array(hexc(cb))
    col = np.where(stripe[:, None], colA, colB).astype(np.float32)
    col *= (1 + (np.random.rand(len(yy), 1) - .5) * .09)
    g[yy, xx] = col
    # dark field edge
    edge = m & ~np.pad(m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:], 1)
    ey_, ex_ = np.nonzero(edge); g[ey_ + oy_, ex_ + ox_] *= .8

# orchard / cemetery / pitch
for p in classes.get('cemetery', []):
    m = mask_of([p]); fill(m, '#5f9a4a', '#548c42', seed=31)
    arr = np.array(p); x0, y0 = arr.min(0); x1, y1 = arr.max(0)
    for yy in np.arange(y0 + 6, y1 - 6, 9):
        for xx in np.arange(x0 + 6, x1 - 6, 7):
            if m[int(yy), int(xx)] and rnd.random() < .8:
                g[int(yy) - 3:int(yy) + 1, int(xx):int(xx) + 3] = hexc('#bdbdb8'); g[int(yy) - 3, int(xx):int(xx) + 3] = hexc('#dcdcd6')
                g[int(yy) + 1, int(xx):int(xx) + 3] = hexc('#3c5a32')
for p in classes.get('pitch', []):
    m = mask_of([p]); fill(m, '#8fcf63', '#86c65d', seed=41)

# ---------------------------------------------------------------- water
river_lines, ponds = [], []
for e in ways:
    tg = e['tags']
    if tg.get('natural') == 'water': ponds.append(pts(e))
    elif tg.get('waterway') in ('stream', 'river', 'ditch', 'canal'): river_lines.append((pts(e), (7 if tg['waterway'] != 'ditch' else 4) * A))
wm = mask_of(ponds, river_lines)
bank = mask_of(ponds, [(l, w + 6) for l, w in river_lines]) & ~wm
wn = noise2(W, H, 6, 51)[..., None]
wcol = np.array(hexc('#3f86c9')) * (1 - wn) + np.array(hexc('#2f6fb0')) * wn
g[bank] = np.array(hexc('#4a7a34'))
g[wm] = wcol[wm]
sp = (np.random.rand(H, W) > .985) & wm
g[sp] = hexc('#9fd0f0')
pond_m = mask_of(ponds)
collide |= pond_m
low |= wm & ~pond_m

# ---------------------------------------------------------------- roads
RW = {'tertiary': 11, 'unclassified': 9, 'residential': 9, 'service': 5, 'track': 5, 'footway': 2.5, 'path': 2.5}
paved = [(pts(e), RW[e['tags']['highway']] * A) for e in ways if e['tags'].get('highway') in ('tertiary', 'unclassified', 'residential')]
dirt = [(pts(e), RW[e['tags']['highway']] * A) for e in ways if e['tags'].get('highway') in ('service', 'track', 'footway', 'path')]
dm = mask_of([], dirt); de = mask_of([], [(l, w + 3) for l, w in dirt]) & ~dm
dn = noise2(W, H, 4, 61)[..., None]
dcol = np.array(hexc('#cfae78')) * (1 - dn) + np.array(hexc('#bb9a66')) * dn
g[de] *= .85; g[dm] = dcol[dm]
pm = mask_of([], paved); pe = mask_of([], [(l, w + 4) for l, w in paved]) & ~pm
pn = noise2(W, H, 3, 71)[..., None]
pcol = np.array(hexc('#5c5d63')) * (1 - pn) + np.array(hexc('#505157')) * pn
g[pe] = hexc('#8d8a7e'); g[pm] = pcol[pm]
ground = Image.fromarray(g.clip(0, 255).astype(np.uint8))
gd = ImageDraw.Draw(ground)
for l, w in paved:  # centre dashes
    for a_, b_ in zip(l, l[1:]):
        L = math.hypot(b_[0] - a_[0], b_[1] - a_[1]); n = int(L // 16)
        for k in range(n):
            t0, t1 = k / max(1, L / 16), (k + .45) / max(1, L / 16)
            gd.line([(a_[0] + (b_[0] - a_[0]) * t0, a_[1] + (b_[1] - a_[1]) * t0), (a_[0] + (b_[0] - a_[0]) * t1, a_[1] + (b_[1] - a_[1]) * t1)], fill=(232, 230, 214), width=2)

# ---------------------------------------------------------------- objects layer (buildings + trees)
objects_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(objects_img)
objects = []  # dicts with rect + base (sort key)
occupied = pm | dm | wm


def shade(c, k): return tuple(int(max(0, min(255, v * k))) for v in c)


ROOFS_HOUSE = ['#c8452e', '#b23a2a', '#a44a36', '#7c7f88', '#5d6470', '#8a4c34', '#c86a3a']
ROOFS_FARM = ['#8d9096', '#767b82', '#9aa0a6', '#6f5a48', '#8a6a4c']
WALLS = ['#efe8d8', '#e6dcc4', '#f2eee2', '#e8d6b0', '#d8cdb8']
LANDMARK_IDS = set()

buildings = []
for e in ways:
    tg = e['tags']
    if 'building' not in tg: continue
    p = pts(e)
    if len(p) < 3: continue
    arr = np.array(p[:-1] if p[0] == p[-1] else p)
    c = arr.mean(0)
    u, s, vt = np.linalg.svd(arr - c)
    ax = vt[0]; nx = vt[1]
    pl = (arr - c) @ ax; pn_ = (arr - c) @ nx
    length, width = pl.max() - pl.min(), pn_.max() - pn_.min()
    maxdim = max(length, width) / A
    k = min(2.3, max(1.25, 26 / max(maxdim, 1)))
    kind = tg['building']
    if kind == 'church' or tg.get('amenity') == 'place_of_worship': LANDMARK_IDS.add(e['id'])
    buildings.append(dict(id=e['id'], kind=kind, c=c, ax=ax, nx=nx, L=length, Wd=width))

# Fit exaggerated footprints: largest scale (<= target) that avoids roads and already-placed buildings.
placed = np.zeros((H, W), bool)
road_block = pm | dm | wm
def footprint(b, k):
    c, ax, nx = b['c'], b['ax'], b['nx']; L, Wd = b['L0'] * k, b['W0'] * k
    return [tuple(c + ax * sx * L / 2 + nx * sy * Wd / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], L, Wd
for b in buildings:
    b['L0'], b['W0'] = b['L'], b['Wd']
    b['kmax'] = min(2.3, max(1.25, 26 / max(max(b['L'], b['Wd']) / A, 1)))
    b['L'] = b['W'] = None
for b in sorted(buildings, key=lambda b: -(b['L0'] * b['W0'])):
    k = b['kmax']
    while True:
        poly, L, Wd = footprint(b, k)
        xs = [v[0] for v in poly]; ys = [v[1] for v in poly]
        x0, y0, x1, y1 = int(max(0, min(xs) - 3)), int(max(0, min(ys) - 3)), int(min(W, max(xs) + 4)), int(min(H, max(ys) + 4))
        if x1 - x0 < 4 or y1 - y0 < 4 or min(xs) < 0 or min(ys) < 30 or max(xs) > W or max(ys) > H:
            b['skip'] = True; break
        m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in poly], fill=255)
        mm = np.array(m) > 0
        hit = (mm & (placed[y0:y1, x0:x1] | road_block[y0:y1, x0:x1])).sum()
        if hit == 0 or k <= 1.0:
            break
        k -= .1
    if b.get('skip'): continue
    b['poly'], b['L'], b['Wd'] = poly, L, Wd
    grown = Image.fromarray((mm * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))
    placed[y0:y1, x0:x1] |= np.array(grown) > 0
LM_NODES = []
for e in nodes:
    t = e.get('tags', {})
    if t.get('man_made') == 'windmill': LM_NODES.append(('windmill', P(e['lat'], e['lon'])))
    if 'Sklep' in t.get('name', ''): LM_NODES.append(('shop', P(e['lat'], e['lon'])))
for e in ways:
    if e['id'] in LANDMARK_IDS:
        bb = e['bounds']; LM_NODES.append(('church', P((bb['minlat'] + bb['maxlat']) / 2, (bb['minlon'] + bb['maxlon']) / 2)))
for b in buildings:
    for k_, (lx, ly) in LM_NODES:
        if math.hypot(b['c'][0] - lx, b['c'][1] - ly) < {'church': 70, 'shop': 30, 'windmill': 40}[k_]: b['skip'] = True
buildings = [b for b in buildings if not b.get('skip')]
buildings.sort(key=lambda b: max(v[1] for v in b['poly']))

# Replace one generic OSM house with the first photo-inspired (but not literal) AI house sprite.
# This way remains deterministic and keeps every other real building on its mapped footprint.
CUSTOM_HOUSE_WAY_ID = 1095382322
CUSTOM_HOUSE = None

for b in buildings:
    if b['id'] in LANDMARK_IDS: continue
    poly = b['poly']; kind = b['kind']
    if b['id'] == CUSTOM_HOUSE_WAY_ID:
        CUSTOM_HOUSE = b
        fm = Image.new('L', (W, H), 0); ImageDraw.Draw(fm).polygon(poly, fill=255)
        fmask = np.array(fm) > 0
        collide |= fmask; occupied |= fmask
        continue
    house = kind in ('house', 'detached', 'bungalow', 'yes', 'residential')
    hw = int((9 if house else 11) * A / 2 + (b['Wd'] + b['L']) * .03)
    wall = hexc(rnd.choice(WALLS)) if house else hexc(rnd.choice(['#b8a488', '#a89478', '#c4c0b6', '#9c8a70']))
    roof = hexc(rnd.choice(ROOFS_HOUSE if house else ROOFS_FARM))
    xs = [v[0] for v in poly]; ys = [v[1] for v in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys) - hw, max(ys)
    # ground shadow
    gd.polygon([(x + 5, y + 3) for x, y in poly], fill=(58, 84, 40))
    # walls: south-facing edges
    for i in range(4):
        a_, b_ = poly[i], poly[(i + 1) % 4]
        ex, ey = b_[0] - a_[0], b_[1] - a_[1]
        cx_, cy_ = (a_[0] + b_[0]) / 2 - np.mean(xs), (a_[1] + b_[1]) / 2 - np.mean(ys)
        if cy_ <= 0.5: continue
        lit = 1.0 if cx_ < 0 else .86
        quad = [a_, b_, (b_[0], b_[1] - hw), (a_[0], a_[1] - hw)]
        od.polygon(quad, fill=shade(wall, lit), outline=shade(wall, .55))
        L_ = math.hypot(ex, ey)
        if house and L_ > 14:
            nwin = max(1, int(L_ // 13))
            for kx in range(nwin):
                t_ = (kx + .5) / nwin
                wx, wy = a_[0] + ex * t_, a_[1] + ey * t_ - hw * .55
                od.rectangle([wx - 2, wy - 2, wx + 2, wy + 2], fill=(54, 84, 130), outline=(245, 240, 225))
        elif not house and L_ > 20:
            t_ = .5; wx, wy = a_[0] + ex * t_, a_[1] + ey * t_
            od.rectangle([wx - 5, wy - hw * .75, wx + 5, wy], fill=shade(wall, .45))
    # roof: split along ridge (long axis)
    rp = [(x, y - hw) for x, y in poly]
    c = np.mean(rp, 0); ax = b['ax']
    side = [(i, ((np.array(v) - c) @ b['nx'])) for i, v in enumerate(rp)]
    od.polygon(rp, fill=roof, outline=shade(roof, .45))
    half = [v for v in rp if (np.array(v) - c) @ b['nx'] >= 0]
    r1 = c + ax * b['L'] / 2; r0 = c - ax * b['L'] / 2
    if len(half) == 2:
        hp = [tuple(r0), tuple(r1)] + sorted(half, key=lambda v: -((np.array(v) - c) @ ax))
        dark_side_south = np.mean([v[1] for v in half]) > c[1]
        od.polygon(hp, fill=shade(roof, .78 if dark_side_south else 1.14), outline=shade(roof, .45))
    od.line([tuple(r0), tuple(r1)], fill=shade(roof, .5), width=1)
    # tile rows
    for kx in range(1, int(b['L'] // 6)):
        pa = r0 + ax * kx * 6
        od.line([tuple(pa + b['nx'] * b['Wd'] / 2), tuple(pa - b['nx'] * b['Wd'] / 2)], fill=shade(roof, .88), width=1)
    od.polygon(rp, outline=shade(roof, .4))
    if house and rnd.random() < .7:  # chimney
        ch = c + ax * b['L'] * .25 - b['nx'] * b['Wd'] * .1
        od.rectangle([ch[0] - 2, ch[1] - 7, ch[0] + 2, ch[1]], fill=(150, 80, 60), outline=(70, 40, 30))
    objects.append(dict(x=int(x0) - 2, y=int(y0) - 8, w=int(x1 - x0) + 12, h=int(y1 - y0) + 12, base=float(y1)))
    fm = Image.new('L', (W, H), 0); ImageDraw.Draw(fm).polygon(poly, fill=255)
    fmask = np.array(fm) > 0
    collide |= fmask; occupied |= fmask

# ---------------------------------------------------------------- minigame venues
# Sept 28 moves/additions, given as CURRENT map art pixels (the in-game coordinate readout), meaning "near here".
CUR_SITES = dict(pig=(3487, 3308), dogs=(1321, 888), jazz=tuple(int(round(v)) for v in P(52.27757, 22.87983)), gravel=(873, 2322))


def clear_rect(cx, cy, w, h, block, soft=None, search=600, step=10):
    """Top-left (x0, y0) of the w x h rectangle nearest to centre (cx, cy) with no `block` pixel; `soft` pixels cost distance."""
    wx0, wy0 = max(0, int(cx - w / 2 - search)), max(60, int(cy - h / 2 - search))
    wx1, wy1 = min(W, int(cx + w / 2 + search)), min(H, int(cy + h / 2 + search))
    def integral(mask):
        ii = np.zeros((wy1 - wy0 + 1, wx1 - wx0 + 1), np.int64); ii[1:, 1:] = mask[wy0:wy1, wx0:wx1].cumsum(0).cumsum(1); return ii
    ib, isf = integral(block), integral(soft) if soft is not None else None
    best = None
    for y0 in range(wy0, wy1 - h, step):
        for x0 in range(wx0, wx1 - w, step):
            a, b = y0 - wy0, x0 - wx0
            if ib[a + h, b + w] - ib[a, b + w] - ib[a + h, b] + ib[a, b]: continue
            cost = math.hypot(x0 + w / 2 - cx, y0 + h / 2 - cy)
            if isf is not None: cost += (isf[a + h, b + w] - isf[a, b + w] - isf[a + h, b] + isf[a, b]) * .05
            if best is None or cost < best[0]: best = (cost, x0, y0)
    assert best, f'no clear {w}x{h} area near {cx},{cy}'
    return best[1], best[2]


_forest_early = mask_of(classes.get('forest', []) + classes.get('wood', []))   # the forest is walkable but reads as woods, not a clearing
_venue_block = collide | wm | placed | _forest_early
_venue_soft = pm | dm | mask_of(classes.get('farmland', []) + classes.get('orchard', []))

# The race oval is at the supplied coordinate on the preceding map.
_tc = pre_expansion_i(*PRE_EXPANSION_ADDITIONS['race_oval'])
# Keep the complete oval inside the southern edge while staying within the requested vicinity.
TRACK = dict(cx=_tc[0], cy=min(_tc[1], H - 220), rx=300, ry=150, w=44)
_ox, _oy = clear_rect(*CUR_SITES['pig'], 260, 220, _venue_block, _venue_soft); CORRAL = dict(cx=_ox + 130, cy=_oy + 110, r=100)
# dog meadow (twice the old 420x270): open grass cleared near the requested spot
_mx0, _my0 = clear_rect(*CUR_SITES['dogs'], 840, 540, _venue_block, _venue_soft)
MEADOW = dict(x0=_mx0, y0=_my0, x1=_mx0 + 840, y1=_my0 + 540)
# JAZZ W STODOLE: a smaller barn sprite in the supplied developed-area location,
# with an open yard in front of the door.
_jx0, _jy0 = clear_rect(*CUR_SITES['jazz'], 160, 190, _venue_block | pm, dm)
BARN = dict(cx=_jx0 + 80, foot=_jy0 + 112, w=120)
JAZZ = dict(x=BARN['cx'], y=BARN['foot'] + 38, r=140)
# Wapnica: gravel pit / village dump
_gx0, _gy0 = clear_rect(*CUR_SITES['gravel'], 300, 220, _venue_block, _venue_soft)
PIT = dict(cx=_gx0 + 150, cy=_gy0 + 110, rx=140, ry=100)
GRAVEL = dict(x=PIT['cx'] + 40, y=PIT['cy'] + 42, r=60)
print('venues', dict(corral=CORRAL, meadow=MEADOW, barn=BARN, jazz=JAZZ, pit=PIT, gravel=GRAVEL))
_rc = tuple(int(round(v)) for v in P(52.2736642, 22.867767)); RANGE = dict(x=_rc[0], y=_rc[1])   # PPM Strzelectwo
_pc = pre_expansion_i(*PRE_EXPANSION_ADDITIONS['football_pitch']); FOOTBALL_PITCH = dict(cx=_pc[0] + 200, cy=_pc[1] + 100, w=110, h=190)


def window(cx, cy, rx, ry):
    """Coordinate grids (yy, xx) for a window around a venue, plus its offset."""
    x0, y0 = max(0, int(cx - rx)), max(0, int(cy - ry)); x1, y1 = min(W, int(cx + rx) + 1), min(H, int(cy + ry) + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    return x0, y0, yy, xx


g3 = np.array(ground).astype(np.float32)
x0_, y0_, yy, xx = window(TRACK['cx'], TRACK['cy'], TRACK['rx'] + 80, TRACK['ry'] + 80)
def ell(dx):  # normalised elliptic radius for an ellipse grown by dx pixels
    return ((xx - TRACK['cx']) / (TRACK['rx'] + dx)) ** 2 + ((yy - TRACK['cy']) / (TRACK['ry'] + dx)) ** 2
outer, inner = ell(TRACK['w'] / 2) <= 1, ell(-TRACK['w'] / 2) <= 1
ring = outer & ~inner
tn = noise2(xx.shape[1], xx.shape[0], 4, 91)[..., None]
tcol = np.array(hexc('#c79a62')) * (1 - tn) + np.array(hexc('#b48752')) * tn
sub = g3[y0_:y0_ + xx.shape[0], x0_:x0_ + xx.shape[1]]
sub[ring] = tcol[ring]
ang = np.arctan2((yy - TRACK['cy']) / TRACK['ry'], (xx - TRACK['cx']) / TRACK['rx'])
kerb_o = outer & ~(ell(TRACK['w'] / 2 - 4) <= 1); kerb_i = (ell(-TRACK['w'] / 2 + 4) <= 1) & ~inner
stripes = (np.floor(ang / (2 * np.pi) * 90) % 2).astype(bool)
for kb in (kerb_o, kerb_i):
    sub[kb & stripes] = hexc('#d8262c'); sub[kb & ~stripes] = hexc('#f4f1e6')
occupied[y0_:y0_ + xx.shape[0], x0_:x0_ + xx.shape[1]] |= outer & ~(ell(-TRACK['w'] / 2 - 25) <= 1)
# chequered start/finish line at the bottom of the oval
sx0 = TRACK['cx'] - 6; sy0, sy1 = TRACK['cy'] + TRACK['ry'] - TRACK['w'] / 2, TRACK['cy'] + TRACK['ry'] + TRACK['w'] / 2
for i_ in range(int(sy0), int(sy1), 4):
    for j_ in range(3):
        g3[i_:i_ + 4, sx0 + j_ * 4:sx0 + j_ * 4 + 4] = (20, 20, 20) if (i_ // 4 + j_) % 2 else (245, 245, 245)
TRACK_BALES = []
for deg in (200, 330):   # two bale walls across the track: jump them!
    a_ = math.radians(deg)
    for k_ in (-1, 0, 1):
        r_ = 1 + k_ * (TRACK['w'] / 2 - 9) / ((TRACK['rx'] + TRACK['ry']) / 2)
        TRACK_BALES.append((int(TRACK['cx'] + math.cos(a_) * TRACK['rx'] * r_), int(TRACK['cy'] + math.sin(a_) * TRACK['ry'] * r_)))
# corral: muddy floor + low fence with a gate on the west side
x0_, y0_, yy, xx = window(CORRAL['cx'], CORRAL['cy'], CORRAL['r'] + 24, CORRAL['r'] + 24)
cm_ = (((xx - CORRAL['cx']) / (CORRAL['r'] - 8)) ** 2 + ((yy - CORRAL['cy']) / ((CORRAL['r'] - 8) * .8)) ** 2) <= 1
mud = noise2(xx.shape[1], xx.shape[0], 4, 93) > .62
sub = g3[y0_:y0_ + xx.shape[0], x0_:x0_ + xx.shape[1]]
sub[cm_] = sub[cm_] * .8 + np.array(hexc('#a88a5c')) * .2; sub[cm_ & mud] = sub[cm_ & mud] * .75 + np.array(hexc('#8a6a44')) * .25
occupied[y0_:y0_ + xx.shape[0], x0_:x0_ + xx.shape[1]] |= (((xx - CORRAL['cx']) / (CORRAL['r'] + 20)) ** 2 + ((yy - CORRAL['cy']) / ((CORRAL['r'] + 20) * .8)) ** 2) <= 1
ground = Image.fromarray(g3.clip(0, 255).astype(np.uint8)); gd = ImageDraw.Draw(ground)
# A procedural football pitch at the shifted preceding-map coordinate. It is deliberately
# simple pixel art, not a fabricated photographic sprite, and remains fully walkable.
fp = FOOTBALL_PITCH
fx0, fx1 = int(fp['cx'] - fp['w'] / 2), int(fp['cx'] + fp['w'] / 2)
fy0, fy1 = int(fp['cy'] - fp['h'] / 2), int(fp['cy'] + fp['h'] / 2)
gd.rectangle([fx0, fy0, fx1, fy1], fill=hexc('#8fcf63'))
del g3, yy, xx, ang, sub
for k_ in range(0, 360, 3):
    if 165 < k_ < 195: continue
    a_ = math.radians(k_); x_, y_ = int(CORRAL['cx'] + math.cos(a_) * CORRAL['r']), int(CORRAL['cy'] + math.sin(a_) * CORRAL['r'] * .8)
    gd.rectangle([x_ - 1, y_ - 6, x_ + 1, y_ - 5], fill=(150, 104, 62)); gd.rectangle([x_ - 1, y_ - 3, x_ + 1, y_ - 2], fill=(128, 88, 52))
    if k_ % 9 == 0: gd.rectangle([x_ - 1, y_ - 8, x_ + 1, y_], fill=(110, 74, 42))
    low[y_ - 3:y_ + 2, x_ - 2:x_ + 3] = True
# shooting stand: planks + sandbags (walkable); clays fly north over the field
sx, sy = RANGE['x'], RANGE['y']
gd.rectangle([sx - 18, sy - 10, sx + 18, sy + 6], fill=(120, 84, 48), outline=(70, 46, 26))
for k_ in range(-18, 19, 6): gd.line([(sx + k_, sy - 10), (sx + k_, sy + 6)], fill=(98, 66, 38))
for k_ in range(-22, 23, 8): gd.ellipse([sx + k_ - 4, sy - 16, sx + k_ + 4, sy - 10], fill=(176, 160, 118), outline=(110, 96, 64))
occupied[sy - 160:sy + 30, sx - 80:sx + 80] = True
occupied[MEADOW['y0']:MEADOW['y1'], MEADOW['x0']:MEADOW['x1']] = True
# the dog meadow: crop rows / orchard inside it become mown meadow grass (roads stay), with a ragged, dithered edge
g6 = np.array(ground).astype(np.float32); mn = noise2(840, 540, 6, 96)[..., None]
_my, _mx = np.mgrid[0:540, 0:840]
_edge = np.minimum.reduce([_mx, 839 - _mx, _my, 539 - _my]).astype(np.float32)
_keep = (_edge > 10 + 60 * noise2(840, 540, 48, 95)) & ~(pm | dm)[MEADOW['y0']:MEADOW['y1'], MEADOW['x0']:MEADOW['x1']]
_sub6 = g6[MEADOW['y0']:MEADOW['y1'], MEADOW['x0']:MEADOW['x1']]
_sub6[_keep] = (np.array(hexc('#80bb50')) * (1 - mn) + np.array(hexc('#70ab46')) * mn)[_keep]
ground = Image.fromarray(g6.clip(0, 255).astype(np.uint8)); gd = ImageDraw.Draw(ground); del g6, _sub6
# Wapnica (gravel pit + village dump): pale excavated floor, walkable; heaps, spoil and the skip are solid.
x0_, y0_, yy, xx = window(PIT['cx'], PIT['cy'], PIT['rx'] + 20, PIT['ry'] + 20)
g4 = np.array(ground).astype(np.float32); sub = g4[y0_:y0_ + xx.shape[0], x0_:x0_ + xx.shape[1]]
pr = np.hypot((xx - PIT['cx']) / PIT['rx'], (yy - PIT['cy']) / PIT['ry'])
pit_rim, pit_floor = (pr <= 1.08) & (pr > .96), pr <= .96
gn = noise2(xx.shape[1], xx.shape[0], 5, 97)[..., None]
sub[pit_rim] = np.array(hexc('#9a8a66'))
sub[pit_floor] = (np.array(hexc('#d9cfb4')) * (1 - gn) + np.array(hexc('#bfb398')) * gn)[pit_floor]
pebble = (np.random.RandomState(98).rand(*pr.shape) > .93) & pit_floor
sub[pebble] = np.array(hexc('#8e8a82'))
# excavated look: the north wall of the pit is in shadow, the south edge catches the light
wall_n = (pr <= 1.0) & (pr > .78) & (yy < PIT['cy'] - PIT['ry'] * .35)
sub[wall_n] = sub[wall_n] * .72 + np.array(hexc('#6e6048')) * .28
lip_s = (pr <= 1.0) & (pr > .9) & (yy > PIT['cy'] + PIT['ry'] * .4)
sub[lip_s] = sub[lip_s] * .7 + np.array(hexc('#efe6cc')) * .3
ground = Image.fromarray(g4.clip(0, 255).astype(np.uint8)); gd = ImageDraw.Draw(ground); del g4, sub
for i_ in range(2):       # two tyre ruts across the floor
    ry_ = PIT['cy'] + 40 + i_ * 9
    gd.line([(PIT['cx'] - PIT['rx'] + 10, ry_), (PIT['cx'] + PIT['rx'] - 10, ry_ - 20)], fill=hexc('#a89c80'), width=3)
occupied[PIT['cy'] - PIT['ry'] - 30:PIT['cy'] + PIT['ry'] + 25, PIT['cx'] - PIT['rx'] - 25:PIT['cx'] + PIT['rx'] + 25] = True


def gravel_heap(cx, cy, r, col='#a9a296'):
    base = hexc(col)
    rs = random.Random(cx * 7 + cy)
    gd.ellipse([cx - r - 4, cy - 5, cx + r + 6, cy + 7], fill=hexc('#8f8674'))
    # lumpy conical silhouette: a jagged outline instead of a smooth dome
    prof = [(cx - r, cy)]
    for k in range(1, 12):
        t = k / 12; hgt = r * 1.25 * (1 - abs(2 * t - 1)) ** .8 * rs.uniform(.82, 1.08)
        prof.append((cx - r + 2 * r * t, cy - hgt))
    prof.append((cx + r, cy))
    od.polygon(prof, fill=shade(base, .92), outline=shade(base, .5))
    od.polygon([prof[0]] + prof[1:7] + [(cx - r * .05, cy)], fill=shade(base, 1.12))   # sunlit west face
    for _ in range(int(r * 5)):
        px, py = cx + rs.uniform(-r, r), cy - rs.uniform(0, r * 1.15)
        if py > cy - r * 1.25 * (1 - abs((px - cx) / r)) ** .8 * .85: od.rectangle([px, py, px + 1, py], fill=shade(base, rs.choice([.62, 1.3, .8, 1.05])))
    objects.append(dict(x=int(cx - r - 3), y=int(cy - r * 1.3 - 3), w=int(2 * r + 8), h=int(r * 1.3 + 10), base=float(cy + 2)))
    collide[int(cy - r * .45):int(cy + 2), int(cx - r * .8):int(cx + r * .8)] = True


gravel_heap(PIT['cx'] - 78, PIT['cy'] - 30, 30)
gravel_heap(PIT['cx'] - 22, PIT['cy'] - 56, 24, '#c2b58f')
gravel_heap(PIT['cx'] + 70, PIT['cy'] - 48, 20, '#9d9486')
# rusty skip container with rubbish next to the drop-off point
kx_, ky_ = GRAVEL['x'] + 34, GRAVEL['y'] - 6
gd.rectangle([kx_ - 22, ky_ - 1, kx_ + 26, ky_ + 5], fill=hexc('#7d735c'))
od.polygon([(kx_ - 24, ky_ - 20), (kx_ + 24, ky_ - 20), (kx_ + 20, ky_), (kx_ - 20, ky_)], fill=hexc('#3f6b3a'), outline=hexc('#1f3520'))
od.rectangle([kx_ - 24, ky_ - 22, kx_ + 24, ky_ - 19], fill=hexc('#5a8a4a'), outline=hexc('#1f3520'))
for rx_, ry_, c_ in [(-16, -24, '#1c1c1c'), (-6, -26, '#e8e2d0'), (3, -24, '#3a78c8'), (12, -25, '#9a6a3a'), (18, -23, '#c8c8c8'), (-11, -27, '#c84a3a')]:
    od.rectangle([kx_ + rx_, ky_ + ry_, kx_ + rx_ + 5, ky_ + ry_ + 3], fill=hexc(c_))
for rx_ in (-18, -6, 6, 18): od.line([(kx_ + rx_, ky_ - 18), (kx_ + rx_ * .85, ky_ - 2)], fill=hexc('#2c4c2a'))
od.rectangle([kx_ - 20, ky_ - 12, kx_ - 10, ky_ - 8], fill=hexc('#8a4a2a'))   # rust patch
objects.append(dict(x=kx_ - 26, y=ky_ - 30, w=54, h=36, base=float(ky_)))
collide[ky_ - 8:ky_ + 1, kx_ - 22:kx_ + 22] = True
# wooden sign post "WAPNICA" (the game draws the readable label; the board is pixel art)
sx_, sy_ = PIT['cx'] - PIT['rx'] + 18, PIT['cy'] + 20
od.rectangle([sx_ - 1, sy_ - 22, sx_ + 1, sy_], fill=hexc('#6a4a2a'))
od.rectangle([sx_ - 16, sy_ - 30, sx_ + 16, sy_ - 18], fill=hexc('#c9a46a'), outline=hexc('#5a3a1a'))
for lx_ in range(sx_ - 12, sx_ + 12, 4): od.rectangle([lx_, sy_ - 26, lx_ + 2, sy_ - 22], fill=hexc('#5a3a1a'))
objects.append(dict(x=sx_ - 18, y=sy_ - 32, w=36, h=34, base=float(sy_)))
collide[sy_ - 3:sy_ + 1, sx_ - 2:sx_ + 3] = True

# JAZZ W STODOLE: barn sprite (generated pixel art) on a farmyard, lit yard with benches in front.
yx0, yy0, yx1, yy1 = BARN['cx'] - 95, BARN['foot'] - 10, BARN['cx'] + 95, BARN['foot'] + 95
g5 = np.array(ground).astype(np.float32); yn = noise2(yx1 - yx0, yy1 - yy0, 4, 99)[..., None]
_yy, _yx = np.mgrid[0:yy1 - yy0, 0:yx1 - yx0]
_ye = np.minimum.reduce([_yx, yx1 - yx0 - 1 - _yx, yy1 - yy0 - 1 - _yy]).astype(np.float32)   # ragged edge, open to the barn
_ym = _ye > 12 * np.random.RandomState(94).rand(*_ye.shape)
_ys = g5[yy0:yy1, yx0:yx1]; _ys[_ym] = (np.array(hexc('#b89a6c')) * (1 - yn) + np.array(hexc('#a8895e')) * yn)[_ym]
ground = Image.fromarray(g5.clip(0, 255).astype(np.uint8)); gd = ImageDraw.Draw(ground); del g5, _ys
barn = Image.fromarray(chroma_key('gen/lm_barn.png')); barn = barn.crop(barn.getbbox())
bw_ = BARN['w']; bh_ = round(barn.height * bw_ / barn.width); barn = barn.resize((bw_, bh_), Image.Resampling.LANCZOS)
bx0_, by0_ = BARN['cx'] - bw_ // 2, BARN['foot'] - bh_
objects_img.alpha_composite(barn, (bx0_, by0_))
objects.append(dict(x=bx0_, y=by0_, w=bw_, h=bh_, base=float(BARN['foot'] - 8)))
collide[max(0, by0_ + int(bh_ * .45)):BARN['foot'] - 8, bx0_ + 8:bx0_ + bw_ - 8] = True
occupied[max(0, by0_ - 10):yy1 + 20, yx0 - 20:yx1 + 20] = True
for bxx in (-60, 44):   # benches
    by_ = BARN['foot'] + 62
    od.rectangle([BARN['cx'] + bxx, by_ - 7, BARN['cx'] + bxx + 20, by_ - 4], fill=hexc('#8a5a30'), outline=hexc('#4a2a10'))
    for lg in (2, 17): od.rectangle([BARN['cx'] + bxx + lg, by_ - 4, BARN['cx'] + bxx + lg + 1, by_], fill=hexc('#4a2a10'))
    objects.append(dict(x=BARN['cx'] + bxx - 1, y=by_ - 9, w=23, h=11, base=float(by_)))
    low[by_ - 5:by_ + 1, BARN['cx'] + bxx:BARN['cx'] + bxx + 21] = True
for lx_ in (yx0 + 10, yx1 - 10):   # two lantern posts at the front corners of the yard
    ly_ = yy1 - 12
    od.rectangle([lx_ - 1, ly_ - 26, lx_ + 1, ly_], fill=hexc('#3a2a1a'))
    od.rectangle([lx_ - 3, ly_ - 32, lx_ + 3, ly_ - 25], fill=hexc('#ffd86a'), outline=hexc('#5a3a1a'))
    od.point((lx_ - 1, ly_ - 30), fill=hexc('#fff6c8'))
    objects.append(dict(x=lx_ - 4, y=ly_ - 33, w=9, h=35, base=float(ly_)))
    collide[ly_ - 2:ly_ + 1, lx_ - 2:lx_ + 3] = True

# ---------------------------------------------------------------- fences around gardens + hay bales (low, jumpable)
road_near = np.array(Image.fromarray(((pm | dm) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(21))) > 0
for poly_ in classes.get('residential', []):
    run = 0.0   # distance along this fence line; a 16 px gate opens every 110 px so every garden can be entered on foot
    for a_, b_ in zip(poly_, poly_[1:]):
        L = math.hypot(b_[0] - a_[0], b_[1] - a_[1]); n = int(L // 3)
        for k in range(n):
            t_ = k / max(1, n); x, y = a_[0] + (b_[0] - a_[0]) * t_, a_[1] + (b_[1] - a_[1]) * t_
            xi, yi = int(x), int(y)
            run += 3
            if run % 110 < 16: continue
            if not (2 < xi < W - 3 and 40 < yi < H - 3) or road_near[yi, xi] or occupied[yi, xi]: continue
            # two rails + a post every ~9 px
            gd.rectangle([xi - 1, yi - 6, xi + 1, yi - 5], fill=(150, 104, 62))
            gd.rectangle([xi - 1, yi - 3, xi + 1, yi - 2], fill=(128, 88, 52))
            gd.point((xi, yi), fill=(70, 96, 44))
            if k % 3 == 0:
                gd.rectangle([xi - 1, yi - 8, xi + 1, yi], fill=(110, 74, 42)); gd.point((xi, yi - 8), fill=(170, 124, 80))
            low[yi - 3:yi + 2, xi - 2:xi + 3] = True
bales = []
def draw_bale(x, y):
    gd.ellipse([x - 11, y - 2, x + 13, y + 5], fill=(96, 84, 40))
    od.rectangle([x - 11, y - 16, x + 11, y + 1], fill=(206, 168, 80), outline=(112, 84, 36))
    od.ellipse([x - 11, y - 20, x + 11, y - 12], fill=(226, 192, 104), outline=(112, 84, 36))
    od.ellipse([x - 6, y - 18, x + 6, y - 14], outline=(180, 142, 64))
    for yy_ in (y - 9, y - 4): od.line([(x - 10, yy_), (x + 10, yy_)], fill=(186, 150, 70))
    objects.append(dict(x=x - 13, y=y - 22, w=27, h=26, base=float(y + 2)))
    low[y - 6:y + 2, x - 11:x + 12] = True
    occupied[max(0, y - 24):y + 8, max(0, x - 16):x + 17] = True   # keep trees and other props off static track bales
for x_, y_ in TRACK_BALES: draw_bale(x_, y_)
for p_ in classes.get('farmland', []):
    ox_, oy_, m_ = mask_win(p_)
    if not m_.size: continue
    ys_, xs_ = np.nonzero(m_ & ~occupied[oy_:oy_ + m_.shape[0], ox_:ox_ + m_.shape[1]]); ys_ = ys_ + oy_; xs_ = xs_ + ox_
    if len(xs_) < 4000: continue
    for _ in range(3):
        i_ = rnd.randrange(len(xs_)); x, y = int(xs_[i_]), int(ys_[i_])
        if not (20 < x < W - 20 and 60 < y < H - 20): continue
        bales.append(dict(x=x, y=y))
        occupied[max(0, y - 24):y + 8, max(0, x - 16):x + 17] = True   # reserve the dynamic bale footprint
print('hay bales', len(bales))

# ---------------------------------------------------------------- landmark sprites
LM_SIZE = {'church': 150, 'windmill': 84, 'shop': 140}   # sprite width in art px
for k_, (lx, ly) in LM_NODES:
    a = chroma_key(f'gen/lm_{k_}.png'); im = Image.fromarray(a); im = im.crop(im.getbbox())
    w = LM_SIZE[k_]; h = int(im.height * w / im.width); im = im.resize((w, h), Image.LANCZOS)
    x0, y0 = int(lx - w / 2), int(ly - h * .78)          # the node sits in the lower part of the sprite
    objects_img.alpha_composite(im, (max(0, x0), max(0, y0)))
    base = y0 + h * .82
    objects.append(dict(x=x0, y=y0, w=w, h=h, base=float(base)))
    cw, ch_ = w * .55, h * .28
    collide[int(base - ch_):int(base), int(lx - cw / 2):int(lx + cw / 2)] = True
    occupied[max(0, y0):y0 + h, max(0, x0):x0 + w] = True

# Wayside shrines and crosses stand at real OSM road junctions (nodes shared by two or more roads/tracks).
# The photos have no GPS, so the four sites are chosen to spread across the whole map: greedy farthest-point
# selection, at least SHRINE_GAP px from each other and from the landmarks, sign, venues and the start.
SHRINE_NAMES = [('cross_iron', 32), ('shrine_stone', 36), ('shrine_white', 34), ('shrine_fenced', 32)]
SHRINE_GAP = 650
_node_roads = {}
for e in ways:
    if 'highway' not in e['tags'] or e['tags']['highway'] in ('footway', 'path', 'bus_stop'): continue
    for g_ in e['geometry']: _node_roads.setdefault((round(g_['lat'], 7), round(g_['lon'], 7)), set()).add(e['id'])
junctions = [P(*k) for k, v in _node_roads.items() if len(v) >= 2]
junctions = [(x, y) for x, y in junctions if 120 < x < W - 120 and 160 < y < H - 80]
keep_away = [xy for _, xy in LM_NODES] + [legacy_i(1150, 2405), (TRACK['cx'], TRACK['cy']), (CORRAL['cx'], CORRAL['cy']),
             ((MEADOW['x0'] + MEADOW['x1']) / 2, (MEADOW['y0'] + MEADOW['y1']) / 2), (RANGE['x'], RANGE['y']),
             (JAZZ['x'], JAZZ['y']), (PIT['cx'], PIT['cy'])]
cands = [j for j in junctions if all(math.hypot(j[0] - k[0], j[1] - k[1]) > 260 for k in keep_away)]
chosen = []
while len(chosen) < len(SHRINE_NAMES) and cands:
    best = max(cands, key=lambda j: min([math.hypot(j[0] - c[0], j[1] - c[1]) for c in chosen] + [math.hypot(j[0] - k[0], j[1] - k[1]) for k in keep_away]))
    if chosen and min(math.hypot(best[0] - c[0], best[1] - c[1]) for c in chosen) < SHRINE_GAP * .5: break
    chosen.append(best); cands = [j for j in cands if math.hypot(j[0] - best[0], j[1] - best[1]) > SHRINE_GAP]


def verge(x, y, w):
    """A spot beside the junction: off the road, not on anything else, closest to the junction."""
    for r in range(14, 60, 3):
        for k in range(16):
            a_ = k / 16 * 2 * math.pi; cx, cy = int(x + math.cos(a_) * r), int(y + math.sin(a_) * r)
            x0, x1 = cx - w // 2, cx + w // 2
            if not (10 < x0 and x1 < W - 10 and 60 < cy - w < H - 10): continue
            if not (road_block[cy - 12:cy + 2, x0:x1].any() or occupied[cy - 12:cy + 2, x0:x1].any()): return cx, cy
    return int(x + 20), int(y + 20)


GENERATED_SHRINES = [(name, *verge(jx, jy, w), w) for (name, w), (jx, jy) in zip(SHRINE_NAMES, chosen)]
print('shrines', [(n, x, y) for n, x, y, _ in GENERATED_SHRINES])

def add_generated_sprite(name, cx, foot_y, width, block_base=True):
    image = Image.fromarray(chroma_key(f'gen/lm_{name}.png'))
    image = image.crop(image.getbbox())
    height = max(1, round(image.height * width / image.width))
    image = image.resize((width, height), Image.Resampling.NEAREST)
    x0, y0 = int(cx - width / 2), int(foot_y - height)
    objects_img.alpha_composite(image, (x0, y0))
    objects.append(dict(x=x0, y=y0, w=width, h=height, base=float(foot_y)))
    occupied[max(0, y0):min(H, foot_y), max(0, x0):min(W, x0 + width)] = True
    if block_base:
        collide[max(0, foot_y - 9):min(H, foot_y + 1), max(0, cx - 5):min(W, cx + 6)] = True

if CUSTOM_HOUSE:
    house_poly = CUSTOM_HOUSE['poly']
    house_cx = float(np.mean([p[0] for p in house_poly]))
    house_foot_y = int(max(p[1] for p in house_poly))
    add_generated_sprite('house_generic', house_cx, house_foot_y, 90, block_base=False)
else:
    raise RuntimeError(f'Expected generated-house OSM way {CUSTOM_HOUSE_WAY_ID} was not placed')

for name, cx, foot_y, width in GENERATED_SHRINES:
    add_generated_sprite(name, cx, foot_y, width)

# Chłopków entrance sign, based on Tomek's reference photo; positioned beside the southern road.
sign = Image.fromarray(chroma_key('gen/lm_village_sign.png'))
sign = sign.crop(sign.getbbox())
sign_w = 110
sign_h = round(sign.height * sign_w / sign.width)
sign = sign.resize((sign_w, sign_h), Image.LANCZOS)
sign_x, sign_base = legacy_i(1150, 2405)
sign_y = sign_base - sign_h
objects_img.alpha_composite(sign, (sign_x - sign_w // 2, sign_y))
objects.append(dict(x=sign_x - sign_w // 2, y=sign_y, w=sign_w, h=sign_h, base=float(sign_base)))
collide[sign_base - 9:sign_base, sign_x - 4:sign_x + 5] = True
occupied[max(0, sign_y):sign_base, max(0, sign_x - sign_w // 2):sign_x + sign_w // 2] = True

# ---------------------------------------------------------------- trees
occ_img = Image.fromarray((occupied * 255).astype(np.uint8))
occ_d = np.array(occ_img.filter(ImageFilter.MaxFilter(15))) > 0


tree_stats = {'conifer': 0, 'oak': 0, 'deciduous': 0}


def tree(x, y, r, kind='deciduous'):
    """Draw one y-sorted village tree; its trunk collision footprint stays unchanged."""
    x, y, r = int(x), int(y), int(r)
    if kind == 'oak':
        # Oaks are broad-canopied hardwoods; scale the crown and trunk, not the foot.
        r = int(r * 1.25)
    gd.ellipse([x - r * .9, y - 3, x + r * .9, y + 4], fill=(52, 80, 36))
    trunk_top = y - int(r * (.42 if kind == 'oak' else .7))
    trunk = (116, 82, 48) if kind == 'oak' else (98, 66, 40)
    if kind == 'deciduous':
        trunk = (218, 211, 176)  # birch-like pale bark
    od.rectangle([x - 2, trunk_top, x + 2, y], fill=trunk, outline=(58, 38, 24))
    if kind == 'deciduous':
        for mark_y in range(trunk_top + 4, y, 7): od.point((x - 1, mark_y), fill=(74, 62, 45))

    cy = y - r * 1.25
    if kind == 'conifer':
        # Three stepped, pointed tiers in deep blue-green; hard polygon edges keep it crisp.
        colors = [hexc('#183d3d'), hexc('#205448'), hexc('#2b6950')]
        for i, (top, bottom, half) in enumerate(((cy - r * 1.05, cy + r * .15, r * .9),
                                                  (cy - r * .48, cy + r * .62, r * 1.15),
                                                  (cy + r * .05, cy + r * 1.05, r * 1.4))):
            od.polygon([(x, int(top)), (x - int(half), int(bottom)), (x + int(half), int(bottom))],
                       fill=colors[i], outline=(17, 43, 38))
            od.line([(x, int(top) + 3), (x - int(half * .72), int(bottom) - 2)], fill=shade(colors[i], 1.28), width=1)
        half_width, top_y = r * 1.4, cy - r * 1.05
    elif kind == 'oak':
        # Broad, low oak crown: separated leaf-cluster silhouettes over a deep olive
        # canopy make the lobes read as an oak rather than a round shrub.
        base = hexc('#465b25')
        dark_rim = (25, 38, 20)
        crown_y = cy - r * .06
        od.ellipse([x - r * 1.62, crown_y - r * .69, x + r * 1.62, crown_y + r * .62],
                   fill=(34, 48, 22), outline=dark_rim)
        # Thick trunk and visible root flares; two branches show through deliberate
        # gaps between the clusters. Keep the foot at y for unchanged collision/sort.
        trunk_top = int(crown_y + r * .12)
        trunk_col = (105, 71, 39)
        od.polygon([(x - r * .20, y), (x - r * .39, y + 1), (x - r * .48, y + 3),
                    (x - r * .12, y + 2), (x + r * .08, y + 2), (x + r * .42, y + 3),
                    (x + r * .34, y + 1), (x + r * .17, y)], fill=trunk_col, outline=(55, 38, 23))
        od.rectangle([x - r * .20, trunk_top, x + r * .20, y + 1], fill=trunk_col)
        od.line([(x, trunk_top + 2), (x - r * .42, crown_y + r * .48)], fill=(66, 48, 29), width=2)
        od.line([(x, trunk_top + 2), (x + r * .43, crown_y + r * .44)], fill=(66, 48, 29), width=2)
        clusters = [(-1.03, .03, .58), (-.60, -.43, .59), (-.10, -.55, .61),
                    (.51, -.47, .62), (1.02, -.12, .55), (.65, .34, .57),
                    (.08, .39, .58), (-.58, .34, .56)]
        for i, (dx, dy, size) in enumerate(clusters):
            rr = r * size
            cx_, cy_ = x + r * dx, crown_y + r * dy
            tint = [0.96, 1.12, 1.04, .91, .88, 1.02, 1.08, .98][i]
            col = shade(hexc('#52692b'), tint)
            od.ellipse([cx_ - rr, cy_ - rr * .78, cx_ + rr, cy_ + rr * .78],
                       fill=col, outline=dark_rim, width=1)
        # A small broken highlight on upper-left leaves, not a smooth disk.
        for dx, dy, rw, rh in [(-.84, -.57, .32, .17), (-.35, -.80, .29, .16),
                                (-.78, -.16, .22, .13)]:
            hx, hy = x + r * dx, crown_y + r * dy
            od.ellipse([hx - r * rw, hy - r * rh, hx + r * rw, hy + r * rh],
                       fill=(112, 132, 57))
        # Foreground trunk/branches cross the foliage like a small classic oak
        # branching structure; warm bark highlights keep them visible at game scale.
        fork_y = trunk_top + r * .06
        branch_width = max(4, int(r * .38))
        highlight_width = max(2, int(r * .20))
        od.line([(x, y), (x, trunk_top), (x - r * .76, crown_y + r * .10)], fill=(49, 35, 22), width=branch_width)
        od.line([(x, fork_y), (x + r * .78, crown_y + r * .08)], fill=(49, 35, 22), width=branch_width)
        od.line([(x, y - 1), (x, trunk_top), (x - r * .76, crown_y + r * .10)], fill=(153, 105, 57), width=highlight_width)
        od.line([(x, fork_y), (x + r * .78, crown_y + r * .08)], fill=(153, 105, 57), width=highlight_width)
        od.polygon([(x - r * .20, y - 1), (x - r * .39, y + 1), (x - r * .48, y + 3),
                    (x - r * .12, y + 2), (x + r * .08, y + 2), (x + r * .42, y + 3),
                    (x + r * .34, y + 1), (x + r * .17, y - 1)], fill=(123, 83, 45), outline=(49, 35, 22))
        # Two tiny capped acorns make the broadleaf species unmistakably oak.
        for dx, dy in [(-.84, .16), (.80, .22)]:
            ax_, ay_ = x + r * dx, crown_y + r * dy
            od.ellipse([ax_ - 2, ay_ - 1, ax_ + 2, ay_ + 4], fill=(198, 151, 63), outline=(61, 47, 27))
            od.rectangle([ax_ - 2, ay_ - 2, ax_ + 2, ay_], fill=(74, 54, 31))
        half_width, top_y = r * 1.82, crown_y - r * 1.15
    else:
        base = hexc('#2e7a33')
        od.ellipse([x - r, cy - r, x + r, cy + r], fill=shade(base, .75), outline=(24, 52, 26))
        od.ellipse([x - r * .85, cy - r * .95, x + r * .7, cy + r * .6], fill=base)
        od.ellipse([x - r * .6, cy - r * .8, x + r * .15, cy - r * .1], fill=shade(base, 1.35))
        half_width, top_y = r, cy - r
    # Keep the renderer RNG stream stable across visual species variants.
    highlights = [(x + rnd.uniform(-r * .6, r * .5), cy + rnd.uniform(-r * .7, r * .5)) for _ in range(4)]
    if kind == 'deciduous':
        for px, py in highlights: od.point((px, py), fill=shade(base, 1.6))
    tree_stats[kind] += 1
    # Preserve foot/base sorting while bounding the wider crowns for renderer culling.
    objects.append(dict(x=int(x - half_width - 2), y=int(top_y) - 2,
                        w=int(2 * half_width + 4), h=int(y - top_y) + 8, base=float(y), kind='tree', species=kind))
    collide[max(0, y - 3):y + 1, max(0, x - 3):x + 4] = True


def village_tree_type(x, y):
    """Stable spatial variation without consuming the renderer's layout RNG stream."""
    return 'oak' if ((int(x) * 73856093) ^ (int(y) * 19349663)) % 100 < 24 else 'deciduous'


res_mask = mask_of(classes.get('residential', []) + classes.get('religious', []) + classes.get('cemetery', []))
forest_mask = mask_of(classes.get('forest', []) + classes.get('wood', []))
orch = classes.get('orchard', [])
tree_pts = []
# residential gardens
for _ in range(9000):
    x, y = rnd.uniform(8, W - 8), rnd.uniform(20, H - 4)
    xi, yi = int(x), int(y)
    if res_mask[yi, xi] and not occ_d[yi, xi] and rnd.random() < .35: tree_pts.append((x, y, rnd.uniform(8, 13), village_tree_type(x, y)))
# river banks
for l, w in river_lines:
    for a_, b_ in zip(l, l[1:]):
        L = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
        for k in range(int(L // 26)):
            t_ = rnd.random(); side = rnd.choice([-1, 1])
            ex, ey = (b_[0] - a_[0]) / L, (b_[1] - a_[1]) / L
            x, y = a_[0] + (b_[0] - a_[0]) * t_ - ey * side * (w / 2 + 12), a_[1] + (b_[1] - a_[1]) * t_ + ex * side * (w / 2 + 12)
            if 0 < x < W and 20 < y < H and not occ_d[int(y), int(x)] and rnd.random() < .55: tree_pts.append((x, y, rnd.uniform(10, 15), village_tree_type(x, y)))
# orchards
for p in orch:
    m = mask_of([p]); arr = np.array(p); x0, y0 = arr.min(0); x1, y1 = arr.max(0)
    for y in np.arange(y0 + 10, y1, 22):
        for x in np.arange(x0 + 10, x1, 22):
            if m[int(y), int(x)] and not occ_d[int(y), int(x)]: tree_pts.append((x, y, 8, 'deciduous'))
# thin out overlaps
tree_pts.sort(key=lambda t: t[1]); kept = []
for t_ in tree_pts:
    if all(math.hypot(t_[0] - k_[0], t_[1] - k_[1]) > (t_[2] + k_[2]) * .9 for k_ in kept[-60:]): kept.append(t_)
for x, y, r, kind in kept: tree(x, y, r, kind)

# forests: species are mixed on the ground layer, preserving walkable forest-floor collision.
fy, fx = np.nonzero(forest_mask)
g2 = np.array(ground).astype(np.float32); g2[forest_mask] = hexc('#1f4f24'); ground = Image.fromarray(g2.astype(np.uint8)); gd = ImageDraw.Draw(ground)
cand = list(zip(fx[::37], fy[::37])); rnd.shuffle(cand); cand = sorted(cand[:2600], key=lambda v: v[1])
forest_tree_stats = {'conifer': 0, 'oak': 0, 'deciduous': 0}
for x, y in cand:
    r = int(rnd.uniform(7, 12))
    roll = rnd.random()
    kind = 'conifer' if roll < .60 else 'oak' if roll < .85 else 'deciduous'
    if kind == 'oak':
        r = int(r * 1.3)
    if kind == 'conifer':
        # Layered, pointed blue-green tiers: visibly narrower and sharper than the broad crowns.
        for top, bottom, half, color in ((y - 2 * r, y - r, r // 2, '#173b42'),
                                         (y - int(1.5 * r), y - r // 3, int(.8 * r), '#205248'),
                                         (y - r, y + 2, r, '#2d6950')):
            gd.polygon([(x, top), (x - half, bottom), (x + half, bottom)], fill=hexc(color), outline=(18, 43, 39))
        gd.line([(x, y - 2 * r + 2), (x - r // 3, y - r)], fill=hexc('#4b8261'), width=1)
    elif kind == 'oak':
        # Forest oaks get the same wide, broken olive crown as garden oaks,
        # with pixel-scale trunk/root and fork marks kept visible below the canopy.
        oak = hexc(rnd.choice(['#4c6329', '#556b2e', '#465e2a']))
        crown_y = y - int(.35 * r)
        trunk_top = int(crown_y + .22 * r)
        gd.polygon([(x - 2, y + 4), (x - int(.43 * r), y + 5), (x - int(.52 * r), y + 7),
                    (x - 1, y + 6), (x + 1, y + 6), (x + int(.48 * r), y + 7),
                    (x + int(.38 * r), y + 5), (x + 2, y + 4)], fill=(83, 57, 34), outline=(43, 34, 23))
        gd.rectangle([x - 2, trunk_top, x + 2, y + 5], fill=(105, 71, 39))
        gd.line([(x, trunk_top + 1), (x - int(.55 * r), crown_y + int(.5 * r))], fill=(66, 48, 29), width=1)
        gd.line([(x, trunk_top + 1), (x + int(.55 * r), crown_y + int(.48 * r))], fill=(66, 48, 29), width=1)
        gd.ellipse([x - int(1.62 * r), crown_y - int(.68 * r), x + int(1.62 * r), crown_y + int(.62 * r)],
                   fill=(34, 48, 22), outline=(25, 38, 20))
        clusters = [(-1.02, .02, .58, .96), (-.60, -.43, .59, 1.12), (-.10, -.55, .61, 1.04),
                    (.51, -.47, .62, .91), (1.02, -.12, .55, .88), (.65, .34, .57, 1.02),
                    (.08, .39, .58, 1.08), (-.58, .34, .56, .98)]
        for dx, dy, size, light in clusters:
            rr = max(3, int(r * size))
            cx_, cy_ = x + int(r * dx), crown_y + int(r * dy)
            col = shade(oak, light)
            gd.ellipse([cx_ - rr, cy_ - int(rr * .78), cx_ + rr, cy_ + int(rr * .78)],
                       fill=col, outline=(25, 38, 20), width=1)
        for dx, dy, rw, rh in [(-.84, -.57, .32, .17), (-.35, -.80, .29, .16)]:
            hx, hy = x + int(r * dx), crown_y + int(r * dy)
            gd.ellipse([hx - max(2, int(r * rw)), hy - max(1, int(r * rh)),
                        hx + max(2, int(r * rw)), hy + max(1, int(r * rh))], fill=(112, 132, 57))
        gd.line([(x, y + 5), (x, trunk_top), (x - int(.72 * r), crown_y + int(.10 * r))], fill=(49, 35, 22), width=3)
        gd.line([(x, trunk_top), (x + int(.74 * r), crown_y + int(.08 * r))], fill=(49, 35, 22), width=3)
        gd.line([(x, y + 5), (x, trunk_top), (x - int(.72 * r), crown_y + int(.10 * r))], fill=(153, 105, 57), width=1)
        gd.line([(x, trunk_top), (x + int(.74 * r), crown_y + int(.08 * r))], fill=(153, 105, 57), width=1)
        gd.polygon([(x - 2, y + 3), (x - int(.43 * r), y + 5), (x - int(.52 * r), y + 7),
                    (x - 1, y + 6), (x + 1, y + 6), (x + int(.48 * r), y + 7),
                    (x + int(.38 * r), y + 5), (x + 2, y + 3)], fill=(123, 83, 45), outline=(49, 35, 22))
        # Visible acorn-and-cap marks are an oak-specific cue at game scale.
        for dx, dy in [(-.84, .16), (.80, .22)]:
            ax_, ay_ = x + int(r * dx), crown_y + int(r * dy)
            gd.ellipse([ax_ - 2, ay_ - 1, ax_ + 2, ay_ + 4], fill=(198, 151, 63), outline=(61, 47, 27))
            gd.rectangle([ax_ - 2, ay_ - 2, ax_ + 2, ay_], fill=(74, 54, 31))
    else:
        base = hexc(rnd.choice(['#5ca04a', '#519343', '#68ad52', '#478a3e']))
        gd.ellipse([x - r, y - r, x + r, y + r], fill=shade(base, .75), outline=(20, 44, 22))
        gd.ellipse([x - int(.8 * r), y - int(.9 * r), x + int(.6 * r), y + int(.5 * r)], fill=base)
        gd.ellipse([x - int(.55 * r), y - int(.75 * r), x + int(.1 * r), y - int(.15 * r)], fill=shade(base, 1.3))
    tree_stats[kind] += 1
    forest_tree_stats[kind] += 1

# ---------------------------------------------------------------- POIs + named real-world landmarks
pois = []
landmarks = []


def add_landmark(key, name, lat, lon, kind='poi'):
    x, y = P(lat, lon)
    if 20 < x < W - 20 and 50 < y < H - 20:
        landmarks.append(dict(key=key, name=name, kind=kind, lat=lat, lon=lon, x=round(x), y=round(y)))


for landmark in REAL_POIS:
    add_landmark(landmark['key'], landmark['name'], landmark['lat'], landmark['lon'])


for key, name, kind in [('bus_budka', 'BUDKA', 'bus_stop'), ('football_pitch', 'Boisko', 'football_pitch')]:
    lx, ly = pre_expansion_i(*PRE_EXPANSION_ADDITIONS[key])
    if key == 'football_pitch':
        lx, ly = FOOTBALL_PITCH['cx'], FOOTBALL_PITCH['cy']
    lat, lon = to_latlon(lx, ly)
    add_landmark(key, name, lat, lon, kind)
for key, name, kind, (lx, ly) in [('jazz', 'JAZZ W STODOLE', 'jazz', (JAZZ['x'], JAZZ['y'])), ('wapnica', 'Wapnica', 'gravel', (PIT['cx'], PIT['cy'] + PIT['ry'] + 12))]:
    add_landmark(key, name, *to_latlon(lx, ly), kind)
# every wayside figure/cross gets a quiz board: shrine1..4 are the generated junction sprites, shrine5 the real Kapliczka
SHRINES = [dict(spot=f'shrine{i + 1}', kind=n, x=int(x), y=int(y)) for i, (n, x, y, _) in enumerate(GENERATED_SHRINES)]
_kap = next(l for l in landmarks if l['key'] == 'kapliczka')
SHRINES.append(dict(spot=f'shrine{len(SHRINES) + 1}', kind='kapliczka', x=_kap['x'], y=_kap['y']))
print('shrine boards', SHRINES)


def add_poi(key, lat, lon, **kw):
    x, y = P(lat, lon)
    if 20 < x < W - 20 and 50 < y < H - 20: pois.append(dict(key=key, x=round(x), y=round(y), **kw))
for e in nodes:
    t = e.get('tags', {})
    if t.get('man_made') == 'windmill': add_poi('windmill', e['lat'], e['lon'])
    if 'Sklep' in t.get('name', ''): add_poi('shop', e['lat'], e['lon'])
    if t.get('highway') == 'bus_stop': add_poi('bus', e['lat'], e['lon'], name=t.get('name'))
for e in ways:
    t = e['tags']
    if e['id'] in LANDMARK_IDS or t.get('amenity') == 'place_of_worship':
        b = e['bounds']; add_poi('church', (b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2)
    if t.get('landuse') == 'cemetery':
        b = e['bounds']; add_poi('cemetery', (b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2)
    if t.get('name') == 'Plebania':
        b = e['bounds']; add_poi('rectory', (b['minlat'] + b['maxlat']) / 2, (b['minlon'] + b['maxlon']) / 2)
# river poi at the bridge (road/river crossing)
add_poi('river', 52.2621, 22.8752)
# BUDKA remains a regular bus POI so existing game interaction works; the full
# named landmark record above preserves its requested preceding-map placement.
_budka_x, _budka_y = pre_expansion_i(*PRE_EXPANSION_ADDITIONS['bus_budka'])
pois.append(dict(key='bus', x=_budka_x, y=_budka_y, name='BUDKA'))

# 256-colour palette: pixel art survives it and the download shrinks several times
ground.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save('docs/img/map_ground.png', optimize=True)
objects_img.save('docs/img/map_objects.png')
low &= ~(pm | dm)   # roads and tracks cross the Białka on bridges: walkable, not a jump
collide &= ~(pm | dm)   # nothing solid on roads/tracks (woods and bridges included)
cm = np.where(collide, 255, np.where(low, 128, 0)).astype(np.uint8)
Image.fromarray(cm).save('docs/img/map_collide.png')   # 255 tall, 128 low (jumpable)
# terrain classes for walking speed, 1/4 scale: 0 grass, 60 paved road, 100 dirt road, 160 crop field, 220 forest floor
terr = np.zeros((H, W), np.uint8)
terr[forest_mask] = 220
terr[mask_of(classes.get('farmland', []))] = 160
terr[MEADOW['y0']:MEADOW['y1'], MEADOW['x0']:MEADOW['x1']] = 0
terr[dm] = 100; terr[pm] = 60
Image.fromarray(terr[2::4, 2::4]).save('docs/img/map_terrain.png', optimize=True)
shop = next((p for p in pois if p['key'] == 'shop'), dict(x=W // 2, y=H // 2))
# spawn: the walkable dirt-path pixel nearest to the spot just below the shop door (never inside a fenced garden)
cm_free = (cm == 0)
py_, px_ = np.nonzero(dm[shop['y']:shop['y'] + 200, shop['x'] - 150:shop['x'] + 150] & cm_free[shop['y']:shop['y'] + 200, shop['x'] - 150:shop['x'] + 150])
k_ = int(np.argmin((px_ - 150) ** 2 + (py_ - 60) ** 2)) if len(px_) else None
spawn = dict(x=int(shop['x'] - 150 + px_[k_]), y=int(shop['y'] + py_[k_])) if k_ is not None else dict(x=shop['x'], y=shop['y'] + 60)
# Sample standable banks alongside OSM water features, at roughly 40 px spacing.
water = []
def add_water_point(x, y):
    if len(water) >= 400: return
    x, y = int(round(x)), int(round(y))
    if not (8 <= x < W - 8 and 40 <= y < H - 8) or cm[y, x] != 0 or wm[y, x]: return
    if any((x - p['x']) ** 2 + (y - p['y']) ** 2 < 30 ** 2 for p in water): return
    water.append(dict(x=x, y=y))
for line, width in river_lines:
    for a_, b_ in zip(line, line[1:]):
        dx, dy = b_[0] - a_[0], b_[1] - a_[1]
        length = math.hypot(dx, dy)
        if length < 1: continue
        nx_, ny_ = -dy / length, dx / length
        for d_ in np.arange(20, length, 40):
            t_ = d_ / length; px_ = a_[0] + dx * t_; py_ = a_[1] + dy * t_
            for side_ in (-1, 1):
                for extra_ in (0, 10, 20, 30):
                    add_water_point(px_ + nx_ * side_ * (width / 2 + 4 + extra_), py_ + ny_ * side_ * (width / 2 + 4 + extra_))
                    if water and water[-1]['x'] == round(px_ + nx_ * side_ * (width / 2 + 4 + extra_)) and water[-1]['y'] == round(py_ + ny_ * side_ * (width / 2 + 4 + extra_)): break
for poly in ponds:
    center_ = np.mean(np.asarray(poly), axis=0)
    for a_, b_ in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b_[0] - a_[0], b_[1] - a_[1]; length = math.hypot(dx, dy)
        if length < 1: continue
        nx_, ny_ = -dy / length, dx / length
        mid_ = ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
        if (mid_[0] - center_[0]) * nx_ + (mid_[1] - center_[1]) * ny_ < 0: nx_, ny_ = -nx_, -ny_
        for d_ in np.arange(0, length, 40):
            t_ = d_ / length; px_ = a_[0] + dx * t_; py_ = a_[1] + dy * t_
            for extra_ in (4, 14, 24, 34):
                add_water_point(px_ + nx_ * extra_, py_ + ny_ * extra_)
                if water and math.hypot(water[-1]['x'] - (px_ + nx_ * extra_), water[-1]['y'] - (py_ + ny_ * extra_)) < 2: break
            if len(water) >= 400: break
        if len(water) >= 400: break
    if len(water) >= 400: break
water = water[:400]
json.dump(dict(w=W, h=H, scale=A, bbox=BBOX, objects=objects, bales=bales, water=water, pois=pois, landmarks=landmarks, track=TRACK, corral=CORRAL, meadow=MEADOW, range=RANGE, football_pitch=FOOTBALL_PITCH, jazz=JAZZ, gravel=GRAVEL, shrines=SHRINES, spawn=spawn, tree_stats=tree_stats, forest_tree_stats=forest_tree_stats,
               attribution='Map data © OpenStreetMap contributors (ODbL)'), open('docs/map.json', 'w'), indent=0)
print('tree types', tree_stats)
print(W, H, len(objects), 'objects', len(pois), 'pois', [p['key'] for p in pois], 'landmarks', [(p['key'], p['x'], p['y']) for p in landmarks])

# Keep full-map downloads small on every regeneration, with decoded-pixel
# equality checks before optimized files replace the renderer output.
from optimize_map_pngs import main as optimize_map_pngs
optimize_map_pngs()
