"""A2 pilot post-processing + side-by-side comparison (2026-10-02).

Turns the raw GPT images into game-grid pixel art following the draft style rules:
key magenta -> drop debris -> downscale with BOX to the real game grid -> one shared palette
(no dither) -> hard alpha. Then builds compare.html (old vs new, in map context at game zoom).

    python gen/pilot_2026-10-02/process.py
Outputs (local candidates, NOT wired into the game): gen/pilot_2026-10-02/oak.png, boar_row.png,
asset-review/2026-10-02-pilot/compare.html
"""
import base64
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'gen'))
from build_walk_cycles import remove_magenta_background  # noqa: E402

OAK_W = 56          # world px; procedural village oaks are ~51-62 px wide (map.json)
BOAR_H = 34         # cell px of body height, same as the current boar row (critters.png row 5)
CELL, BOAR_FOOT = 64, 55
COLORS = 24


def clean(raw):
    arr = np.array(remove_magenta_background(Image.open(raw)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        arr[(lab > 0) & (sizes[lab] < max(60, sizes.max() * 0.01)), 3] = 0
    arr[arr[..., 3] == 0, :3] = 0
    return Image.fromarray(arr)


def pixelate(im, size, colors=COLORS):
    small = im.resize(size, Image.Resampling.BOX)
    a = np.array(small.getchannel('A')) >= 128
    rgb = small.convert('RGB').quantize(colors=colors, dither=Image.Dither.NONE).convert('RGB')
    out = np.dstack([np.array(rgb), np.where(a, 255, 0).astype(np.uint8)])
    out[~a, :3] = 0
    return Image.fromarray(out)


def oak():
    im = clean(D / 'oak_raw.png'); im = im.crop(im.getbbox())
    h = round(im.height * OAK_W / im.width)
    out = pixelate(im, (OAK_W, h)); out = out.crop(out.getbbox()); out.save(D / 'oak.png')
    return out


def boar():
    im = clean(D / 'boar_raw.png'); im = im.crop(im.getbbox())
    cols = np.array(im.getchannel('A')).max(0) > 0
    lab, n = ndimage.label(cols)
    spans = sorted(ndimage.find_objects(lab), key=lambda s: s[0].start)
    spans = [s[0] for s in spans if s[0].stop - s[0].start > im.width * 0.08]
    if len(spans) != 4:
        raise RuntimeError(f'expected 4 frames, found {len(spans)}')
    frames = [im.crop((s.start, 0, s.stop, im.height)) for s in spans]
    frames = [f.crop(f.getbbox()) for f in frames]
    k = BOAR_H / max(f.height for f in frames)          # one scale for all frames
    strip = Image.new('RGBA', (CELL * 4, CELL), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        f = f.resize((max(1, round(f.width * k)), max(1, round(f.height * k))), Image.Resampling.BOX)
        if f.width > CELL - 2:
            f = f.resize((CELL - 2, round(f.height * (CELL - 2) / f.width)), Image.Resampling.BOX)
        strip.alpha_composite(f, (i * CELL + (CELL - f.width) // 2, BOAR_FOOT + 1 - f.height))
    out = pixelate(strip, strip.size)                   # shared palette + hard alpha across frames
    out.save(D / 'boar_row.png')
    return out


def b64(im, z):
    im = im.resize((im.width * z, im.height * z), Image.Resampling.NEAREST)
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def context(new_oak, new_boar):
    m = json.load(open(ROOT / 'docs/map.json', encoding='utf-8'))
    g = Image.open(ROOT / 'docs/img/map_ground.png').convert('RGBA')
    o = Image.open(ROOT / 'docs/img/map_objects.png').convert('RGBA')
    old = next(x for x in m['objects'] if x.get('species') == 'oak' and x['x'] > 4000)
    x0, y0 = old['x'] - 70, old['y'] - 40
    scene = g.crop((x0, y0, x0 + 220, y0 + 130)); scene.alpha_composite(o.crop((x0, y0, x0 + 220, y0 + 130)))
    # new oak to the right of the old one, same baseline
    bx = old['x'] + old['w'] + 20 - x0
    scene.alpha_composite(new_oak, (bx, int(old['base']) - y0 - new_oak.height + 2))
    arek = Image.open(ROOT / 'docs/img/arek_sheet_8dir.png').crop((0, 0, 130, 170))
    k = 40 / 150; arek = arek.resize((round(130 * k), round(170 * k)), Image.Resampling.NEAREST)
    scene.alpha_composite(arek, (bx - 30, int(old['base']) - y0 - arek.height + 2))
    # boars on grass: old row frame 0 vs new frame 0 at their real world size (64 cell -> 64*21/44 px)
    crit = Image.open(ROOT / 'docs/img/critters.png').convert('RGBA')
    s = 64 * 21 / 44
    def at_world(cell):
        return cell.resize((round(s), round(s)), Image.Resampling.NEAREST)
    scene.alpha_composite(at_world(crit.crop((0, 5 * 64, 64, 6 * 64))), (20, 95))
    scene.alpha_composite(at_world(new_boar.crop((0, 0, 64, 64))), (60, 95))
    return scene


def main():
    o, b = oak(), boar()
    old_boar = Image.open(ROOT / 'docs/img/critters.png').convert('RGBA').crop((0, 5 * 64, 256, 6 * 64))
    scene = context(o, b)
    anchors = [Image.open(D / f'ref_{k}.png') for k in ('shrine_stone', 'cross_iron')]
    rows = [
        ('W grze (zoom 3): stary dąb | nowy dąb + Arek; na dole stary dzik | nowy dzik', b64(scene, 3)),
        ('Nowy dąb (1 piksel = 1 piksel mapy), x6', b64(o, 6)),
        ('Stary dzik (4 klatki), x4', b64(old_boar, 4)),
        ('Nowy dzik (4 klatki), x4', b64(b, 4)),
        ('Wzory stylu (kapliczka, krzyż) dla porównania', ''.join(f'<img src="{b64(a, 1)}" style="width:256px">' for a in anchors)),
    ]
    out = ROOT / 'asset-review/2026-10-02-pilot'; out.mkdir(parents=True, exist_ok=True)
    body = ''.join(f'<h3>{t}</h3>' + (src if src.startswith('<img') else f'<img src="{src}">') for t, src in rows)
    (out / 'compare.html').write_text(
        '<!doctype html><meta charset=utf-8><style>body{padding:8px}h3{font-size:14px;margin:14px 0 4px}'
        'img{image-rendering:pixelated;max-width:100%;border:1px solid var(--border,#ccc);margin-right:6px}</style>'
        '<h2>Pilot A2: dąb + dzik</h2>' + body, encoding='utf-8')
    print('oak', o.size, 'boar row', b.size, '->', out / 'compare.html')


if __name__ == '__main__':
    main()
