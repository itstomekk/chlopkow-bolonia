#!/usr/bin/env python3
"""Build IWONA's 4-frame walk-cycle atlas (same pipeline as WIESIO, no sway).

Inputs: gen/iwona/iwona_walk_frontback_raw.png (rows DOWN, UP) and
gen/iwona/iwona_walk_side_raw.png (rows LEFT, RIGHT), GPT Image 2 via openai-codex.
Frames are aligned on the head centroid (owner: front/back walk swayed too much
when the swinging keys moved the bbox).
Owner choices (2026-10-12): everyday variant 1 (floral top, beige trousers),
keys as her attribute, height 1.70 m -> 71 small px (142 px) against BERCIK's
75 (150 px, ~1.80 m).
"""
from __future__ import annotations

import json
from pathlib import Path

import build_wiesio as bw

NAME = "iwona"
CONTENT_H_SMALL = 71
NO_LEAN = {d: (0, 0, 0, 0) for d in bw.ROWS}
RAW = {
    "frontback": Path("gen/iwona/iwona_walk_frontback_raw.png"),
    "side": Path("gen/iwona/iwona_walk_side_raw.png"),
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
