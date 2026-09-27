"""Key, crop, and pixel-grid the three GPT-generated cemetery-memory scenes."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "procession": ROOT / "gen/cemetery_memories_raw/procession.png",
    "memorial": ROOT / "gen/cemetery_memories_raw/memorial_ceremony.png",
    "wooden_cross": ROOT / "gen/cemetery_memories_raw/wooden_cross_gathering.png",
}
DEST = ROOT / "docs/img/memories"
KEY_SIZE = 160
OUTPUT_SIZE = 512


def prepare(source: Path, target: Path) -> None:
    rgba = np.array(Image.open(source).convert("RGBA"))
    red, green, blue = (rgba[..., i].astype(np.int16) for i in range(3))
    magenta = (red > 140) & (blue > 140) & (green < 125) & (np.abs(red - blue) < 110)
    rgba[..., 3] = np.where(magenta, 0, 255).astype(np.uint8)
    keyed = Image.fromarray(rgba, "RGBA").filter(ImageFilter.MinFilter(3))
    bounds = keyed.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError(f"No foreground survived chroma keying: {source}")
    crop = keyed.crop(bounds)

    # Reduce noisy AI texture to a deliberately coarse, nearest-neighbor pixel grid.
    rgb = crop.convert("RGB").quantize(colors=56, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    rgb = rgb.resize((KEY_SIZE, KEY_SIZE), Image.Resampling.NEAREST)
    pixelated = rgb.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.NEAREST).convert("RGBA")
    alpha = crop.getchannel("A").resize((KEY_SIZE, KEY_SIZE), Image.Resampling.NEAREST)
    alpha = alpha.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.NEAREST)
    pixelated.putalpha(alpha)
    pixelated.save(target, optimize=True)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, source in SOURCES.items():
        target = DEST / f"{name}.png"
        prepare(source, target)
        print(f"{target.relative_to(ROOT)} {Image.open(target).size}")


if __name__ == "__main__":
    main()
