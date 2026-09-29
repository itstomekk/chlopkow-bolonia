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

# stage: entities - override moves in place, add appends, remove drops, unknown ids FAIL LOUDLY
tgt = {'npc:soltys': {'id': 'soltys', 'x': 1, 'y': 1, 'secret': True}, 'npc:halina': {'id': 'halina', 'x': 2, 'y': 2}}
lst = [tgt['npc:soltys'], tgt['npc:halina']]
lat, lon = geo.to_latlon(1234, 2345)
edoc = {'layers': {'entities': {
    'npc:soltys': {'lat': lat, 'lon': lon},
    'remove': ['npc:halina'],
    'add': [{'kind': 'npc', 'id': 'gosia', 'lat': lat, 'lon': lon, 'secret': True}],
}}}
check(edits.validate(edoc) == [], 'entities add/remove doc validates')
edits.apply('entities', edoc, {'target': tgt, 'target_list': lst})
check(tgt['npc:soltys']['x'] == 1234 and tgt['npc:soltys']['y'] == 2345 and tgt['npc:soltys']['secret'],
      'entity override moves in place, keeps other fields')
check(lst[0] is tgt['npc:soltys'], 'override mutates the generator record (list identity)')
check('npc:gosia' in tgt and tgt['npc:gosia']['x'] == 1234 and tgt['npc:gosia']['y'] == 2345
      and tgt['npc:gosia']['secret'] is True and lst[-1] is tgt['npc:gosia'],
      'entities.add appends a new record at the exact lat/lon')
check('npc:halina' not in tgt and all(n['id'] != 'halina' for n in lst),
      'entities.remove drops the record from target and the generator list')
try:
    edits.apply('entities', {'layers': {'entities': {'npc:ghost': {'lat': lat, 'lon': lon}}}}, {'target': tgt})
    check(False, 'unknown entity override raises')
except ValueError as e:
    check('npc:ghost' in str(e), 'unknown entity override raises with the id')
try:
    edits.apply('entities', {'layers': {'entities': {'remove': ['npc:ghost']}}}, {'target': tgt})
    check(False, 'unknown entity remove raises')
except ValueError:
    check(True, 'unknown entity remove raises')
bad4 = {'version': 1, 'layers': {'entities': {'add': [{'kind': 'npc', 'lat': 52.26, 'lon': 22.86}], 'remove': ['halina']}}}
check(len(edits.validate(bad4)) == 2, 'bad entities add (missing id) and remove (no kind:) rejected')

# stage: zones - a people zone moves its npc to the venue anchor; music stays runtime data
tgt2 = {'npc:kuba': {'id': 'kuba', 'x': 1, 'y': 1}}
edits.apply('zones', {'layers': {'zones': {'items': [{'id': 'yard', 'kind': 'people',
    'poly': square(100, 100, 10), 'props': {'npc': 'kuba', 'venue': 'church'}}]}}},
    {'target': tgt2, 'venues': {'church': (3000, 4000)}, 'spot': lambda x, y: dict(x=round(x), y=round(y))})
check(tgt2['npc:kuba']['x'] == 3000 and tgt2['npc:kuba']['y'] == 4000,
      'people zone moves the npc to the venue anchor')
try:
    edits.apply('zones', {'layers': {'zones': {'items': [{'id': 'x', 'kind': 'people',
        'poly': square(50, 50, 5), 'props': {'npc': 'kuba', 'venue': 'nowhere'}}]}}},
        {'target': tgt2, 'venues': {'church': (1, 1)}})
    check(False, 'unknown zone venue raises')
except ValueError:
    check(True, 'unknown zone venue raises')
try:
    edits.apply('zones', {'layers': {'zones': {'items': [{'id': 'x', 'kind': 'people',
        'poly': square(50, 50, 5), 'props': {'npc': 'ghost', 'venue': 'church'}}]}}},
        {'target': tgt2, 'venues': {'church': (1, 1)}})
    check(False, 'unknown zone npc raises')
except ValueError:
    check(True, 'unknown zone npc raises')

# stage: buildings
lat, lon = geo.to_latlon(1000, 2000)
bl = [dict(id=11, kind='house', c=np.array([5., 5.]), ax=np.array([1., 0.]), nx=np.array([0., 1.]), L=10., Wd=8.),
      dict(id=22, kind='barn', c=np.array([50., 50.]), ax=np.array([1., 0.]), nx=np.array([0., 1.]), L=20., Wd=10.),
      dict(id=33, kind='house', c=np.array([90., 90.]), ax=np.array([1., 0.]), nx=np.array([0., 1.]), L=9., Wd=9.)]
bdoc = {'version': 1, 'layers': {'buildings': {
    'remove': [11],
    'modify': {'22': {'lat': lat, 'lon': lon, 'len': 12, 'wid': 6, 'angle': 90}},
    'add': [{'lat': lat, 'lon': lon, 'len': 8, 'wid': 5, 'angle': 0, 'kind': 'farm'}]}}}
check(edits.validate(bdoc) == [], 'buildings layer validates')
check(edits.validate({'version': 1, 'layers': {'buildings': {'add': [{'lat': lat, 'lon': lon, 'len': 0, 'wid': 5}], 'remove': ['x'], 'modify': {'abc': {}}}}}).__len__() >= 3,
      'bad buildings rejected (size, remove ids, modify key)')
edits.apply('buildings', bdoc, {'buildings': bl})
ids = [b['id'] for b in bl]
check(ids == [22, 33, 'edit:0'], f'buildings remove/keep/add order ({ids})')
m = bl[0]
check(abs(m['c'][0] - 1000) < 1e-6 and abs(m['c'][1] - 2000) < 1e-6 and m['L'] == 12 * geo.A and m['Wd'] == 6 * geo.A
      and abs(m['ax'][1] - 1) < 1e-9 and m['kind'] == 'barn' and m['fixed'], 'building modify: centre, size in metres, 90° axis, keeps kind, fixed')
check(bl[1].get('fixed') is None and bl[2]['kind'] == 'farm' and bl[2]['fixed'], 'untouched building unchanged, added one is fixed farm')

# the editor's OSM building extraction matches the generator fit (centre, dims, axis)
sys.path.insert(0, os.path.join(ROOT, 'editor'))
import server  # noqa: E402
ob = server.osm_buildings()
check(len(ob) > 50 and all(o['len'] > 0 and o['wid'] > 0 for o in ob), f'editor lists OSM buildings ({len(ob)})')
rec = edits.building_record(ob[0], ob[0]['id'])
check(abs(rec['L'] / geo.A - ob[0]['len']) < 1e-6, 'editor building round-trips through building_record')

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
