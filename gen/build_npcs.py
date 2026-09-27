"""Pack NPC sprites (gen/npc_src/*.png, transparent 8-bit sprites from the Grand Theft Tractor video)
into docs/img/npcs.png: 4 cells of 130x170, feet 6 px above the cell bottom. Order must match NPC_IDX in docs/js/game.js."""
from PIL import Image
ORDER = ['kasia', 'marcin', 'damian', 'grandpa', 'halina']
CELL_W, CELL_H, FOOT, TARGET_H = 130, 170, 6, 150
atlas = Image.new('RGBA', (CELL_W * len(ORDER), CELL_H), (0, 0, 0, 0))
for i, n in enumerate(ORDER):
    im = Image.open(f'gen/npc_src/{n}.png').convert('RGBA'); im = im.crop(im.getbbox())
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
