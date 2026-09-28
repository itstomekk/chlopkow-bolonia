"""Add OpenStreetMap data for a bigger map bbox to osm/chlopkow.json (Overpass `out geom` format).

Usage (from the repo root):
    python osm/fetch_osm.py 52.25585 22.8586 52.285 22.89292 [--old S W N E]

Fetches the same feature types the renderer uses for the whole bbox and merges them into
osm/chlopkow.json by (type, id). Existing elements are kept as they are, so a failed or partial
fetch never removes anything. Multipolygon relations (e.g. forests mapped as relations) are
turned into plain ways that carry the relation's tags, because render_map.py reads ways only.
With --old (the previous map bbox), the already-drawn area stays exactly as it was: new elements
lying wholly inside it are skipped, and relation rings (whose holes are dropped) must lie wholly
outside it.
Map data © OpenStreetMap contributors (ODbL).
"""
import json, sys, time, urllib.parse, urllib.request

OUT = 'osm/chlopkow.json'
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
             'https://overpass.private.coffee/api/interpreter']

args = sys.argv[1:]
old_bb = None
if '--old' in args:
    i = args.index('--old'); old_bb = tuple(map(float, args[i + 1:i + 5])); args = args[:i] + args[i + 5:]
s, w, n, e = map(float, args[:4])
bb = f'{s},{w},{n},{e}'
query = f"""[out:json][timeout:120];
(
  way["building"]({bb});
  way["highway"]({bb});
  way["landuse"]({bb});
  way["natural"]({bb});
  way["waterway"]({bb});
  way["leisure"]({bb});
  way["amenity"]({bb});
  way["man_made"]({bb});
  way["historic"]({bb});
  way["power"="line"]({bb});
  node["place"]({bb});
  node["shop"]({bb});
  node["amenity"]({bb});
  node["highway"]({bb});
  node["man_made"]({bb});
  node["historic"]({bb});
  relation["type"="multipolygon"]["landuse"]({bb});
  relation["type"="multipolygon"]["natural"]({bb});
);
out geom;"""

data = None
for url in ENDPOINTS:
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': query}).encode(),
                                     headers={'User-Agent': 'chlopkow-bolonia-game/1.0 (map renderer)'})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.load(r)
        print('fetched from', url, len(data['elements']), 'elements')
        break
    except Exception as ex:   # try the next mirror
        print('failed', url, ex); time.sleep(2)
if data is None:
    sys.exit('all Overpass endpoints failed; nothing changed')

# multipolygon relations -> one way per outer ring member, tagged like the relation
extra = []
for el in data['elements']:
    if el['type'] != 'relation': continue
    tags = {k: v for k, v in el.get('tags', {}).items() if k != 'type'}
    for i, m in enumerate(el.get('members', [])):
        if m.get('type') == 'way' and m.get('role') in ('outer', '') and m.get('geometry'):
            extra.append(dict(type='way', id=-(el['id'] * 1000 + i), tags=tags, geometry=m['geometry']))
new = [x for x in data['elements'] if x['type'] != 'relation'] + extra

old = json.load(open(OUT, encoding='utf-8'))
have = {(x['type'], x['id']) for x in old['elements']}
added = [x for x in new if (x['type'], x['id']) not in have]


def inside_old(x):
    g = x.get('geometry') or ([{'lat': x['lat'], 'lon': x['lon']}] if 'lat' in x else [])
    return [old_bb[0] <= p['lat'] <= old_bb[2] and old_bb[1] <= p['lon'] <= old_bb[3] for p in g]


if old_bb:
    def wholly_old(x):
        flags = inside_old(x)
        return bool(flags) and all(flags)

    # Keep objects that are new or cross the old boundary. Relation-derived rings are
    # handled conservatively: a ring touching the old bbox is dropped because its holes
    # were flattened and re-drawing it would alter existing terrain.
    added = [x for x in added if not (x['id'] < 0 and any(inside_old(x)))] + \
            [x for x in added if x['id'] >= 0 and not wholly_old(x)]
old['elements'].extend(added)
old.setdefault('osm3s', {})['timestamp_osm_base'] = data.get('osm3s', {}).get('timestamp_osm_base', '')
json.dump(old, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('added', len(added), 'new elements; total', len(old['elements']))
