"""Per-building satellite check sheets: magenta = current outline (OSM + global shift + snap), 2 m grid,
used to read how far each roof really is from its outline (iteration 9c, Tomek: relative positions closer to truth)."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.argv = [sys.argv[0], "x"] + sys.argv[1:]
sys.path.insert(0, str(Path(__file__).parent))
import yard_strip as y  # noqa: E402

P = [b for b in json.loads((y.OUT / "plan.json").read_text(encoding="utf-8")) if b["yard"]]
S = 360
cells = []
for b in P:
    half = 14
    im = y.sat_crop(*b["c"], half, b["pts"], size=S)
    d = ImageDraw.Draw(im); k = S / (2 * half)              # px per metre
    for m in range(-half, half + 1, 2):
        col = (255, 255, 255) if m == 0 else (90, 90, 90)
        d.line([(S / 2 + m * k, 0), (S / 2 + m * k, S)], fill=col, width=1)
        d.line([(0, S / 2 + m * k), (S, S / 2 + m * k)], fill=col, width=1)
    d.rectangle([0, 0, 120, 18], fill=(0, 0, 0)); d.text((4, 3), f"#{len(cells) + 1} {b['id']}", fill=(255, 255, 0))
    cells.append(im)
for s in range(0, len(cells), 6):
    o = Image.new("RGB", (3 * S + 20, 2 * S + 10), (20, 20, 20))
    for i, im in enumerate(cells[s:s + 6]):
        o.paste(im, ((i % 3) * (S + 10), (i // 3) * (S + 10)))
    o.save(y.OUT / f"roof_check_{s // 6 + 1}.png")
print([(i + 1, b["id"], b["yard"], b["house"]) for i, b in enumerate(P)])
