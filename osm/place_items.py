"""Place NPCs, collectibles and quiz signboards on walkable, sensible spots -> docs/items.json.

Run after osm/render_map.py. Hand-tuned spots use legacy_i() (see osm/geo.py), so they stay on
the same real-world place when the map is resized. Deterministic (fixed seed).
"""
import json, math, random, sys
import numpy as np
from PIL import Image
sys.path.insert(0, 'osm')
from geo import legacy_i, pre_expansion_i, P, PRE_EXPANSION_ADDITIONS

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
    'shop': (shop['x'] - 45, shop['y'] + 30), 'bus1': (bus_near['x'] + 60, bus_near['y'] + 30),
    'bus2': (bus_far['x'] + 30, bus_far['y'] - 20), 'river': legacy_i(1300, 1650), 'pitch': legacy_i(690, 120),
    'orchard': legacy_i(1300, 2020), 'woods': legacy_i(1760, 1600), 'eastroad': (er[0], er[1] - 26),
}
# one board beside every wayside figure / cross / shrine (map.json shrines, see render_map.py) and one in the jazz yard
for s in m.get('shrines', []): anchors[s['spot']] = (s['x'] + 34, s['y'] + 16)
if 'jazz' in m: anchors['jazz'] = (m['jazz']['x'] - 60, m['jazz']['y'] + 20)
boards = []
for k, v in anchors.items():
    p = at(*v, r=8); boards.append(dict(spot=k, **p))

# ---------------------------------------------------------------- NPCs
soltys_spot = pre_expansion_i(*PRE_EXPANSION_ADDITIONS['soltys'])
cem = poi['cemetery']; TR = m['track']; RG = m['range']
# litter for Mateusz's clean-up: fixed piles by the cemetery and by the southern shop (+3 random ones spawned per new game)
south_shop = pre_expansion_i(2150, 2506)
trash = [dict(id='cemetery', **at(cem['x'] + 150, cem['y'] + 60, r=8)), dict(id='southshop', **at(south_shop[0] - 50, south_shop[1] + 20, r=8))]
npcs = [
    dict(id='kasia', **at(*P(52.26261, 22.88575))),          # far east, by a Chłopków-Kolonia farmstead
    dict(id='marcin', **at(1106, 4251)),                      # hangs around the bus stop (the game lets him wander a little)
    dict(id='damian', **at(TR['cx'] + 80, TR['cy'] + TR['ry'] + TR['w'] / 2 + 34)),   # always by the race track, outside the oval
    dict(id='grandpa', **at(poi['windmill']['x'] + 60, poi['windmill']['y'] + 40)),
    dict(id='halina', **at(poi['church']['x'] - 120, poi['church']['y'] + 70)),   # the chronicler waits by the church
    # hidden Sołtys at the supplied preceding-map coordinate, away from every quiz board
    dict(id='soltys', secret=True, **at(*soltys_spot)),
    dict(id='michal', **at(RG['x'] - 44, RG['y'] + 26)),      # owner of the PPM range
    dict(id='kuba', **at(RG['x'] - 90, RG['y'] + 40)),        # regular at the range
    dict(id='mateusz', **at(trash[0]['x'] + 70, trash[0]['y'] + 30)),   # clean-up organiser by the cemetery
]
if 'jazz' in m: npcs.append(dict(id='patryk', **at(m['jazz']['x'] + 50, m['jazz']['y'] - 5)))
# Edytka: the game puts her at a random reachable spot on every new game (NPC_ZONE_RADIUS covers the whole map);
# this is only her default, somewhere quiet south-east of the shop.
npcs.append(dict(id='edytka', **at(shop['x'] + 420, shop['y'] + 380)))
for n in npcs:
    for b in boards:
        assert math.hypot(n['x'] - b['x'], n['y'] - b['y']) > 45, f"{n['id']} blocks the {b['spot']} signboard"
    for o in npcs:
        assert o is n or math.hypot(n['x'] - o['x'], n['y'] - o['y']) > 38, f"{n['id']} overlaps {o['id']}"

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

json.dump(dict(npcs=npcs, apples=apples, cap=cap, boards=boards, landmarks=landmarks, trash=trash), open('docs/items.json', 'w'), indent=1)
print(f'reachable {reach.mean():.0%} of map |', len(apples), 'apples |', ', '.join(f"{n['id']}@{n['x']},{n['y']}" for n in npcs), '| cap', cap, '| trash', trash,
      '| boards', ', '.join(f"{b['spot']}@{b['x']},{b['y']}" for b in boards),
      '| landmarks', ', '.join(f"{lm['key']}->{lm['access']['x']},{lm['access']['y']}" for lm in landmarks))
