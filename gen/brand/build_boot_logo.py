"""Build the small indexed PNG used by the immediate black-and-logo boot screen."""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "img" / "chlopkow-polonia-logo.png"
OUTPUT = ROOT / "docs" / "img" / "boot-logo.png"


def main():
    source = Image.open(SOURCE).convert("RGBA")
    small = source.resize((768, round(source.height * 768 / source.width)), Image.Resampling.NEAREST)
    rgba = np.asarray(small)
    alpha = rgba[:, :, 3]
    rgb = rgba[:, :, :3].copy()
    rgb[alpha == 0] = 0
    quantized = Image.fromarray(rgb, "RGB").quantize(
        colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    indices = np.asarray(quantized).copy()
    indices[alpha == 0] = 0
    indices[alpha != 0] += 1
    indexed = Image.frombytes("P", small.size, indices.astype(np.uint8).tobytes())
    palette = [0, 0, 0] + quantized.getpalette()[:765]
    palette += [0] * (768 - len(palette))
    indexed.putpalette(palette)
    indexed.info["transparency"] = 0
    indexed.save(OUTPUT, optimize=True)
    print(f"{OUTPUT.name}: {indexed.width}x{indexed.height}, {OUTPUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
