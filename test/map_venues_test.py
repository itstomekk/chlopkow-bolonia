"""Map venues (Sept 28): every new venue / NPC / trash spot / quiz board is walkable and connected to the spawn.
Run: python test/map_venues_test.py"""
import json, math, pathlib, sys
import numpy as np
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
ROOT = pathlib.Path(__file__).resolve().parents[1] / 'docs'
m = json.loads((ROOT / 'map.json').read_text(encoding='utf-8'))
items = json.loads((ROOT / 'items.json').read_text(encoding='utf-8'))
solid = np.array(Image.open(ROOT / 'img/map_collide.png').convert('L')) > 64
lab, _ = ndimage.label(~solid)
home = lab[m['spawn']['y'], m['spawn']['x']]
fails = []


def check(name, x, y, near=None, within=None):
    x, y = int(round(x)), int(round(y))
    win = lab[y - 3:y + 4, x - 3:x + 4]
    if not (win == home).any(): fails.append(f'{name} at {x},{y} is solid or not connected to the spawn')
    if near and math.hypot(x - near[0], y - near[1]) > within: fails.append(f'{name} at {x},{y} is {math.hypot(x - near[0], y - near[1]):.0f}px from {near}, want <= {within}')


check('jazz', m['jazz']['x'], m['jazz']['y'], (2471, 1091), 250)
check('gravel', m['gravel']['x'], m['gravel']['y'], (873, 2322), 250)
check('corral', m['corral']['cx'], m['corral']['cy'], (3487, 3308), 250)
M = m['meadow']
if (M['x1'] - M['x0'], M['y1'] - M['y0']) != (840, 540): fails.append(f'meadow is {M["x1"] - M["x0"]}x{M["y1"] - M["y0"]}, want 840x540')
if solid[M['y0']:M['y1'], M['x0']:M['x1']].any(): fails.append('meadow interior has solid pixels')
check('meadow', (M['x0'] + M['x1']) / 2, (M['y0'] + M['y1']) / 2, (1321, 888), 450)
npc = {n['id']: n for n in items['npcs']}
for i in ('michal', 'kuba', 'patryk', 'marcin', 'damian'):
    if i not in npc: fails.append(f'missing npc {i}'); continue
    check(i, npc[i]['x'], npc[i]['y'])
check('marcin@bus', npc['marcin']['x'], npc['marcin']['y'], (1106, 4251), 20)
free = (~solid[4251 - 60:4251 + 61, 1106 - 60:1106 + 61]).mean()
if free < .6: fails.append(f'only {free:.0%} walkable around Marcin')
T = m['track']
d = math.hypot(npc['damian']['x'] - T['cx'], npc['damian']['y'] - T['cy'])
if d > 400: fails.append(f'damian is {d:.0f}px from the race track')
R = m['range']
for i in ('michal', 'kuba'):
    if math.hypot(npc[i]['x'] - R['x'], npc[i]['y'] - R['y']) > 130: fails.append(f'{i} is not by the range')
    if math.hypot(npc[i]['x'] - R['x'] - 40, npc[i]['y'] - R['y'] - 22) < 40: fails.append(f'{i} stands on the skeet flag')
if 'patryk' in npc and math.hypot(npc['patryk']['x'] - m['jazz']['x'], npc['patryk']['y'] - m['jazz']['y']) > m['jazz']['r']: fails.append('patryk not in the jazz yard')
trash = {t['id']: t for t in items.get('trash', [])}
for k in ('cemetery', 'southshop'):
    if k not in trash: fails.append(f'missing trash {k}'); continue
    check('trash ' + k, trash[k]['x'], trash[k]['y'])
if 'mateusz' in npc: fails.append('mateusz (trash-collector NPC) should not be on the map; trash bags are plain pickups')
spots = {b['spot']: b for b in items['boards']}
want = [s['spot'] for s in m['shrines']] + ['jazz']
if len(m['shrines']) < 5: fails.append(f'only {len(m["shrines"])} shrines exported')
for s in want:
    if s not in spots: fails.append(f'missing quiz board {s}'); continue
    check('board ' + s, spots[s]['x'], spots[s]['y'])
for s in m['shrines']:
    b = spots.get(s['spot'])
    if b and math.hypot(b['x'] - s['x'], b['y'] - s['y']) > 80: fails.append(f"board {s['spot']} is far from its {s['kind']}")
lm = {l['key']: l for l in items['landmarks']}
for k in ('jazz', 'wapnica'):
    if k not in lm: fails.append(f'missing landmark {k}')
fp = m['football_pitch']
if (lm['football_pitch']['x'], lm['football_pitch']['y']) != (fp['cx'], fp['cy']): fails.append('football landmark != pitch centre')

print('\n'.join(fails) or 'map venues OK')
sys.exit(1 if fails else 0)
