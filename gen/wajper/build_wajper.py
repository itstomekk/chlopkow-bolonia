"""WAJPER round 2: key, slice, scale and pack gen/wajper/raw2/*.png into Frodo-compatible 32 px atlases.

Scale: walk side frames are fit to SIDE_W px wide (Frodo's side frames are 26; WAJPER is a bit smaller). Every pose
sheet starts with a standing side anchor; its scale makes that anchor as tall as the standing walk frame, so all
sheets share one dog size. Every animation uses frames from ONE sheet row, aligned on the ground line and on the
x-centroid of the lower body, so same-body animations (yawn, tilt, pant, lick) do not jump or zoom.
All frames are quantised to one shared palette.

Outputs (candidates in gen/wajper/out/, not wired into docs/):
  wajper.png         64x128 walk atlas, docs/img/frodo.png contract (rows down/up/right/left, 2 frames = cols 0,2 of the 4-frame walk)
  wajper_walk4.png   128x128 4-frame walk, same rows
  wajper_poses.png   32 px strip of all poses (facing right); wajper_poses.json {cell, facing, poses, anims}
  wajper_portrait.png 96 px select-screen portrait
  review.png, anim.gif
Run: python gen/wajper/build_wajper.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW, OUT = HERE / "raw2", HERE / "out"
TILE, BOTTOM, SIDE_W, MAXDIM, COLOURS = 32, 3, 20, 29, 32
OUTLINE = (24, 22, 26, 255)   # added 1 px silhouette outline (BOX downscale washes the raw outline out)

# sheet -> rows of pose names (row 1 starts with the 'stand' anchor)
SHEETS = {
    "idle": [["stand", "pant1", "pant2", "pant3", "pant4"], ["scratch1", "scratch2", "sniff1", "sniff2"]],
    "yawn": [["_a", "yawn1", "yawn2", "yawn3", "yawn4"], ["tilt1", "tilt2", "tilt3", "tilt4"]],
    "fun": [["_a", "shake1", "shake2", "shake3", "shake4"], ["bark1", "bark2", "howl1", "howl2"]],
    "dig": [["_a", "dig1", "dig2", "dig3", "dig4"], ["playbow", "lie", "belly1", "belly2"]],
    "run": [["_a", "run1", "run2", "run3", "run4"], ["jump", "beg", "wag1", "wag2"]],
    "sleep": [["_a", "sleep1", "sleep2", "stretch1", "stretch2"], ["lick1", "lick2", "lickpaw1", "lickpaw2"]],
}
ANIMS = {"stand": ["stand"], "pant": ["pant1", "pant2", "pant3", "pant4"], "scratch": ["scratch1", "scratch2"],
         "sniff": ["sniff1", "sniff2"], "yawn": ["yawn1", "yawn2", "yawn3", "yawn3", "yawn4", "yawn1"],
         "tilt": ["tilt1", "tilt2", "tilt2", "tilt3", "tilt4", "tilt4"], "shake": ["shake1", "shake2", "shake3", "shake4"],
         "bark": ["bark1", "bark2"], "howl": ["howl1", "howl2", "howl2"], "dig": ["dig1", "dig2", "dig3", "dig4"],
         "playbow": ["playbow"], "lie": ["lie"], "belly": ["belly1", "belly2"], "run": ["run1", "run2", "run3", "run4"],
         "jump": ["jump"], "beg": ["beg"], "wag": ["wag1", "wag2"], "sleep": ["sleep1", "sleep1", "sleep2", "sleep2"],
         "stretch": ["stretch1", "stretch2"], "lick": ["lick1", "lick2", "lick1", "lick2"], "lickpaw": ["lickpaw1", "lickpaw2"]}


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
    a[ring] = OUTLINE
    return Image.fromarray(a, "RGBA")


def body_cx(fr):
    """x centroid of the lower 40% of the figure (legs/body), stable while the head moves."""
    a = np.asarray(fr)[..., 3] > 0
    lo = a[int(a.shape[0] * 0.6):]
    xs = np.nonzero(lo)[1]
    return xs.mean() if len(xs) else fr.width / 2


def place_row(frames):
    """Cells for one animation row: shared ground line, lower-body centroid at the same x."""
    cells = []
    for fr in frames:
        c = Image.new("RGBA", (TILE, TILE))
        x = round(TILE / 2 - body_cx(fr))
        x = min(max(x, 0), TILE - fr.width)
        c.alpha_composite(fr, (x, TILE - BOTTOM - fr.height))
        cells.append(c)
    return cells


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


def main():
    OUT.mkdir(exist_ok=True)
    report = {}
    walk = figures(key(Image.open(RAW / "walk.png")), [4, 4, 4, 4])
    s = SIDE_W / max(f.width for f in walk[2] + walk[3])
    walk = [[shrink(f, s) for f in row] for row in walk]
    stand_h = int(np.median([f.height for f in walk[2] + walk[3]])) - 2   # minus the added outline
    report["walk_scale"], report["stand_h"] = round(s, 4), stand_h
    walk4 = Image.new("RGBA", (TILE * 4, TILE * 4))
    for r, row in enumerate(walk):
        for c, cell in enumerate(place_row(row)):
            walk4.alpha_composite(cell, (c * TILE, r * TILE))

    names, cells = [], []
    for sheet, rows in SHEETS.items():
        figs = figures(key(Image.open(RAW / f"{sheet}.png")), [len(r) for r in rows])
        sc = stand_h / figs[0][0].height
        biggest = max(max(f.size) for row in figs for f in row) * sc
        if biggest > MAXDIM:
            report.setdefault("clamped", []).append(sheet); sc *= MAXDIM / biggest
        report[f"{sheet}_scale"] = round(sc, 4)
        for rnames, rfigs in zip(rows, figs):
            keep = [(n, shrink(f, sc)) for n, f in zip(rnames, rfigs) if not n.startswith("_")]
            # place each animation group (same prefix) on a shared centroid; anchors/singles alone
            for n, c in zip([k for k, _ in keep], place_row([f for _, f in keep])):
                names.append(n); cells.append(c)

    strip = Image.new("RGBA", (TILE * len(cells), TILE))
    for i, c in enumerate(cells):
        strip.alpha_composite(c, (i * TILE, 0))

    por = key(Image.open(RAW / "portrait.png")); por = por.crop(por.getchannel("A").getbbox())
    por = shrink(por, 90 / max(por.size))
    pc = Image.new("RGBA", (96, 96)); pc.alpha_composite(por, ((96 - por.width) // 2, 93 - por.height))

    walk4, strip = quantise([walk4, strip])
    pc = quantise([pc])[0]
    atlas = Image.new("RGBA", (TILE * 2, TILE * 4))
    for r in range(4):
        for j, c in enumerate((0, 2)):
            atlas.alpha_composite(walk4.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE)), (j * TILE, r * TILE))
    atlas.save(OUT / "wajper.png"); walk4.save(OUT / "wajper_walk4.png"); strip.save(OUT / "wajper_poses.png"); pc.save(OUT / "wajper_portrait.png")
    json.dump({"cell": TILE, "facing": "right", "poses": names, "anims": ANIMS}, open(OUT / "wajper_poses.json", "w"), indent=1)

    # checks: hard alpha, no key colour, colour count, every anim frame exists, motion between consecutive frames
    for nm, im in (("walk4", walk4), ("strip", strip), ("portrait", pc)):
        a = np.asarray(im).astype(np.int32); op = a[..., 3] > 0
        assert set(np.unique(a[..., 3])) <= {0, 255}, nm
        report[f"{nm}_magenta"] = int((op & (a[..., 0] > 150) & (a[..., 2] > 150) & (a[..., 1] < 110)).sum())
        report[f"{nm}_colours"] = len({tuple(p) for p in a[op][:, :3].tolist()})
    cell = {n: np.asarray(strip.crop((i * TILE, 0, (i + 1) * TILE, TILE))) for i, n in enumerate(names)}
    motion = {}
    for an, seq in ANIMS.items():
        assert all(f in cell for f in seq), an
        u = list(dict.fromkeys(seq))
        if len(u) > 1:
            motion[an] = min(int((np.any(cell[u[i]] != cell[u[i + 1]], axis=2)).sum()) for i in range(len(u) - 1))
    report["min_px_changed_between_frames"] = motion
    report["frame_h"] = {n: int(np.ptp(np.nonzero(cell[n][..., 3].any(1))[0])) + 1 for n in names}
    review(atlas, walk4, strip, names, pc)
    print(json.dumps(report, indent=0))


def review(atlas, walk4, strip, names, pc):
    Z, cols = 5, 10
    frodo = Image.open(ROOT / "docs" / "img" / "frodo.png").convert("RGBA")
    cw = TILE * Z + 8
    rows_p = (len(names) + cols - 1) // cols
    H = 30 + 4 * (TILE * Z + 22) + 30 + rows_p * (TILE * Z + 22) + 40 + TILE * 3 + 20
    sheet = Image.new("RGBA", (cols * cw + 20, H), (58, 64, 52, 255)); d = ImageDraw.Draw(sheet)
    d.text((10, 8), "WAJPER round 2 (x5). Walk 4 frames x down/up/right/left | FRODO walk frame 1 | portrait x3", fill="white")
    y0 = 30
    for r in range(4):
        y = y0 + r * (TILE * Z + 22)
        for c in range(4):
            sheet.alpha_composite(walk4.crop((c * TILE, r * TILE, (c + 1) * TILE, (r + 1) * TILE)).resize((TILE * Z,) * 2, Image.NEAREST), (10 + c * cw, y))
        sheet.alpha_composite(frodo.crop((0, r * TILE, TILE, (r + 1) * TILE)).resize((TILE * Z,) * 2, Image.NEAREST), (30 + 4 * cw, y))
        d.text((10, y + TILE * Z + 4), ["down", "up", "right", "left"][r], fill="white")
    d.text((30 + 4 * cw, y0 - 12), "FRODO", fill="#ffd27a")
    sheet.alpha_composite(pc.resize((288, 288), Image.NEAREST), (60 + 5 * cw, y0))
    y1 = y0 + 4 * (TILE * Z + 22) + 10
    d.text((10, y1), "Poses (facing right, mirrored in-game for left):", fill="white"); y1 += 18
    for i, n in enumerate(names):
        x, y = 10 + (i % cols) * cw, y1 + (i // cols) * (TILE * Z + 22)
        sheet.alpha_composite(strip.crop((i * TILE, 0, (i + 1) * TILE, TILE)).resize((TILE * Z,) * 2, Image.NEAREST), (x, y))
        d.text((x, y + TILE * Z + 4), f"{i + 1}. {n}", fill="white")
    y2 = y1 + rows_p * (TILE * Z + 22) + 6
    d.text((10, y2), "In-game x3: FRODO | WAJPER walk right, stand, pant, shake, dig, run, sleep, beg, belly, tilt", fill="white")
    row = Image.new("RGBA", (TILE * 11, TILE)); row.alpha_composite(frodo.crop((0, 64, 32, 96)), (0, 0))
    row.alpha_composite(atlas.crop((0, 64, 32, 96)), (TILE, 0))
    for j, n in enumerate(["stand", "pant1", "shake2", "dig1", "run2", "sleep1", "beg", "belly1", "tilt2"]):
        k = names.index(n); row.alpha_composite(strip.crop((k * TILE, 0, (k + 1) * TILE, TILE)), ((j + 2) * TILE, 0))
    sheet.alpha_composite(row.resize((row.width * 3, row.height * 3), Image.NEAREST), (10, y2 + 16))
    sheet.convert("RGB").save(OUT / "review.png")

    Z2, show = 4, ["walk", "pant", "scratch", "sniff", "yawn", "tilt", "shake", "bark", "howl", "dig", "belly",
                   "run", "wag", "sleep", "stretch", "lick", "lickpaw"]
    per = 9
    frames = []
    for t in range(12):
        fr = Image.new("RGBA", (per * TILE * Z2, 2 * (TILE * Z2 + 14)), (58, 64, 52, 255)); dd = ImageDraw.Draw(fr)
        for j, a in enumerate(show):
            if a == "walk":
                cell = walk4.crop(((t % 4) * TILE, 64, (t % 4 + 1) * TILE, 96))
            else:
                seq = ANIMS[a]; k = names.index(seq[t % len(seq)]); cell = strip.crop((k * TILE, 0, (k + 1) * TILE, TILE))
            x, y = (j % per) * TILE * Z2, (j // per) * (TILE * Z2 + 14)
            fr.alpha_composite(cell.resize((TILE * Z2,) * 2, Image.NEAREST), (x, y))
            dd.text((x + 4, y + TILE * Z2), a, fill="white")
        frames.append(fr.convert("RGB"))
    frames[0].save(OUT / "anim.gif", save_all=True, append_images=frames[1:], duration=180, loop=0)


if __name__ == "__main__":
    main()
