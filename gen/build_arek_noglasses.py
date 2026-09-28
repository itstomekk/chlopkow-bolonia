"""Arek without sunglasses, for the cemetery.

Reads docs/img/arek_sheet.png and writes docs/img/arek_sheet_noglasses.png with the same layout
(so docs/img/arek_sheet.json describes both). Only the sunglasses are painted over: every other
pixel stays identical, so the walk cycle, size and outline match the normal sprite exactly.

Per frame: the blue-ish lens pixels locate the glasses; dark frame/lens pixels in a box around them
are replaced by the nearest skin colour in the same column, then simple eyes and brows are drawn.
Back-view frames have no lenses and are copied unchanged.

Run from the repo root: python gen/build_arek_noglasses.py
"""
import json
import numpy as np
from PIL import Image
from scipy import ndimage

SRC, DST, META = 'docs/img/arek_sheet.png', 'docs/img/arek_sheet_noglasses.png', 'docs/img/arek_sheet.json'
EYE_WHITE, PUPIL, BROW = (246, 240, 228, 255), (38, 24, 18, 255), (70, 38, 20, 255)

a = np.array(Image.open(SRC).convert('RGBA')).astype(int)
meta = json.load(open(META, encoding='utf-8'))
frames = {(f['x'], f['y'], f['w'], f['h']) for an in meta['anims'].values() for f in an['frames']}


def is_skin(p):
    r, g, b, al = p
    return al > 200 and r > 150 and g > 80 and r > b + 40


def fix_frame(x0, y0, w, h, facing):
    f = a[y0:y0 + h, x0:x0 + w]
    r, g, b, al = f[..., 0], f[..., 1], f[..., 2], f[..., 3]
    band = np.zeros(al.shape, bool); band[35:62] = True
    lens = band & (al > 200) & (b > r) & (b > 60)
    if lens.sum() < 6:
        return 0
    lab, n = ndimage.label(ndimage.binary_dilation(lens, iterations=2))
    comps = sorted((ndimage.find_objects(lab)[i] for i in range(n)), key=lambda s: s[1].start)
    comps = [c for c in comps if (lens[c]).sum() >= 4]
    ys, xs = np.nonzero(lens)
    bx0, bx1, by0, by1 = xs.min() - 3, xs.max() + 3, ys.min() - 3, ys.max() + 2
    dark = (al > 200) & ((r + g + b) < 150)
    mask = np.zeros(al.shape, bool)
    mask[by0:by1 + 1, bx0:bx1 + 1] = (dark | lens)[by0:by1 + 1, bx0:bx1 + 1]
    # the glasses' top edge sits on the brow line; keep a 1 px dark line only above each eye (drawn later as a brow)
    out = f.copy()
    # flat fill with the face's dominant light skin tone (nearest-pixel fill copied cheek shadows and looked smeared)
    skin = f[(al > 200) & (r > 230) & (g > 170) & (g < 215) & (r > b + 80)]
    fill = np.median(skin, axis=0).astype(int) if len(skin) else np.array([253, 194, 124, 255])
    fill[3] = 255
    out[mask] = fill
    # eyes: front view has two (one per lens), side view only the lens nearest the nose
    if facing == 'right':
        comps = comps[-1:]
    eye_y = int(np.median(ys))   # same height for both eyes
    for c in comps:
        cx = (c[1].start + c[1].stop) // 2 + (1 if facing == 'right' else 0)
        if facing == 'down':   # white | pupil pupil | white, 2 rows
            out[eye_y:eye_y + 2, cx - 2:cx + 2] = EYE_WHITE
            out[eye_y:eye_y + 2, cx - 1:cx + 1] = PUPIL
            out[eye_y - 3, cx - 2:cx + 2] = BROW
        else:                  # looking right: white | pupil pupil
            out[eye_y:eye_y + 2, cx - 1:cx + 2] = EYE_WHITE
            out[eye_y:eye_y + 2, cx:cx + 2] = PUPIL
            out[eye_y - 3, cx - 1:cx + 3] = BROW
    a[y0:y0 + h, x0:x0 + w] = out
    return len(comps)


done = set()
for name, an in meta['anims'].items():
    if an.get('flip'):
        continue
    facing = 'down' if name.endswith('down') else 'right' if name.endswith('right') else 'up'
    for fr in an['frames']:
        k = (fr['x'], fr['y'])
        if k in done or facing == 'up':
            continue
        done.add(k)
        print(name, k, 'eyes', fix_frame(fr['x'], fr['y'], fr['w'], fr['h'], facing))

Image.fromarray(a.astype(np.uint8)).save(DST, optimize=True)
print('wrote', DST)
