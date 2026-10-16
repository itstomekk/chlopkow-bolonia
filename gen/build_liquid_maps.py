"""Build the WOJNA PŁYNÓW (Liquid War minigame) levels from the game's own village map.

Reads docs/map.json (size, bbox, venue/POI anchors) and docs/img/map_collide.png (the exact mask the
game uses for walking: 255 = tall obstacle: houses, walls; 128 = low obstacle: fences, the river),
crops several windows of the village at different zoom levels, downsamples each to the 160x84 fighter
grid, and writes docs/data/liquid-maps.json:

  python gen/build_liquid_maps.py            # rewrite docs/data/liquid-maps.json
  python gen/build_liquid_maps.py --preview  # also write PNG previews to asset-review/2026-10-15-liquid/maps/

A cell is a wall when enough of its footprint is blocked in the collision mask; the threshold shrinks
with the cell size so that a thin fence still closes a gap at coarse zoom. Then:
  * the grid border is forced to wall,
  * only the largest connected open region is kept (tiny islands and pockets become wall), using
    the same movement rule as the game (8 directions, a diagonal step needs both side cells open),
  * four start areas (anchors) are picked in open space: the best-cleared cell near each corner zone.
Run it again after the village map changes; test/liquid_board_test.py checks the file still matches map.json.
Original Liquid War maps/graphics are NOT used (GPL): only this project's own map data.
"""
import json, os, sys
from collections import deque
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GW, GH = 160, 84

# id, PL name, EN name, zoom label, centre (world px: a POI from map.json or fixed), cell size in world px, wall threshold
LEVELS = [
    dict(id='village', pl='CAŁA WIEŚ', en='WHOLE VILLAGE', zoom='coarse', center=(1800, 4550), cell=20, thr=.10),
    dict(id='shop', pl='OKOLICE SKLEPU', en='AROUND THE SHOP', zoom='medium', poi='shop', shift=(0, 140), cell=8, thr=.20),
    dict(id='church', pl='KOŚCIÓŁ I PLEBANIA', en='CHURCH AND RECTORY', zoom='close', poi='church', shift=(0, -30), cell=4, thr=.30),
    dict(id='cemetery', pl='CMENTARZ', en='CEMETERY', zoom='close', poi='cemetery', shift=(0, 25), cell=5, thr=.28),
    dict(id='farmyard', pl='PODWÓRKA', en='FARMYARDS', zoom='close', center=(1000, 4200), cell=5, thr=.28),
]
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def components(open_):
    """Connected regions of open cells under the game rule. Returns (label array, sizes)."""
    lab = np.zeros(open_.shape, np.int32); sizes = [0]
    for sy, sx in zip(*np.nonzero(open_)):
        if lab[sy, sx]: continue
        n = len(sizes); sizes.append(0); lab[sy, sx] = n; q = deque([(sy, sx)])
        while q:
            y, x = q.popleft(); sizes[n] += 1
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < GW and 0 <= ny < GH) or not open_[ny, nx] or lab[ny, nx]: continue
                if dx and dy and not (open_[y, nx] and open_[ny, x]): continue
                lab[ny, nx] = n; q.append((ny, nx))
    return lab, sizes


def clearance(open_):
    """Chessboard distance of each open cell to the nearest wall (capped), by repeated erosion."""
    d = np.zeros(open_.shape, np.int32); cur = open_.copy(); k = 0
    while cur.any() and k < 12:
        d += cur; k += 1
        p = np.pad(cur, 1, constant_values=False)
        cur = cur & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:] & p[:-2, :-2] & p[:-2, 2:] & p[2:, :-2] & p[2:, 2:]
    return d


def pick_anchors(open_):
    clear = clearance(open_); ys, xs = np.nonzero(open_)
    zones = [(.18, .22), (.82, .78), (.82, .22), (.18, .78)]   # TL, BR, TR, BL: two teams face each other diagonally
    out = []
    for fx, fy in zones:
        tx, ty = fx * GW, fy * GH
        best = None
        for x, y in zip(xs, ys):
            if any((x - ax) ** 2 + (y - ay) ** 2 < 40 ** 2 for ax, ay in out): continue
            d = ((x - tx) ** 2 + (y - ty) ** 2) ** .5
            if d > 34: continue
            s = min(int(clear[y, x]), 7) * 5 - d * .5
            if best is None or s > best[0]: best = (s, int(x), int(y))
        if best is None: return None
        out.append([best[1], best[2]])
    return out


def build(level, collide, poi):
    if 'poi' in level:
        cx, cy = poi[level['poi']]; sx, sy = level.get('shift', (0, 0)); cx += sx; cy += sy
    else:
        cx, cy = level['center']
    k = level['cell']; x0 = int(round(cx - GW * k / 2)); y0 = int(round(cy - GH * k / 2))
    H, W = collide.shape
    x0 = max(0, min(W - GW * k, x0)); y0 = max(0, min(H - GH * k, y0))   # keep the window inside the map
    sub = collide[y0:y0 + GH * k, x0:x0 + GW * k] > 64
    frac = sub.reshape(GH, k, GW, k).mean(axis=(1, 3))
    open_ = frac < level['thr']
    open_[0, :] = open_[-1, :] = open_[:, 0] = open_[:, -1] = False
    lab, sizes = components(open_)
    main = int(np.argmax(sizes[1:])) + 1 if len(sizes) > 1 else 0
    open_ = lab == main
    anchors = pick_anchors(open_)
    if anchors is None: raise SystemExit(f"level {level['id']}: no room for four start areas")
    rows = [''.join('.' if open_[y, x] else '#' for x in range(GW)) for y in range(GH)]
    return dict(id=level['id'], name=dict(pl=level['pl'], en=level['en']), zoom=level['zoom'], cell=k, origin=[x0, y0], center=[int(cx), int(cy)],
                open=int(open_.sum()), anchors=anchors, rows=rows), open_


def main():
    m = json.load(open(os.path.join(ROOT, 'docs/map.json'), encoding='utf-8'))
    collide = np.array(Image.open(os.path.join(ROOT, 'docs/img/map_collide.png')))
    assert collide.shape == (m['h'], m['w']), 'map_collide.png and map.json disagree on the map size'
    poi = {p['key']: (p['x'], p['y']) for p in m['pois']}
    levels, masks = [], []
    for lv in LEVELS:
        l, o = build(lv, collide, poi); levels.append(l); masks.append(o)
        print(f"{l['id']:9s} cell {l['cell']:2d} px  origin {l['origin']}  open {l['open']:5d}/{GW * GH}  anchors {l['anchors']}")
    doc = dict(version=1, generator='gen/build_liquid_maps.py', grid=dict(w=GW, h=GH),
               source=dict(w=m['w'], h=m['h'], bbox=m['bbox'], scale=m['scale'], mask='img/map_collide.png: >64 = wall'), levels=levels)
    out = os.path.join(ROOT, 'docs/data/liquid-maps.json')
    with open(out, 'w', encoding='utf-8', newline='\n') as f: json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
    print('wrote', out, os.path.getsize(out), 'bytes')
    if '--preview' in sys.argv:
        pv = os.path.join(ROOT, 'asset-review/2026-10-15-liquid/maps'); os.makedirs(pv, exist_ok=True)
        ground = Image.open(os.path.join(ROOT, 'docs/img/map_ground.png')).convert('RGB')
        for l, o in zip(levels, masks):
            k = l['cell']; x0, y0 = l['origin']; S = 5
            g = ground.crop((x0, y0, x0 + GW * k, y0 + GH * k)).resize((GW * S, GH * S))
            a = np.array(Image.fromarray(np.where(o, 0, 255).astype('uint8')).resize((GW * S, GH * S), Image.NEAREST))
            rgb = np.array(g); rgb[a > 0] = (rgb[a > 0] * .35 + np.array([200, 40, 40]) * .65).astype('uint8')
            for ax, ay in l['anchors']:
                rgb[ay * S - 4:ay * S + 5, ax * S - 4:ax * S + 5] = (255, 255, 0)
            Image.fromarray(rgb).save(os.path.join(pv, f"{l['id']}.png"))


if __name__ == '__main__':
    main()
