"""Rebuild accepted J12 yard props without touching shared generated map images.

python gen/build_j12_props.py --raw RAW_SHEET --decisions DECISIONS_JSON
Raw source: one Codex OAuth sprite sheet, four isolated quadrants.
Object identification is Tomek's local review, NOT independent satellite confirmation.
Placements are conservative ground-adjacent adaptations of approximate source centers.
"""
import argparse
import json
import re
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gen'))
from build_walk_cycles import remove_magenta_background

SPECS = {'truck': (0, 24), 'silo': (1, 12), 'shrub': (2, 12), 'hedge': (3, 24)}
EXPECTED = {'j12-15-materials': 'ciężarówka', 'j12-15-object': 'cylindryczny silos na zboże',
            'j12-15-vegetation': 'krzewy / małe drzewa', 'j12-18-vegetation': 'krzewy / żywopło',
            'j12-18-ground': 'belki siana jak na polu'}
GROUPS = [
    ('j12-15-materials', 'truck', [(0, 0)]),
    ('j12-15-object', 'silo', [(0, 0)]),
    ('j12-15-vegetation', 'shrub', [(-12, -10), (-4, 2), (8, 12)]),
    ('j12-18-vegetation', 'hedge', [(36, -28), (36, 0)]),
    ('j12-18-ground', 'bale', [(-14, -8), (12, -2), (0, 18)]),
]


def pixelate(cell, width):
    ar = np.array(remove_magenta_background(cell))
    labels, n = ndimage.label(ar[..., 3] > 0, structure=np.ones((3, 3)))
    if not n:
        raise ValueError('Empty sprite quadrant')
    counts = np.bincount(labels.ravel()); counts[0] = 0
    ar[labels != counts.argmax(), 3] = 0
    clean = Image.fromarray(ar)
    clean = clean.crop(clean.getbbox())
    small = clean.resize((width, round(clean.height * width / clean.width)), Image.Resampling.BOX)
    alpha = np.array(small.getchannel('A')) >= 128
    rgb = small.convert('RGB').quantize(colors=32, dither=Image.Dither.NONE).convert('RGB')
    result = np.array(rgb.convert('RGBA'))
    result[..., 3] = np.where(alpha, 255, 0)
    result[~alpha, :3] = 0
    return Image.fromarray(result)


def field_bale():
    # Reuse the EXACT accepted field sprite, not a newly invented bale.
    text = (ROOT / 'docs/js/game.js').read_text(encoding='utf-8')
    runs = json.loads(re.search(r'const BALE_PX = (\[.*?\]);', text).group(1))
    palette = json.loads(re.search(r'Object.assign\(PICK_PAL,\s*// hay bale colours\s*(\{.*?\})\);', text).group(1))
    w = max(x + n for x,y,n,c in runs); h = max(y+1 for x,y,n,c in runs)
    im = Image.new('RGBA', (w,h)); draw = ImageDraw.Draw(im)
    for x,y,n,c in runs:
        draw.rectangle((x,y,x+n-1,y), fill=palette[c])
    return im


def build(raw, decision_path):
    decision_text = decision_path.read_text(encoding='utf-8')
    decisions = json.loads(decision_text)
    assert decisions['review'] == 'yard-evidence-j12-v1'
    assert set(decisions['decisions']) == {cid for cid,_,_ in GROUPS} | {'j12-18-object'}
    for cid,expected in EXPECTED.items():
        choice = decisions['decisions'][cid]
        if choice['decision'] == 'add' and choice['identification'] != expected:
            raise ValueError(f'Changed identification for {cid}; review the normalized sprite mapping first')
    provenance = {v['id']: v for v in decisions['provenance']}
    sheet = Image.open(raw).convert('RGBA')
    images = {}
    for kind,(idx,width) in SPECS.items():
        x,y = idx%2,idx//2
        cell = sheet.crop((x*sheet.width//2,y*sheet.height//2,(x+1)*sheet.width//2,(y+1)*sheet.height//2))
        images[kind] = pixelate(cell, width)
    images['bale'] = field_bale()
    assets = {}
    for kind,im in images.items():
        dest = ROOT / f'docs/img/j12_prop_{kind}.png'
        im.save(dest, optimize=True)
        assets[kind] = {'src': f'img/{dest.name}', 'size': list(im.size),
                        'origin': 'existing-field-bale-art' if kind == 'bale' else 'openai-codex-gpt-image-2-medium'}

    # Full sprite clearance keeps art off roofs/trees and leaves a 4px gap.
    obj = np.array(Image.open(ROOT / 'docs/img/map_objects.png').convert('RGBA'))[...,3] > 0
    solid = np.array(Image.open(ROOT / 'docs/img/map_collide.png').convert('L')) > 0
    occupied = ndimage.binary_dilation(obj | solid, iterations=4)
    terrain = np.array(Image.open(ROOT / 'docs/img/map_terrain.png').convert('L'))
    props = []
    for cid,kind,offsets in GROUPS:
        choice = decisions['decisions'][cid]
        if choice['decision'] != 'add':
            continue
        source = provenance[cid]['mapPointApprox']
        w,h = images[kind].size
        for idx,(dx,dy) in enumerate(offsets):
            target = [source[0]+dx,source[1]+dy]
            # Nearest-first, deterministic; no unchecked fallback.
            candidates = [(ox*ox+oy*oy, oy, ox) for oy in range(-64,65,2) for ox in range(-64,65,2)]
            candidates.sort()
            placed = None
            for _,oy,ox in candidates:
                x,y = target[0]+ox,target[1]+oy
                if not (4608+w <= x < 5120-w and 5632+h <= y < 6144-h):
                    continue
                if abs(x-source[0]) > 70 or abs(y-source[1]) > 70:
                    continue
                left,top = x-w//2,y-h
                if occupied[top:y+2,left:x+(w+1)//2+1].any():
                    continue
                patch = terrain[top//4:(y+2)//4+1,left//4:(x+(w+1)//2+1)//4+1]
                if np.isin(patch,[60,100,220]).any():
                    continue
                # Don't close an access corridor or interactable approach.
                if any(abs(x-p['x']) < (w+assets[p['kind']]['size'][0])/2+8 and abs(y-p['y']) < max(h,assets[p['kind']]['size'][1])+8 for p in props):
                    continue
                placed = [x,y]
                occupied[top-4:y+5,left-4:x+(w+1)//2+5] = True
                break
            if placed is None:
                raise ValueError(f'No verified clear placement near {cid}:{idx}')
            props.append({'id': f'{cid}:{idx}', 'candidate': cid, 'kind': kind,
                          'x': placed[0], 'y': placed[1], 'sourcePoint': source,
                          'source': provenance[cid]['source'], 'sourceBox': provenance[cid]['box'],
                          'identification': choice['identification'], 'note': choice['note'],
                          'footprint': {'rx': max(3,w*.35), 'ry': max(2,h*.20), 'cy': -2,
                                        'tall': kind in ('truck','silo')}})
    data = {'review': decisions['review'], 'identificationSource': 'user-review-not-independent-satellite-confirmation',
            'placementPolicy': 'Nearest safe ground, approximate crop centers adapted to existing game buildings; no shared map rewrite.',
            'assets': assets, 'props': props, 'skipped': [k for k,v in decisions['decisions'].items() if v['decision'] != 'add'],
            'artCost': {'provider': 'openai-codex', 'calls': 1, 'usdIncremental': 0, 'billing': 'ChatGPT subscription quota'}}
    out = ROOT / 'docs/data/j12-yard-props.json'; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    snapshot = ROOT / 'plans/yard-evidence-j12-decisions.json'
    snapshot.write_bytes(decision_path.read_bytes())
    print(json.dumps({'props': len(props), 'assets': {k:v['size'] for k,v in assets.items()},
                      'placements': [{k:p[k] for k in ('kind','x','y','sourcePoint')} for p in props]},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',required=True,type=Path)
    parser.add_argument('--decisions',required=True,type=Path)
    args = parser.parse_args()
    build(args.raw,args.decisions)
