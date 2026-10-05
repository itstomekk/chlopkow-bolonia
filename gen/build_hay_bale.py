"""Process the user-requested cylindrical bale and emit a reviewable engine V4A patch.

python gen/build_hay_bale.py RAW_PNG
Does not edit game.js automatically. Apply asset-review/cylindrical-bale/game-art.patch
with the patch tool, then run test/cylindrical_bale_test.py and bale_styles_test.py.
Keeps original 24x16 art size, six straw colours, field physics and yard placements.
"""
import json
import re
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'gen'))
from build_walk_cycles import remove_magenta_background


def build(raw):
    text = (ROOT / 'docs/js/game.js').read_text(encoding='utf-8')
    palette = json.loads(re.search(r'Object.assign\(PICK_PAL,\s*// hay bale colours\s*(\{.*?\})\);',text).group(1))
    ar = np.array(remove_magenta_background(Image.open(raw)))
    labels,n = ndimage.label(ar[...,3]>0,structure=np.ones((3,3)))
    if not n:
        raise ValueError('No sprite found')
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    ar[labels != sizes.argmax(),3] = 0
    clean = Image.fromarray(ar); clean = clean.crop(clean.getbbox())
    im = clean.resize((24,16),Image.Resampling.BOX)
    px = np.array(im); opaque = px[...,3] >= 128
    colors = np.array([tuple(bytes.fromhex(value[1:])) for value in palette.values()],dtype=np.int32)
    diff = px[...,:3].astype(np.int32)[...,None,:]-colors
    indices = (diff*diff).sum(axis=-1).argmin(axis=-1)
    px[...,:3] = colors[indices]; px[...,3] = np.where(opaque,255,0)
    px[~opaque,:3] = 0
    result = Image.fromarray(px)
    if result.getbbox() != (0,0,24,16):
        raise ValueError('Reprocess silhouette to retain original 24x16 visible bounds')
    result.save(ROOT / 'docs/img/hay_bale.png',optimize=True)
    result.save(ROOT / 'docs/img/j12_prop_bale.png',optimize=True)
    keys = list(palette)
    runs = []
    for y in range(16):
        x=0
        while x < 24:
            if not opaque[y,x]:
                x+=1; continue
            start=x; key=int(indices[y,x]); x+=1
            while x < 24 and opaque[y,x] and int(indices[y,x]) == key:
                x+=1
            runs.append([start,y,x-start,keys[key]])
    old = next(line for line in text.splitlines() if 'const BALE_PX = ' in line)
    new = '  const BALE_PX = '+json.dumps(runs,separators=(',',':'))+';'
    out = ROOT / 'asset-review/cylindrical-bale'; out.mkdir(parents=True,exist_ok=True)
    (out / 'game-art.patch').write_text('*** Begin Patch\n*** Update File: '+str(ROOT / 'docs/js/game.js')+'\n@@\n-'+old+'\n+'+new+'\n*** End Patch\n',encoding='utf-8')
    # Inspectable provenance without changing the J12 decision snapshot or placement solver.
    manifest = {'size':[24,16],'palette':palette,'runs':runs,'source':'Codex-generated horizontal cylinder; user requested straight sides and full round end',
                'raw':str(raw),'provider':'openai-codex','requestedModel':'gpt-image-2-medium','reportedQuality':'low',
                'requestId':'500f2821-06ba-4d3b-90ff-606459f04b97','estimatedIncrementalUSD':0}
    (out / 'recipe.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Generated same 24x16 cylinder for fields and J12;',len(runs),'runs; palette unchanged.')
    print(new)


if __name__ == '__main__':
    build(Path(sys.argv[1]))
