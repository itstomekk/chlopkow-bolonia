#!/usr/bin/env python3
"""Build WIESIO's 4-frame walk-cycle atlas from two GPT Image sheets.

Inputs (opaque, flat magenta background, 4 columns x 2 rows each):

    gen/wiesio/wiesio_walk_frontback_raw.png   row 0: DOWN f0..f3, row 1: UP f0..f3
    gen/wiesio/wiesio_walk_side_raw.png        row 0: LEFT f0..f3, row 1: RIGHT f0..f3

Frame order in every row: step, passing, other step, passing.  Each cell is
keyed and cropped with the BERCIK cleaner, then every row is regridded with ONE
shared scale (tallest frame -> 65 px) so the walk keeps its bob and tilt.  A
small foot-pivoted pixel shear adds the owner-approved light sway ("version 1",
2026-10-12).  One shared <=40-colour palette, hard alpha, 2x NEAREST, placed on
130x170 cells with a 6 px foot like BERCIK.  WIESIO is 1.55 m, so his content is
130 px tall against BERCIK's 150 px.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

import build_bercik as bb

CELL_W, CELL_H, FOOT = 130, 170, 6
CONTENT_H_SMALL = 65
ROWS = ("down", "up", "left", "right")
SOURCES = {"down": ("frontback", 0), "up": ("frontback", 1), "left": ("side", 0), "right": ("side", 1)}
LEAN = {"down": (-3, 0, 3, 0), "up": (-3, 0, 3, 0), "left": (-1, 0, 1, 0), "right": (1, 0, -1, 0)}
SWAY = 1  # extra small-pixel side shift on the leaning front/back frames

DEFAULT_RAW = {
    "frontback": Path("gen/wiesio/wiesio_walk_frontback_raw.png"),
    "side": Path("gen/wiesio/wiesio_walk_side_raw.png"),
}
DEFAULT_SHEET = Path("docs/img/wiesio_sheet.png")
DEFAULT_METADATA = Path("docs/img/wiesio_sheet.json")
DEFAULT_NPC = Path("docs/img/wiesio.png")
DEFAULT_MANIFEST = Path("gen/wiesio/processed_manifest.json")


def _cells(path: Path, row: int) -> list[tuple[Image.Image, tuple[int, int]]]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    xs = [round(i * width / 4) for i in range(5)]
    ys = [round(i * height / 2) for i in range(3)]
    result = []
    for col in range(4):
        cell = image.crop((xs[col], ys[row], xs[col + 1], ys[row + 1]))
        cleaned, _ = bb.clean_cell(cell)
        arr = np.asarray(cleaned).copy()
        r, g, b = (arr[..., i].astype(np.int32) for i in range(3))
        arr[(r > 165) & (b > 145) & (g < 125), 3] = 0  # enclosed magenta pockets (arm gaps)
        arr[arr[..., 3] == 0, :3] = 0
        result.append((Image.fromarray(arr, "RGBA"), cell.size))
    return result


def _shear(image: Image.Image, lean: int) -> Image.Image:
    """Shift rows so the head moves `lean` px while the feet stay fixed."""
    if not lean:
        return image
    pad = abs(lean)
    arr = np.asarray(image)
    height, width = arr.shape[:2]
    out = np.zeros((height, width + 2 * pad, 4), np.uint8)
    for y in range(height):
        dx = round(lean * (height - 1 - y) / max(1, height - 1))
        out[y, pad + dx:pad + dx + width] = arr[y]
    sheared = Image.fromarray(out, "RGBA")
    return sheared.crop(sheared.getchannel("A").getbbox())


def build_wiesio(raw=DEFAULT_RAW, *, sheet_path=DEFAULT_SHEET, metadata_path=DEFAULT_METADATA,
                 npc_path=DEFAULT_NPC, manifest_path=DEFAULT_MANIFEST, name="wiesio",
                 content_h=CONTENT_H_SMALL, lean=LEAN, sway_px=SWAY, align_head=False) -> dict:
    """Shared 4-frame walk builder; other characters (IWONA) pass their own name/height/lean."""
    raw = {key: Path(value) for key, value in raw.items()}
    for path in raw.values():
        if not path.exists():
            raise FileNotFoundError(path)
    small: dict[tuple[str, int], Image.Image] = {}
    offset: dict[tuple[str, int], float] = {}
    for direction in ROWS:
        source, row = SOURCES[direction]
        cells = _cells(raw[source], row)
        boxes = [image.getchannel("A").getbbox() for image, _ in cells]
        tallest = max(box[3] - box[1] for box in boxes)
        k = content_h / tallest  # one scale per row keeps the bob and tilt
        for col, ((image, size), box) in enumerate(zip(cells, boxes)):
            crop = image.crop(box)
            frame = crop.resize((max(1, round(crop.width * k)), max(1, round(crop.height * k))), Image.Resampling.BOX)
            arr = np.asarray(frame).copy()
            arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
            arr[arr[..., 3] == 0, :3] = 0
            tilt = lean[direction][col]
            small[(direction, col)] = _shear(Image.fromarray(arr, "RGBA"), tilt)
            offset[(direction, col)] = ((box[0] + box[2]) / 2 - size[0] / 2) * k + tilt / 2
        mean = sum(offset[(direction, c)] for c in range(4)) / 4
        for col in range(4):
            offset[(direction, col)] -= mean

    palette = bb._common_palette(small.values())
    if len(palette) > 40:
        raise ValueError("shared palette exceeds 40 colours")
    sway = {"down": (-sway_px, 0, sway_px, 0), "up": (-sway_px, 0, sway_px, 0), "left": (0, 0, 0, 0), "right": (0, 0, 0, 0)}
    sheet = Image.new("RGBA", (CELL_W * 4, CELL_H * 4), (0, 0, 0, 0))
    frames_out = {}
    for row, direction in enumerate(ROWS):
        for col in range(4):
            final = bb._final_frame(bb._apply_palette(small[(direction, col)], palette))
            if align_head:
                # Keep the head centroid on the cell centre: swinging props (keys) must not
                # shift the whole body sideways between frames.
                alpha = np.asarray(final.getchannel("A")) > 0
                rows = np.nonzero(alpha.any(axis=1))[0]
                top = alpha[rows[0]:rows[0] + max(1, int((rows[-1] - rows[0]) * 0.3))]
                head_x = float(np.nonzero(top)[1].mean())
                x = col * CELL_W + round(CELL_W / 2 - head_x)
            else:
                x = col * CELL_W + (CELL_W - final.width) // 2 + 2 * round(offset[(direction, col)] + sway[direction][col])
            x = min(max(x, col * CELL_W + 1), col * CELL_W + CELL_W - final.width - 1)
            y = row * CELL_H + CELL_H - FOOT - final.height
            sheet.alpha_composite(final, (x, y))
            frames_out[f"{direction}_{col}"] = {"size": list(final.size), "pos_in_cell": [x - col * CELL_W, y - row * CELL_H]}

    for path in (sheet_path, metadata_path, npc_path, manifest_path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, optimize=True)
    metadata = {"image": f"{name}_sheet.png", "foot": FOOT, "anims": {
        f"walk_{direction}": {"frames": [{"x": c * CELL_W, "y": r * CELL_H, "w": CELL_W, "h": CELL_H} for c in range(4)]}
        for r, direction in enumerate(ROWS)}}
    Path(metadata_path).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    sheet.crop((0, 0, CELL_W, CELL_H)).save(npc_path, optimize=True)
    manifest = {
        "asset": name,
        "content_height_small_px": content_h,
        "provider": "GPT Image 2 medium via openai-codex",
        "inputs": {key: {"path": p.as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                         "dimensions": list(Image.open(p).size)} for key, p in raw.items()},
        "rows": {d: {"source": SOURCES[d][0], "row": SOURCES[d][1], "lean_small_px": list(lean[d])} for d in ROWS},
        "sway_small_px": sway_px,
        "align": "head centroid" if align_head else "bbox centre offset + lean/sway",
        "palette": {"size": len(palette), "colors": [bb._hex(c) for c in palette]},
        "frames": frames_out,
        "output": {"sheet": Path(sheet_path).as_posix(), "metadata": Path(metadata_path).as_posix(), "npc": Path(npc_path).as_posix()},
    }
    Path(manifest_path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--npc", type=Path, default=DEFAULT_NPC)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    manifest = build_wiesio(sheet_path=args.sheet, metadata_path=args.metadata, npc_path=args.npc, manifest_path=args.manifest)
    print(json.dumps({"sheet": manifest["output"]["sheet"], "palette": manifest["palette"]["size"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
