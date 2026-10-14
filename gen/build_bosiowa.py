#!/usr/bin/env python3
"""Build BOSIOWA's 4-frame walk-cycle atlas (same pipeline as WIESIO/IWONA, no sway).

Inputs: gen/bosiowa/bosiowa_walk_frontback_raw.png (rows DOWN, UP) and
gen/bosiowa/bosiowa_walk_side_raw.png (rows LEFT, RIGHT), GPT Image 2 via openai-codex.
Frames are aligned on the head centroid. Owner choices (2026-10-13): variant 13
(navy softshell with red zips, grey crate of mushrooms, tablet), proportions with a
bigger head than the first drafts, height 1.70 m -> 71 small px (142 px).
"""
from __future__ import annotations

import json
from pathlib import Path

import build_wiesio as bw

NAME = "bosiowa"
CONTENT_H_SMALL = 71
NO_LEAN = {d: (0, 0, 0, 0) for d in bw.ROWS}
RAW = {
    "frontback": Path("gen/bosiowa/bosiowa_walk_frontback_raw.png"),
    "side": Path("gen/bosiowa/bosiowa_walk_side_raw.png"),
}


def main() -> int:
    manifest = bw.build_wiesio(
        RAW,
        sheet_path=Path(f"docs/img/{NAME}_sheet.png"),
        metadata_path=Path(f"docs/img/{NAME}_sheet.json"),
        npc_path=Path(f"docs/img/{NAME}.png"),
        manifest_path=Path(f"gen/{NAME}/processed_manifest.json"),
        name=NAME,
        content_h=CONTENT_H_SMALL,
        lean=NO_LEAN,
        sway_px=0,
        align_head=True,
    )
    print(json.dumps({"sheet": manifest["output"]["sheet"], "palette": manifest["palette"]["size"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
