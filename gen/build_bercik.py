#!/usr/bin/env python3
"""Build Bercik's reproducible hard-alpha walk-cycle assets.

The input is an opaque GPT Image sheet with an exact 4x2 layout:

    row 0: DOWN A, DOWN B, RIGHT A, RIGHT B
    row 1: UP A,   UP B,   LEFT A,  LEFT B

Each source cell is cleaned and cropped independently.  The content is regridded
with BOX to 75 px high, quantized once to a shared <=40-colour palette, then
upscaled 2x with NEAREST.  No source art is fabricated by this builder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

CELL_W = 130
CELL_H = 170
SHEET_SIZE = (CELL_W * 4, CELL_H * 4)
FOOT = 6
CONTENT_H_SMALL = 75
DIRECTIONS = ("down", "up", "left", "right")
FRAME_NAMES = ("a", "b")
GRID_KEYS = (
    ("down_a", 0, 0),
    ("down_b", 0, 1),
    ("right_a", 0, 2),
    ("right_b", 0, 3),
    ("up_a", 1, 0),
    ("up_b", 1, 1),
    ("left_a", 1, 2),
    ("left_b", 1, 3),
)

DEFAULT_RAW = Path("gen/bercik/bercik_walkcycle_raw.png")
DEFAULT_SHEET = Path("docs/img/bercik_sheet.png")
DEFAULT_METADATA = Path("docs/img/bercik_sheet.json")
DEFAULT_NPC = Path("docs/img/bercik.png")
DEFAULT_MANIFEST = Path("gen/bercik/processed_manifest.json")
DEFAULT_PREVIEW = Path("gen/bercik/preview.png")


class BercikAssetError(ValueError):
    """Raised when the raw sheet violates the asset contract."""


def _grid_edges(length: int, divisions: int) -> list[int]:
    return [round(index * length / divisions) for index in range(divisions + 1)]


def parse_walkcycle_grid(raw_path: Path | str) -> OrderedDict[str, Image.Image]:
    """Return eight independently cropped raw cells using rounded boundaries."""
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    image = Image.open(raw_path).convert("RGBA")
    width, height = image.size
    # Divisibility is deliberately not required; GPT returned an odd-sized
    # sheet, so rounded boundaries prevent a dropped/duplicated pixel row.
    if width < 4 or height < 2:
        raise BercikAssetError("raw sheet must contain a 4x2 equal grid")
    if any(end <= start for start, end in zip(_grid_edges(width, 4), _grid_edges(width, 4)[1:])):
        raise BercikAssetError("raw sheet must contain a 4x2 equal grid")
    if any(end <= start for start, end in zip(_grid_edges(height, 2), _grid_edges(height, 2)[1:])):
        raise BercikAssetError("raw sheet must contain a 4x2 equal grid")

    xs = _grid_edges(width, 4)
    ys = _grid_edges(height, 2)
    cells: OrderedDict[str, Image.Image] = OrderedDict()
    for key, row, col in GRID_KEYS:
        cells[key] = image.crop((xs[col], ys[row], xs[col + 1], ys[row + 1]))
    return cells


def _magenta_like(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., index].astype(np.int16) for index in range(3))
    return (r > 165) & (b > 145) & (g < 125) & (np.abs(r - b) < 105)


def _edge_connected(mask: np.ndarray) -> np.ndarray:
    """Return mask pixels connected to a border through mask pixels."""
    seeds = np.zeros(mask.shape, dtype=bool)
    seeds[0, :] = mask[0, :]
    seeds[-1, :] |= mask[-1, :]
    seeds[:, 0] |= mask[:, 0]
    seeds[:, -1] |= mask[:, -1]
    return ndimage.binary_propagation(
        seeds,
        structure=np.ones((3, 3), dtype=bool),
        mask=mask,
    )


def clean_cell(image: Image.Image, *, minimum_area: int = 24) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Key magenta/fringes, remove detached debris, and crop one cell safely."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[..., :3]
    key = _magenta_like(rgb) | (rgba[..., 3] == 0)
    background = _edge_connected(key)

    # Remove near-magenta anti-aliased fringe only when it is adjacent to the
    # connected backdrop. This cannot erase a similarly coloured interior detail.
    near_background = ndimage.binary_dilation(background, iterations=3)
    r, g, b = (rgb[..., index].astype(np.int16) for index in range(3))
    fringe = near_background & (r > 105) & (b > 90) & (g < r - 35) & (g < b - 30)
    transparent = background | fringe
    rgba[transparent, 3] = 0
    rgba[rgba[..., 3] == 0, :3] = 0

    mask = rgba[..., 3] > 0
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=bool))
    if count == 0:
        raise BercikAssetError("each raw grid cell must contain one meaningful sprite")
    sizes = np.bincount(labels.ravel())
    largest_label = int(np.argmax(sizes[1:]) + 1)
    largest_area = int(sizes[largest_label])
    if largest_area < minimum_area:
        raise BercikAssetError("each raw grid cell must contain one meaningful sprite")

    main = labels == largest_label
    # Preserve a genuinely attached bag/strap component while dropping isolated
    # specks. Components must be substantial and close to the main silhouette.
    keep = main.copy()
    near_main = ndimage.binary_dilation(main, iterations=8)
    for label in range(1, count + 1):
        if label == largest_label:
            continue
        area = int(sizes[label])
        if area >= max(8, int(largest_area * 0.01)) and np.any((labels == label) & near_main):
            keep |= labels == label

    rgba[~keep, 3] = 0
    rgba[rgba[..., 3] == 0, :3] = 0
    bbox = Image.fromarray(rgba, "RGBA").getchannel("A").getbbox()
    if bbox is None:
        raise BercikAssetError("each raw grid cell must contain one meaningful sprite")
    x0, y0, x1, y1 = bbox
    width, height = image.size
    if x0 <= 0 or y0 <= 0 or x1 >= width or y1 >= height:
        raise BercikAssetError("sprite touches a raw cell boundary; refusing cross-cell crop")
    return Image.fromarray(rgba, "RGBA"), bbox


def _small_frame(cell: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    cleaned, bbox = clean_cell(cell)
    cropped = cleaned.crop(bbox)
    target_width = max(1, round(cropped.width * CONTENT_H_SMALL / cropped.height))
    if target_width * 2 > CELL_W:
        raise BercikAssetError("sprite is too wide for a 130px output cell at 150px content height")
    small = cropped.resize((target_width, CONTENT_H_SMALL), Image.Resampling.BOX)
    arr = np.asarray(small.convert("RGBA"), dtype=np.uint8).copy()
    arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0).astype(np.uint8)
    arr[arr[..., 3] == 0, :3] = 0
    return Image.fromarray(arr, "RGBA"), bbox


def _common_palette(frames: Iterable[Image.Image]) -> list[tuple[int, int, int]]:
    rgb_parts = []
    for frame in frames:
        arr = np.asarray(frame.convert("RGBA"))
        opaque = arr[..., 3] == 255
        if np.any(opaque):
            rgb_parts.append(arr[..., :3][opaque])
    if not rgb_parts:
        raise BercikAssetError("no opaque sprite pixels remain after keying")
    colors = np.unique(np.concatenate(rgb_parts, axis=0), axis=0)
    if len(colors) <= 40:
        return [tuple(int(value) for value in color) for color in colors]

    # Quantize a compact image containing only sprite colours, not transparent
    # padding. The single palette is then applied to every frame by nearest RGB.
    sample = Image.fromarray(colors.reshape(1, len(colors), 3).astype(np.uint8), "RGB")
    quantized = sample.quantize(colors=40, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    used = sorted({index for index in np.asarray(quantized).ravel()})
    palette = quantized.getpalette()
    return [tuple(int(value) for value in palette[index * 3:index * 3 + 3]) for index in used]


def _apply_palette(frame: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    arr = np.asarray(frame.convert("RGBA"), dtype=np.uint8).copy()
    opaque = arr[..., 3] == 255
    # Squared RGB deltas can exceed int16 (255**2); overflow swaps navy and skin.
    source = arr[..., :3][opaque].astype(np.int32)
    palette_array = np.asarray(palette, dtype=np.int32)
    distances = ((source[:, None, :] - palette_array[None, :, :]) ** 2).sum(axis=2)
    arr[..., :3][opaque] = palette_array[np.argmin(distances, axis=1)].astype(np.uint8)
    arr[~opaque, :3] = 0
    arr[~opaque, 3] = 0
    return Image.fromarray(arr, "RGBA")


def _repair_front_temple(small: Image.Image) -> Image.Image:
    """Fill isolated one-pixel left contour notches in the frontal head only.

    Both generated front poses have a one-pixel indentation at the left temple.
    Copy the existing outline color above it; do not repaint facial details,
    change the palette, smooth the body, or touch intentional limb gaps.
    """
    arr = np.asarray(small).copy()
    head_rows = min(small.height // 4, small.height - 1)
    left = []
    for row in arr[:head_rows + 1]:
        occupied = np.flatnonzero(row[:, 3] == 255)
        left.append(int(occupied[0]) if occupied.size else None)
    # Restrict to the temple band; keep the intentionally asymmetric upper hair.
    for y in range(max(1, small.height // 12), head_rows):
        previous, current, following = left[y - 1:y + 2]
        if previous is not None and previous == following and current == previous + 1:
            arr[y, previous] = arr[y - 1, previous]
    return Image.fromarray(arr)


def _final_frame(small: Image.Image) -> Image.Image:
    return small.resize((small.width * 2, small.height * 2), Image.Resampling.NEAREST)


def _metadata() -> dict:
    metadata = {"image": "bercik_sheet.png", "foot": FOOT, "anims": {}}
    for row, direction in enumerate(DIRECTIONS):
        metadata["anims"][f"walk_{direction}"] = {
            "frames": [
                {"x": col * CELL_W, "y": row * CELL_H, "w": CELL_W, "h": CELL_H}
                for col in range(4)
            ]
        }
    return metadata


def _hex(color: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in color)


def _preview(sheet: Image.Image, destination: Path) -> None:
    panel_w, panel_h = 560, 570
    canvas = Image.new("RGBA", (panel_w * 2, panel_h * 2), (190, 190, 184, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, direction in enumerate(DIRECTIONS):
        px, py = (index % 2) * panel_w, (index // 2) * panel_h
        draw.rectangle((px + 4, py + 4, px + panel_w - 5, py + panel_h - 5), fill=(232, 231, 222, 255), outline=(90, 90, 84, 255))
        draw.text((px + 18, py + 14), direction.upper(), fill=(20, 20, 20, 255), font=font)
        for frame_index, label in enumerate(("A", "B")):
            cell = sheet.crop((frame_index * CELL_W, index * CELL_H, (frame_index + 1) * CELL_W, (index + 1) * CELL_H))
            enlarged = cell.resize((CELL_W * 2, CELL_H * 2), Image.Resampling.NEAREST)
            canvas.alpha_composite(enlarged, (px + 18 + frame_index * 270, py + 40))
            draw.text((px + 24 + frame_index * 270, py + 385), f"{label}  2x review", fill=(25, 25, 25, 255), font=font)
            native = cell.resize((CELL_W, CELL_H), Image.Resampling.NEAREST)
            canvas.alpha_composite(native, (px + 300 + frame_index * 130, py + 390))
        draw.text((px + 18, py + 545), "native game scale: 130x170", fill=(25, 25, 25, 255), font=font)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, optimize=True)


def build_bercik(
    raw_path: Path | str = DEFAULT_RAW,
    *,
    sheet_path: Path | str = DEFAULT_SHEET,
    metadata_path: Path | str = DEFAULT_METADATA,
    npc_path: Path | str = DEFAULT_NPC,
    manifest_path: Path | str = DEFAULT_MANIFEST,
    preview_path: Path | str = DEFAULT_PREVIEW,
    provider: str = "GPT Image 2 medium via openai-codex (provider not otherwise specified)",
) -> dict:
    """Process the real raw sheet and write all owned Bercik artifacts."""
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    cells = parse_walkcycle_grid(raw_path)
    small_frames: OrderedDict[str, Image.Image] = OrderedDict()
    source_bboxes: dict[str, tuple[int, int, int, int]] = {}
    for key, cell in cells.items():
        small, bbox = _small_frame(cell)
        small_frames[key] = small
        source_bboxes[key] = bbox

    palette = _common_palette(small_frames.values())
    if len(palette) > 40:
        raise BercikAssetError("shared palette exceeds 40 colours")
    final_frames: OrderedDict[str, Image.Image] = OrderedDict()
    for key, small in small_frames.items():
        colored = _apply_palette(small, palette)
        if key.startswith('down_'):
            colored = _repair_front_temple(colored)
        final_frames[key] = _final_frame(colored)

    fingerprints = [frame.tobytes() for frame in final_frames.values()]
    if len(set(fingerprints)) != len(fingerprints):
        raise BercikAssetError("all eight Bercik poses must be distinct")

    sheet = Image.new("RGBA", SHEET_SIZE, (0, 0, 0, 0))
    output_bboxes: dict[str, list[int]] = {}
    directions_to_keys = {
        "down": ("down_a", "down_b"),
        "up": ("up_a", "up_b"),
        "left": ("left_a", "left_b"),
        "right": ("right_a", "right_b"),
    }
    for row, direction in enumerate(DIRECTIONS):
        for col in range(4):
            key = directions_to_keys[direction][col % 2]
            frame = final_frames[key]
            x = col * CELL_W + (CELL_W - frame.width) // 2
            y = row * CELL_H + CELL_H - FOOT - frame.height
            sheet.alpha_composite(frame, (x, y))
            bbox = frame.getchannel("A").getbbox()
            assert bbox is not None
            output_bboxes[key] = [x + bbox[0], row * CELL_H + y - row * CELL_H + bbox[1], x + bbox[2], row * CELL_H + y - row * CELL_H + bbox[3]]

    sheet_path = Path(sheet_path)
    metadata_path = Path(metadata_path)
    npc_path = Path(npc_path)
    manifest_path = Path(manifest_path)
    preview_path = Path(preview_path)
    for path in (sheet_path, metadata_path, npc_path, manifest_path, preview_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    sheet.save(sheet_path, optimize=True)
    metadata_path.write_text(json.dumps(_metadata(), indent=2) + "\n", encoding="utf-8")
    sheet.crop((0, 0, CELL_W, CELL_H)).save(npc_path, optimize=True)
    _preview(sheet, preview_path)

    raw_image = Image.open(raw_path)
    manifest = {
        "asset": "bercik",
        "provider": provider,
        "input": {
            "path": raw_path.as_posix(),
            "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
            "dimensions": list(raw_image.size),
            "grid": {"columns": 4, "rows": 2},
            "cell_bounds": {
                key: [
                    _grid_edges(raw_image.width, 4)[col],
                    _grid_edges(raw_image.height, 2)[row],
                    _grid_edges(raw_image.width, 4)[col + 1],
                    _grid_edges(raw_image.height, 2)[row + 1],
                ]
                for key, row, col in GRID_KEYS
            },
            "background_key": "magenta-like edge-connected pixels and adjacent fringe",
        },
        "output": {
            "sheet": sheet_path.as_posix(),
            "sheet_dimensions": list(SHEET_SIZE),
            "cell_dimensions": [CELL_W, CELL_H],
            "npc": npc_path.as_posix(),
            "preview": preview_path.as_posix(),
        },
        "palette": {"size": len(palette), "colors": [_hex(color) for color in palette], "dither": False},
        "frames": {
            key: {
                "source_cell": key,
                "bbox": list(source_bboxes[key]),
                "content_grid": [small_frames[key].width, small_frames[key].height],
                "final_content_dimensions": [final_frames[key].width, final_frames[key].height],
                "sheet_bbox_within_cell": [
                    output_bboxes[key][0] % CELL_W,
                    output_bboxes[key][1] % CELL_H,
                    output_bboxes[key][2] % CELL_W,
                    output_bboxes[key][3] % CELL_H,
                ],
            }
            for key in cells
        },
        "recipe": [
            "round(col*width/4) and round(row*height/2) cell boundaries",
            "edge-connected magenta key plus nearby magenta fringe removal",
            "largest connected sprite component plus substantial nearby components; detached debris removed",
            "crop each cell independently; BOX regrid to 75px content height",
            "one shared <=40-colour palette, no dithering, hard alpha 0/255",
            "integer 2x NEAREST upscale to 150px content height",
            "place on 130x170 cells with 6px foot and repeat A,B,A,B",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--sheet", type=Path, default=DEFAULT_SHEET)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--npc", type=Path, default=DEFAULT_NPC)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--preview", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--provider", default="GPT Image 2 medium via openai-codex (provider not otherwise specified)")
    args = parser.parse_args(argv)
    try:
        manifest = build_bercik(
            args.input,
            sheet_path=args.sheet,
            metadata_path=args.metadata,
            npc_path=args.npc,
            manifest_path=args.manifest,
            preview_path=args.preview,
            provider=args.provider,
        )
    except (FileNotFoundError, BercikAssetError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"sheet": manifest["output"]["sheet"], "palette": manifest["palette"]["size"], "sha256": manifest["input"]["sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
