"""Process the GPT Image Wapnica master into the game's hard-edged terrain decal.

Run from repo root: python gen/wapnica/process.py
The final ground.png is a pixel-grid 16-colour asset, redrawn on a 2x grid and
rotated clockwise by 15 degrees with nearest-neighbour sampling (no smoothing).
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "gen/wapnica/source_gpt_image.png"
OUTPUT = ROOT / "gen/wapnica/ground.png"
TARGET = (160, 84)  # coarse authoring grid; output is an integer 2x nearest scale


def key_magenta(rgb: np.ndarray) -> np.ndarray:
    """Remove magenta and edge spill connected to the canvas background."""
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    seed = ((r > 80) & (b > 80) & (g < 180) & (np.abs(r - b) < 120)).astype(np.uint8)
    _, labels, _, _ = cv2.connectedComponentsWithStats(seed, 8)
    border_labels = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    background = np.isin(labels, border_labels) & (labels > 0)
    return ~background


def main() -> None:
    rgb = np.asarray(Image.open(MASTER).convert("RGB"))
    alpha = key_magenta(rgb)
    yy, xx = np.nonzero(alpha)
    x0, x1, y0, y1 = xx.min(), xx.max() + 1, yy.min(), yy.max() + 1
    rgb = rgb[y0:y1, x0:x1]
    alpha = alpha[y0:y1, x0:x1]

    # BOX reduction to a 1-art-pixel grid, then no-dither 16-colour quantization.
    small = Image.fromarray(rgb).resize(TARGET, Image.Resampling.BOX)
    quantized = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGBA")
    hard_alpha = Image.fromarray((alpha.astype(np.uint8) * 255)).resize(TARGET, Image.Resampling.NEAREST)
    quantized.putalpha(hard_alpha)

    # Positive Pillow angle is counter-clockwise; negative rotates clockwise in screen space.
    rotated = quantized.rotate(-15, resample=Image.Resampling.NEAREST, expand=True, fillcolor=(0, 0, 0, 0))
    out = rotated.resize((rotated.width * 2, rotated.height * 2), Image.Resampling.NEAREST)
    data = np.asarray(out).copy()
    r, g, b = (data[..., i].astype(np.int16) for i in range(3))
    spill = (data[..., 3] > 0) & (r > 125) & (b > 115) & (g < 145) & (np.abs(r - b) < 120)
    data[spill, 3] = 0
    Image.fromarray(data, "RGBA").save(OUTPUT, optimize=True)
    print(f"saved {OUTPUT} {out.width}x{out.height}; clockwise rotation 15 degrees; 16-colour coarse grid")


if __name__ == "__main__":
    main()
