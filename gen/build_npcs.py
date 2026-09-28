"""Pack NPC sprites (gen/npc_src/*.png, transparent 8-bit sprites from the Grand Theft Tractor video)
into docs/img/npcs.png: 4 cells of 130x170, feet 6 px above the cell bottom. Order must match NPC_IDX in docs/js/game.js."""
from PIL import Image
import sys
sys.path.insert(0, 'gen')
from build_walk_cycles import remove_checker_background, remove_magenta_background
import os
import numpy as np
from scipy import ndimage
# DJ Renik: key the magenta GPT Image backdrop once into gen/npc_src/renik.png (largest blob + attached props).
if os.path.exists('gen/npc_src/renik_raw.png'):
    a = np.array(remove_magenta_background(Image.open('gen/npc_src/renik_raw.png')))
    lab, k = ndimage.label(a[..., 3] > 0, structure=np.ones((3, 3)))
    if k:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        a[..., 3] = np.where(sizes[lab] >= max(60, sizes.max() * .01), a[..., 3], 0)
    im = Image.fromarray(a); im.crop(im.getbbox()).save('gen/npc_src/renik.png')
# Fifth atlas slot retains the saved NPC id 'halina', but displays Irenka; Kuba hosts the range.
ORDER = ['kasia', 'marcin', 'damian', 'grandpa', 'irenka', 'kuba', 'michal', 'mateusz', 'patryk', 'zbyszek', 'wesoly_swiat', 'edytka', 'renik', 'soltys']
CELL_W, CELL_H, FOOT, TARGET_H = 130, 170, 6, 150
atlas = Image.new('RGBA', (CELL_W * len(ORDER), CELL_H), (0, 0, 0, 0))
for i, n in enumerate(ORDER):
    # Keep the stable internal NPC id `michal` for save data and map references;
    # the in-world display name and source sprite are now Bukała.
    source_name = 'bukala' if n == 'michal' else n
    im = Image.open(f'gen/npc_src/{source_name}.png').convert('RGBA')
    if n in {'zbyszek', 'wesoly_swiat'}:
        im = remove_checker_background(im)
    im = im.crop(im.getbbox())
    s = TARGET_H / im.height; im = im.resize((round(im.width * s), TARGET_H), Image.LANCZOS)
    if im.width > CELL_W: im = im.resize((CELL_W, round(im.height * CELL_W / im.width)), Image.LANCZOS)
    atlas.alpha_composite(im, (i * CELL_W + (CELL_W - im.width) // 2, CELL_H - FOOT - im.height))
atlas.save('docs/img/npcs.png'); print('docs/img/npcs.png')

# ---- animals: pig + dog, 4 frames each (0-1 run right, 2 run toward camera, 3 run away) ----
import sys; sys.path.insert(0, 'gen')
from slice_sheet import frames_grid
A_W, A_H, A_TARGET = 110, 90, 70
animals = Image.new('RGBA', (A_W * 4, A_H * 2), (0, 0, 0, 0))
for r, name in enumerate(['pig', 'dog']):
    frs = frames_grid(f'gen/{name}_raw.png', 1, 4)[0]
    s = A_TARGET / max(f['h'] for f in frs)
    for c, f in enumerate(frs):
        im = Image.fromarray(f['img']); im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        animals.alpha_composite(im, (int(c * A_W + A_W / 2 - f['ax'] * s), int(r * A_H + A_H - 4 - im.height)))
animals.save('docs/img/animals.png'); print('docs/img/animals.png')
