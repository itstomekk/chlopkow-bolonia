"""Build the scrolling road stage for BIJATYKA (docs/img/brawl/stage_road.webp).

Input : gen/brawl/raw/road/<id>_raw.png  - one property vignette each, on magenta #FF00FF (gpt-image-2),
        gen/brawl/raw/road/bg2_raw.png   - empty sky / tree band / verge / asphalt road / meadow, 1672x941,
        gen/brawl/raw/road/side_*.png    - the same background with a side road going north in the middle,
        gen/brawl/raw/road/end_raw.png   - the east end: T-junction with the road running north.
Order : the real order along the main road, west -> east, looking north (OSM buildings and side roads projected
        on the Street View panorama line, corrected by Tomek 2026-10-12). Distances are real metres * M_TO_PX,
        pushed apart only where two vignettes would overlap too much. See plans/2026-10-10-brawl-road-arena.md.
Output: the strip, raw/road/layout.json (numbers for review sheets) and the numbers brawl.js needs.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw" / "road"
OUT = ROOT.parent.parent / "docs" / "img" / "brawl" / "stage_road.webp"

# id: (metres along the road, kind, short Polish name for the review sheet)
#   kind: house = vignette on the common ground line, front = small prop in front of the fences,
#   back = vignette set further back (smaller, higher), road:<variant> = side road insert (side_<variant>_raw.png)
ITEMS = {
    "track96": (96, "road:track", "polna droga"),
    "h00": (140, "house", "nr 27A"),
    "h01": (255, "house", "nr 27"),
    "h02": (328, "house", "nr 26, garaż"),
    "h03": (366, "house", "nr 25"),
    "h04": (404, "house", "nr 24"),
    "h05": (430, "house", "nr 23"),
    "road469": (462, "road:asphalt", "droga przy kapliczce"),
    "kapliczka": (478, "front", "kapliczka"),
    "h07": (500, "house", "nr 19"),
    "h08": (522, "house", "niebieski dach"),
    "booths": (548, "house", "budki"),
    "track569": (572, "road:track", "polna droga"),
    "h09": (600, "house", "drewniany w krzakach"),
    "track625": (626, "road:track", "droga w prawo"),
    "orange": (652, "house", "pomarańczowy"),
    "pks": (676, "front", "przystanek PKS"),
    "h10": (687, "house", "chatka, zielona brama"),
    "h11": (712, "house", "szary, wysoki"),
    "h12": (759, "house", "stodoła + biały domek"),
    "h12b": (800, "house", "dom z wieżyczką"),
    "h13": (897, "house", "grafitowy z balkonem"),
    "gate": (921, "house", "duża brama"),
    "h14": (946, "house", "kremowy, czarna brama"),
    "h15": (982, "back", "miętowy"),
    "h16": (1018, "house", "biały z gankiem"),
    "h17": (1043, "house", "bordowy w krzakach"),
    "h18": (1074, "house", "pomarańczowy drewniany"),
}
END_M = 1150          # T-junction with the road going north
SIZE = {"kapliczka": 0.55, "h02": 0.8, "h15": 0.85, "pks": 0.55}   # extra scale per vignette
BACK_LIFT = 22        # px: a "back" vignette stands this much higher (further from the road)
M_TO_PX = 12.0
SCALE = 0.46          # vignette size relative to the 1672 px raw image, in strip pixels
ROAD_CLEAR = 330      # px kept free of houses around a side road
MINSEP = 0.55         # neighbouring vignettes overlap (their trees) at most down to this share of the summed half-widths
LEAD = 300
H = 720


def key(im):
    a = np.array(im.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 170) & (b > 170) & (g < 110) & (abs(r - b) < 90)
    out = np.zeros(a.shape[:2] + (4,), np.uint8)
    out[..., :3] = a
    out[..., 3] = np.where(m, 0, 255)
    return Image.fromarray(out, "RGBA")


def load_h(path):
    im = Image.open(path).convert("RGB")
    return im.resize((round(im.width * H / im.height), H), Image.LANCZOS)


def ramp_mask(w, fade):
    x = np.arange(w)
    r = np.clip(np.minimum(x, w - 1 - x) / fade, 0, 1)
    return Image.fromarray((np.tile(r[None, :], (H, 1)) * 255).astype(np.uint8), "L")


def main():
    bg = Image.open(RAW / "bg2_raw.png").convert("RGB")
    a = np.array(bg).astype(int)
    road_row = next(y for y in range(300, 700) if (a[y, :, 1] - a[y, :, 0]).mean() < 8)
    bgs = load_h(RAW / "bg2_raw.png")
    road = round(road_row * H / bg.height)
    kind = {k: v[1] for k, v in ITEMS.items()}
    sprites = {}
    for k, (m, kd, _) in ITEMS.items():
        if kd.startswith("road"):
            continue
        o = key(Image.open(RAW / f"{k}_raw.png"))
        c = o.crop(o.getbbox())
        s = SCALE * SIZE.get(k, 1)
        sprites[k] = c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS)
    # chain the vignettes by real metres, pushing apart only where they would overlap too much
    # side roads take part in the chain with a fixed clear width, so no house hides them
    chain = sorted([k for k in ITEMS if kind[k] != "front"], key=lambda k: ITEMS[k][0])
    half = lambda k: ROAD_CLEAR / 2 if kind[k].startswith("road") else sprites[k].width / 2 * MINSEP
    pos, shift, prev = {}, 0.0, None
    for k in chain:
        x = LEAD + ITEMS[k][0] * M_TO_PX + shift
        if prev is not None:
            need = pos[prev] + half(prev) + half(k)
            if x < need:
                shift += need - x
                x = need
        pos[k], prev = x, k

    def at(m):   # strip x of a metre position, interpolated along the chain
        pts = [(ITEMS[k][0], pos[k]) for k in chain]
        if m <= pts[0][0]:
            return pts[0][1] + (m - pts[0][0]) * M_TO_PX
        if m >= pts[-1][0]:
            return pts[-1][1] + (m - pts[-1][0]) * M_TO_PX
        for (m0, x0), (m1, x1) in zip(pts, pts[1:]):
            if m0 <= m <= m1:
                return x0 + (x1 - x0) * (m - m0) / max(1e-6, m1 - m0)

    for k in ITEMS:
        if k not in pos:
            pos[k] = at(ITEMS[k][0])
    end = load_h(RAW / "end_raw.png")
    last = [k for k in chain if k in sprites][-1]
    endx = round(max(at(END_M) - end.width * .62, pos[last] + sprites[last].width / 2 - end.width * .3))
    total = endx + end.width
    strip = Image.new("RGB", (total, H))
    flip = bgs.transpose(Image.FLIP_LEFT_RIGHT)
    for i in range(0, total, bgs.width):
        strip.paste(bgs if (i // bgs.width) % 2 == 0 else flip, (i, 0))
    # side roads going north: the middle half of the side_* backgrounds, cross-faded in
    for k in ITEMS:
        if kind[k].startswith("road:"):
            sd = load_h(RAW / f"side_{kind[k].split(':')[1]}_raw.png")
            mid = sd.crop((round(sd.width * .22), 0, round(sd.width * .78), H))
            strip.paste(mid, (round(pos[k] - mid.width / 2), 0), ramp_mask(mid.width, 120))
    em = np.tile(np.clip(np.arange(end.width) / 160, 0, 1)[None, :], (H, 1))
    strip.paste(end, (endx, 0), Image.fromarray((em * 255).astype(np.uint8), "L"))
    strip = strip.convert("RGBA")
    layer = {"back": 0, "house": 1, "front": 2}
    for k in sorted(sprites, key=lambda k: (layer[kind[k]], pos[k])):
        c = sprites[k]
        y = road + (6 if kind[k] == "front" else -4 - (BACK_LIFT if kind[k] == "back" else 0)) - c.height
        strip.alpha_composite(c, (round(pos[k] - c.width / 2), y))
    strip.convert("RGB").save(OUT, "WEBP", quality=84, method=6)
    print(f"{OUT.name}: {total}x{H}px, road top {road}px = {road / H:.4f}, world {round(total * 0.75)} game px, {OUT.stat().st_size // 1024} KB")
    order = sorted(ITEMS, key=lambda k: pos[k])
    layout = [{"nr": i + 1, "id": k, "x": round(pos[k]), "w": sprites[k].width if k in sprites else 0,
               "h": sprites[k].height if k in sprites else 0, "m": ITEMS[k][0], "kind": kind[k], "name": ITEMS[k][2]}
              for i, k in enumerate(order)]
    (RAW / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1), encoding="utf8")
    print(" ".join(f"{l['nr']}:{l['id']}@{l['x']}" for l in layout))


if __name__ == "__main__":
    sys.exit(main())
