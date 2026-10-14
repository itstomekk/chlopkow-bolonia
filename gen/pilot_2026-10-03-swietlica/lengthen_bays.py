"""Deterministic 'longer' świetlica: repeat window bays of the picked v7 sprite (pixel-exact, no generation).

    python lengthen_bays.py [n ...]      -> annex_b<n>.png with n extra bays (default 2 4)
The sprite is drawn on a diagonal (the building drifts right as it goes down), so a bay is a (period P rows,
shift s px) translation. (P, s) is found by matching the hall body against itself; the inserted bay and
everything below it are shifted by s per bay, so roof, walls, windows and outline stay continuous.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

D = Path(__file__).resolve().parent
src = np.array(Image.open(D / "annex_v7.png").convert("RGBA")).astype(int)
H, W = src.shape[:2]
lo, hi = int(H * 0.25), int(H * 0.6)          # hall body, between the north end and the south annex


def shifted(a, s):
    out = np.zeros_like(a)
    if s >= 0: out[:, s:] = a[:, :a.shape[1] - s]
    else: out[:, :s] = a[:, -s:]
    return out


best = None
for P in range(6, 22):
    for s in range(0, 6):
        a, b = shifted(src[lo:hi - P], s), src[lo + P:hi]
        err = np.abs(a - b).sum() / a.size
        if best is None or err < best[2]:
            best = (P, s, err)
P, s, err = best
cut = lo + P   # insert after the first full bay of the body
print(f"bay period {P} rows, shift {s} px, match err {err:.2f}, cut at row {cut}")
for n in [int(x) for x in sys.argv[1:]] or [2, 4]:
    Wn = W + n * s
    pad = lambda a, k: np.pad(a, ((0, 0), (k, Wn - W - k), (0, 0)))
    parts = [pad(src[:cut], 0)]
    for i in range(1, n + 1):
        parts.append(pad(src[cut - P:cut], i * s))
    parts.append(pad(src[cut:], n * s))
    out = np.concatenate(parts, axis=0).astype(np.uint8)
    Image.fromarray(out).save(D / f"annex_b{n}.png")
    print(f"annex_b{n}.png {out.shape[1]}x{out.shape[0]}")
