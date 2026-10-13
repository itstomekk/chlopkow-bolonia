#!/usr/bin/env python3
"""Build a cast walk sheet with the exact BERCIK recipe, at a chosen height.

Uses gen/build_bercik.py (4x2 raw grid, BOX regrid, shared <=40-colour palette,
hard alpha, 2x NEAREST, 130x170 cells, 6 px foot) with two additions:
  * --height sets the native content height (BERCIK = 75, so 80 is ~7% taller);
  * large magenta regions enclosed by an arm and the body are keyed too.

Outputs stay in the character's gen folder until Tomek approves integration.

    python gen/build_cast_walk.py build --name kostek --raw gen/kostek/walk/kostek_walkcycle_raw.png --out gen/kostek/walk --height 80
    python gen/build_cast_walk.py lineup --out review.png gen/kostek/walk/kostek_sheet.png ...
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "gen"))
import build_bercik as bb  # noqa: E402

_original_edge_connected = bb._edge_connected


def _edge_or_enclosed(mask: np.ndarray, *, minimum_hole: int = 40) -> np.ndarray:
    connected = _original_edge_connected(mask)
    labels, count = ndimage.label(mask & ~connected, structure=np.ones((3, 3), dtype=bool))
    if count:
        sizes = np.bincount(labels.ravel())
        big = np.flatnonzero(sizes >= minimum_hole)
        connected |= np.isin(labels, big[big != 0])
    return connected


bb._edge_connected = _edge_or_enclosed
FONT = "C:/Windows/Fonts/arial.ttf"


def build(name: str, raw: Path, out: Path, height: int, provider: str, cell_h: int = 170, colors: int = 40) -> dict:
    if not 40 <= height <= (cell_h - bb.FOOT) // 2:
        raise SystemExit(f"height must fit a {cell_h} px cell at 2x with a {bb.FOOT} px foot")
    bb.CONTENT_H_SMALL = height
    bb.PALETTE_COLORS = colors
    bb.CELL_H = cell_h
    bb.SHEET_SIZE = (bb.CELL_W * 4, cell_h * 4)
    out.mkdir(parents=True, exist_ok=True)
    manifest = bb.build_bercik(
        raw,
        sheet_path=out / f"{name}_sheet.png",
        metadata_path=out / f"{name}_sheet.json",
        npc_path=out / f"{name}.png",
        manifest_path=out / "processed_manifest.json",
        preview_path=out / "preview.png",
        provider=provider,
    )
    meta_path = out / f"{name}_sheet.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["image"] = f"{name}_sheet.png"
    if cell_h != 170:
        # game.js normalises by (f.h - foot - 14); taller cells need the renderer
        # to use this 150 px reference instead, or the extra height is lost.
        meta["ref_h"] = 150
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    manifest["asset"] = name
    manifest["content_height_native"] = height
    print(name, "height", height, "palette", manifest["palette"]["size"],
          {k: v["content_grid"] for k, v in manifest["frames"].items()})
    return manifest


def lineup(sheets: list[Path], out: Path, labels: list[str] | None = None) -> None:
    """Front + right frames of each sheet, BERCIK first, feet aligned, at 2x and 1:1."""
    paths = [ROOT / "docs/img/bercik_sheet.png", *sheets]
    names = ["BERCIK", *(labels or [p.stem.replace("_sheet", "").upper() for p in sheets])]
    cell_hs = [Image.open(p).height // 4 for p in paths]
    max_h = max(cell_hs)
    scale = 2
    col_w = 2 * 130 * scale + 30
    canvas = Image.new("RGBA", (len(paths) * col_w + 30, max_h * scale + 120 + max_h), (226, 224, 214, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT, 18)
    small = ImageFont.truetype(FONT, 14)
    base_line = 30 + max_h * scale  # bottom of every cell
    for i, (path, name, ch) in enumerate(zip(paths, names, cell_hs)):
        sheet = Image.open(path).convert("RGBA")
        x = 20 + i * col_w
        draw.text((x, 6), name, fill=(150, 20, 20) if i == 0 else (20, 20, 20), font=font)
        for j, row in enumerate((0, 3)):
            cell = sheet.crop((0, row * ch, 130, (row + 1) * ch))
            canvas.alpha_composite(cell.resize((130 * scale, ch * scale), Image.Resampling.NEAREST), (x + j * 130 * scale, base_line - ch * scale))
    bercik = Image.open(paths[0]).convert("RGBA").crop((0, 0, 130, cell_hs[0]))
    top = bercik.getchannel("A").getbbox()[1]
    y = base_line - (cell_hs[0] - top) * scale
    draw.line((10, y, canvas.width - 10, y), fill=(200, 40, 40), width=1)
    draw.line((10, base_line - 6 * scale, canvas.width - 10, base_line - 6 * scale), fill=(120, 120, 120), width=1)
    draw.text((20, base_line + 14), "skala gry 1:1 (czerwona linia = czubek głowy BERCIKA):", fill=(20, 20, 20), font=small)
    small_base = base_line + 40 + max_h
    for i, (path, ch) in enumerate(zip(paths, cell_hs)):
        sheet = Image.open(path).convert("RGBA")
        canvas.alpha_composite(sheet.crop((0, 0, 130, ch)), (20 + i * 120, small_base - ch))
    gy = small_base - (cell_hs[0] - top)
    draw.line((20, gy, 20 + len(paths) * 120, gy), fill=(200, 40, 40), width=1)
    canvas.convert("RGB").save(out, optimize=True)
    print(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--name", required=True)
    b.add_argument("--raw", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--height", type=int, default=75)
    b.add_argument("--cell-h", type=int, default=170)
    b.add_argument("--colors", type=int, default=40, help="shared palette size (BERCIK 40; lower = simpler)")
    b.add_argument("--provider", default="GPT Image 2 medium via openai-codex")
    l = sub.add_parser("lineup")
    l.add_argument("--out", type=Path, required=True)
    l.add_argument("--labels", nargs="*")
    l.add_argument("sheets", type=Path, nargs="+")
    args = parser.parse_args()
    if args.cmd == "build":
        build(args.name, args.raw, args.out, args.height, args.provider, args.cell_h, args.colors)
    else:
        lineup(args.sheets, args.out, args.labels)


if __name__ == "__main__":
    main()
