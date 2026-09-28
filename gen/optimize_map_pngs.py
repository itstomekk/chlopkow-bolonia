"""Losslessly recompress generated map PNG layers in place.

Run after ``python osm/render_map.py``. For full oxipng compression on a fresh
machine, use ``uv run --python 3.11 --with pyoxipng --with pillow --with numpy
python osm/render_map.py``. Without pyoxipng, Pillow's level-9 optimizer is used.
Pixel values (including alpha and the collision mask's exact L bytes) are checked
before each optimized file replaces its source. Formats and filenames remain
unchanged for the browser game.
"""
from pathlib import Path
import os

import numpy as np
from PIL import Image

try:
    import oxipng
except ImportError:
    oxipng = None

ROOT = Path(__file__).resolve().parents[1]
LAYERS = ("map_ground.png", "map_objects.png", "map_collide.png", "map_terrain.png")


def decoded_pixels(path: Path, mode: str) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert(mode)).copy()


def optimize(path: Path) -> tuple[int, int]:
    before_size = path.stat().st_size
    mode = "L" if path.name == "map_collide.png" else "RGBA"
    before = decoded_pixels(path, mode)
    tmp = path.with_name(path.stem + ".optimized.png")
    try:
        if oxipng is not None:
            oxipng.optimize(path, tmp, level=6, force=True)
        else:
            with Image.open(path) as image:
                image.save(tmp, format="PNG", optimize=True, compress_level=9)
        after = decoded_pixels(tmp, mode)
        if not np.array_equal(before, after):
            raise RuntimeError(f"lossless verification failed for {path.name}")
        after_size = tmp.stat().st_size
        if after_size < before_size:
            os.replace(tmp, path)
        return before_size, min(after_size, before_size)
    finally:
        if tmp.exists():
            tmp.unlink()


def main() -> None:
    for name in LAYERS:
        old, new = optimize(ROOT / "docs" / "img" / name)
        print(f"{name}: {old:,} -> {new:,} bytes ({(old - new) / old:.1%} smaller)")


if __name__ == "__main__":
    main()
