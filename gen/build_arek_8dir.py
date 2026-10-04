"""Build Arek's prototype 8-direction sheet from the existing four-direction art.

The diagonal rows are deliberately marked as a prototype: they use a small
pixel-art shear of the matching front/back pose, keeping the silhouette stable
until dedicated diagonal reference art is approved.
"""
from pathlib import Path
from PIL import Image

CELL_W, CELL_H, COLS = 130, 170, 4


# Existing sheet rows: down, up, right. Left is the runtime mirror of right.
def frame(row, col, flip=False):
    im = SRC.crop((col * CELL_W, row * CELL_H, (col + 1) * CELL_W, (row + 1) * CELL_H))
    if flip:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return im


def shear(im, amount):
    """Lean a sprite by shifting scanlines, without interpolating pixels."""
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    px = im.load()
    dst = out.load()
    mid = (im.height - 1) / 2
    for y in range(im.height):
        dx = round(amount * (y - mid))
        for x in range(im.width):
            if 0 <= x + dx < im.width and px[x, y][3]:
                dst[x + dx, y] = px[x, y]
    return out


# Direction rows used by game.js. Cardinal rows are the original artwork;
# diagonals are stable sheared prototypes for this gameplay test.
ROWS = [
    ('down', lambda c: frame(0, c)),
    ('down_right', lambda c: shear(frame(0, c), .075)),
    ('right', lambda c: frame(2, c)),
    ('up_right', lambda c: shear(frame(1, c), .075)),
    ('up', lambda c: frame(1, c)),
    ('up_left', lambda c: shear(frame(1, c), -.075)),
    ('left', lambda c: frame(2, c, True)),
    ('down_left', lambda c: shear(frame(0, c), -.075)),
]

def build(source, output):
    global SRC
    SRC = Image.open(source).convert('RGBA')
    out = Image.new('RGBA', (CELL_W * COLS, CELL_H * 8), (0, 0, 0, 0))
    for row, (_, make) in enumerate(ROWS):
        for col in range(COLS):
            out.alpha_composite(make(col), (col * CELL_W, row * CELL_H))
    out.save(output)
    print(output, out.size)


build('docs/img/arek_sheet.png', 'docs/img/arek_sheet_8dir.png')

