"""Satellite strip aligned to game pixels, with OSM building outlines, for yard review.

    python gen/streetview/sat_strip.py x0 y0 x1 y1 out.png [zoom]
The output has the same size as the game box x zoom (default 3), so it can be stacked with process5.render panels.
"""
import io
import json
import math
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "osm"))
from geo import A, BBOX, MX, MY, P  # noqa: E402

Z = 19


def merc(lat, lon):
    n = 256 * 2 ** Z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def game_to_ll(x, y):
    return BBOX[2] - y / (MY * A), BBOX[1] + x / (MX * A)


def strip(box, zoom=3, outlines=True):
    x0, y0, x1, y1 = box
    la0, lo0 = game_to_ll(x0, y0); la1, lo1 = game_to_ll(x1, y1)
    mx0, my0 = merc(la0, lo0); mx1, my1 = merc(la1, lo1)
    tx0, ty0, tx1, ty1 = int(mx0 // 256), int(my0 // 256), int(mx1 // 256), int(my1 // 256)
    big = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            b = urllib.request.urlopen(urllib.request.Request(f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={Z}",
                                       headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read()
            big.paste(Image.open(io.BytesIO(b)).convert("RGB"), ((tx - tx0) * 256, (ty - ty0) * 256))
    crop = big.crop((round(mx0 - tx0 * 256), round(my0 - ty0 * 256), round(mx1 - tx0 * 256), round(my1 - ty0 * 256)))
    W, H = (x1 - x0) * zoom, (y1 - y0) * zoom
    im = crop.resize((W, H), Image.Resampling.LANCZOS)
    if outlines:
        d = ImageDraw.Draw(im)
        osm = json.load(open(ROOT / "osm/chlopkow.json", encoding="utf-8"))
        for e in osm["elements"]:
            if "building" not in e.get("tags", {}) or not e.get("geometry"): continue
            pts = [P(p["lat"], p["lon"]) for p in e["geometry"]]
            pts = [((x - x0) * zoom, (y - y0) * zoom) for x, y in pts]
            if all(not (0 <= x < W and 0 <= y < H) for x, y in pts): continue
            d.line(pts, fill=(255, 0, 255), width=2)
            cx = sum(p[0] for p in pts[:-1]) / (len(pts) - 1); cy = sum(p[1] for p in pts[:-1]) / (len(pts) - 1)
            d.text((cx - 12, cy - 5), str(e["id"])[-4:], fill=(255, 255, 0))
    return im


if __name__ == "__main__":
    b = tuple(int(v) for v in sys.argv[1:5])
    strip(b, int(sys.argv[6]) if len(sys.argv) > 6 else 3).save(sys.argv[5])
