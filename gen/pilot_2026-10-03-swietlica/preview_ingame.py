"""In-context previews of świetlica candidates on the real release map (one render without the hall, then composite).

    python preview_fast.py v3 v5 v6 v7
Shadow/placement follow osm/render_map.py (sprite left edge 2284, top 4583). Leaves the worktree docs/ at HEAD.
"""
import shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

WT = Path('C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/chlopkow-release-muchy')
SRC = Path('C:/Users/Lenovo/Hermes/projects/games/arek-w-chlopkowie/gen/pilot_2026-10-03-swietlica')
OUT = Path('C:/Users/Lenovo/AppData/Local/hermes/cache/scratch/waldek')
BOX = (2190, 4520, 2390, 4720)
X, Y = 2284, 4583
Z = 4
Image.MAX_IMAGE_PIXELS = None

Image.new('RGBA', (43, 10), (0, 0, 0, 0)).save(WT / 'gen/lm_swietlica.png')
subprocess.run([sys.executable, 'osm/render_map.py'], cwd=WT, check=True, capture_output=True)
ground = Image.open(WT / 'docs/img/map_ground.png').convert('RGBA').crop(BOX)
objs = Image.open(WT / 'docs/img/map_objects.png').convert('RGBA').crop(BOX)
subprocess.run(['git', 'checkout', '--', 'docs', 'gen/lm_swietlica.png'], cwd=WT, check=True)

F = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 28)
panels = []
def hall_left(s):
    m = np.array(s.getchannel('A')) > 0
    return int(np.nonzero(m[int(m.shape[0] * 0.35): int(m.shape[0] * 0.6)].any(0))[0].min())
v7 = Image.open(SRC / 'annex_v7.png').convert('RGBA')
HL7, BOT = X + hall_left(v7), Y + v7.height   # round 3: south end and hall west wall stay where v7 has them
for v in sys.argv[1:]:
    s = Image.open(SRC / f'annex_{v}.png').convert('RGBA')
    a = np.array(s.getchannel('A')) > 0
    sx, sy = HL7 - hall_left(s), BOT - s.height
    sx = max(sx, 2284)   # nothing west of the road's east edge
    print(v, 'top-left', (sx, sy), 'size', s.size)
    g = ground.copy()
    sh = Image.fromarray(((a & (np.arange(a.shape[0])[:, None] >= s.height // 2)) * 255).astype(np.uint8))
    g.paste((58, 84, 40, 255), (sx + 5 - BOX[0], sy + 3 - BOX[1]), sh)
    g.alpha_composite(objs)
    g.alpha_composite(s, (sx - BOX[0], sy - BOX[1]))
    panels.append((v, g.resize((g.width * Z, g.height * Z), Image.Resampling.NEAREST)))
w, h = panels[0][1].size
sheet = Image.new('RGB', (w * len(panels) + 16 * (len(panels) - 1), h + 44), (20, 20, 20)); d = ImageDraw.Draw(sheet)
for i, (v, p) in enumerate(panels):
    sheet.paste(p.convert('RGB'), (i * (w + 16), 44)); d.text((i * (w + 16) + 10, 6), str(i + 1), fill=(255, 230, 80), font=F)
sheet.save(OUT / 'swietlica_candidates_ingame.png')
print('wrote', OUT / 'swietlica_candidates_ingame.png', sheet.size, [v for v, _ in panels])
