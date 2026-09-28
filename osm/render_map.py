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
from geo import A, BBOX, W, H, P, legacy_i
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
    m = mask_of([p]); fill(m, '#4fae4a', '#45a042', seed=41)
    im_ = Image.fromarray(g.clip(0, 255).astype(np.uint8)); d_ = ImageDraw.Draw(im_); d_.polygon(p, outline=(240, 240, 235)); g = np.array(im_).astype(np.float32)

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
# Positions were tuned on the first map; legacy_i() keeps them on the same real-world spot.
_tc = legacy_i(1080, 300); TRACK = dict(cx=_tc[0], cy=_tc[1], rx=300, ry=150, w=44)
_cc = legacy_i(1490, 565); CORRAL = dict(cx=_cc[0], cy=_cc[1], r=100)
# dog meadow: open grass between the street and the Białka
_m0, _m1 = legacy_i(680, 1060), legacy_i(1100, 1330); MEADOW = dict(x0=_m0[0], y0=_m0[1], x1=_m1[0], y1=_m1[1])
_rc = tuple(int(v) for v in P(52.26016, 22.87064)); RANGE = dict(x=_rc[0], y=_rc[1])   # shooting range: open wheat by Damian's farmstead (south)


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
bales = 0
def bale(x, y):
    gd.ellipse([x - 11, y - 2, x + 13, y + 5], fill=(96, 84, 40))
    od.rectangle([x - 11, y - 16, x + 11, y + 1], fill=(206, 168, 80), outline=(112, 84, 36))
    od.ellipse([x - 11, y - 20, x + 11, y - 12], fill=(226, 192, 104), outline=(112, 84, 36))
    od.ellipse([x - 6, y - 18, x + 6, y - 14], outline=(180, 142, 64))
    for yy_ in (y - 9, y - 4): od.line([(x - 10, yy_), (x + 10, yy_)], fill=(186, 150, 70))
    objects.append(dict(x=x - 13, y=y - 22, w=27, h=26, base=float(y + 2)))
    low[y - 6:y + 2, x - 11:x + 12] = True
for x_, y_ in TRACK_BALES: bale(x_, y_)
for p_ in classes.get('farmland', []):
    ox_, oy_, m_ = mask_win(p_)
    if not m_.size: continue
    ys_, xs_ = np.nonzero(m_ & ~occupied[oy_:oy_ + m_.shape[0], ox_:ox_ + m_.shape[1]]); ys_ = ys_ + oy_; xs_ = xs_ + ox_
    if len(xs_) < 4000: continue
    for _ in range(3):
        i_ = rnd.randrange(len(xs_)); x, y = int(xs_[i_]), int(ys_[i_])
        if not (20 < x < W - 20 and 60 < y < H - 20): continue
        bale(x, y); bales += 1
print('hay bales', bales)

# ---------------------------------------------------------------- landmark sprites
LM_SIZE = {'church': 150, 'windmill': 84, 'shop': 100}   # sprite width in art px
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
             ((MEADOW['x0'] + MEADOW['x1']) / 2, (MEADOW['y0'] + MEADOW['y1']) / 2), (RANGE['x'], RANGE['y'])]
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


def tree(x, y, r, dark=False):
    x, y, r = int(x), int(y), int(r)
    gd.ellipse([x - r * .9, y - 3, x + r * .9, y + 4], fill=(52, 80, 36))
    od.rectangle([x - 2, y - r * .7, x + 2, y], fill=(98, 66, 40), outline=(58, 38, 24))
    base = hexc('#2e7a33') if not dark else hexc('#276a2c')
    cy = y - r * 1.25
    od.ellipse([x - r, cy - r, x + r, cy + r], fill=shade(base, .75), outline=(24, 52, 26))
    od.ellipse([x - r * .85, cy - r * .95, x + r * .7, cy + r * .6], fill=base)
    od.ellipse([x - r * .6, cy - r * .8, x + r * .15, cy - r * .1], fill=shade(base, 1.35))
    for _ in range(4):
        px, py = x + rnd.uniform(-r * .6, r * .5), cy + rnd.uniform(-r * .7, r * .5)
        od.point((px, py), fill=shade(base, 1.6))
    objects.append(dict(x=x - r - 2, y=int(cy - r) - 2, w=2 * r + 4, h=int(y - cy + r) + 6, base=float(y)))
    collide[max(0, y - 3):y + 1, max(0, x - 3):x + 4] = True


res_mask = mask_of(classes.get('residential', []) + classes.get('religious', []) + classes.get('cemetery', []))
forest_mask = mask_of(classes.get('forest', []) + classes.get('wood', []))
orch = classes.get('orchard', [])
tree_pts = []
# residential gardens
for _ in range(9000):
    x, y = rnd.uniform(8, W - 8), rnd.uniform(20, H - 4)
    xi, yi = int(x), int(y)
    if res_mask[yi, xi] and not occ_d[yi, xi] and rnd.random() < .35: tree_pts.append((x, y, rnd.uniform(8, 13), False))
# river banks
for l, w in river_lines:
    for a_, b_ in zip(l, l[1:]):
        L = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
        for k in range(int(L // 26)):
            t_ = rnd.random(); side = rnd.choice([-1, 1])
            ex, ey = (b_[0] - a_[0]) / L, (b_[1] - a_[1]) / L
            x, y = a_[0] + (b_[0] - a_[0]) * t_ - ey * side * (w / 2 + 12), a_[1] + (b_[1] - a_[1]) * t_ + ex * side * (w / 2 + 12)
            if 0 < x < W and 20 < y < H and not occ_d[int(y), int(x)] and rnd.random() < .55: tree_pts.append((x, y, rnd.uniform(10, 15), False))
# orchards
for p in orch:
    m = mask_of([p]); arr = np.array(p); x0, y0 = arr.min(0); x1, y1 = arr.max(0)
    for y in np.arange(y0 + 10, y1, 22):
        for x in np.arange(x0 + 10, x1, 22):
            if m[int(y), int(x)] and not occ_d[int(y), int(x)]: tree_pts.append((x, y, 8, False))
# thin out overlaps
tree_pts.sort(key=lambda t: t[1]); kept = []
for t_ in tree_pts:
    if all(math.hypot(t_[0] - k_[0], t_[1] - k_[1]) > (t_[2] + k_[2]) * .9 for k_ in kept[-60:]): kept.append(t_)
for x, y, r, dk in kept: tree(x, y, r, dk)

# forests: dense canopy drawn on ground layer, solid
fy, fx = np.nonzero(forest_mask)
collide |= forest_mask
g2 = np.array(ground).astype(np.float32); g2[forest_mask] = hexc('#1f4f24'); ground = Image.fromarray(g2.astype(np.uint8)); gd = ImageDraw.Draw(ground)
cand = list(zip(fx[::37], fy[::37])); rnd.shuffle(cand); cand = sorted(cand[:2600], key=lambda v: v[1])
for x, y in cand:
    r = rnd.uniform(7, 12); base = hexc(rnd.choice(['#2c6e30', '#2a6430', '#357a38', '#24592a']))
    gd.ellipse([x - r, y - r, x + r, y + r], fill=shade(base, .75), outline=(20, 44, 22))
    gd.ellipse([x - r * .8, y - r * .9, x + r * .6, y + r * .5], fill=base)
    gd.ellipse([x - r * .55, y - r * .75, x + r * .1, y - r * .15], fill=shade(base, 1.3))

# ---------------------------------------------------------------- POIs + landmark placeholders
pois = []
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

# 256-colour palette: pixel art survives it and the download shrinks several times
ground.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save('docs/img/map_ground.png', optimize=True)
objects_img.save('docs/img/map_objects.png')
low &= ~(pm | dm)   # roads and tracks cross the Białka on bridges: walkable, not a jump
collide &= ~(pm | dm)   # nothing solid on roads/tracks (woods and bridges included)
cm = np.where(collide, 255, np.where(low, 128, 0)).astype(np.uint8)
Image.fromarray(cm).save('docs/img/map_collide.png')   # 255 tall, 128 low (jumpable)
shop = next((p for p in pois if p['key'] == 'shop'), dict(x=W // 2, y=H // 2))
# spawn: the walkable dirt-path pixel nearest to the spot just below the shop door (never inside a fenced garden)
cm_free = (cm == 0)
py_, px_ = np.nonzero(dm[shop['y']:shop['y'] + 200, shop['x'] - 150:shop['x'] + 150] & cm_free[shop['y']:shop['y'] + 200, shop['x'] - 150:shop['x'] + 150])
k_ = int(np.argmin((px_ - 150) ** 2 + (py_ - 60) ** 2)) if len(px_) else None
spawn = dict(x=int(shop['x'] - 150 + px_[k_]), y=int(shop['y'] + py_[k_])) if k_ is not None else dict(x=shop['x'], y=shop['y'] + 60)
json.dump(dict(w=W, h=H, scale=A, bbox=BBOX, objects=objects, pois=pois, track=TRACK, corral=CORRAL, meadow=MEADOW, range=RANGE, spawn=spawn,
               attribution='Map data © OpenStreetMap contributors (ODbL)'), open('docs/map.json', 'w'), indent=0)
print(W, H, len(objects), 'objects', len(pois), 'pois', [p['key'] for p in pois])
