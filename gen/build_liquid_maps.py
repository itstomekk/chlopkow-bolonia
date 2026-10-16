"""Build the WOJNA PŁYNÓW (Liquid War minigame) levels from the game's own village map.

Reads docs/map.json (size, bbox, POI anchors), docs/img/map_collide.png (the exact mask the game
walks by: 255 = tall obstacle: houses, walls, water; 128 = low obstacle: fences, river banks) and
docs/img/map_terrain.png (1/4 scale: 0 grass, 60 paved, 100 dirt road, 160 field, 220 forest), crops
many windows of the village at different zooms, downsamples each to the 320x168 fighter grid, and
writes docs/data/liquid-maps.json:

  python gen/build_liquid_maps.py            # rewrite docs/data/liquid-maps.json
  python gen/build_liquid_maps.py --explore  # report levels that fail the bounds instead of stopping (tuning aid)
  python gen/build_liquid_maps.py --preview  # also write PNG previews + a contact sheet to asset-review/2026-10-15-liquid-v2/maps/

A cell is a wall when enough of its footprint is blocked in the collision mask (the threshold shrinks
with the cell size so a thin fence still closes a gap at coarse zoom). A level may also turn terrain classes into walls:
`forest` (220: the wood is a thicket), `field` (160: crop fields), `track` (100: dirt roads); `grow` fattens walls by n cells. Then:
  * the grid border is forced to wall,
  * only the largest connected open region is kept (tiny islands and pockets become wall), using
    the same movement rule as the game (8 directions, a diagonal step needs both side cells open),
  * four start areas (anchors) are picked in open space far from each other,
  * the open share must be inside OPEN_MIN..OPEN_MAX (no near-empty or near-solid level): the build
    fails loudly otherwise.
The rows are run-length encoded (see encode()): the file stays small and docs/js/boards/liquid.js
decodes it lazily. Run it again after the village map changes; test/liquid_board_test.py checks the
file against map.json and the mask. Original Liquid War maps/graphics are NOT used (GPL): only this
project's own map data.
"""
import json, math, os, sys
from collections import deque
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GW, GH = 320, 168
OPEN_MIN, OPEN_MAX = .35, .92      # share of open cells in the whole grid (enforced here and in the test)
MIN_SEP = 64                        # start areas are at least this many cells apart (straight line) ...
MIN_WALK = 60                       # ... and this many steps apart by walking around the walls
MIN_CLEAR = 4                       # a start area has a free (2*MIN_CLEAR-1) square around it: never inside a tiny pocket

# Each level: id, PL name, EN name, zoom label, centre (world px: `center`, a POI key from map.json, or `poi_xy` = a map.json
# entry with x/y), cell size in world px (1 cell = cell x cell map pixels), wall threshold (share of blocked pixels), optional layers.
FF = ['field', 'forest']
LEVELS = [
    dict(id='village', pl='CAŁA WIEŚ', en='WHOLE VILLAGE', zoom='far', center=(2560, 4700), cell=16, thr=.08, layers=FF),
    dict(id='street', pl='GŁÓWNA ULICA', en='MAIN STREET', zoom='medium', center=(1500, 4120), cell=6, thr=.22, layers=FF),
    dict(id='shop', pl='OKOLICE SKLEPU', en='AROUND THE SHOP', zoom='medium', poi='shop', shift=(0, 140), cell=5, thr=.22, layers=['field']),
    dict(id='church', pl='KOŚCIÓŁ I PLEBANIA', en='CHURCH AND RECTORY', zoom='close', poi='church', shift=(0, -30), cell=3, thr=.30, layers=FF),
    dict(id='cemetery', pl='CMENTARZ', en='CEMETERY', zoom='medium', poi='cemetery', shift=(0, 25), cell=5, thr=.25, layers=['field']),
    dict(id='farmyard', pl='PODWÓRKA', en='FARMYARDS', zoom='close', center=(1000, 4200), cell=3, thr=.28, layers=FF),
    dict(id='pond', pl='STAW', en='THE POND', zoom='medium', center=(4500, 4000), cell=6, thr=.20, layers=FF),
    dict(id='river', pl='MELIORANKA', en='MELIORANKA RIVER', zoom='close', poi='river', cell=4, thr=.25, layers=FF),
    dict(id='forest', pl='SKRAJ LASU', en='FOREST EDGE', zoom='medium', center=(2500, 6000), cell=6, thr=.25, layers=FF),
    dict(id='pitch', pl='BOISKO I ŚWIETLICA', en='PITCH AND COMMUNITY HALL', zoom='close', center=(2420, 4680), cell=4, thr=.26, layers=FF),
    dict(id='kolonia', pl='CHŁOPKÓW-KOLONIA', en='CHŁOPKÓW-KOLONIA', zoom='medium', center=(4800, 5500), cell=5, thr=.22, layers=FF),
    dict(id='barn', pl='JAZZ W STODOLE', en='JAZZ IN THE BARN', zoom='medium', center=(2892, 1758), cell=5, thr=.25, layers=['forest']),
]
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def components(open_):
    """Connected regions of open cells under the game rule. Returns (label array, sizes)."""
    lab = np.zeros(open_.shape, np.int32); sizes = [0]
    h, w = open_.shape
    for sy, sx in zip(*np.nonzero(open_)):
        if lab[sy, sx]: continue
        n = len(sizes); sizes.append(0); lab[sy, sx] = n; q = deque([(sy, sx)])
        while q:
            y, x = q.popleft(); sizes[n] += 1
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or not open_[ny, nx] or lab[ny, nx]: continue
                if dx and dy and not (open_[y, nx] and open_[ny, x]): continue
                lab[ny, nx] = n; q.append((ny, nx))
    return lab, sizes


def clearance(open_, cap=16):
    """Chessboard distance of each open cell to the nearest wall (capped), by repeated erosion."""
    d = np.zeros(open_.shape, np.int32); cur = open_.copy(); k = 0
    while cur.any() and k < cap:
        d += cur; k += 1
        p = np.pad(cur, 1, constant_values=False)
        cur = cur & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] & p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return d


def pick_anchors(open_):
    """Four start areas: the best-cleared cell near each corner zone, far from the others (TL, BR, TR, BL: two teams face each other diagonally)."""
    clear = clearance(open_); ys, xs = np.nonzero(open_)
    zones = [(.17, .22), (.83, .78), (.83, .22), (.17, .78)]
    for radius in (60, 80, 110, 150):
        out = []
        for fx, fy in zones:
            tx, ty = fx * GW, fy * GH; best = None
            for x, y in zip(xs, ys):
                if clear[y, x] < MIN_CLEAR or any((x - ax) ** 2 + (y - ay) ** 2 < MIN_SEP ** 2 for ax, ay in out): continue
                d = math.hypot(x - tx, y - ty)
                if d > radius: continue
                s = min(int(clear[y, x]), 9) * 5 - d * .4
                if best is None or s > best[0]: best = (s, int(x), int(y))
            if best is None: break
            out.append([best[1], best[2]])
        if len(out) == 4: return out
    return None


def walk_dist(open_, src):
    """Steps from src to every open cell under the game's movement rule (-1 = unreachable)."""
    dist = np.full(open_.shape, -1, np.int32); sx, sy = src; dist[sy, sx] = 0; q = deque([(sx, sy)])
    while q:
        x, y = q.popleft()
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not open_[ny, nx] or dist[ny, nx] >= 0: continue
            if dx and dy and not (open_[y, nx] and open_[ny, x]): continue
            dist[ny, nx] = dist[y, x] + 1; q.append((nx, ny))
    return dist


def min_walk(open_, anchors):
    ds = [walk_dist(open_, tuple(a)) for a in anchors]
    return min(int(ds[i][anchors[j][1], anchors[j][0]]) for i in range(len(anchors)) for j in range(i + 1, len(anchors)))


B36 = '0123456789abcdefghijklmnopqrstuvwxyz'


def encode(open_):
    """Run-length rows: each row is the list of alternating run lengths, starting with a WALL run (may be 0), written in base 36
    and joined with ','. Rows are joined with ';'. The client decodes it into a Uint8Array (see liquid.js decodeRle)."""
    def b36(n):
        s = ''
        while True:
            n, r = divmod(n, 36); s = B36[r] + s
            if not n: return s
    rows = []
    for y in range(open_.shape[0]):
        runs = []; cur = False; n = 0
        for v in open_[y]:
            if bool(v) == cur: n += 1
            else: runs.append(n); cur = bool(v); n = 1
        runs.append(n)
        rows.append(','.join(b36(r) for r in runs))
    return ';'.join(rows)


def decode(s):
    out = np.zeros((GH, GW), bool)
    for y, row in enumerate(s.split(';')):
        x = 0; cur = False
        for r in row.split(','):
            n = int(r, 36)
            if cur: out[y, x:x + n] = True
            x += n; cur = not cur
        assert x == GW, (y, x)
    return out


def window(level, mp, poi, shape):
    """Top-left corner and centre of a level's crop window in map pixels, clamped to the map."""
    if 'center' in level: cx, cy = level['center']
    elif 'poi_xy' in level: cx, cy = mp[level['poi_xy']]['x'], mp[level['poi_xy']]['y']
    elif 'poi' in level: cx, cy = poi[level['poi']]
    else: raise SystemExit(f"level {level['id']}: no centre")
    sx, sy = level.get('shift', (0, 0)); cx += sx; cy += sy
    k = level['cell']; H, W = shape
    x0 = int(round(cx - GW * k / 2)); y0 = int(round(cy - GH * k / 2))
    x0 = max(0, min(W - GW * k, x0)); y0 = max(0, min(H - GH * k, y0))
    return x0, y0, int(cx), int(cy)


TERRAIN_WALL = {'forest': 220, 'field': 160, 'track': 100}   # terrain classes a level may turn into walls


def grow(wall, n):
    """Fatten walls by n cells (8-neighbourhood): chunkier houses at close zoom."""
    for _ in range(n):
        p = np.pad(wall, 1, constant_values=False)
        wall = wall | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return wall


def walls(level, collide, terrain, x0, y0, objects=None):
    k = level['cell']
    sub = collide[y0:y0 + GH * k, x0:x0 + GW * k] > 64
    frac = sub.reshape(GH, k, GW, k).mean(axis=(1, 3))
    wall = grow(frac >= level['thr'], level.get('grow', 0))
    ts = collide.shape[1] / terrain.shape[1]            # terrain is 1/4 scale
    yy = ((y0 + np.arange(GH * k)) / ts).astype(int).clip(0, terrain.shape[0] - 1)
    xx = ((x0 + np.arange(GW * k)) / ts).astype(int).clip(0, terrain.shape[1] - 1)
    tw = terrain[np.ix_(yy, xx)]
    if 'objects' in level.get('layers', []):               # trees, graves, props, buildings drawn in map_objects.png (alpha > 128)
        a = np.array(objects.crop((x0, y0, x0 + GW * k, y0 + GH * k)).getchannel('A')) > 128
        wall |= a.reshape(GH, k, GW, k).mean(axis=(1, 3)) >= level.get('othr', .35)
    for name in [n for n in level.get('layers', []) if n in TERRAIN_WALL]:
        share = (tw == TERRAIN_WALL[name]).reshape(GH, k, GW, k).mean(axis=(1, 3))
        wall |= share >= level.get('tthr', .5)
    return despeckle(wall, level.get('speck', 6))


def despeckle(wall, n):
    """Wall blobs smaller than n cells (single posts, fence stubs) become open: the arena stays readable."""
    h, w = wall.shape; seen = np.zeros(wall.shape, bool)
    for sy, sx in zip(*np.nonzero(wall)):
        if seen[sy, sx]: continue
        seen[sy, sx] = True; q = deque([(sy, sx)]); cells = [(sy, sx)]
        while q:
            y, x = q.popleft()
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and wall[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx)); cells.append((ny, nx))
        if len(cells) < n:
            for y, x in cells: wall[y, x] = False
    return wall


def build(level, collide, terrain, mp, poi, objects=None):
    x0, y0, cx, cy = window(level, mp, poi, collide.shape)
    open_ = ~walls(level, collide, terrain, x0, y0, objects)
    open_[0, :] = open_[-1, :] = open_[:, 0] = open_[:, -1] = False
    lab, sizes = components(open_)
    main = int(np.argmax(sizes[1:])) + 1 if len(sizes) > 1 else 0
    open_ = lab == main
    share = open_.mean()
    if not OPEN_MIN <= share <= OPEN_MAX: raise SystemExit(f"level {level['id']}: open share {share:.0%} outside {OPEN_MIN:.0%}..{OPEN_MAX:.0%} (change the window or threshold)")
    anchors = pick_anchors(open_)
    if anchors is None: raise SystemExit(f"level {level['id']}: no room for four start areas")
    if min_walk(open_, anchors) < MIN_WALK: raise SystemExit(f"level {level['id']}: start areas are closer than {MIN_WALK} steps by walking")
    return dict(id=level['id'], name=dict(pl=level['pl'], en=level['en']), zoom=level['zoom'], cell=level['cell'], origin=[x0, y0], center=[cx, cy],
                layers=['collide'] + level.get('layers', []), thr=level['thr'], open=int(open_.sum()), anchors=anchors, rle=encode(open_)), open_


def main():
    m = json.load(open(os.path.join(ROOT, 'docs/map.json'), encoding='utf-8'))
    collide = np.array(Image.open(os.path.join(ROOT, 'docs/img/map_collide.png')))
    terrain = np.array(Image.open(os.path.join(ROOT, 'docs/img/map_terrain.png')))
    assert collide.shape == (m['h'], m['w']), 'map_collide.png and map.json disagree on the map size'
    objects = Image.open(os.path.join(ROOT, 'docs/img/map_objects.png'))
    poi = {}
    for p in m['pois']: poi.setdefault(p['key'], (p['x'], p['y']))
    levels, masks = [], []
    for lv in LEVELS:
        try: l, o = build(lv, collide, terrain, m, poi, objects)
        except SystemExit as e:
            if '--explore' in sys.argv: print('SKIP', e); continue
            raise
        levels.append(l); masks.append(o)
        assert (decode(l['rle']) == o).all(), 'RLE round trip'
        print(f"{l['id']:9s} cell {l['cell']:2d} px  origin {l['origin']}  open {l['open']:5d}/{GW * GH} ({o.mean():.0%})  anchors {l['anchors']}")
    doc = dict(version=2, generator='gen/build_liquid_maps.py', grid=dict(w=GW, h=GH), open_bounds=[OPEN_MIN, OPEN_MAX], min_sep=MIN_SEP, min_walk=MIN_WALK, min_clear=MIN_CLEAR,
               source=dict(w=m['w'], h=m['h'], bbox=m['bbox'], scale=m['scale'], mask='img/map_collide.png: >64 = wall; terrain layers: img/map_terrain.png 220 forest, 160 field, 100 track'), levels=levels)
    out = os.path.join(ROOT, 'docs/data/liquid-maps.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f: json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    print('wrote', out, os.path.getsize(out), 'bytes')
    if '--preview' in sys.argv:
        pv = os.path.join(ROOT, 'asset-review/2026-10-15-liquid-v2/maps'); os.makedirs(pv, exist_ok=True)
        ground = Image.open(os.path.join(ROOT, 'docs/img/map_ground.png')).convert('RGB')
        tiles = []
        for l, o in zip(levels, masks):
            k = l['cell']; x0, y0 = l['origin']; S = 3
            g = ground.crop((x0, y0, x0 + GW * k, y0 + GH * k)).resize((GW * S, GH * S))
            a = np.array(Image.fromarray(np.where(o, 0, 255).astype('uint8')).resize((GW * S, GH * S), Image.NEAREST))
            rgb = np.array(g); rgb[a > 0] = (rgb[a > 0] * .35 + np.array([200, 40, 40]) * .65).astype('uint8')
            for ax, ay in l['anchors']:
                rgb[ay * S - 4:ay * S + 5, ax * S - 4:ax * S + 5] = (255, 255, 0)
            im = Image.fromarray(rgb); im.save(os.path.join(pv, f"{l['id']}.png")); tiles.append(im.resize((GW * 2, GH * 2)))
        cols = 3; rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * GW * 2, rows * GH * 2))
        for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * GW * 2, (i // cols) * GH * 2))
        sheet.save(os.path.join(pv, 'contact-sheet.png'))


if __name__ == '__main__':
    main()
