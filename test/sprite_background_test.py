"""Background-keying regression test for Codex-generated character sprite sheets."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gen"))
from build_walk_cycles import remove_checker_background

# A neutral checker backdrop with a dark-outlined character and enclosed white clothing.
image = Image.new("RGBA", (24, 24), (255, 255, 255, 255))
draw = ImageDraw.Draw(image)
for y in range(0, 24, 4):
    for x in range(0, 24, 4):
        if (x // 4 + y // 4) % 2:
            draw.rectangle((x, y, x + 3, y + 3), fill=(210, 211, 210, 255))
draw.rectangle((7, 4, 16, 20), fill=(25, 20, 18, 255))
draw.rectangle((8, 5, 15, 19), fill=(60, 110, 180, 255))
draw.rectangle((10, 9, 13, 13), fill=(250, 250, 250, 255))

keyed = remove_checker_background(image)
assert keyed.getpixel((1, 1))[3] == 0, "edge-connected checkerboard must become transparent"
assert keyed.getpixel((22, 22))[3] == 0, "checkerboard must be removed across the image"
assert keyed.getpixel((7, 4))[3] == 255, "dark character outline must remain"
assert keyed.getpixel((11, 11))[3] == 255, "enclosed near-white clothing must remain"
print("Sprite background key passed: checkerboard transparent, enclosed character pixels preserved")
