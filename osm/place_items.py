"""Place NPCs and collectibles on walkable, sensible spots of the generated map -> docs/items.json."""
import json, math, random
import numpy as np
from PIL import Image
m = json.load(open('docs/map.json'))
W, H = m['w'], m['h']
solid = np.array(Image.open('docs/img/map_collide.png').convert('L')) > 127
ground = np.array(Image.open('docs/img/map_ground.png').convert('RGB')).astype(int)
rnd = random.Random(3)
def free(x, y, r=10):
    x, y = int(x), int(y)
    if x < r or y < 40 or x >= W - r or y >= H - r: return False
    return not solid[y - r:y + 3, x - r:x + r].any()
def near_free(x, y, r=10):
    for rad in range(0, 200, 3):
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            px, py = x + math.cos(a) * rad, y + math.sin(a) * rad
            if free(px, py, r): return round(px), round(py)
    return round(x), round(y)
poi = {p['key']: p for p in m['pois']}
bus = [p for p in m['pois'] if p['key'] == 'bus']
bus_near = min(bus, key=lambda p: math.hypot(p['x'] - poi['shop']['x'], p['y'] - poi['shop']['y']))
npcs = [
    dict(id='kasia', **dict(zip('xy', near_free(poi['shop']['x'] + 55, poi['shop']['y'] + 30)))),
    dict(id='marcin', **dict(zip('xy', near_free(bus_near['x'] + 25, bus_near['y'] + 10)))),
    dict(id='damian', **dict(zip('xy', near_free(631, 150)))),
    dict(id='grandpa', **dict(zip('xy', near_free(poi['windmill']['x'] + 60, poi['windmill']['y'] + 40)))),
]
# apples: next to tree trunks (objects with small width) in orchard + gardens
trees = [o for o in m['objects'] if o['w'] < 34]
orchard = [t for t in trees if abs(t['x'] - 1343) < 90 and abs(t['base'] - 2171) < 260]
garden = [t for t in trees if t not in orchard and 350 < t['base'] < 1300]
apples = []
def add_apples(pool, n):
    rnd.shuffle(pool)
    for t in pool:
        if len([a for a in apples if a['src'] == id(pool)]) >= n: break
        cx = t['x'] + t['w'] / 2 + rnd.choice([-1, 1]) * rnd.uniform(9, 16); cy = t['base'] + rnd.uniform(2, 10)
        if free(cx, cy, 4) and all(math.hypot(cx - a['x'], cy - a['y']) > 60 for a in apples):
            apples.append(dict(x=round(cx), y=round(cy), src=id(pool)))
add_apples(orchard, 6); add_apples(garden, 8)
for a in apples: a.pop('src')
# cap: inside a yellow wheat field, walkable, not too close to roads
ys, xs = np.nonzero((ground[..., 0] > 190) & (ground[..., 1] > 150) & (ground[..., 2] < 110) & ~solid)
cands = [(x, y) for x, y in zip(xs[::500], ys[::500]) if 900 < math.hypot(x - poi['shop']['x'], y - poi['shop']['y']) < 1600 and free(x, y, 12)]
cap = dict(zip('xy', map(int, rnd.choice(cands))))
json.dump(dict(npcs=npcs, apples=apples, cap=cap), open('docs/items.json', 'w'), indent=1)
print(len(apples), 'apples', npcs, 'cap', cap)
