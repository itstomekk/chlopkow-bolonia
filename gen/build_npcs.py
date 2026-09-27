"""Pack NPC sprites (gen/npc_src/*.png, transparent 8-bit sprites from the Grand Theft Tractor video)
into docs/img/npcs.png: 4 cells of 130x170, feet 6 px above the cell bottom. Order must match NPC_IDX in docs/js/game.js."""
from PIL import Image
ORDER = ['kasia', 'marcin', 'damian', 'grandpa']
CELL_W, CELL_H, FOOT, TARGET_H = 130, 170, 6, 150
atlas = Image.new('RGBA', (CELL_W * len(ORDER), CELL_H), (0, 0, 0, 0))
for i, n in enumerate(ORDER):
    im = Image.open(f'gen/npc_src/{n}.png').convert('RGBA'); im = im.crop(im.getbbox())
    s = TARGET_H / im.height; im = im.resize((round(im.width * s), TARGET_H), Image.LANCZOS)
    if im.width > CELL_W: im = im.resize((CELL_W, round(im.height * CELL_W / im.width)), Image.LANCZOS)
    atlas.alpha_composite(im, (i * CELL_W + (CELL_W - im.width) // 2, CELL_H - FOOT - im.height))
atlas.save('docs/img/npcs.png'); print('docs/img/npcs.png')
