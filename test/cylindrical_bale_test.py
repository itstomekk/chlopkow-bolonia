"""Cylindrical hay bale: one exact bitmap for fields and J12, original size/palette."""
import json
import re
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
art = ROOT / 'docs/img/hay_bale.png'
assert art.is_file(), 'New cylindrical bale art is missing'
im = Image.open(art).convert('RGBA')
assert im.size == (24, 16)
ar = np.array(im)
assert set(np.unique(ar[..., 3])) == {0, 255}
assert np.array_equal(ar, np.array(Image.open(ROOT / 'docs/img/j12_prop_bale.png').convert('RGBA'))), 'Yard and field art diverged'
text = (ROOT / 'docs/js/game.js').read_text(encoding='utf-8')
runs = json.loads(re.search(r'const BALE_PX = (\[.*?\]);', text).group(1))
palette = json.loads(re.search(r'Object.assign\(PICK_PAL,\s*// hay bale colours\s*(\{.*?\})\);', text).group(1))
rendered = Image.new('RGBA', (24,16)); draw = ImageDraw.Draw(rendered)
for x,y,n,c in runs:
    draw.rectangle((x,y,x+n-1,y),fill=palette[c])
assert np.array_equal(np.array(rendered),ar), 'Live field pixel runs are not the new cylindrical sprite'
opaque = ar[...,3] > 0
# Guard the old peaked croissant silhouette: straight top/bottom barrel spans.
top = [int(np.flatnonzero(opaque[:,x])[0]) for x in range(24) if opaque[:,x].any()]
bottom = [int(np.flatnonzero(opaque[:,x])[-1]) for x in range(24) if opaque[:,x].any()]
def longest_equal(values):
    best = streak = 1
    for old,new in zip(values,values[1:]):
        streak = streak+1 if old == new else 1
        best = max(best,streak)
    return best
assert longest_equal(top) >= 7, ('No straight cylindrical top',top)
assert longest_equal(bottom) >= 7, ('No straight cylindrical bottom',bottom)
assert rendered.getbbox() == (0,0,24,16)
print('cylindrical bale: PASS (24x16, original palette, straight barrel contours, exact field/J12 bitmap match)')
