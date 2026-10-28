"""Style canon reference (Tomek 2026-10-27): IWONA, HALINA and AREK define line weight, chunkiness, head and hand size.
Writes gen/style_canon/canon_ref.png = walk-down + walk-right frames of the three, upscaled 3x with NEAREST on a flat light ground.
Used as an extra --ref image whenever a character is (re)generated. Run: python gen/style_canon/build_canon_ref.py"""
import json
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "docs" / "img"
frames = []
for cid, name in (("arek", "arek_sheet_8dir"), ("iwona", "iwona_sheet"), ("halina", "halina_sheet")):
    im = Image.open(D / f"{name}.png").convert("RGBA"); m = json.load(open(D / f"{name}.json"))
    for a in ("walk_down", "walk_right"):
        f = m["anims"][a]["frames"][0]
        c = im.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"])); frames.append(c.crop(c.getbbox()))
H = max(f.height for f in frames); S = 3; gap = 40
W = sum(f.width * S + gap for f in frames) + gap
out = Image.new("RGB", (W, H * S + 2 * gap), (226, 224, 214)); x = gap
for f in frames:
    g = f.resize((f.width * S, f.height * S), Image.NEAREST)
    out.paste(g, (x, gap + H * S - g.height), g); x += g.width + gap
out.save(Path(__file__).with_name("canon_ref.png")); print(out.size)
