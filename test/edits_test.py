"""Unit tests for osm/edits.py (no browser, no map rebuild).

    python test/edits_test.py
"""
import json, os, sys, tempfile
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'osm'))
import edits, geo  # noqa: E402

fails = []


def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)


def square(cx, cy, half):
    """lat/lon polygon of an axis-aligned art-pixel square."""
    return [list(geo.to_latlon(x, y)) for x, y in
            [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]]


# empty / missing file
tmpd = tempfile.mkdtemp()
p = os.path.join(tmpd, 'edits.json')
d = edits.load(p)
check(d == edits.empty() and edits.is_empty(d), 'missing file loads as empty edits')

# geo round-trip
for x, y in [(0, 0), (949, 4665), (3000, 100)]:
    lat, lon = edits.to_ll(x, y)
    X, Y = edits.to_px(lat, lon)
    check(abs(X - x) < 1e-6 and abs(Y - y) < 1e-6, f'geo round-trip ({x},{y})')

# validation
bad = {'version': 1, 'layers': {'trees': {'add': [{'lat': 'x', 'lon': 22.8}]},
                                'forest': {'add': [{'poly': [[1, 2]]}]},
                                'zones': {'items': [{'id': 'a', 'kind': 'weather', 'poly': square(10, 10, 5)}]},
                                'entities': {'soltys': {'lat': 52.26, 'lon': 22.86}}}}
errs = edits.validate(bad)
check(any('trees.add[0]: lat' in e for e in errs), 'invalid tree lat reported')
check(any('forest.add[0]' in e for e in errs), 'short polygon reported')
check(any('kind must be one of' in e for e in errs), 'bad zone kind reported')
check(any('kind:id' in e for e in errs), 'entity key format reported')
check(edits.validate({'version': 99}) and 'newer' in edits.validate({'version': 99})[0], 'newer version rejected')
try:
    edits.save(bad, p); check(False, 'save refuses invalid edits')
except ValueError:
    check(not os.path.exists(p), 'save refuses invalid edits and writes nothing')

# round-trip + unknown layer preserved
good = {'version': 1, 'meta': {'note': 'test'}, 'layers': {
    'trees': {'add': [{'lat': 52.2639, 'lon': 22.8655, 'r': 10, 'dark': True}], 'clear': [{'poly': square(500, 500, 50)}]},
    'zones': {'items': [{'id': 'jazz', 'kind': 'music', 'poly': square(100, 100, 20), 'props': {'track': 'jazz'}}]},
    'futureLayer': {'anything': [1, 2, 3]}}}
check(edits.validate(good) == [], 'valid document passes')
edits.save(good, p)
back = edits.load(p)
check(back['layers'] == good['layers'], 'save/load round-trip is lossless')
check(edits.unknown_layers(back) == ['futureLayer'], 'unknown layers preserved')
check(not [f for f in os.listdir(tmpd) if f.endswith('.tmp')], 'atomic save leaves no temp files')

# masks
m = np.zeros((300, 300), bool)
edits.paint(m, square(150, 150, 40), True)
check(abs(int(m.sum()) - 80 * 80) <= 2 * 80 + 4, f'square mask area ~6400 (got {int(m.sum())})')
check(m[150, 150] and not m[150, 200] and not m[100, 100 - 1 - 40 + 40 - 10], 'mask inside/outside')

# stage: forest
ctx = {'forest_mask': np.zeros((300, 300), bool)}
edits.apply('forest', {'layers': {'forest': {'add': [{'poly': square(100, 100, 30)}], 'remove': [{'poly': square(100, 100, 10)}]}}}, ctx)
fm = ctx['forest_mask']
check(fm[100, 75] and not fm[100, 100], 'forest add then remove hole')

# stage: trees
pts = [(500, 500, 10, False), (700, 700, 10, False)]
ctx = {'tree_pts': pts}
edits.apply('trees', good, ctx)
check((500, 500, 10, False) not in pts and (700, 700, 10, False) in pts, 'trees.clear removes generated trees inside polygon only')
added = ctx['tree_keep'][0]
check(abs(added[0] - geo.P(52.2639, 22.8655)[0]) < 1e-6 and added[3] is True, 'trees.add appends kept tree at lat/lon')

# stage: water + collision
ctx = {'pond_m': np.zeros((200, 200), bool), 'collide': np.zeros((200, 200), bool)}
edits.apply('water', {'layers': {'water': {'add': [{'poly': square(50, 50, 10), 'name': 'Staw'}]}}}, ctx)
check(ctx['pond_m'][50, 50] and ctx['collide'][50, 50], 'water adds pond + collision')
img = np.zeros((200, 200), np.uint8); road = np.zeros((200, 200), bool); road[100, :] = True
ctx = {'collide_img': img, 'road_m': road}
edits.apply('collision', {'layers': {'collision': {'block': [{'poly': square(100, 100, 20)}]}}}, ctx)
check(img[90, 100] == 255 and img[100, 100] == 0, 'collision block, roads stay walkable')

# stage: entities
tgt = {'npc:soltys': {'id': 'soltys', 'x': 1, 'y': 1, 'secret': True}}
lat, lon = geo.to_latlon(1234, 2345)
edits.apply('entities', {'layers': {'entities': {'npc:soltys': {'lat': lat, 'lon': lon}, 'npc:ghost': {'lat': lat, 'lon': lon}}}}, {'target': tgt})
check(tgt['npc:soltys']['x'] == 1234 and tgt['npc:soltys']['y'] == 2345 and tgt['npc:soltys']['secret'], 'entity override moves, keeps other fields')
check('npc:ghost' not in tgt, 'unknown entity ids are ignored, not invented')

# empty edits change nothing
fm = np.random.default_rng(1).random((50, 50)) > .5; before = fm.copy()
edits.apply('forest', edits.empty(), {'forest_mask': fm})
check((fm == before).all(), 'empty edits are a no-op')

# example file (if present) is valid
ex = os.path.join(ROOT, 'osm', 'edits.example.json')
if os.path.exists(ex):
    check(edits.validate(json.load(open(ex, encoding='utf-8'))) == [], 'osm/edits.example.json is valid')

print('\nFAILED:', len(fails)) if fails else print('\nALL PASSED')
sys.exit(1 if fails else 0)
