"""Build BIJATYKA fighter atlases, item atlas and stage backgrounds from generated sheets.

Inputs  gen/brawl/raw/<fighter>_s1..s3.png  (4x3 pose grids on flat magenta, facing right)
        gen/brawl/raw/items.png             (4x2 item grid on magenta)
        gen/brawl/raw/stage_*.png           (16:9 stage art)
Outputs docs/img/brawl/<fighter>.webp + .json, items.webp + .json, stage_*.webp, preview_*.png (gen/brawl)

Frames are stored at 2x the arena's logical scale (FIG_H px standing height); the game draws them at 0.5.
Anchor (ax, ay) = foot point: ay = bottom of the figure, ax = mean x of the lower 35 % of the figure.
Run: python gen/brawl/build_fight_sprites.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "gen" / "brawl" / "raw"
OUT = ROOT / "docs" / "img" / "brawl"
PREV = ROOT / "gen" / "brawl"
VERBOSE = True
FIG_H = 200          # standing figure height in stored pixels (= 100 logical arena px)
FIG_H_BY = {"ernest": 184}   # per-fighter standing height (ERNEST is short: 184/200 = 0.92)

SHEETS = {
    "s1": ["stand", "walk1", "run1", "punch1", "punch2", "kick", "jump", "jkick", "defend", "hurt", "lying_back", "cast"],
    "s2": ["walk2", "run2", "dash", "super", "dizzy", "grab", "held", "throw", "fall", "roll", "lying_front", "getup"],
    "s3": ["w_stand", "w_walk", "w_thrust", "w_swing", "w_jump", "w_throw", "carry", "heavy_throw", "drink", "win", "pickup", "special2"],
}
# frames whose thrown object must be removed (the game spawns it as a separate entity)
DROP_DETACHED = {"cast", "w_throw", "heavy_throw"}
ITEMS = ["widly", "stone", "crate", "milk", "apple", "mushroom", "hay", "spark"]
ITEMS2 = ["rake", "shovel", "scythe", "lomza", "pieczarki", "churn", "tyre", "bucket"]
ITEMS3 = ["teczka", "pistol", "broom", "pan", "club", "picket", "rollpin", "kulka"]   # raw/weapons.png
# s4: weapon poses holding a flat CYAN marker stick/block instead of a real weapon. The builder reads the grip
# (hand point + direction to the tip) from the marker, erases it, and the game draws any weapon sprite there.
S4 = ["w_stand", "w_walk", "w_thrust", "w_swing", "w_jump", "w_throw", "w_shoot", "w_case"]
ITEM_W = {"rake": 104, "shovel": 96, "scythe": 110, "lomza": 14, "pieczarki": 40, "churn": 38, "tyre": 54, "bucket": 34, "widly": 112, "stone": 46, "crate": 44, "milk": 18, "apple": 22, "mushroom": 22, "hay": 58, "spark": 36,
          "teczka": 34, "pistol": 30, "broom": 104, "pan": 54, "club": 70, "picket": 92, "rollpin": 46, "kulka": 9}  # logical px


def key_magenta(img):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # magenta-ness: strong red+blue, weak green
    mag = np.minimum(r, b) - g
    bg = (mag > 90) & (np.abs(r - b) < 110)
    fg = ~bg
    fg = ndimage.binary_opening(fg, iterations=1)
    # despill: soften pink fringe on edge pixels
    edge = fg & ~ndimage.binary_erosion(fg, iterations=2)
    spill = edge & (mag > 25)
    a2 = a.copy()
    a2[spill, 0] = np.minimum(a2[spill, 0], a2[spill, 1] + 40)
    a2[spill, 2] = np.minimum(a2[spill, 2], a2[spill, 1] + 40)
    return a2.astype(np.uint8), fg


def components(fg, min_area=60):
    lab, n = ndimage.label(fg)
    objs = ndimage.find_objects(lab)
    areas = ndimage.sum(fg, lab, range(1, n + 1))
    out = []
    for i, (sl, ar) in enumerate(zip(objs, areas)):
        if ar < min_area:
            continue
        ys, xs = sl
        cy, cx = ndimage.center_of_mass(fg, lab, i + 1)
        out.append({"id": i + 1, "area": float(ar), "x0": xs.start, "x1": xs.stop, "y0": ys.start, "y1": ys.stop, "cx": cx, "cy": cy})
    return lab, out


def slice_grid(path, cols, rows, names):
    img = Image.open(path)
    rgb, fg = key_magenta(img)
    H, W = fg.shape
    lab, comps = components(fg)
    # the N largest components are the figures; assign them to grid cells, then attach every
    # smaller piece (stars, motion lines, thrown objects) to the nearest figure
    n = cols * rows
    bodies = sorted(comps, key=lambda c: -c["area"])[:n]
    if len(bodies) < n:
        raise SystemExit(f"{path.name}: found {len(bodies)} figures, expected {n}")
    cells = {}
    for c in bodies:
        col = min(cols - 1, int(c["cx"] / (W / cols)))
        row = min(rows - 1, int(c["cy"] / (H / rows)))
        if row * cols + col in cells:
            raise SystemExit(f"{path.name}: two figures in cell {row * cols + col}")
        cells[row * cols + col] = [c]

    def gap(a, b):
        dx = max(0, max(a["x0"], b["x0"]) - min(a["x1"], b["x1"]))
        dy = max(0, max(a["y0"], b["y0"]) - min(a["y1"], b["y1"]))
        return (dx * dx + dy * dy) ** .5
    for c in comps:
        if c in bodies:
            continue
        k, body = min(((k, v[0]) for k, v in cells.items()), key=lambda kv: gap(c, kv[1]))
        c["gap"] = gap(c, body)
        cells[k].append(c)
    frames = {}
    for k, name in enumerate(names):
        cs = cells[k]
        main = cs[0]
        keep = [main]
        for c in cs[1:]:
            # small detached bits (stars, motion lines) may float near the figure; bigger
            # detached objects (a flying pitchfork, a thrown stone) belong to no frame
            limit = 6 if name in DROP_DETACHED or c["area"] > 1200 else 45
            if name == "carry" and c["area"] > 600:
                limit = -1   # never keep separate big pieces in the carry pose (stone, a neighbour's flying pitchfork)
            if c["gap"] <= limit:
                keep.append(c)
            elif VERBOSE:
                print(f"  {path.name}:{name} drop piece area={c['area']:.0f} gap={c['gap']:.0f} at x={c['x0']}-{c['x1']} y={c['y0']}-{c['y1']}")
        x0 = min(c["x0"] for c in keep); x1 = max(c["x1"] for c in keep)
        y0 = min(c["y0"] for c in keep); y1 = max(c["y1"] for c in keep)
        m = np.isin(lab[y0:y1, x0:x1], [c["id"] for c in keep])
        rgba = np.dstack([rgb[y0:y1, x0:x1], (m * 255).astype(np.uint8)])
        frames[name] = {"img": Image.fromarray(rgba, "RGBA"), "main_y1": main["y1"] - y0}
    return frames


def strip_stone(im):
    """Remove the generated grey field stone held over the head; the game draws the real carried item."""
    a = np.asarray(im).copy()
    rgb = a[..., :3].astype(np.int32); al = a[..., 3] > 0
    H = a.shape[0]
    mx, mn = rgb.max(-1), rgb.min(-1)
    grey = al & (mx - mn < 64) & (mx > 95) & (mx < 225) & (rgb[..., 0] - rgb[..., 2] < 64)
    grey[int(H * .42):] = False
    grey = ndimage.binary_opening(grey, iterations=1)
    lab, n = ndimage.label(grey)
    if not n:
        return im
    sizes = ndimage.sum(grey, lab, range(1, n + 1))
    stone = lab == (int(np.argmax(sizes)) + 1)
    stone = ndimage.binary_fill_holes(ndimage.binary_closing(stone, iterations=3))
    ring = ndimage.binary_dilation(stone, iterations=5) & al & (mx < 70)   # its dark outline
    kill = stone | ring
    a[kill, 3] = 0
    keep = a[..., 3] > 0
    lab2, n2 = ndimage.label(keep)
    if n2 > 1:
        sizes2 = ndimage.sum(keep, lab2, range(1, n2 + 1))
        big = int(np.argmax(sizes2)) + 1
        for i in range(1, n2 + 1):
            if i != big and sizes2[i - 1] < 400:
                a[lab2 == i, 3] = 0
    out = Image.fromarray(a, "RGBA")
    return out.crop(out.getbbox())


def cyan_mask(a):
    rgb = a[..., :3].astype(np.int32)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (a[..., 3] > 0) & (g - r > 70) & (b - r > 70) & (g > 120) & (b > 120)


def take_grip(im, name):
    """Find the cyan marker in a weapon pose, return (image without it, grip dict or None)."""
    a = np.asarray(im).copy()
    m = cyan_mask(a)
    if m.sum() < 12:
        return im, None
    body = (a[..., 3] > 0) & ~ndimage.binary_dilation(m, iterations=2)
    by, bx = np.nonzero(body)
    bc = np.array([bx.mean(), by.mean() - (by.max() - by.min()) * .1]) if len(bx) else None
    ys, xs = np.nonzero(m)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    c = pts.mean(0)
    if name in ("w_shoot", "w_case"):
        hand = c; d = np.array([1.0, 0.0]) if name == "w_shoot" else np.array([0.0, 1.0])
        tip = hand + d * 10
    else:
        u, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
        d = vt[0]
        t = (pts - c) @ d
        t0, t1 = t.min(), t.max()
        bins = np.zeros(int(t1 - t0) // 2 + 1, bool); bins[((t - t0) // 2).astype(int)] = True
        best, run, start = (0, 0), 0, 0
        for i, v in enumerate(bins):
            if not v:
                if run == 0: start = i
                run += 1
                if run > best[0]: best = (run, start)
            else:
                run = 0
        if best[0] >= 3:
            th = t0 + (best[1] + best[0] / 2) * 2
        elif bc is not None:
            th = float(np.clip((bc - c) @ d, t0, t1))
        else:
            th = t0
        hand = c + d * th
        e0, e1 = c + d * t0, c + d * t1
        if name in ("w_stand", "w_walk"):        # carried upright: the business end is up
            tip = e0 if e0[1] < e1[1] else e1
        elif name in ("w_thrust", "w_jump"):     # stabbing: the business end is in front
            tip = e0 if e0[0] > e1[0] else e1
        else:
            tip = e0 if np.linalg.norm(e0 - hand) > np.linalg.norm(e1 - hand) else e1
    kill = ndimage.binary_dilation(m, iterations=1)
    rgb = a[..., :3].astype(np.int32)
    near = ndimage.binary_dilation(m, iterations=3) & (rgb[..., 2] - rgb[..., 0] > 30) & (rgb[..., 1] - rgb[..., 0] > 30)
    a[kill | near, 3] = 0
    keep = a[..., 3] > 0
    lab, n = ndimage.label(keep)
    if n > 1:
        sizes = ndimage.sum(keep, lab, range(1, n + 1)); big = int(np.argmax(sizes)) + 1
        for i in range(1, n + 1):
            if i != big and sizes[i - 1] < 60:
                a[lab == i, 3] = 0
    out = Image.fromarray(a, "RGBA")
    return out, {"hx": round(float(hand[0]), 1), "hy": round(float(hand[1]), 1), "tx": round(float(tip[0]), 1), "ty": round(float(tip[1]), 1)}


def anchor(im):
    a = np.asarray(im)[..., 3] > 127
    ys, xs = np.nonzero(a)
    bot = ys.max(); top = ys.min()
    low = ys >= top + (bot - top) * 0.65
    return float(xs[low].mean()), float(bot + 1)


def scale_rgba(im, s):
    w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
    a = np.asarray(im).astype(np.float32) / 255
    pre = a.copy(); pre[..., :3] *= pre[..., 3:4]
    small = np.stack([np.asarray(Image.fromarray((pre[..., i] * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255 for i in range(4)], -1)
    al = small[..., 3]
    rgb = np.where(al[..., None] > 1e-3, small[..., :3] / np.maximum(al[..., None], 1e-3), 0)
    hard = (al > 0.5).astype(np.float32)
    out = np.dstack([np.clip(rgb, 0, 1), hard])
    return Image.fromarray((out * 255).astype(np.uint8), "RGBA")


def pack(frames, path_png, path_json, extra=None):
    pad = 2
    order = list(frames)
    maxw = 1400
    x = y = rowh = 0
    pos = {}
    for n in order:
        im = frames[n]["img"]
        if x + im.width + pad > maxw:
            x = 0; y += rowh + pad; rowh = 0
        pos[n] = (x, y); x += im.width + pad; rowh = max(rowh, im.height)
    atlas = Image.new("RGBA", (maxw, y + rowh), (0, 0, 0, 0))
    meta = {"scale": 0.5, "frames": {}}
    for n in order:
        im = frames[n]["img"]; px, py = pos[n]
        atlas.alpha_composite(im, (px, py))
        meta["frames"][n] = {"x": px, "y": py, "w": im.width, "h": im.height, "ax": round(frames[n]["ax"], 1), "ay": round(frames[n]["ay"], 1)}
        if frames[n].get("grip"):
            meta["frames"][n]["grip"] = frames[n]["grip"]
    if extra:
        meta.update(extra)
    atlas.save(path_png.with_suffix('.webp'), quality=92, alpha_quality=100, method=6)
    if path_png.exists():
        path_png.unlink()
    path_json.write_text(json.dumps(meta, indent=1))
    return atlas, meta


def preview(frames, path, bg=(40, 60, 40)):
    cell = 240
    names = list(frames)
    cols = 6
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), bg + (255,))
    for i, n in enumerate(names):
        im = frames[n]["img"]
        cx, cy = (i % cols) * cell + cell // 2, (i // cols) * cell + cell - 20
        sheet.alpha_composite(im, (int(cx - frames[n]["ax"]), int(cy - frames[n]["ay"])))
    sheet.convert("RGB").save(path)


def build_fighter(fid):
    raw = {}
    for s, names in SHEETS.items():
        raw.update(slice_grid(RAW / f"{fid}_{s}.png", 4, 3, names))
    beer = RAW / f"{fid}_s3beer.png"   # later edit: only its drinking cell (beer instead of milk) is used
    if beer.exists():
        raw["drink"] = slice_grid(beer, 4, 3, SHEETS["s3"])["drink"]
    carry = RAW / f"{fid}_s3carry.png"   # later edit: empty raised hands; the game draws the carried item
    if carry.exists():
        raw["carry"] = slice_grid(carry, 4, 3, SHEETS["s3"])["carry"]
    s4 = RAW / f"{fid}_s4.png"   # weapon poses with the cyan grip marker (replace the pitchfork poses of s3)
    if s4.exists():
        raw.update(slice_grid(s4, 4, 2, S4))
    stand_h = raw["stand"]["img"].height
    s = FIG_H_BY.get(fid, FIG_H) / stand_h
    frames = {}
    for n, f in raw.items():
        im = scale_rgba(f["img"], s)
        grip = None
        if s4.exists() and n in S4:
            im, grip = take_grip(im, n)
        ax, ay = anchor(im)
        frames[n] = {"img": im, "ax": ax, "ay": ay}
        if grip:
            frames[n]["grip"] = grip
        elif s4.exists() and n in S4 and VERBOSE:
            print(f"  {fid}:{n} no cyan grip found")
    atlas, meta = pack(frames, OUT / f"{fid}.png", OUT / f"{fid}.json", {"fighter": fid, "standH": FIG_H_BY.get(fid, FIG_H)})
    preview(frames, PREV / f"preview_{fid}.png")
    print(fid, "scale", round(s, 3), "atlas", atlas.size, "frames", len(frames))


def _canvas(w, h):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return im, im.load()


def football():
    im, px = _canvas(22, 22)
    pent = {(10, 10), (11, 10), (10, 11), (11, 11), (9, 10), (12, 11), (10, 9), (11, 12), (4, 8), (5, 8), (4, 9), (16, 6), (17, 6), (17, 7),
            (6, 16), (7, 16), (7, 17), (15, 16), (16, 15), (16, 16), (10, 3), (11, 3), (10, 4), (11, 18), (10, 18)}
    for y in range(22):
        for x in range(22):
            r = ((x - 10.5) ** 2 + (y - 10.5) ** 2) ** .5
            if r <= 10.5:
                px[x, y] = (20, 20, 24, 255) if r > 9.6 or (x, y) in pent else (236, 236, 230, 255) if x + y > 14 else (255, 255, 255, 255)
    return im


def hammer():
    im, px = _canvas(26, 14)
    for x in range(2, 20):
        for y in range(6, 9):
            px[x, y] = (20, 16, 12, 255) if y in (6, 8) else (150, 96, 50, 255)
    for x in range(18, 25):
        for y in range(1, 13):
            edge = x in (18, 24) or y in (1, 12)
            if y > 6 and x > 21 and not edge:
                continue
            px[x, y] = (20, 20, 24, 255) if edge else (160, 165, 175, 255)
    return im


def szarlotka():
    im, px = _canvas(26, 12)
    for y in range(12):
        for x in range(26):
            dx, dy = (x - 12.5) / 12.5, (y - 6) / 5.5
            r = dx * dx + dy * dy
            if r <= 1:
                px[x, y] = (40, 24, 10, 255) if r > .78 else (214, 160, 80, 255) if (x + y) % 4 else (240, 205, 120, 255)
                if y > 7 and r <= .78:
                    px[x, y] = (170, 110, 50, 255)
    return im


def pieczarka():
    im, px = _canvas(12, 12)
    for y in range(12):
        for x in range(12):
            if y <= 6 and ((x - 5.5) ** 2) / 30 + ((y - 6.5) ** 2) / 36 <= 1:
                px[x, y] = (40, 34, 30, 255) if ((x - 5.5) ** 2) / 30 + ((y - 6.5) ** 2) / 36 > .7 else (246, 240, 228, 255)
            elif 4 <= x <= 7 and 6 < y <= 11:
                px[x, y] = (40, 34, 30, 255) if x in (4, 7) or y == 11 else (226, 214, 196, 255)
    return im


def rzutek():   # orange clay shooting target (skeet) seen slightly from the side
    im, px = _canvas(24, 10)
    for y in range(10):
        for x in range(24):
            dx, dy = (x - 11.5) / 11.5, (y - 5) / 4.5
            r = dx * dx + dy * dy
            if r <= 1:
                px[x, y] = (40, 20, 10, 255) if r > .72 else (245, 120, 30, 255) if y < 5 else (205, 85, 20, 255)
    return im


def cytryna():   # lemon: ERNEST's thrown special (his shirt is lemon-print)
    im, px = _canvas(24, 14)
    for y in range(14):
        for x in range(24):
            dx, dy = (x - 11.5) / 11.0, (y - 6.5) / 6.0
            r = dx * dx + dy * dy
            if r <= 1 or (x in (0, 1, 22, 23) and y in (6, 7)):
                px[x, y] = (60, 50, 8, 255) if r > .74 or x in (0, 23) else (255, 226, 52, 255) if y < 7 else (232, 190, 24, 255)
    for x, y in ((8, 4), (9, 4), (14, 5)):
        px[x, y] = (255, 248, 170, 255)
    px[11, 0] = px[12, 0] = (40, 120, 40, 255)
    return im


def kluczyk():   # car key with a four-ring fob: FELCU's thrown special
    im, px = _canvas(28, 12)
    for x in range(1, 12):
        for y in range(4, 8):
            edge = y in (4, 7) or x in (1, 11)
            px[x, y] = (40, 40, 48, 255) if edge else (196, 202, 212, 255)
    for x in (4, 6, 8):
        px[x, 8] = px[x, 9] = (40, 40, 48, 255)
    for x in range(12, 27):
        for y in range(1, 11):
            edge = x in (12, 26) or y in (1, 10)
            px[x, y] = (12, 12, 16, 255) if edge else (34, 34, 42, 255)
    for i in range(4):   # four interlocking rings
        cx = 14 + i * 3
        for (x, y) in ((cx, 4), (cx + 1, 4), (cx - 1, 5), (cx + 2, 5), (cx - 1, 6), (cx + 2, 6), (cx, 7), (cx + 1, 7)):
            if 12 < x < 26:
                px[x, y] = (214, 218, 226, 255)
    return im


def smartfon():   # black smartphone seen from the side/top: ARTUR's thrown special
    im, px = _canvas(18, 10)
    for x in range(18):
        for y in range(10):
            edge = x in (0, 17) or y in (0, 9)
            if (x in (0, 17)) and y in (0, 9):
                continue
            px[x, y] = (96, 100, 120, 255) if edge else (22, 22, 30, 255)
    for x in range(2, 16):
        for y in range(2, 8):
            px[x, y] = (10, 10, 16, 255)
    for i in range(5):   # screen glint
        px[4 + i * 2, 7 - i // 2 - 1] = (74, 92, 150, 255)
    px[1, 4] = px[1, 5] = (48, 52, 70, 255)   # camera / speaker end
    return im


def deska():   # skateboard seen from the side: URBAN's thrown special
    im, px = _canvas(32, 10)
    for x in range(32):
        for y in (2, 3, 4):
            kick = x < 3 or x > 28
            yy = y - 1 if kick else y
            if y == 4 and kick:
                continue
            edge = y == 2 or x in (0, 31) or y == 4
            px[x, yy] = (60, 22, 18, 255) if edge else (222, 74, 56, 255) if x % 8 < 4 else (240, 188, 70, 255)
    for x in range(3, 29):
        px[x, 3] = (222, 74, 56, 255) if x % 8 < 4 else (240, 188, 70, 255)
    for cx in (7, 24):
        for x in range(cx - 2, cx + 3):
            px[x, 5] = (150, 154, 166, 255)
        for x in range(cx - 1, cx + 2):
            for y in range(6, 9):
                px[x, y] = (244, 238, 210, 255)
        px[cx - 2, 7] = px[cx + 2, 7] = (60, 60, 68, 255)
        px[cx, 8] = (60, 60, 68, 255)
    return im


def bitcoin():   # gold Bitcoin coin: TOMEK's thrown special
    im, px = _canvas(20, 20)
    glyph = ["010100", "111110", "110011", "110011", "111110", "110011", "110011", "111111", "010100"]
    for y in range(20):
        for x in range(20):
            r = ((x - 9.5) ** 2 + (y - 9.5) ** 2) ** .5
            if r <= 9.8:
                if r > 8.8:
                    px[x, y] = (74, 46, 6, 255)
                elif r > 7.2:
                    px[x, y] = (255, 214, 64, 255) if (x + y) < 17 else (214, 150, 20, 255)
                else:
                    px[x, y] = (247, 180, 40, 255) if (x + y) < 19 else (232, 150, 22, 255)
    for gy, row in enumerate(glyph):
        for gx, v in enumerate(row):
            if v == "1":
                px[7 + gx, 5 + gy] = (92, 52, 6, 255)
    for x, y in ((4, 5), (5, 4), (6, 4), (4, 6)):
        px[x, y] = (255, 246, 190, 255)
    return im


PROC_ITEMS = {"bitcoin": bitcoin, "cytryna": cytryna, "kluczyk": kluczyk, "smartfon": smartfon, "deska": deska, "rzutek": rzutek, "football": football, "hammer": hammer, "szarlotka": szarlotka, "pieczarka": pieczarka}


def build_items():
    raw = slice_grid(RAW / "items.png", 4, 2, ITEMS)
    raw.update(slice_grid(RAW / "items2.png", 4, 2, ITEMS2))
    raw.update(slice_grid(RAW / "weapons.png", 4, 2, ITEMS3))
    frames = {}
    for n, f in raw.items():
        s = ITEM_W[n] * 2 / f["img"].width
        im = scale_rgba(f["img"], s)
        frames[n] = {"img": im, "ax": im.width / 2, "ay": float(im.height)}
    # pixel vinyl record (Renik's special ball), drawn here rather than generated
    v = Image.new("RGBA", (22, 22), (0, 0, 0, 0)); px = v.load()
    for y in range(22):
        for x in range(22):
            r = ((x - 10.5) ** 2 + (y - 10.5) ** 2) ** .5
            if r <= 10.5:
                px[x, y] = (16, 16, 20, 255) if r > 9.6 else (210, 40, 46, 255) if r < 3.4 else (40, 40, 48, 255) if int(r) % 2 else (24, 24, 30, 255)
                if r < 1.2: px[x, y] = (240, 236, 220, 255)
                if 5 < r < 8 and x < y - 4: px[x, y] = (110, 110, 125, 255)
    v = v.resize((44, 44), Image.NEAREST)
    frames["vinyl"] = {"img": v, "ax": 22.0, "ay": 44.0}
    for name, fn in PROC_ITEMS.items():
        im = fn().resize(None, Image.NEAREST) if False else fn()
        im = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
        frames[name] = {"img": im, "ax": im.width / 2, "ay": float(im.height)}
    frames["bitcoin"]["ay"] = frames["bitcoin"]["img"].height * .62   # spins about its centre, not its bottom edge
    pack(frames, OUT / "items.png", OUT / "items.json")
    preview(frames, PREV / "preview_items.png")
    print("items", {n: frames[n]["img"].size for n in frames})


def build_stages():
    for p in sorted(RAW.glob("stage_*.png")):
        im = Image.open(p).convert("RGB")
        w, h = im.size
        tw = round(h * 16 / 9)
        if tw <= w:
            l = (w - tw) // 2; im = im.crop((l, 0, l + tw, h))
        im = im.resize((1280, 720), Image.LANCZOS)
        im.save(OUT / f"{p.stem}.webp", quality=88, method=6)
        print(p.stem, "->", (OUT / f"{p.stem}.webp").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for fid in ("arek", "edytka", "renik", "damian", "wesoly", "soltys", "michal", "ernest", "felcu", "urban", "artur", "tomek"):
        build_fighter(fid)
    build_items()
    build_stages()
