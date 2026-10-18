#!/usr/bin/env python3
"""Build the runtime ZOSIA sheet from the picked variant (round 1: 3 = rower_prowadzi).

Uses the 2x frames written by process_wide.py. Layout follows the cast sheets
(rows walk_down, walk_up, walk_left, walk_right; 4 frames A, B, A, B; feet on
y = CELL_H - FOOT) but with 160 px wide cells, because the side-view bicycle is
~146 px wide at 2x. game.js reads f.w from the JSON, so a wider cell needs no
renderer change; height is still normalised by (f.h - foot - 14).

    python gen/zosia/build_sheet.py            # writes docs/img/zosia_sheet.{png,json}
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
VARIANT = "rower_prowadzi"
CELL_W, CELL_H, FOOT = 160, 170, 6
ROWS = [("walk_down", "down"), ("walk_up", "up"), ("walk_left", "left"), ("walk_right", "right")]


def main():
    src = ROOT / "gen/zosia" / VARIANT
    sheet = Image.new("RGBA", (CELL_W * 4, CELL_H * 4))
    anims = {}
    for r, (anim, d) in enumerate(ROWS):
        frames = []
        for c, ab in enumerate("abab"):
            img = Image.open(src / f"wide_{d}_{ab}.png").convert("RGBA")
            img = img.crop(img.getchannel("A").getbbox())
            if img.width > CELL_W - 4 or img.height > CELL_H - FOOT - 14:
                raise SystemExit(f"{d}_{ab} {img.size} does not fit the {CELL_W}x{CELL_H} cell")
            x = c * CELL_W + (CELL_W - img.width) // 2
            y = r * CELL_H + CELL_H - FOOT - img.height
            sheet.alpha_composite(img, (x, y))
            frames.append({"x": c * CELL_W, "y": r * CELL_H, "w": CELL_W, "h": CELL_H})
        anims[anim] = {"frames": frames}
    out = ROOT / "docs/img"
    sheet.save(out / "zosia_sheet.png", optimize=True)
    (out / "zosia_sheet.json").write_text(json.dumps(
        {"image": "zosia_sheet.png", "foot": FOOT, "anims": anims, "source": f"gen/zosia/{VARIANT}"}, indent=2) + "\n")
    print("docs/img/zosia_sheet.png", sheet.size)


if __name__ == "__main__":
    main()
