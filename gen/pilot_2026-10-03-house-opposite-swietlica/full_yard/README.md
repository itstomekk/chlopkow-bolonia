# Chlopkow 3 whole-yard pilot

Preview only. No runtime, shared map, physics, or save files changed.

## Sources and scope

- Main house: OSM way `993157691`, Chlopkow 3. Preserve `../with_tree/4.png` (selected fourth candidate) pixel-for-pixel.
- House/tree preview translation: +2 map pixels east, +12 south relative to the previous preview. This is the owner's explicit request to increase the gap from the diagonal road, not a claim of satellite-accurate house positioning.
- Western outbuilding B1: OSM way `993157696`, roof corroborated on satellite.
- Southern outbuilding B2: OSM way `993157706`, roof corroborated on satellite.
- Small candidate B3: pale rectangular satellite feature, original clean crop envelope `(365,500)-(430,555)`. No corresponding nearby OSM footprint. Could be a roof, vehicle, or paved feature; the generated simple shed is an UNCONFIRMED hypothesis, not verified architecture.

`prepare_refs.py` retrieves a clean z20 Google satellite crop, overlays local OSM geometry and writes `references.json`. `sat_candidates.png` additionally marks B3 in cyan. Satellite material is reference evidence, not a redistributable game asset.

`outbuildings_raw.png` is the actual output of a single Codex GPT Image call, drawing three isolated outbuilding sprites together for palette/camera consistency. Prompt and returned generator metadata are preserved in session history; `manifest.json` records the returned source, provider/model, requested and reported quality, sizes and placement. Satellite-only walls intentionally have no invented openings.

## Repeat processing

Run `python gen/pilot_2026-10-03-house-opposite-swietlica/full_yard/process.py` from any directory. It reuses the saved generated cache file specified by `RAW`, not a new generation. Before cache pruning, replace `RAW` with local `outbuildings_raw.png` if needed. The process verifies three connected components, hard alpha, no magenta, exact selected old component sizes, unrelated object/ground pixels unchanged, no occlusion of unrelated objects, and unchanged shared map/accepted-sprite hashes.

B1 and B2 ground centres follow OSM footprint centres. B3 position derives from the satellite candidate via inverse Mercator and the game's own coordinate conversion. Projected ground-band centroid is 81% down each sprite. No flat rotation/shear, no fractional rescaling of completed pixel art; raw components are repixelated to target grid sizes.

## Review

Delivery: `C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-full-yard/`.

- `whole_yard_map.png`: clean context.
- `whole_yard_compare.png`: original procedural yard versus pilot.
- `whole_yard_labelled.png`: review labels, B3 explicitly provisional.
- `outbuildings_closeup.png`: all three source-grid sprites at integer 6x zoom.
- `sat_candidates.png`: evidence and uncertain candidate location.

Visual review: house stays road-clear; B1/B2 fit the yard without unrelated-building occlusion. B3 is partly hidden by the retained tree in context, so review its close-up and satellite marker before accepting it. Do not move it onto empty ground merely to make it visible. No integration, commit, or deployment performed.
