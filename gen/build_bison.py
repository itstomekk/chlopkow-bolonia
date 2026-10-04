"""Żubr (European bison) sprite: generate with Codex GPT Image from approved anchors, then
convert to the game grid (style guide v0.1, same pixel density as critters: ~2.1 art px per world px).

    python gen/build_bison.py            # generate raw + build docs/img/bison.png
    python gen/build_bison.py --process  # rebuild from gen/critters_src/bison_raw.png only

Output: docs/img/bison.png = 4 frames (walk1, walk2, stand, graze), cells 96x80, feet at y=77, facing right.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'gen'))
from build_walk_cycles import remove_magenta_background  # noqa: E402

CODEX_PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
RAW = ROOT / 'gen/critters_src/bison_raw.png'
OUT = ROOT / 'docs/img/bison.png'
CELL_W, CELL_H, FOOT, BODY_H = 96, 80, 77, 60
REFS = [ROOT / 'gen/pilot_2026-10-02/ref_shrine_stone.png', ROOT / 'gen/pilot_2026-10-02/ref_cross_iron.png',
        ROOT / 'gen/critters_src/boar_row.png']
PROMPT = (
    "Create a sprite strip of one European bison (Polish zubr, wisent) for a cozy Polish village pixel-art game, "
    "side view facing right, exactly 4 frames in one horizontal row with equal spacing: slow dignified walk step 1, "
    "walk step 2, standing proudly, grazing with head lowered. Massive dark brown body, tall shoulder hump, thick "
    "shaggy mane and beard, short curved horns, slimmer lighter hindquarters, all frames the same size with hooves on "
    "the same baseline. Each frame drawn on an approximately 96x64 pixel grid. The third reference is a boar sprite "
    "from the same game: match its pixel size, outline and shading exactly. "
    "Match exactly the art style of the reference images: genuine low-resolution game pixel art with chunky crisp "
    "square pixels, large flat color clusters, a 1 pixel dark outline, simple 2-3 step shading lit from the upper left, "
    "muted earthy palette. About 20 flat colors total, no anti-aliasing, no smooth gradients, no fine noise, no painted "
    "texture, no photorealism. Plain perfectly flat solid magenta #FF00FF background for removal, no ground, no cast "
    "shadow, no text."
)


def generate():
    args = [CODEX_PY, str(ROOT / 'gen/codex_gen.py'), '--aspect', 'landscape', '--prompt', PROMPT, '--out', str(RAW)]
    for r in REFS:
        args += ['--ref', str(r)]
    subprocess.run(args, cwd=ROOT, check=True)


def process():
    arr = np.array(remove_magenta_background(Image.open(RAW)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        arr[(lab > 0) & (sizes[lab] < max(60, sizes.max() * 0.01)), 3] = 0
    im = Image.fromarray(arr); im = im.crop(im.getbbox())
    cols = np.array(im.getchannel('A')).max(0) > 0
    lab, _ = ndimage.label(cols)
    spans = [s[0] for s in ndimage.find_objects(lab) if s[0].stop - s[0].start > im.width * 0.08]
    if len(spans) != 4:
        raise RuntimeError(f'expected 4 frames, found {len(spans)}')
    frames = [im.crop((s.start, 0, s.stop, im.height)) for s in spans]
    frames = [f.crop(f.getbbox()) for f in frames]
    k = BODY_H / max(f.height for f in frames)
    strip = Image.new('RGBA', (CELL_W * 4, CELL_H), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        w, h = max(1, round(f.width * k)), max(1, round(f.height * k))
        if w > CELL_W - 2:
            h = round(h * (CELL_W - 2) / w); w = CELL_W - 2
        f = f.resize((w, h), Image.Resampling.BOX)
        strip.alpha_composite(f, (i * CELL_W + (CELL_W - w) // 2, FOOT + 1 - h))
    a = np.array(strip.getchannel('A')) >= 128
    rgb = np.array(strip.convert('RGB').quantize(colors=24, dither=Image.Dither.NONE).convert('RGB'))
    out = np.dstack([rgb, np.where(a, 255, 0).astype(np.uint8)]); out[~a, :3] = 0
    Image.fromarray(out).save(OUT, optimize=True)
    print(OUT, Image.fromarray(out).size)


if __name__ == '__main__':
    if '--process' not in sys.argv:
        generate()
    process()
