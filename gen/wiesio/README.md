# WIESIO asset provenance

- `wiesio_walk_frontback_raw.png`: GPT Image 2 (openai-codex) sheet, 4x2, row 0 DOWN, row 1 UP; frames step / passing / other step / passing.
- `wiesio_walk_side_raw.png`: same, row 0 LEFT, row 1 RIGHT.
- Both were edited from earlier Wiesio sprites in the same session; the character design started from a private reference photo kept only in ignored `references/wiesio/`.
- Owner choices (2026-10-12): face of variant 2, lightly worn outfit of variant 1 (variant 5), light tipsy walk version 1. Rejected: stiff 2-frame walk, high knee lifts, strong drunk stagger and red nose.

Rebuild (pixel-identical to the approved review sheet):

```bash
python gen/build_wiesio.py
```

Writes `docs/img/wiesio_sheet.png`, `docs/img/wiesio_sheet.json`, `docs/img/wiesio.png` and `gen/wiesio/processed_manifest.json`.
Exploration sheets and GIFs: `C:/Users/Lenovo/Hermes/image-gen/2026-10-12-wiesio/`.
