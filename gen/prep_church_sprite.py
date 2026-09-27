"""Turn a raw GPT image into a church sprite the game picks up automatically.
  python gen/prep_church_sprite.py gen/raw/altar.png altar
  python gen/prep_church_sprite.py gen/raw/backwall.png backwall      (no keying, cropped to the 320x104 box aspect)
Keys out the magenta background, crops to the object, caps the size at 4x its box in docs/js/church.js
and writes docs/img/church/<name>.png. Names: backwall altar candles cross ambo banner mary flags flowers100 pew
confessional font soltys."""
import sys
from pathlib import Path
from PIL import Image
BOX = {'backwall': (320, 104), 'altar': (68, 45), 'candles': (24, 48), 'cross': (12, 63), 'ambo': (34, 45), 'banner': (28, 44),
       'mary': (48, 53), 'flags': (20, 70), 'flowers100': (52, 32), 'pew': (120, 20), 'confessional': (36, 39), 'font': (14, 17),
       'soltys': (28, 44)}
src, name = sys.argv[1], sys.argv[2]
if name not in BOX: sys.exit(f'unknown name {name}; use one of {", ".join(BOX)}')
im = Image.open(src).convert('RGBA'); bw, bh = BOX[name]
if name == 'backwall':   # centre-crop to the wall's aspect, keep it opaque
    W, H = im.size; t = bw / bh
    if W / H > t: nw = int(H * t); im = im.crop(((W - nw) // 2, 0, (W - nw) // 2 + nw, H))
    else: nh = int(W / t); im = im.crop((0, (H - nh) // 2, W, (H - nh) // 2 + nh))
else:
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r > 150 and b > 150 and g < 110 and abs(r - b) < 90: px[x, y] = (0, 0, 0, 0)        # magenta
            elif r > 120 and b > 120 and g < r * .6 and g < b * .6: px[x, y] = (r, min(r, b) // 2, b // 2, a)  # de-fringe
    bbox = im.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
    if not bbox: sys.exit('nothing left after keying - is the background magenta #FF00FF?')
    im = im.crop(bbox)
k = min(1, bw * 4 / im.width, bh * 4 / im.height)
if k < 1: im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
out = Path(__file__).resolve().parent.parent / 'docs' / 'img' / 'church' / f'{name}.png'
out.parent.mkdir(parents=True, exist_ok=True); im.save(out, optimize=True)
print(f'saved {out} {im.size} (box {bw}x{bh})')
