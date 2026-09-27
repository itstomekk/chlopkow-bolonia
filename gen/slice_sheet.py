"""Chroma-key magenta sprite sheets, split into frames, align (feet baseline + torso centre), pack into game atlas."""
import json, numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

def key(path):
    a = np.array(Image.open(path).convert('RGBA')).astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mag = (r > 140) & (b > 140) & (g < 120) & (np.abs(r - b) < 100)
    alpha = np.where(mag, 0, 255).astype(np.uint8)
    alpha = np.array(Image.fromarray(alpha).filter(ImageFilter.MinFilter(3)))
    spill = (r > g + 50) & (b > g + 50) & (alpha > 0)
    a[..., 0] = np.where(spill, np.minimum(r, g + 50), r); a[..., 2] = np.where(spill, np.minimum(b, g + 50), b)
    a[..., 3] = alpha
    return a.astype(np.uint8)

def blobs(a, min_px=3000):
    lab, n = ndimage.label(a[..., 3] > 0)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if (lab[sl] == i).sum() >= min_px:
            out.append(sl)
    return out

def frames_grid(path, rows, cols):
    a = key(path)
    bs = blobs(a)
    # merge small detached parts: group by grid cell using centres
    H, W = a.shape[:2]
    cells = {}
    for sl in bs:
        cy = (sl[0].start + sl[0].stop) / 2; cx = (sl[1].start + sl[1].stop) / 2
        # row/col by clustering on positions
        cells.setdefault((cy, cx), sl)
    ys = sorted({(sl[0].start + sl[0].stop) / 2 for sl in bs})
    items = sorted(bs, key=lambda sl: ((sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2))
    assert len(items) == rows * cols, f'{path}: found {len(items)} sprites, expected {rows*cols}'
    grid = [sorted(items[r * cols:(r + 1) * cols], key=lambda sl: sl[1].start) for r in range(rows)]
    out = []
    for row in grid:
        fr = []
        for sl in row:
            y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            crop = a[y0:y1, x0:x1].copy()
            m = crop[..., 3] > 0
            top = m[: max(1, int(m.shape[0] * .55))]
            cxs = np.nonzero(top)[1]
            anchor_x = cxs.mean() if len(cxs) else m.shape[1] / 2
            fr.append(dict(img=crop, ax=anchor_x, h=m.shape[0]))
        out.append(fr)
    return out

if __name__ == '__main__':
    TARGET_H = 150
    walk = frames_grid('gen/walk_sheet_v1.png', 3, 4)
    idle = frames_grid('gen/model_sheet_v1.png', 1, 4)[0]  # front, 3/4, side, back
    # normalise scale: median walk height -> TARGET_H (same factor for all frames so heights stay natural)
    import statistics
    s_walk = TARGET_H / statistics.median(f['h'] for r in walk for f in r)
    s_idle = TARGET_H / statistics.median(f['h'] for f in idle)
    cellW, cellH = 130, 170
    names = [('walk_down', walk[0], s_walk), ('walk_up', walk[1], s_walk), ('walk_right', walk[2], s_walk),
             ('idle_down', [walk[0][1]], s_walk), ('idle_right', [walk[2][1]], s_walk), ('idle_up', [walk[1][1]], s_walk)]
    total = sum(len(f) for _, f, _ in names)
    atlas = Image.new('RGBA', (cellW * 4, cellH * len(names)), (0, 0, 0, 0))
    meta = dict(image='arek_sheet.png', anims={})
    for r, (name, frs, s) in enumerate(names):
        lst = []
        for c, f in enumerate(frs):
            im = Image.fromarray(f['img']); w, h = im.size
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
            x = c * cellW + cellW / 2 - f['ax'] * s; y = r * cellH + cellH - 6 - im.size[1]
            atlas.alpha_composite(im, (int(round(x)), int(round(y))))
            lst.append(dict(x=c * cellW, y=r * cellH, w=cellW, h=cellH))
        meta['anims'][name] = dict(frames=lst)
    meta['anims']['walk_left'] = dict(frames=meta['anims']['walk_right']['frames'], flip=True)
    meta['anims']['idle_left'] = dict(frames=meta['anims']['idle_right']['frames'], flip=True)
    meta['foot'] = 6  # px from cell bottom to feet
    atlas.save('docs/img/arek_sheet.png'); json.dump(meta, open('docs/img/arek_sheet.json', 'w'), indent=1)
    prev = Image.new('RGBA', atlas.size, (60, 140, 60, 255)); prev.alpha_composite(atlas); prev.save('gen/atlas_preview.png')
    print('ok', atlas.size)
