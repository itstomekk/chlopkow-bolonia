"""Fetch a Google satellite top view around a coordinate (no key, plain tiles).

Usage: python sat_top.py <outdir> <lat> <lng> [zoom] [grid]
"""
import io
import math
import os
import sys
import urllib.request

from PIL import Image

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

OUT, LAT, LNG = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
Z = int(sys.argv[4]) if len(sys.argv) > 4 else 19
GRID = int(sys.argv[5]) if len(sys.argv) > 5 else 3
os.makedirs(OUT, exist_ok=True)


def ll2tile(lat, lng, z):
    n = 2 ** z
    x = int((lng + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return x, y


cx, cy = ll2tile(LAT, LNG, Z)
half = GRID // 2

canvas = Image.new("RGB", (GRID * 256, GRID * 256))
for i in range(GRID):
    for j in range(GRID):
        x, y = cx - half + i, cy - half + j
        url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={Z}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read()
            tile = Image.open(io.BytesIO(body)).convert("RGB")
            if tile.size == (256, 256):
                canvas.paste(tile, (i * 256, j * 256))
            else:
                print(f"  tile {x},{y} size {tile.size} (skip)")
        except Exception as e:  # noqa: BLE001
            print(f"  tile {x},{y} {type(e).__name__}")

path = os.path.join(OUT, f"top_{LAT}_{LNG}_z{Z}.png")
canvas.save(path)
print("saved", path, canvas.size)
