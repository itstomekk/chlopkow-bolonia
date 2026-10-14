"""Build contact sheets from the street sweep + landmark references."""
import json
import os
import shutil
import sys

from PIL import Image, ImageDraw

SWEEP = sys.argv[1]
REFS = sys.argv[2]
DEST = sys.argv[3]
os.makedirs(DEST, exist_ok=True)

TILE_W, TILE_H = 400, 267
LABEL_H = 18
COLS = 3
PER_SHEET = 10  # samples per sheet (COLS tiles per row)


def sheet(entries, out_path, title):
    rows = (len(entries) + COLS - 1) // COLS
    W = COLS * TILE_W
    H = rows * (TILE_H + LABEL_H) + 26
    canvas = Image.new("RGB", (W, H), (18, 18, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((6, 6), title, fill=(180, 255, 180))
    y = 26
    for r in range(rows):
        row = entries[r * COLS:(r + 1) * COLS]
        for c, (path, label) in enumerate(row):
            try:
                im = Image.open(path).convert("RGB").resize((TILE_W, TILE_H))
            except Exception:  # noqa: BLE001
                continue
            canvas.paste(im, (c * TILE_W, y + LABEL_H))
            draw.text((c * TILE_W + 4, y + 3), label, fill=(220, 220, 220))
        y += TILE_H + LABEL_H
    canvas.save(out_path)
    print("wrote", out_path, canvas.size)


idx = json.load(open(os.path.join(SWEEP, "index.json"), encoding="utf-8"))
in_map = [r for r in idx if r.get("in_game_map") and r.get("shots")]
print(f"in-map samples: {len(in_map)}")

for start in range(0, len(in_map), PER_SHEET):
    chunk = in_map[start:start + PER_SHEET]
    entries = []
    for rec in chunk:
        for sh in rec["shots"]:
            entries.append((os.path.join(SWEEP, sh["file"]),
                            f"#{rec['i']:02d} {rec['lat']:.5f},{rec['lng']:.5f} "
                            f"{sh['view']} pano {rec['pano_dist_m']}m"))
    n = start // PER_SHEET + 1
    sheet(entries, os.path.join(DEST, f"atlas-inmap-{n}.png"),
          f"Chlopkow main street (game road) - Street View Jul 2024 - part {n}")

lm = json.load(open(os.path.join(REFS, "index.json"), encoding="utf-8"))
entries = []
for label, rec in lm.items():
    for sh in rec.get("shots", []):
        entries.append((os.path.join(REFS, sh["file"]),
                        f"{label} d{sh['dist_m']}m yaw{sh['yaw']}"))
if entries:
    sheet(entries, os.path.join(DEST, "landmarks.png"),
          "Game landmarks aimed from Street View")

# full-size copies of everything collected
for src, name in ((SWEEP, "sweep"), (REFS, "landmarks")):
    dst = os.path.join(DEST, name)
    os.makedirs(dst, exist_ok=True)
    for root, _dirs, files in os.walk(src):
        for f in files:
            if f.endswith(".jpg"):
                shutil.copy2(os.path.join(root, f), os.path.join(dst, f))
    print(name, "copied", len(os.listdir(dst)), "jpg")
