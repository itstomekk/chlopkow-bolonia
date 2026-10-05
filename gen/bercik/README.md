# BERCIK sprites and integration

Local addition for Chłopków Bolonia, approved by Tomek for a scoped BERCIK commit. No push or deployment performed.

## Assets

- `bercik_walkcycle_raw.png`: actual GPT Image 2 medium output through openai-codex; 1774x887, 4x2 grid. Top row down A/B, right A/B; bottom row up A/B, left A/B.
- `../../docs/img/bercik_sheet.png`: 520x680 hard-alpha atlas, 130x170 cells, foot offset 6, four animations with A/B/A/B frames.
- `../../docs/img/bercik.png`: forward-facing portrait/NPC fallback.
- `generation.json`: original generation provenance; private photographs only inspected locally, not uploaded.
- `processed_manifest.json`: output dimensions, palette, baseline, source hash and frame measurements.
- `preview.png`: enlarged review of the processed sprites, not raw output.
- `browser_evidence.json`, `in_game.png`, `dialogue_pl.png`, `title_desktop.png`, `title_mobile.png`: real browser evidence.

Screenshot capture waits for the eased map camera to converge after teleport; HUD coordinates alone do not prove that the NPC is in view. Tests do not require diagnostics from unrelated uncommitted forest-shade changes. Cached HTTP 304 responses on reload are valid; direct asset fetches still assert HTTP 200.

Summer appearance: dark hair, short beard, rectangular sunglasses, navy T-shirt and knee-length shorts, dark shoes, crossbody bag and silver watch. Stylized interpretation, not exact photographic likeness.

Cost: one medium generation charged against ChatGPT image quota, no separate per-image cash charge. Processing and tests are local.

## Rebuild and tests

From project root:

```sh
python gen/build_bercik.py --provider 'GPT Image 2 medium via openai-codex; ChatGPT image quota'
python -m pytest test/bercik_assets_test.py -q
node test/bercik_plugin_test.cjs
python -m http.server 8848 --bind 127.0.0.1 --directory docs
# Separate terminal:
ARK_URL=http://127.0.0.1:8848/index.html python test/bercik_test.py
python gen/bercik/verify_browser.py
```

RGB squared-distance calculations use int32: int16 overflow corrupts navy/skin palette assignments despite apparently valid dimensions, hard alpha and color counts. An exact-color preservation regression covers this.

Tomek selected variant A (original 75 px processing) over the 60/40/32 px pilots. Its viewer-left temple had a one-native-pixel contour indentation in both frontal poses. `_repair_front_temple` fills only isolated one-column notches in the temple band using an existing outline color, retaining upper-hair asymmetry. Exactly 16 atlas pixels change (one 2x2 block in each of four A/B/A/B front cells); the body, glasses, palette, metadata and all other directions are byte-identical to the approved A. Seven asset tests and the desktop/mobile browser regression pass. Closeup before/after and fresh solo J12 screenshots are in `C:/Users/Lenovo/Hermes/image-gen/2026-10-04-bercik/head-fix/` and the parent run directory. No new image generation was needed.

## Gameplay

`docs/js/bercik.js` registers the fixed NPC and PL/EN Space dialogues. Its installation runs once in a microtask after `ark-ready`, since game.js publishes `__game.isSpawnReachable` after the event dispatch. Placement checks center clearance, map collision, existing NPC distance and actual spawn reachability; there is no unchecked fallback. Verified position: (4864,5896), sector J12, track. A future map rebuild may choose a different valid deterministic position in that same sector.

The player selector includes BERCIK and persists the choice. Existing four-direction renderer provides diagonal fallback; regression observes the actual canvas source-frame rows rather than trusting an unused helper. BERCIK alone uses nearest-neighbor rendering. Existing characters retain their rendering behavior.

`test/bercik_test.py` is registered with the integrated runner. Focused tests and isolated minigames rerun passed. Child full run reported 35/36 (mowing timeout); parent full rerun exceeded tool timeout, so no completed full-suite pass is asserted. Other concurrent workstreams own yard/map changes; these were preserved.
