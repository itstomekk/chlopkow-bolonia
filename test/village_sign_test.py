from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "gen" / "build_village_sign.py")], cwd=ROOT, check=True)
image = Image.open(ROOT / "gen" / "lm_village_sign.png").convert("RGB")
pixels = np.asarray(image)

assert pixels[0, 0].tolist() == [255, 0, 255], "sign canvas needs a clean magenta key background"
upper = pixels[15, 110]
assert int(upper[1]) > int(upper[0]) * 2 and int(upper[1]) > int(upper[2]), f"upper panel is not green: {upper}"
lower = pixels[110, 110]
assert lower[0] > 150 and lower[1] > 145 and abs(int(lower[0]) - int(lower[2])) < 80, f"lower panel is not pale: {lower}"

# A visible dark village silhouette must sit within the lower panel, not just its frame.
lower_pixels = pixels[95:155, 25:195]
skyline = (lower_pixels[:, :, 0] < 65) & (lower_pixels[:, :, 1] < 65) & (lower_pixels[:, :, 2] < 75)
assert int(skyline.sum()) > 100, f"lower panel lacks a village skyline: {int(skyline.sum())} dark pixels"

# The upper panel should contain cream pixel lettering over green.
upper_pixels = pixels[15:75, 20:200]
text_pixels = (upper_pixels[:, :, 0] > 170) & (upper_pixels[:, :, 1] > 160) & (upper_pixels[:, :, 2] > 140)
assert int(text_pixels.sum()) > 100, "upper panel is missing legible pale lettering"
print("Village sign check passed: two panels, skyline, lettering, and keyable background")
