"""Image helpers for the pose pipeline (key magenta, find figures, shrink + selective outline, shared palette).
Copied from gen/marty/build_marty.py so gen/poses is self-contained."""
import numpy as np
from PIL import Image
from scipy import ndimage

SEL_OUTLINE = True
OUTLINE = (24, 22, 26, 255)
COLOURS = 32


def key(img):
    px = np.asarray(img.convert("RGB")).astype(np.int32)
    r, g, b = px[..., 0], px[..., 1], px[..., 2]
    bg = ((r > 150) & (b > 150) & (g < 110) & (np.abs(r - b) < 90)) | ((r > 120) & (b > 110) & (g < r - 50) & (g < b - 40))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    lab, n = ndimage.label(alpha > 0, structure=np.ones((3, 3)))
    sizes = ndimage.sum(alpha > 0, lab, range(1, n + 1))
    for i, s in enumerate(sizes, 1):
        if s < 40:
            alpha[lab == i] = 0
    return Image.fromarray(np.dstack([px.astype(np.uint8), alpha]), "RGBA")


def figures(img, row_counts):
    """Largest sum(row_counts) components are figures; smaller pieces join the nearest figure (dirt, drops, hair locks)."""
    n = sum(row_counts)
    a = np.asarray(img)[..., 3] > 0
    lab, k = ndimage.label(a, structure=np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(a, lab, range(1, k + 1))
    order = list(np.argsort(sizes)[::-1])
    main = order[:n]
    groups = {m: [m] for m in main}
    for o in order[n:]:
        sy, sx = objs[o]
        def gap(m):
            my, mx = objs[m]
            return max(0, mx.start - sx.stop, sx.start - mx.stop) + max(0, my.start - sy.stop, sy.start - my.stop)
        best = min(main, key=gap)
        if gap(best) < 60:
            groups[best].append(o)
    figs = []
    for m, members in groups.items():
        mask = np.isin(lab, [i + 1 for i in members])
        ys, xs = np.nonzero(mask)
        box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        cut = np.asarray(img).copy(); cut[..., 3] = np.where(mask, cut[..., 3], 0)
        figs.append((box, Image.fromarray(cut).crop(box)))
    figs.sort(key=lambda f: (f[0][1] + f[0][3]) / 2)
    rows, i = [], 0
    for c in row_counts:
        rows.append([f[1] for f in sorted(figs[i:i + c], key=lambda f: f[0][0])]); i += c
    return rows


def shrink(fr, s):
    w, h = max(1, round(fr.width * s)), max(1, round(fr.height * s))
    fr = fr.resize((w, h), Image.Resampling.BOX)
    fr.putalpha(fr.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
    a = np.asarray(fr).copy()
    op = a[..., 3] > 0
    lab, n = ndimage.label(op, structure=np.ones((3, 3)))          # drop 1-3 px specks left by the downscale
    for i, sz in enumerate(ndimage.sum(op, lab, range(1, n + 1)), 1):
        if sz < 4:
            a[lab == i, 3] = 0
    a = np.pad(a, ((1, 1), (1, 1), (0, 0)))                       # bold outline: 4-neighbour ring in near-black
    op = a[..., 3] > 0
    ring = ndimage.binary_dilation(op, structure=ndimage.generate_binary_structure(2, 1)) & ~op
    if SEL_OUTLINE:
        rgb = a[..., :3].astype(np.float32); w = op.astype(np.float32)[..., None]
        acc = np.zeros_like(rgb); cnt = np.zeros(op.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(rgb * w, (dy, dx), (0, 1)); cnt += np.roll(op.astype(np.float32), (dy, dx), (0, 1))
        mean = acc / np.maximum(cnt, 1)[..., None]
        # only add the ring where the existing edge is NOT already dark: otherwise raw outline + ring = 2 px thick
        lum = mean.mean(2); ring = ring & (lum >= 85)
        a[ring, :3] = np.clip(mean[ring] * 0.42 + np.array([10, 9, 14]) * 0.58, 0, 255).astype(np.uint8)
        a[ring, 3] = 255
    else:
        a[ring] = OUTLINE
    return Image.fromarray(a, "RGBA")


def quantise(images):
    """One shared palette (COLOURS) for all outputs; alpha stays hard."""
    allpx = np.concatenate([np.asarray(im).reshape(-1, 4) for im in images])
    op = allpx[allpx[:, 3] > 0][:, :3]
    sample = Image.fromarray(op.reshape(1, -1, 3).astype(np.uint8), "RGB")
    pal = sample.quantize(COLOURS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for im in images:
        rgb = im.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB")
        q = np.dstack([np.asarray(rgb), np.asarray(im)[..., 3]])
        out.append(Image.fromarray(q.astype(np.uint8), "RGBA"))
    return out
