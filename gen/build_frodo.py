"""Key and pack GPT-generated Frodo frames into the game's 32px sprite atlas."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gen" / "frodo_sheet_raw.png"
OUT = ROOT / "docs" / "img" / "frodo.png"
TILE = 32


def remove_connected_magenta(image):
    """Remove only magenta-like pixels connected to the sheet's outer edge."""
    pixels = np.asarray(image.convert("RGB"))
    red, green, blue = pixels.transpose(2, 0, 1).astype(np.int16)
    candidate = (red > 140) & (blue > 140) & (green < 120) & (np.abs(red - blue) < 100)
    labels, _ = ndimage.label(candidate, structure=np.ones((3, 3), dtype=np.uint8))
    edge_labels = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    background = np.isin(labels, edge_labels[edge_labels > 0])
    rgba = np.dstack((pixels, np.where(background, 0, 255).astype(np.uint8)))
    return Image.fromarray(rgba, "RGBA")


def main():
    source = remove_connected_magenta(Image.open(SOURCE))
    atlas = Image.new("RGBA", (TILE * 2, TILE * 4), (0, 0, 0, 0))

    for row in range(4):
        y0, y1 = round(row * source.height / 4), round((row + 1) * source.height / 4)
        for col in range(2):
            x0, x1 = round(col * source.width / 2), round((col + 1) * source.width / 2)
            frame = source.crop((x0, y0, x1, y1))
            bounds = frame.getchannel("A").getbbox()
            if not bounds:
                raise ValueError(f"Empty Frodo frame at row {row}, column {col}")
            frame = frame.crop(bounds)
            scale = min(26 / frame.width, 26 / frame.height)
            size = (max(1, round(frame.width * scale)), max(1, round(frame.height * scale)))
            frame = frame.resize(size, Image.Resampling.LANCZOS)
            # Hard alpha edges keep the final 32px sprites crisp with smoothing disabled in-game.
            alpha = frame.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
            frame.putalpha(alpha)
            atlas.alpha_composite(frame, (TILE * col + (TILE - frame.width) // 2, TILE * row + TILE - 3 - frame.height))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT)
    print(f"Created {OUT} ({atlas.width}x{atlas.height}, RGBA)")


if __name__ == "__main__":
    main()
