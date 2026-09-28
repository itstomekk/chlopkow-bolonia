#!/usr/bin/env python3
"""
Build playable character walk-cycle sprite sheets from raw 4x2 grids.
Input: gen/npc_src/{name}_walkcycle_raw.png (4 cols x 2 rows = 4 directions x 2 frames)
Output: docs/img/{name}_sheet.png + docs/img/{name}_sheet.json

Grid layout for standard sources:
  Row 0: [DOWN frame1] [DOWN frame2] [RIGHT frame1] [RIGHT frame2]
  Row 1: [UP frame1]   [UP frame2]   [LEFT frame1]  [LEFT frame2]
Marcin's source is interleaved and is remapped explicitly below.

Output format (matching arek_sheet):
  Row 0: [down_f1] [down_f2] [down_f1] [down_f2]  (4x 130px cells)
  Row 1: [up_f1]   [up_f2]   [up_f1]   [up_f2]
  Row 2: [left_f1] [left_f2] [left_f1] [left_f2]
  Row 3: [right_f1][right_f2][right_f1][right_f2]

Run from repo root: python gen/build_walk_cycles.py
"""
import json
import numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage

REPO_ROOT = Path(".")
GEN_DIR = REPO_ROOT / "gen"
DOCS_IMG = REPO_ROOT / "docs" / "img"

import sys
CHARACTERS = sys.argv[1:] or ["marcin", "damian", "edytka", "renik"]


def remove_magenta_background(image):
    """Key out a flat magenta (#FF00FF-ish) backdrop requested from GPT Image.

    A second pass removes the anti-aliased pinkish fringe, but only within a few
    pixels of the keyed backdrop, so magenta details inside the figure survive."""
    rgba = np.array(image.convert("RGBA"), dtype=np.uint8)
    r, g, b = (rgba[..., i].astype(np.int16) for i in range(3))
    magenta = (r > 170) & (b > 150) & (g < 110) & (np.abs(r - b) < 90)
    bg = magenta | (rgba[..., 3] == 0)
    near_bg = ndimage.binary_dilation(bg, iterations=3)
    fringe = near_bg & (r > 110) & (b > 90) & (g < r - 45) & (g < b - 35)
    rgba[bg | fringe, 3] = 0
    # Despill: edge pixels bordering transparency that are still magenta-tinted
    # (r and b well above g) are dropped; two passes peel a 2px anti-aliased halo.
    for _ in range(2):
        clear = rgba[..., 3] == 0
        edge = (rgba[..., 3] > 0) & ndimage.binary_dilation(clear)
        r, g, b = (rgba[..., i].astype(np.int16) for i in range(3))
        tinted = (r - g > 35) & (b - g > 25)
        rgba[edge & tinted, 3] = 0
    rgba[rgba[..., 3] == 0, :3] = 0   # no hidden magenta RGB left to bleed in during LANCZOS resize
    return Image.fromarray(rgba)


def remove_checker_background(image):
    """Make edge-connected, near-neutral checkerboard backdrop pixels transparent.

    GPT Image may return a flattened transparency checkerboard despite an explicit
    transparent-background request. Restricting removal to neutral pixels connected
    to the image border preserves enclosed pale clothing and highlights.
    """
    rgba = np.array(image.convert("RGBA"), dtype=np.uint8)
    rgb = rgba[..., :3].astype(np.int16)
    neutral_light = ((rgb.max(axis=2) - rgb.min(axis=2)) <= 18) & (rgb.min(axis=2) >= 185)
    seeds = np.zeros(neutral_light.shape, dtype=bool)
    seeds[0, :] = neutral_light[0, :]
    seeds[-1, :] = neutral_light[-1, :]
    seeds[:, 0] |= neutral_light[:, 0]
    seeds[:, -1] |= neutral_light[:, -1]
    background = ndimage.binary_propagation(seeds, structure=np.ones((3, 3), dtype=bool), mask=neutral_light)
    rgba[background, 3] = 0
    rgba[background, :3] = 0
    return Image.fromarray(rgba)


# Input grid positions (within 4x2 raw image)
# We need to detect the actual cell positions in the generated image
# For now, assume roughly equal spacing

def parse_walkcycle_grid(raw_path, layout="standard"):
    """
    Extract 4 direction strips from a 4x2 grid raw image.
    Returns dict: {direction: (frame1_img, frame2_img)}
    """
    raw = remove_magenta_background(remove_checker_background(Image.open(raw_path)))
    w, h = raw.size

    # Heuristic: divide into 4x2 grid cells
    cell_w = w // 4
    cell_h = h // 2
    
    # Extract cells
    cells = {}
    for row in range(2):
        for col in range(4):
            x = col * cell_w
            y = row * cell_h
            cell = raw.crop((x, y, x + cell_w, y + cell_h))
            cells[(row, col)] = cell
    
    # Most generated sheets group the two animation frames by direction.
    # Marcin's source instead interleaves directions by frame:
    # row 0 = down0, right0, down1, right1;
    # row 1 = up0, left0, up1, left1.
    if layout == "interleaved":
        result = {
            "down": (cells[(0, 0)], cells[(0, 2)]),
            "right": (cells[(0, 1)], cells[(0, 3)]),
            "up": (cells[(1, 0)], cells[(1, 2)]),
            "left": (cells[(1, 1)], cells[(1, 3)]),
        }
    else:
        result = {
            "down": (cells[(0, 0)], cells[(0, 1)]),
            "right": (cells[(0, 2)], cells[(0, 3)]),
            "up": (cells[(1, 0)], cells[(1, 1)]),
            "left": (cells[(1, 2)], cells[(1, 3)]),
        }
    return result


def build_sheet(name, frames_dict):
    """
    Build a sprite sheet in Arek format: 4 rows x 4 cells per row.
    Each row is a direction (down, up, left, right).
    Each cell is 130x170 px, contains a walk frame or repeat.
    
    frames_dict: {direction: (frame1_img, frame2_img)}
    Returns: (sheet_img, metadata)
    """
    CELL_W, CELL_H = 130, 170
    
    # Target height for all frames (scale to fit)
    TARGET_H = 150
    
    # Build sheet: 4 rows x 4 cells
    sheet = Image.new("RGBA", (CELL_W * 4, CELL_H * 4), (0, 0, 0, 0))
    
    metadata = {
        "image": f"{name}_sheet.png",
        "foot": 6,
        "anims": {},
    }
    
    directions_order = ["down", "up", "left", "right"]
    
    for row_idx, direction in enumerate(directions_order):
        if direction not in frames_dict:
            print(f"  WARNING: {direction} not found in frames")
            continue
        
        frame1, frame2 = frames_dict[direction]
        
        # Scale both frames to TARGET_H maintaining aspect ratio
        frames = [frame1, frame2]
        scaled_frames = []
        
        for frame in frames:
            frame = frame.convert("RGBA")
            if name == "damian":
                # One right-facing source frame contains a detached checkerboard
                # remnant. Keep the connected character and discard tiny islands.
                rgba = np.array(frame)
                mask = rgba[..., 3] > 0
                labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=bool))
                sizes = np.bincount(labels.ravel())
                if len(sizes) > 1:
                    keep = sizes[1:].max()
                    rgba[(labels > 0) & (sizes[labels] < max(80, keep * .02)), 3] = 0
                    frame = Image.fromarray(rgba)
            # Crop to content
            bbox = frame.getbbox()
            if bbox:
                frame = frame.crop(bbox)
            
            # Scale
            s = TARGET_H / frame.height if frame.height > 0 else 1.0
            new_w = max(1, round(frame.width * s))
            new_h = max(1, round(frame.height * s))
            frame = frame.resize((new_w, new_h), Image.LANCZOS)
            
            # Ensure not wider than cell
            if frame.width > CELL_W:
                s2 = CELL_W / frame.width
                frame = frame.resize((CELL_W, round(frame.height * s2)), Image.LANCZOS)
            
            scaled_frames.append(frame)
        
        # Place 4 cells: frame1, frame2, frame1, frame2 (loop)
        anim_frames = []
        for cell_idx in range(4):
            f = scaled_frames[cell_idx % 2]
            x = cell_idx * CELL_W + (CELL_W - f.width) // 2
            y = row_idx * CELL_H + CELL_H - 6 - f.height  # feet 6px above bottom
            sheet.alpha_composite(f, (x, y))
            
            anim_frames.append({
                "x": cell_idx * CELL_W,
                "y": row_idx * CELL_H,
                "w": CELL_W,
                "h": CELL_H,
            })
        
        metadata["anims"][f"walk_{direction}"] = {"frames": anim_frames}
    
    return sheet, metadata


def build_all_characters():
    print("Building walk-cycle sheets...\n")
    for char_name in CHARACTERS:
        raw_file = GEN_DIR / "npc_src" / f"{char_name}_walkcycle_raw.png"

        if not raw_file.exists():
            print(f"✗ {char_name}: {raw_file} not found")
            continue

        print(f"Processing {char_name}...")
        frames_dict = parse_walkcycle_grid(raw_file, "interleaved" if char_name == "marcin" else "standard")
        sheet, metadata = build_sheet(char_name, frames_dict)

        sheet_path = DOCS_IMG / f"{char_name}_sheet.png"
        meta_path = DOCS_IMG / f"{char_name}_sheet.json"
        if char_name == "renik":
            # Magenta-keyed source: neutralise any pink rim left on the outline after scaling.
            px = np.array(sheet)
            rgb = px[..., :3].astype(np.int16)
            opaque = px[..., 3] > 0
            rim = opaque & ndimage.binary_dilation(~opaque, iterations=2)
            tint = rim & (rgb[..., 0] - rgb[..., 1] > 35) & (rgb[..., 2] - rgb[..., 1] > 25)
            px[tint, :3] = (rgb[tint].min(axis=1, keepdims=True) * .6).astype(np.uint8)
            sheet = Image.fromarray(px)
        sheet.save(sheet_path, optimize=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ {sheet_path}")
        print(f"  ✓ {meta_path}\n")
    print("Done! Sheets are ready in docs/img/")


if __name__ == "__main__":
    build_all_characters()
