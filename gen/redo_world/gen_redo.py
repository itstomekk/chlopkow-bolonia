"""Redo of off-style world sprites (Tomek 2026-10-27): pig, hare, stray dog, fox, mouse (critters.png), minigame pig/dog (animals.png),
tractors (vehicles.png rows 0-2). Same method as gen/build_bison.py: Codex strip on magenta -> chunky pixel cells.
  python gen/redo_world/gen_redo.py gen pig hare ...   # generate raw strips (parallel)
  python gen/redo_world/gen_redo.py build              # rebuild atlases from raw/ (keeps untouched rows)
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = Path(__file__).resolve().parents[2]; RAW = Path(__file__).with_name("raw"); RAW.mkdir(exist_ok=True); sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_magenta_background  # noqa
PY = r"C:\Users\Lenovo\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe"
REFS = [ROOT / "gen/critters_src/boar_row.png", ROOT / "gen/trees_src/oak.png"]
STYLE = ("Match exactly the art style of the reference images (the boar strip and the oak are approved game assets): genuine low-resolution "
         "game pixel art, chunky crisp square pixels, large flat colour clusters, a bold dark outline 2 pixels thick, simple 2-3 step flat shading "
         "lit from the upper left, warm muted earthy palette, about 20 colours, no anti-aliasing, no gradients, no fine noise, no comic or cartoon "
         "vector look, not smooth. Plain perfectly flat solid magenta #FF00FF background, no ground, no cast shadow, no text. ")
STRIP = "Create a sprite strip for a cozy Polish village pixel-art game: exactly 4 frames in one horizontal row with equal spacing, all the same size, same baseline. "
ITEMS = {
 "pig": (STRIP + "A pink farm pig, side view facing right. Frames: walk step 1, walk step 2, standing idle, idle with head lowered sniffing. Round chunky body, thick short legs with dark hooves, curly tail, floppy ear, snout. ", "landscape"),
 "hare": (STRIP + "A brown European hare, side view facing right. Frames: hop step 1 (stretched), hop step 2 (gathered), sitting alert with long ears up, sitting with ears down grooming. Long ears, white belly, black ear tips, big hind legs. ", "landscape"),
 "stray": (STRIP + "A scruffy village stray dog (mixed breed, black and tan, shaggy, red collar), side view facing right. Frames: trot step 1, trot step 2, sniffing the ground, sitting. Sturdy, chunky legs. ", "landscape"),
 "fox": (STRIP + "A red fox with a bushy white-tipped tail, side view facing right. Frames: run step 1, run step 2, run step 3, standing alert looking forward. White chest, dark socks on the legs. ", "landscape"),
 "mouse": (STRIP + "A small grey field mouse, side view facing right. Frames: scurry step 1, scurry step 2, sitting up, nibbling. Big round ears with pink inside, pink nose, thin curved tail, chunky body (not stick legs). ", "landscape"),
 "mg_pig": (STRIP + "A pink farm pig for a chase minigame. Frames: walk step 1 side view facing right, walk step 2 side view facing right, front view facing the viewer, back view facing away from the viewer. Chunky, curly tail, floppy ears. ", "landscape"),
 "mg_dog": (STRIP + "A guard dog of a village (brown and black, shaggy, red collar). Frames: run step 1 side view facing right, run step 2 side view facing right, front view facing the viewer, back view facing away. Chunky. ", "landscape"),
 "tractor_side": ("Create one single sprite for a cozy Polish village pixel-art game: an old Ursus farm tractor, green body with red wheel arches and red cab roof, big rear wheels, small front wheels, glass cab with a small driver, exhaust pipe. Pure side view facing right, wheels on the ground. ", "square"),
 "tractor_front": ("Create one single sprite for a cozy Polish village pixel-art game: an old Ursus farm tractor, green body with red details, seen exactly from the FRONT (driving toward the viewer), grille with two headlights, two big rear wheels visible left and right, glass cab with a small driver behind. ", "square"),
 "tractor_back": ("Create one single sprite for a cozy Polish village pixel-art game: an old Ursus farm tractor, green body with red details, seen exactly from the BACK (driving away from the viewer), two big rear wheels left and right, rear of the glass cab with the driver's back, hitch. ", "square"),
}


def gen(ids):
    ps = []
    for i in ids:
        p, asp = ITEMS[i]
        a = [PY, str(ROOT / "gen/codex_gen.py"), "--aspect", asp, "--prompt", p + STYLE, "--out", str(RAW / f"{i}.png")]
        for r in REFS: a += ["--ref", str(r)]
        ps.append((i, subprocess.Popen(a, cwd=ROOT, stdout=open(RAW / f"{i}.log", "w"), stderr=subprocess.STDOUT)))
    for i, p in ps: print(i, p.wait(), flush=True)


def cutout(path):
    arr = np.array(remove_magenta_background(Image.open(path)), dtype=np.uint8)
    lab, n = ndimage.label(arr[..., 3] > 0, structure=np.ones((3, 3), bool))
    if n:
        s = np.bincount(lab.ravel()); s[0] = 0; arr[(lab > 0) & (s[lab] < max(60, s.max() * 0.01)), 3] = 0
    im = Image.fromarray(arr); return im.crop(im.getbbox())


def frames4(path):
    im = cutout(path); cols = np.array(im.getchannel("A")).max(0) > 0
    lab, _ = ndimage.label(cols); sp = [s[0] for s in ndimage.find_objects(lab) if s[0].stop - s[0].start > im.width * 0.06]
    if len(sp) != 4: raise RuntimeError(f"{path.name}: expected 4 frames, found {len(sp)}")
    return [f.crop(f.getbbox()) for f in (im.crop((s.start, 0, s.stop, im.height)) for s in sp)]


def quant(im, n=24):
    a = np.array(im.getchannel("A")) >= 128; rgb = np.array(im.convert("RGB").quantize(colors=n, dither=Image.Dither.NONE).convert("RGB"))
    o = np.dstack([rgb, np.where(a, 255, 0).astype(np.uint8)]); o[~a, :3] = 0; return Image.fromarray(o)


def row_strip(frs, w, h, foot, body_h):
    k = body_h / max(f.height for f in frs); S = Image.new("RGBA", (w * 4, h), (0, 0, 0, 0))
    for i, f in enumerate(frs):
        ww, hh = max(1, round(f.width * k)), max(1, round(f.height * k))
        if ww > w - 2: hh = round(hh * (w - 2) / ww); ww = w - 2
        S.alpha_composite(f.resize((ww, hh), Image.Resampling.BOX), (i * w + (w - ww) // 2, foot + 1 - hh))
    return S


def build():
    cj = json.load(open(ROOT / "docs/img/critters.json")); atlas = Image.open(ROOT / "docs/img/critters.png").convert("RGBA")
    for n, bh in {"pig": 34, "hare": 40, "stray": 40, "fox": 38, "mouse": 28}.items():
        p = RAW / f"{n}.png"
        if not p.exists(): continue
        y = cj["rows"][n]["row"] * 64; atlas.paste((0, 0, 0, 0), (0, y, 256, y + 64)); atlas.alpha_composite(quant(row_strip(frames4(p), 64, 64, 62, bh)), (0, y)); print("critter", n)
    atlas.save(ROOT / "docs/img/critters.png", optimize=True)
    an = Image.open(ROOT / "docs/img/animals.png").convert("RGBA")
    for row, n in ((0, "mg_pig"), (1, "mg_dog")):
        p = RAW / f"{n}.png"
        if not p.exists(): continue
        an.paste((0, 0, 0, 0), (0, row * 90, 440, row * 90 + 90)); an.alpha_composite(quant(row_strip(frames4(p), 110, 90, 85, 62)), (0, row * 90)); print("animals", n)
    an.save(ROOT / "docs/img/animals.png", optimize=True)
    v = Image.open(ROOT / "docs/img/vehicles.png").convert("RGBA")
    for r, n, mw, mh in ((0, "tractor_side", 60, 46), (1, "tractor_front", 46, 54), (2, "tractor_back", 46, 54)):
        p = RAW / f"{n}.png"
        if not p.exists(): continue
        im = cutout(p); k = min(mw / im.width, mh / im.height); v.paste((0, 0, 0, 0), (0, r * 64, 256, r * 64 + 64))
        fr = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.Resampling.BOX)
        for f, (dx, bob) in enumerate(((0, 0), (0, 1), (1, 1), (1, 0))):   # engine-rumble bob; 4 distinct frames (animals_test)
            c = Image.new("RGBA", (64, 64), (0, 0, 0, 0)); c.alpha_composite(fr, ((64 - fr.width) // 2 + dx, 62 - fr.height - bob)); v.alpha_composite(quant(c), (f * 64, r * 64))
        print("vehicle", n)
    v.save(ROOT / "docs/img/vehicles.png", optimize=True)


if __name__ == "__main__":
    gen(sys.argv[2:]) if sys.argv[1] == "gen" else build()
