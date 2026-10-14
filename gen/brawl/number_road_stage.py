"""Numbered review sheets of the road stage: badges 1..N from raw/road/layout.json.

Run after build_road_stage.py: python gen/brawl/number_road_stage.py
Writes gen/brawl/arena_numerowana_preview.jpg (one long strip, half size) and arena_numerowana_4rzedy.jpg.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
lay = json.loads((ROOT / "raw" / "road" / "layout.json").read_text(encoding="utf8"))
im = Image.open(ROOT.parent.parent / "docs" / "img" / "brawl" / "stage_road.webp").convert("RGB")
d = ImageDraw.Draw(im)
fb = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 44)
fs = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
ROAD = 369
for l in lay:
    x = l["x"]
    road = l["kind"].startswith("road")
    y = 150 if l["kind"] == "front" else 96 if road else 34
    top = ROAD - l["h"] + (10 if l["kind"] == "front" else -4) if l["h"] else ROAD - 120
    col = (40, 110, 220) if road else (220, 30, 40)
    d.line([(x, y + 50), (x, max(y + 52, top + 6))], fill=(255, 255, 255), width=3)
    d.ellipse([x - 30, y - 6, x + 30, y + 54], fill=col, outline=(255, 255, 255), width=4)
    t = str(l["nr"]); w = d.textlength(t, font=fb); d.text((x - w / 2, y - 2), t, font=fb, fill=(255, 255, 255))
    sub = f'{l["name"]}  ·  {l["m"]} m'; w2 = d.textlength(sub, font=fs)
    d.rounded_rectangle([x - w2 / 2 - 8, y + 60, x + w2 / 2 + 8, y + 90], 6, fill=(16, 20, 32))
    d.text((x - w2 / 2, y + 63), sub, font=fs, fill=(255, 236, 150))
im.resize((im.width // 2, 360), Image.LANCZOS).save(ROOT / "arena_numerowana_preview.jpg", quality=86)
W = im.width
xs = [l["x"] for l in lay]
mids = [(a + b) // 2 for a, b in zip(xs, xs[1:])]
n = 5
cuts = [0] + [min(mids, key=lambda m: abs(m - W * k / n)) for k in range(1, n)] + [W]
parts = [im.crop((a, 0, b, 720)) for a, b in zip(cuts, cuts[1:])]
rows = Image.new("RGB", (max(p.width for p in parts) // 2, n * 368 - 8), (10, 10, 14))
for i, p in enumerate(parts):
    rows.paste(p.resize((p.width // 2, 360), Image.LANCZOS), (0, i * 368))
rows.save(ROOT / "arena_numerowana_rzedy.jpg", quality=86)
print("ok", len(lay), rows.size)
