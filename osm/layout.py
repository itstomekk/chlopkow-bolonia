"""Render OSM data of Chłopków (gmina Platerów) to a schematic layout, 1 px = 1 m (x SCALE)."""
import json, math, sys
from PIL import Image, ImageDraw
BBOX = (52.2588, 22.8630, 52.2700, 22.8800)  # minlat, minlon, maxlat, maxlon  (village core)
SCALE = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
lat0 = (BBOX[0] + BBOX[2]) / 2
MX = 111320 * math.cos(math.radians(lat0)); MY = 110574
W = int((BBOX[3] - BBOX[1]) * MX * SCALE); H = int((BBOX[2] - BBOX[0]) * MY * SCALE)
def P(lat, lon): return ((lon - BBOX[1]) * MX * SCALE, (BBOX[2] - lat) * MY * SCALE)
d = json.load(open('osm/chlopkow.json', encoding='utf-8'))
im = Image.new('RGB', (W, H), (120, 170, 80)); dr = ImageDraw.Draw(im)
def poly(e): return [P(g['lat'], g['lon']) for g in e.get('geometry', [])]
layers = {'land': [], 'water': [], 'road': [], 'bld': []}
for e in d['elements']:
    t = e.get('tags', {})
    if e['type'] != 'way' or 'geometry' not in e: continue
    if 'building' in t: layers['bld'].append((e, t))
    elif 'highway' in t: layers['road'].append((e, t))
    elif 'waterway' in t or t.get('natural') == 'water': layers['water'].append((e, t))
    else: layers['land'].append((e, t))
LC = {'farmland': (190, 175, 110), 'forest': (40, 100, 45), 'wood': (40, 100, 45), 'residential': (135, 180, 95), 'farmyard': (170, 150, 110),
      'cemetery': (90, 130, 90), 'religious': (150, 190, 120), 'orchard': (100, 150, 70), 'pitch': (60, 160, 70)}
for e, t in layers['land']:
    c = LC.get(t.get('landuse') or t.get('natural') or t.get('leisure'))
    if c and len(e['geometry']) > 2: dr.polygon(poly(e), fill=c, outline=tuple(max(0, v - 25) for v in c))
for e, t in layers['water']:
    if t.get('natural') == 'water': dr.polygon(poly(e), fill=(60, 120, 200))
    else: dr.line(poly(e), fill=(60, 120, 200), width=int(5 * SCALE))
RW = {'tertiary': 9, 'unclassified': 7, 'residential': 7, 'service': 4, 'track': 4, 'footway': 2}
for e, t in layers['road']:
    w = RW.get(t['highway']); 
    if not w: continue
    col = (90, 90, 95) if t['highway'] in ('tertiary', 'unclassified', 'residential') else (200, 170, 120)
    dr.line(poly(e), fill=col, width=max(1, int(w * SCALE)), joint='curve')
for e, t in layers['bld']:
    col = (230, 90, 70) if t['building'] in ('house', 'detached', 'bungalow') else (160, 160, 170) if t['building'] != 'church' else (255, 255, 255)
    dr.polygon(poly(e), fill=col, outline=(40, 30, 30))
for e in d['elements']:
    t = e.get('tags', {})
    if e['type'] == 'node' and (t.get('man_made') == 'windmill' or 'Sklep' in t.get('name', '')):
        x, y = P(e['lat'], e['lon']); dr.ellipse([x - 8 * SCALE, y - 8 * SCALE, x + 8 * SCALE, y + 8 * SCALE], fill=(255, 220, 0))
im.save('osm/layout.png'); print(W, H)
