"""Build the CHŁOPKÓW POLONIA brand assets from the approved emblem illustration.

    python gen/brand/build_brand_assets.py

Input : gen/brand/emblem-source.png   (GPT Image art incl. pixel-font wordmark, flat ivory background)
Output: docs/img/chlopkow-polonia-logo.png     transparent logo: sign, falcon, church, sail-less windmill, wordmark
        docs/img/chlopkow-polonia-emblem.png   same file (kept so older links keep working)
        docs/img/favicon-polonia.png           128 px square crop of the scene above the plank
        docs/img/og-polonia.png                1200x630 share card

The wordmark is baked into the GPT Image art (blocky pixel letters, Polish diacritics checked by eye).
v1 typeset the wordmark in Silkscreen via a browser; that looked smooth next to the pixel art, so it was dropped.
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "gen" / "brand" / "emblem-source.png"
IMG = ROOT / "docs" / "img"


def cut_background(path: Path) -> Image.Image:
    a = np.array(Image.open(path).convert("RGBA"))
    h, w = a.shape[:2]
    bg = a[5, 5, :3].astype(int)
    cand = np.abs(a[:, :, :3].astype(int) - bg).sum(2) < 28
    mask = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if cand[y, x] and not mask[y, x]:
                mask[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if cand[y, x] and not mask[y, x]:
                mask[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not mask[ny, nx]:
                mask[ny, nx] = True
                q.append((ny, nx))
    a[mask, 3] = 0
    out = Image.fromarray(a)
    return out.crop(out.getchannel("A").getbbox())


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    emblem = cut_background(SRC)
    logo_path = IMG / "chlopkow-polonia-logo.png"
    emblem.save(logo_path, optimize=True)
    emblem.save(IMG / "chlopkow-polonia-emblem.png", optimize=True)

    # Favicon: the scene above the plank, squared and reduced (nearest keeps the pixel look).
    scene = emblem.crop((0, 0, emblem.width, round(emblem.height * 0.72)))
    side = max(scene.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(scene, ((side - scene.width) // 2, (side - scene.height) // 2))
    sq.resize((128, 128), Image.LANCZOS).save(IMG / "favicon-polonia.png", optimize=True)

    # Share card: the real splash scene, dimmed, with the logo.
    card = Image.new("RGBA", (1200, 630), (16, 22, 58, 255))
    splash = Image.open(IMG / "splash.png").convert("RGBA")
    k = max(1200 / splash.width, 630 / splash.height)
    splash = splash.resize((round(splash.width * k), round(splash.height * k)), Image.NEAREST)
    card.alpha_composite(splash, ((1200 - splash.width) // 2, (630 - splash.height) // 2))
    card.alpha_composite(Image.new("RGBA", card.size, (8, 12, 28, 170)))
    logo = Image.open(logo_path).convert("RGBA")
    lk = 560 / logo.height
    logo = logo.resize((round(logo.width * lk), 560), Image.LANCZOS)
    card.alpha_composite(logo, ((1200 - logo.width) // 2, 35))
    card.convert("RGB").save(IMG / "og-polonia.png", optimize=True)
    for name in ("chlopkow-polonia-emblem", "chlopkow-polonia-logo", "favicon-polonia", "og-polonia"):
        f = IMG / f"{name}.png"
        print(f.name, Image.open(f).size, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
