"""Prepare the reference-generated, two-panel Chłopków entrance sign."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAW = Path("gen/lm_village_sign_raw.png")
OUT = Path("gen/lm_village_sign.png")
MAGENTA = np.array((255, 0, 255), dtype=np.uint8)
TARGET_WIDTH = 220

# Turn the model's flat magenta background into an exact chroma key and crop
# only the connected sign silhouette, retaining transparent-looking gaps.
raw = np.asarray(Image.open(RAW).convert("RGB")).copy()
r, g, b = raw.astype(np.int16).transpose(2, 0, 1)
key = (r > 140) & (b > 140) & (g < 120) & (np.abs(r - b) < 100)
raw[key] = MAGENTA
y, x = np.nonzero(~key)
if not len(x):
    raise ValueError(f"No sign found in {RAW}")
image = Image.fromarray(raw).crop((x.min(), y.min(), x.max() + 1, y.max() + 1))
target_height = round(image.height * TARGET_WIDTH / image.width)
image = image.resize((TARGET_WIDTH, target_height), Image.Resampling.NEAREST)

# Overlay the exact Polish place name in pixel glyphs so the generated sign
# keeps its correct spelling even if the illustration has no text.
pixels = np.asarray(image).copy()
r, g, b = pixels.astype(np.int16).transpose(2, 0, 1)
y_grid = np.arange(image.height)[:, None]
green = (r < 50) & (g > 60) & (g < 130) & (b > 45) & (b < 100) & (g > r * 1.5) & (y_grid < image.height * 0.4)
y_panel, x_panel = np.nonzero(green)
if not len(x_panel):
    raise ValueError("Could not locate the sign's green upper panel")
panel = (int(x_panel.min()), int(y_panel.min()), int(x_panel.max()) + 1, int(y_panel.max()) + 1)

GLYPHS = {
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "Ł": ("10000", "10100", "10010", "10100", "10000", "10000", "11111"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "Ó": ("00100", "01000", "01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
}
label = "CHŁOPKÓW"
pixel = 3
advance = 6 * pixel
text_width = len(label) * advance - pixel
text_height = 9 * pixel
text_x = (panel[0] + panel[2] - text_width) // 2
text_y = (panel[1] + panel[3] - text_height) // 2
draw = ImageDraw.Draw(image)
for index, character in enumerate(label):
    glyph = GLYPHS[character]
    row_offset = 9 - len(glyph)
    for row, bits in enumerate(glyph):
        for column, bit in enumerate(bits):
            if bit == "1":
                x = text_x + index * advance + column * pixel
                y = text_y + (row_offset + row) * pixel
                draw.rectangle((x, y, x + pixel - 1, y + pixel - 1), fill=(242, 239, 222))

image.save(OUT)
print(f"{OUT} {image.size}; green panel {panel}; overlaid {label}")
