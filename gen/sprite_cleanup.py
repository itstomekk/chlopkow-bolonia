"""Sprite cleanup + re-grid tools for character sheets (style guide v0.1, 2026-10-02).

fix_holes:  fill small enclosed transparent holes left by old magenta keying (MinFilter grew
            pinkish pixels into 3x3 holes in hair/stripes/glasses) and harden alpha to 0/255.
            Real gaps (between arm and torso, between legs) are larger and outlined dark; kept.
regrid:     re-draw a sprite on a coarse pixel grid (BOX downscale -> shared palette -> nearest
            upscale), the recipe that produced the approved Sołtys/Zbyszek cells.

    python gen/sprite_cleanup.py holes docs/img/arek_sheet_8dir.png [...]
    python gen/sprite_cleanup.py upper-holes docs/img/arek_sheet_8dir.png   # diagonal hair/glasses holes
    python gen/sprite_cleanup.py npc grandpa mateusz      # rewrites only those atlas cells
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
CELL_W, CELL_H, FOOT, TARGET_H = 130, 170, 6, 150     # gen/build_npcs.py
ORDER = ['kasia', 'marcin', 'damian', 'grandpa', 'irenka', 'kuba', 'michal', 'mateusz', 'patryk',
         'zbyszek', 'wesoly_swiat', 'edytka', 'renik', 'soltys']
SMALL, MEDIUM = 12, 60


def fix_holes_cell(cell):
    a = np.array(cell.convert('RGBA'))
    alpha = a[..., 3]
    body = alpha >= 128
    holes = ndimage.binary_fill_holes(body) & ~body
    lab, n = ndimage.label(holes)
    fill = np.zeros_like(body)
    luma = a[..., :3].astype(int) @ [299, 587, 114] // 1000
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        comp = lab == i
        size = comp.sum()
        if size > MEDIUM:
            continue
        ring = ndimage.binary_dilation(comp) & ~comp & body
        dark = (luma[ring] < 60).mean() if ring.any() else 0
        if size <= SMALL or dark < 0.6:
            fill |= comp
    solid = body | fill
    # colour filled pixels from the nearest opaque body pixel
    _, (iy, ix) = ndimage.distance_transform_edt(~body, return_indices=True)
    rgb = a[..., :3].copy()
    rgb[fill] = a[iy[fill], ix[fill], :3]
    out = np.dstack([rgb, np.where(solid, 255, 0).astype(np.uint8)])
    out[~solid, :3] = 0
    return Image.fromarray(out), int(fill.sum())


def fix_holes(path):
    im = Image.open(path).convert('RGBA')
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    filled = 0
    for y in range(0, im.height, CELL_H):
        for x in range(0, im.width, CELL_W):
            c, f = fix_holes_cell(im.crop((x, y, x + CELL_W, y + CELL_H)))
            out.paste(c, (x, y)); filled += f
    out.save(path)
    print(f'{path}: filled {filled} hole px, alpha hardened')


def fill_upper_holes(path, rows=(1, 3, 5, 7), head=0.35, chest=0.5, centre=12):
    """Fill enclosed holes in the head/glasses/collar of the given rows (default: Arek's diagonals).

    fix_holes keeps holes > MEDIUM px or ringed by dark outline, which left see-through holes in the
    hair and glasses of the diagonal frames. Here position decides: a hole whose centre lies in the top
    `head` of the sprite, or in the top `chest` and within `centre` px of the body's middle, is filled.
    Armpit gaps (side, ~0.5-0.6 height) and leg gaps (> 0.8) stay transparent.
    """
    im = np.array(Image.open(path).convert('RGBA'))
    filled = 0
    for r in rows:
        for c in range(im.shape[1] // CELL_W):
            ys0, xs0 = r * CELL_H, c * CELL_W
            a = im[ys0:ys0 + CELL_H, xs0:xs0 + CELL_W]
            body = a[..., 3] >= 128
            if not body.any():
                continue
            by, bx = np.nonzero(body)
            top, bot, mid = by.min(), by.max(), bx.mean()
            lab, n = ndimage.label(ndimage.binary_fill_holes(body) & ~body)
            fill = np.zeros_like(body)
            for i in range(1, n + 1):
                hy, hx = np.nonzero(lab == i)
                rel = (hy.mean() - top) / (bot - top)
                if rel < head or (rel < chest and abs(hx.mean() - mid) < centre):
                    fill |= lab == i
            if fill.any():
                _, (iy, ix) = ndimage.distance_transform_edt(~body, return_indices=True)
                a[fill, :3] = a[iy[fill], ix[fill], :3]
                a[fill, 3] = 255
                filled += int(fill.sum())
    Image.fromarray(im).save(path)
    print(f'{path}: filled {filled} upper-body hole px in rows {list(rows)}')


def regrid(im, grid_h=84, colors=40):
    im = im.crop(im.getbbox())
    w = max(1, round(im.width * grid_h / im.height))
    small = im.resize((w, grid_h), Image.Resampling.BOX)
    a = np.array(small.getchannel('A')) >= 128
    rgb = np.array(small.convert('RGB').quantize(colors=colors, dither=Image.Dither.NONE).convert('RGB'))
    small = Image.fromarray(np.dstack([rgb, np.where(a, 255, 0).astype(np.uint8)]))
    small, _ = fix_holes_cell(small)
    return small


def npc(names):
    atlas = Image.open(ROOT / 'docs/img/npcs.png').convert('RGBA')
    for n in names:
        i = ORDER.index(n)
        src = Image.open(ROOT / f'gen/npc_src/{"bukala" if n == "michal" else n}.png').convert('RGBA')
        small = regrid(src)
        small.save(ROOT / f'gen/npc_src/{n}_grid.png')          # coarse-grid source, for review/regeneration
        h = TARGET_H; w = round(small.width * h / small.height)
        if w > CELL_W:
            w = CELL_W; h = round(small.height * w / small.width)
        big = small.resize((w, h), Image.Resampling.NEAREST)
        atlas.paste((0, 0, 0, 0), (i * CELL_W, 0, (i + 1) * CELL_W, CELL_H))
        atlas.alpha_composite(big, (i * CELL_W + (CELL_W - w) // 2, CELL_H - FOOT - h))
        print(f'{n}: slot {i}, grid {small.size}, drawn {w}x{h}')
    atlas.save(ROOT / 'docs/img/npcs.png')


if __name__ == '__main__':
    cmd, *args = sys.argv[1:]
    if cmd == 'holes':
        for p in args:
            fix_holes(p)
    elif cmd == 'upper-holes':
        for p in args:
            fill_upper_holes(p)
    elif cmd == 'npc':
        npc(args)
