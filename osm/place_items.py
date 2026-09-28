"""Place NPCs, collectibles and quiz signboards on walkable, sensible spots -> docs/items.json.

Run after osm/render_map.py. Hand-tuned spots use legacy_i() (see osm/geo.py), so they stay on
the same real-world place when the map is resized. Deterministic (fixed seed).
"""
import json, math, random, sys
import numpy as np
from PIL import Image
sys.path.insert(0, 'osm')
from geo import legacy_i, P

m = json.load(open('docs/map.json'))
W, H = m['w'], m['h']
from scipy import ndimage
cmask = np.array(Image.open('docs/img/map_collide.png').convert('L'))
solid = cmask > 127
ground = np.array(Image.open('docs/img/map_ground.png').convert('RGB')).astype(int)
rnd = random.Random(3)

# Reachability on foot (no jumping — fences count as walls): flood fill from the spawn with Arek's
# 14x6 px foot box on a 4 px grid. Everything placed below must be inside this region.
C = 4
foot = ndimage.binary_dilation(cmask > 64, structure=np.ones((7, 15), bool))
hh, ww = H // C, W // C
passable = (~foot[:hh * C, :ww * C]).reshape(hh, C, ww, C).any(axis=(1, 3))   # a cell is walkable if any pixel in it is
lab, _ = ndimage.label(passable)
reach = lab == lab[m['spawn']['y'] // C, m['spawn']['x'] // C]
assert reach.sum() > .3 * reach.size, 'spawn is boxed in'


def free(x, y, r=10):
    x, y = int(x), int(y)
    if x < r or y < 40 or x >= W - r or y >= H - r: return False
    return reach[min(hh - 1, y // C), min(ww - 1, x // C)] and not solid[y - r:y + 3, x - r:x + r].any()


def near_free(x, y, r=10):
    for rad in range(0, 200, 3):
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            px, py = x + math.cos(a) * rad, y + math.sin(a) * rad
            if free(px, py, r): return round(px), round(py)
    return round(x), round(y)


def at(x, y, r=10):
    px, py = near_free(x, y, r); return dict(x=px, y=py)


landmarks = []
for lm in m.get('landmarks', []):
    ax, ay = near_free(lm['x'], lm['y'], r=8)
    assert free(ax, ay, 8), f"{lm['key']} has no reachable access point"
    landmarks.append(dict(lm, access=dict(x=ax, y=ay)))


poi = {p['key']: p for p in m['pois']}
shop = poi['shop']
bus = [p for p in m['pois'] if p['key'] == 'bus']
bus_near = min(bus, key=lambda p: math.hypot(p['x'] - shop['x'], p['y'] - shop['y']))
bus_far = max(bus, key=lambda p: math.hypot(p['x'] - shop['x'], p['y'] - shop['y']))

# ---------------------------------------------------------------- quiz signboards (one per question spot, see docs/js/quiz.js)
road = (ground[..., 0] < 100) & (ground[..., 1] < 100) & (ground[..., 2] < 110) & (np.abs(ground[..., 0] - ground[..., 2]) < 12)
ry, rx = np.nonzero(road[:, W - 140:W - 60]); er = (W - 100, int(np.median(ry))) if len(ry) else (W - 100, H // 2)
anchors = {
    'church': (poi['church']['x'] - 70, poi['church']['y'] + 40), 'rectory': (poi['rectory']['x'] - 30, poi['rectory']['y'] + 40),
    'cemetery': (poi['cemetery']['x'], poi['cemetery']['y'] + 90), 'windmill': (poi['windmill']['x'] - 60, poi['windmill']['y'] + 40),
    'shop': (shop['x'] - 45, shop['y'] + 30), 'bus1': (bus_near['x'] - 25, bus_near['y'] + 12),
    'bus2': (bus_far['x'] + 30, bus_far['y'] - 20), 'river': legacy_i(1300, 1650), 'pitch': legacy_i(690, 120),
    'orchard': legacy_i(1300, 2020), 'woods': legacy_i(1760, 1600), 'eastroad': (er[0], er[1] - 26),
}
boards = []
for k, v in anchors.items():
    p = at(*v, r=8); boards.append(dict(spot=k, **p))

# ---------------------------------------------------------------- NPCs
woods = next(b for b in boards if b['spot'] == 'woods')
npcs = [
    dict(id='kasia', **at(*P(52.26261, 22.88575))),          # far east, by a Chłopków-Kolonia farmstead
    dict(id='marcin', **at(bus_near['x'] + 25, bus_near['y'] + 10)),
    dict(id='damian', **at(*P(52.25980, 22.86990))),          # far south, farmstead by the shooting range
    dict(id='grandpa', **at(poi['windmill']['x'] + 60, poi['windmill']['y'] + 40)),
    dict(id='halina', **at(poi['church']['x'] - 120, poi['church']['y'] + 70)),   # the chronicler waits by the church
    # hidden Sołtys by the Białka, next to (not on top of) the woods signboard: NPCs win interaction priority
    dict(id='soltys', secret=True, **at(woods['x'] - 70, woods['y'] + 30)),
]
for n in npcs:
    for b in boards:
        assert math.hypot(n['x'] - b['x'], n['y'] - b['y']) > 45, f"{n['id']} blocks the {b['spot']} signboard"

# ---------------------------------------------------------------- apples: next to tree trunks, spread over the village
trees = [o for o in m['objects'] if o['w'] < 34]
oc = legacy_i(1343, 2171)
orchard = [t for t in trees if abs(t['x'] - oc[0]) < 90 and abs(t['base'] - oc[1]) < 260]
street = [t for t in trees if t not in orchard and abs(t['base'] - (shop['y'] + 150)) < 450]
outer = [t for t in trees if t not in orchard and t not in street]
apples = []


def add_apples(pool, n):
    rnd.shuffle(pool); got = 0
    for t in pool:
        if got >= n: break
        cx = t['x'] + t['w'] / 2 + rnd.choice([-1, 1]) * rnd.uniform(9, 16); cy = t['base'] + rnd.uniform(2, 10)
        if free(cx, cy, 4) and all(math.hypot(cx - a['x'], cy - a['y']) > 90 for a in apples):
            apples.append(dict(x=round(cx), y=round(cy))); got += 1


add_apples(orchard, 6); add_apples(street, 6); add_apples(outer, 4)

# ---------------------------------------------------------------- Damian's cap: in a yellow wheat field, away from the shop
ys, xs = np.nonzero((ground[..., 0] > 190) & (ground[..., 1] > 150) & (ground[..., 2] < 110) & ~solid)
dam = next(n for n in npcs if n['id'] == 'damian')   # "I was running through the wheat" -> within ~150-450 m of Damian
cands = [(x, y) for x, y in zip(xs[::200], ys[::200]) if 300 < math.hypot(x - dam['x'], y - dam['y']) < 900 and free(x, y, 12)]
cap = dict(zip('xy', map(int, rnd.choice(cands))))

json.dump(dict(npcs=npcs, apples=apples, cap=cap, boards=boards, landmarks=landmarks), open('docs/items.json', 'w'), indent=1)
print(f'reachable {reach.mean():.0%} of map |', len(apples), 'apples |', ', '.join(f"{n['id']}@{n['x']},{n['y']}" for n in npcs), '| cap', cap,
      '| landmarks', ', '.join(f"{lm['key']}->{lm['access']['x']},{lm['access']['y']}" for lm in landmarks))
