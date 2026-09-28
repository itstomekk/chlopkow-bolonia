"""Sept-28 sprite pipeline: key the PPQ raws in gen/raw0928/ into
  gen/npc_src/{michal,mateusz,patryk}.png   (then build_npcs.py packs docs/img/npcs.png)
  docs/img/trash.png + trash.json            (5 x 32px litter pickups)
  docs/img/critters.png + critters.json      (hen / stray / bird / stork / fox strips, 4 frames each, 64px cells, facing right)
  docs/img/frodo_idle.png + frodo_idle.json  (Frodo idle poses, 32px cells matching frodo.png)
Run from the repo root: python gen/build_0928.py"""
import json, sys, pathlib
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, 'gen')
from slice_sheet import key

RAW = pathlib.Path('gen/raw0928')


def keyed(name):
    im = Image.open(RAW / f'{name}.png')
    if im.mode == 'RGBA' and im.getpixel((2, 2))[3] == 0:   # already transparent: just drop faint alpha fringe
        a = np.array(im); a[..., 3] = np.where(a[..., 3] > 110, 255, 0); return a
    return key(RAW / f'{name}.png')


def parts(a, n, min_px=400):
    """The n largest sprites left-to-right; small detached bits are merged into the nearest sprite by column."""
    lab, k = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones(lab.shape), lab, range(1, k + 1))
    objs = ndimage.find_objects(lab)
    big = sorted((int(i) + 1 for i in np.argsort(sizes)[::-1][:n]), key=lambda i: objs[i - 1][1].start)
    boxes = [list(objs[i - 1]) for i in big]
    owner = np.zeros(lab.shape, int)
    for j, i in enumerate(big): owner[lab == i] = j + 1
    for i in range(1, k + 1):
        if i in big or sizes[i - 1] < min_px // 20: continue
        sl = objs[i - 1]; cx = (sl[1].start + sl[1].stop) / 2
        j = min(range(len(boxes)), key=lambda q: abs((boxes[q][1].start + boxes[q][1].stop) / 2 - cx))
        owner[lab == i] = j + 1
        boxes[j] = [slice(min(boxes[j][0].start, sl[0].start), max(boxes[j][0].stop, sl[0].stop)),
                    slice(min(boxes[j][1].start, sl[1].start), max(boxes[j][1].stop, sl[1].stop))]
    out = []
    for j, (ys, xs) in enumerate(boxes):
        c = a[ys, xs].copy(); c[..., 3] = np.where(owner[ys, xs] == j + 1, c[..., 3], 0); out.append(Image.fromarray(c))
    return out


def strip(frames, cell, target_h, name, bottom=2):
    """Pack frames into a strip; one common scale (tallest frame -> target_h) keeps the animation steady, feet on a baseline."""
    s = min(target_h / max(f.height for f in frames), (cell - 2) / max(f.width for f in frames))
    out = Image.new('RGBA', (cell * len(frames), cell), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im = f.resize((max(1, round(f.width * s)), max(1, round(f.height * s))), Image.LANCZOS)
        a = np.array(im); a[..., 3] = np.where(a[..., 3] > 100, 255, 0); im = Image.fromarray(a)
        out.alpha_composite(im, (i * cell + (cell - im.width) // 2, cell - bottom - im.height))
    return out


# ---- NPCs: the whole figure (all opaque pixels; held props like the litter picker are separate blobs)
for n in ('michal', 'mateusz', 'patryk', 'edytka'):
    a = keyed(n)
    lab, k = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    sizes = ndimage.sum(np.ones(lab.shape), lab, range(1, k + 1))
    a[..., 3] = np.where(np.isin(lab, [i + 1 for i in range(k) if sizes[i] >= 60]), a[..., 3], 0)   # drop keying specks
    fig = Image.fromarray(a); fig = fig.crop(fig.getbbox())
    fig.save(f'gen/npc_src/{n}.png'); print('npc', n, fig.size)

# ---- trash pickups
names = ['bottle', 'can', 'bag', 'paper', 'tyre']
tr = strip(parts(keyed('trash'), 5), 32, 22, 'trash')
tr.save('docs/img/trash.png'); json.dump(dict(cell=32, names=names), open('docs/img/trash.json', 'w'))
print('trash', tr.size)

# ---- critters (all 4-frame strips facing right)
CR = dict(hen=(4, 30, ['walk1', 'walk2', 'peck', 'stand']), stray=(4, 40, ['trot1', 'trot2', 'sniff', 'sit']),
          bird=(4, 22, ['stand', 'hop', 'fly1', 'fly2']), stork=(4, 56, ['walk1', 'walk2', 'stand', 'hunt']),
          fox=(4, 40, ['run1', 'run2', 'run3', 'look']))
cell = 64; rows = []
meta = dict(cell=cell, rows={})
for r, (n, (k, h, fr)) in enumerate(CR.items()):
    fs = parts(keyed(n), k)
    if n == 'stork': fs[3] = fs[3].transpose(Image.FLIP_LEFT_RIGHT)   # the hunting pose was drawn facing left
    rows.append(strip(fs, cell, h, n)); meta['rows'][n] = dict(row=r, frames=fr, h=h)
sheet = Image.new('RGBA', (cell * 4, cell * len(rows)), (0, 0, 0, 0))
for r, im in enumerate(rows): sheet.alpha_composite(im, (0, r * cell))
sheet.save('docs/img/critters.png'); json.dump(meta, open('docs/img/critters.json', 'w'), indent=1)
print('critters', sheet.size)

# ---- Frodo idle poses (32px cells like frodo.png; the dog there is ~27px tall incl. ears)
idle = parts(keyed('frodo_idle'), 6)
idle[4] = idle[4].transpose(Image.FLIP_LEFT_RIGHT); idle[5] = idle[5].transpose(Image.FLIP_LEFT_RIGHT)   # sniff/lie were drawn facing left
poses = ['sit', 'pant1', 'pant2', 'scratch', 'sniff', 'lie']
frames = idle
if (RAW / 'frodo_lick.png').exists():
    frames = idle + parts(keyed('frodo_lick'), 4); poses = poses + ['lick0', 'lick1', 'lick2', 'lickpaw']
fi = strip(frames, 32, 26, 'frodo_idle', bottom=3)
fi.save('docs/img/frodo_idle.png'); json.dump(dict(cell=32, poses=poses, facing='right'), open('docs/img/frodo_idle.json', 'w'))
print('frodo idle', fi.size, poses)
