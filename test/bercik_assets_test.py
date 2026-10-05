from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from gen.build_bercik import (
    CELL_H,
    CELL_W,
    DIRECTIONS,
    build_bercik,
    parse_walkcycle_grid,
)


RAW_SIZE = (400, 200)


def make_fixture_raw(path: Path) -> None:
    """Synthetic processing fixture; this is not a replacement for GPT raw art."""
    image = Image.new("RGBA", RAW_SIZE, (255, 0, 255, 255))
    draw = ImageDraw.Draw(image)
    for row in range(2):
        for col in range(4):
            left, top = col * 100, row * 100
            # Distinct, connected chunky silhouettes with a black hair cluster,
            # dark bag, and a different offset in every frame.
            shift = (col % 2) * 7 + row * 3
            x0 = left + 34 + shift
            y0 = top + 17
            draw.rectangle((x0, y0, x0 + 25 + row, top + 76), fill=(22, 29, 45, 255))
            draw.rectangle((x0 + 5, y0 + 9, x0 + 20, top + 47), fill=(24, 79 + col * 2, 104 + row * 4, 255))
            draw.rectangle((x0 - 5, top + 49, x0 + 30, top + 75), fill=(16, 33, 54 + col, 255))
            draw.rectangle((x0 - 12 + row, top + 35 + (col % 2) * 3, x0 - 6 + row, top + 57), fill=(108, 69 + col, 48 + row, 255))
            draw.point((left + 4, top + 4), fill=(0, 255, 0, 255))  # debris
    image.save(path)


def crop_cell(sheet: Image.Image, row: int, col: int) -> Image.Image:
    return sheet.crop((col * CELL_W, row * CELL_H, (col + 1) * CELL_W, (row + 1) * CELL_H))


def test_raw_grid_is_read_as_eight_independent_cells(tmp_path: Path):
    raw_path = tmp_path / "fixture_raw.png"
    make_fixture_raw(raw_path)

    cells = parse_walkcycle_grid(raw_path)

    assert list(cells) == [
        "down_a", "down_b", "right_a", "right_b",
        "up_a", "up_b", "left_a", "left_b",
    ]
    assert len(cells) == 8
    assert all(cell.size == (100, 100) for cell in cells.values())


def test_raw_grid_uses_rounded_boundaries_for_odd_dimensions(tmp_path: Path):
    raw_path = tmp_path / "odd_raw.png"
    Image.new("RGBA", (1774, 887), (242, 11, 240, 255)).save(raw_path)

    cells = parse_walkcycle_grid(raw_path)

    assert cells["down_a"].size == (444, 444)
    assert cells["down_b"].size == (443, 444)
    assert cells["up_a"].size == (444, 443)
    assert cells["left_b"].size == (444, 443)


def test_builder_writes_canonical_sheet_npc_metadata_manifest_and_preview(tmp_path: Path):
    raw_path = tmp_path / "fixture_raw.png"
    make_fixture_raw(raw_path)
    sheet_path = tmp_path / "bercik_sheet.png"
    metadata_path = tmp_path / "bercik_sheet.json"
    npc_path = tmp_path / "bercik.png"
    manifest_path = tmp_path / "processed_manifest.json"
    preview_path = tmp_path / "preview.png"

    result = build_bercik(
        raw_path,
        sheet_path=sheet_path,
        metadata_path=metadata_path,
        npc_path=npc_path,
        manifest_path=manifest_path,
        preview_path=preview_path,
        provider="fixture-provider",
    )

    assert result["provider"] == "fixture-provider"
    assert Image.open(sheet_path).size == (520, 680)
    assert Image.open(npc_path).size == (130, 170)
    assert Image.open(preview_path).size[0] > 520

    sheet = Image.open(sheet_path).convert("RGBA")
    pixels = np.asarray(sheet)
    assert set(np.unique(pixels[..., 3])).issubset({0, 255})
    opaque = pixels[..., 3] == 255
    colors = {tuple(rgb) for rgb in pixels[..., :3][opaque]}
    assert len(colors) <= 40
    assert not any(r > 180 and b > 150 and g < 100 for r, g, b in colors)

    fingerprints = []
    for row, direction in enumerate(DIRECTIONS):
        frame_cells = [crop_cell(sheet, row, col) for col in range(4)]
        alpha_boxes = [frame.getchannel("A").getbbox() for frame in frame_cells]
        assert all(box is not None for box in alpha_boxes), direction
        assert frame_cells[0].tobytes() == frame_cells[2].tobytes()
        assert frame_cells[1].tobytes() == frame_cells[3].tobytes()
        assert frame_cells[0].tobytes() != frame_cells[1].tobytes(), direction
        assert all(box[3] == 164 for box in alpha_boxes), (direction, alpha_boxes)
        fingerprints.extend(frame.tobytes() for frame in frame_cells[:2])
    assert len(set(fingerprints)) == 8

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["image"] == "bercik_sheet.png"
    assert metadata["foot"] == 6
    assert list(metadata["anims"]) == ["walk_down", "walk_up", "walk_left", "walk_right"]
    assert all(len(metadata["anims"][f"walk_{d}"]["frames"]) == 4 for d in DIRECTIONS)

    npc = Image.open(npc_path).convert("RGBA")
    assert npc.tobytes() == crop_cell(sheet, 0, 0).tobytes()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["input"]["dimensions"] == [400, 200]
    assert manifest["input"]["grid"] == {"columns": 4, "rows": 2}
    assert manifest["output"]["sheet_dimensions"] == [520, 680]
    assert manifest["output"]["cell_dimensions"] == [130, 170]
    assert manifest["palette"]["size"] <= 40
    assert set(manifest["frames"]) == set(
        f"{direction}_{frame}" for direction in DIRECTIONS for frame in ("a", "b")
    )
    assert all("bbox" in frame for frame in manifest["frames"].values())


def test_palette_preserves_exact_colors_across_full_rgb_distance():
    from gen.build_bercik import _apply_palette

    colors = [(15, 23, 34), (249, 176, 107), (255, 255, 255), (0, 0, 0)]
    image = Image.new("RGBA", (4, 1))
    image.putdata([(*rgb, 255) for rgb in colors])
    mapped = _apply_palette(image, colors)
    assert np.asarray(mapped).reshape(-1, 4).tolist() == [[*rgb, 255] for rgb in colors]


def test_real_front_walk_frames_have_no_single_pixel_left_temple_notch(tmp_path: Path):
    raw = Path(__file__).resolve().parents[1] / 'gen/bercik/bercik_walkcycle_raw.png'
    if not raw.exists():
        pytest.skip('Real generated source is not installed in this checkout')
    sheet_path = tmp_path / 'sheet.png'
    build_bercik(raw, sheet_path=sheet_path, metadata_path=tmp_path / 'meta.json',
                 npc_path=tmp_path / 'npc.png', manifest_path=tmp_path / 'manifest.json',
                 preview_path=tmp_path / 'preview.png')
    sheet = Image.open(sheet_path)
    for col in (0, 1):
        alpha = np.asarray(crop_cell(sheet, 0, col))[..., 3]
        # Native row 9 is the left temple: row 14 + 9*2 in the canonical cell.
        left = [int(np.flatnonzero(alpha[y])[0]) for y in (30, 32, 34)]
        assert left[1] <= min(left[0], left[2]), (col, left)


def test_temple_repair_preserves_upper_hair_right_edge_and_body():
    from gen.build_bercik import _repair_front_temple
    original = np.zeros((75, 30, 4), dtype=np.uint8)
    original[3:71, 8:23] = (30, 25, 20, 255)
    original[5, 8] = 0  # intentional upper-hair contour
    original[9, 8] = 0  # isolated left temple indentation
    original[9, 22] = 0  # right outline is outside this correction
    original[40, 8] = 0  # body outline is outside this correction
    expected = original.copy()
    expected[9, 8] = original[8, 8]
    repaired = np.asarray(_repair_front_temple(Image.fromarray(original)))
    assert np.array_equal(repaired, expected)


def test_builder_rejects_missing_or_malformed_raw_input(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_bercik(tmp_path / "missing.png")

    malformed = tmp_path / "malformed.png"
    Image.new("RGBA", (3, 200), (255, 0, 255, 255)).save(malformed)
    with pytest.raises(ValueError, match="4x2 equal grid"):
        build_bercik(malformed)
