# CHŁOPKÓW BOLONIA: asset style guide (DRAFT v0.1, 2026-10-02)

Status: **A2 pilot approved by Tomek 2026-10-02 (oak + boar, "super"; keep oaks rare).** Draft from Tomek's A0 labels (`plans/asset-labels-2026-10-02.json`). Becomes normative only after Tomek accepts the A2 pilot (oak + boar).
Roadmap: `plans/2026-09-28-asset-style-roadmap.md`. Audit: `plans/2026-10-02-architecture-asset-audit.md`.

## Style anchors (chosen by Tomek)

| ID | File | Why it is an anchor |
|---|---|---|
| `char.player.arek_8dir` | `docs/img/arek_sheet_8dir.png` | character proportions, outline, clothing clusters |
| `char.player.renik` | `docs/img/renik_sheet.png` | same, cleaner colour blocks |
| `animal.critter.bird` | `docs/img/critters.png` row 2 | small creature readability, hard edges |
| `landmark.shrine_stone` | `gen/lm_shrine_stone.png` (as composited in the map) | map-object detail level, texture, palette |
| `landmark.cross_iron` | `gen/lm_cross_iron.png` (as composited in the map) | same |

Compatible keepers (follow them, do not copy them): Arek (4-dir frame), Damian, Edytka, Sołtys and Zbyszek/Wesoły Świat atlas cells, trash, splash.

## What Tomek rejected, and the rule it implies

| Feedback | Assets | Rule |
|---|---|---|
| "too high resolution: pixels too small, too detailed" | grandpa, Mateusz, stork, minigame pig/dogs | Art must be authored on the **game grid**, not downscaled from a detailed painting. Fine 1-screen-pixel detail is out. |
| "too low quality" | procedural boar, pig, hare, mouse; tractors | Flat polygons with ~6 colours are out. Every sprite needs 2-3 step shading, outline and some texture clusters. |
| "make according to style" | procedural oak and birch | Trees should look like the shrines: textured clusters, outline, same palette. |
| "too big" | village sign | Objects keep real-world proportions relative to shrines (32-36 px) and characters (40 px). |
| "directions do not work" | car | Vehicles that move need views for every travel direction they use. |

## Required rules (proposed)

1. **Pixel scale.** One art pixel is between 1 and ~2 world pixels, never smaller:
   - map objects (trees, houses, shrines, signs): **1 art px = 1 world px**, composited into the map as-is;
   - critters and characters: **~2 art px per world px** (current boar/dog atlas ratio; Sołtys/Zbyszek recipe: 84 px grid for a 40 px tall character, then nearest-neighbour upscale).
2. **Palette and shading.** About 16-40 flat colours per sprite, no dithering, 2-3 shading steps, light from the upper left. Earthy village palette (greens, ochres, greys, brick) as in the shrine anchors.
3. **Edges.** Hard alpha only (0 or 255), 1 px dark outline, no magenta/halo pixels. No LANCZOS or smoothing at runtime (`imageSmoothingEnabled = false`).
4. **Perspective.** Slight top-down 3/4 for map objects; characters front/back/side + diagonals; animals side view, mirrored for left.
5. **Size and baseline.** Feet/trunk base on one baseline per sheet; all frames of one sheet share one scale. Reference sizes: character 40 world px tall, shrine 32-36 wide, village oak ~52-62 wide, sign proposed ~60 wide.
6. **Animation.** Same silhouette size across frames; walk cycles at least 2 frames; idle at least 2.
7. **Orientation (learned 2026-10-03).** A building's orientation comes from its on-map footprint, never from the reference photo's camera angle. Read the real footprint bearing from the game's own data (the fitted building rect in `docs/map.json`, or the OSM way axis), then state it explicitly in the prompt ("long axis vertical / north-south, sprite taller than wide" or "long axis horizontal / east-west, sprite wider than tall"). Example: the świetlica runs north-south, so its sprite must be vertical. A photo shot down the length of a building will otherwise make the sprite come out the wrong way.
8. **No fractional scaling (learned 2026-10-03).** Never resize finished pixel art by a non-integer factor (1.2x, 1.5x): nearest-neighbour on 1.2x doubles some pixels and not others, which reads as blurry/uneven. Re-pixelate the raw at the target size instead (BOX downscale to the exact grid), and use whole-number NEAREST only for display zoom.

## Generation recipe (GPT Image)

1. References: **anchor images only** (map crops upscaled with nearest, or atlas frames). Never private photos for style refs; photo refs only for likeness, local Codex only, never PPQ.
2. Prompt core (stored in `gen/pilot_2026-10-02/generate.py` as `STYLE`): genuine low-res pixel art, chunky square pixels, large flat clusters, 1 px dark outline, 2-3 step shading from upper left, ~20 colours, no anti-aliasing/gradients/noise, flat magenta #FF00FF background, no ground/shadow/text. State the target grid (e.g. "56x56 grid") AND the on-map orientation of the subject (see Required rule 7).
3. Post-process (`gen/pilot_2026-10-02/process.py`): magenta key -> drop debris -> **BOX downscale to the game grid** -> one quantized palette per sheet, no dither -> hard alpha -> place on baseline.
4. Review: in-context comparison at game zoom (old vs new, with Arek for scale), then Tomek approves before anything is wired into the game.
5. Record per asset: anchor IDs used, prompt, recipe, source/rights, cost (Codex = ChatGPT quota, no per-image charge).

## Real buildings from Street View + satellite (pilot 2026-10-03, Chłopków 27A)

1. Identify the building by OSM way id; address = OSM `addr:*` (46 of 118 houses have one). GUGiK UUG/PRG is
   unreachable from outside Poland (port 443 times out), so unaddressed houses stay "unknown", never guessed.
2. `python gen/streetview/building_refs.py <way_id> <dir>` makes the pack: aimed Street View frames
   (filename says which facade they see), north-up satellite with the OSM footprint, current in-game crop, refs.json.
3. Camera contract (from `osm/render_map.py` procedural houses): north up, viewed from the south, roof mostly
   from above, only the **south** wall visible, front-on (not isometric), light from the west, ground shadow to
   the south-east drawn by the map. Check which facade the photos show: if the road is not south of the house,
   the photos show a side the game never draws; say so before generating.
4. Pass the photos themselves to GPT Image (all frames on one sheet, then satellite, then 2 style anchors =
   4 images, the Codex limit). Do not rely on a vision model's description in the prompt.
5. Tomek: more colourful than the photos, same colour family; use all frames even if partly blocked; parts missing
   from the OSM footprint (extensions) may still be drawn.
6. Size: in-game house widths are OSM footprint x1.25-2.3; compare candidates in map context next to Arek before
   choosing (`gen/pilot_2026-10-03-house-27A/process.py`). Tomek's pick for 27A (11.5 m wall): **82 px**
   (~7.1 px per metre of wall); scale other houses by their real wall length.
7. Orientation: OSM footprints from the address import can be templates (27A and 28 are identical 11.5x10.2 m at
   92 deg), so check the satellite before trusting the angle. Along the main road the houses mostly stand E-W
   while the road runs at 113 deg; "parallel to the road" is not automatically true.
8. Skip houses whose road is north of them (e.g. Chłopków 28): Street View only sees the north wall, which the
   game never draws.
9. Rotated houses: GPT Image can redraw a house turned ~15-20 deg (pilot `gen/pilot_2026-10-03-houses/`), at the
   cost of jaggier slanted edges. Collision should then be the rotated footprint polygon (as the procedural houses
   already do, `render_map.py` fmask), and y-sort base = lowest footprint corner.
10. Do not trust a vision model's artifact reports blindly: verify halos/alpha numerically on the PNG.
11. Decided (Tomek, iteration 3): every house along a road is drawn **parallel to the road** at one shared angle;
    anchor `gen/pilot_2026-10-03-houses/27A_road.png`. Houses whose road is north of them still get done: their
    street side is drawn as the visible front wall (layout as in the photos).
12. Shadow and collision come from the sprite pixels, not from the OSM rectangle (`process3.py`): remove the flat
    procedural shadow colour around the old house, shadow = lower half of the silhouette offset (+5, +3), collision
    = silhouette shifted down by the wall height (~38% of sprite height) and clipped at the base.
13. Roof depth (Tomek, iteration 4: 28 and 26 were "too thin"): real roofs here are nearly square on the
    satellite (length:depth 1.1-1.3) and deeper than the OSM template outline. House sprite size:
    W = wall length along the road x 7.5 px/m, H = depth x 7.5 x 1.1 x 0.75 + 12 + 6 per extra storey
    (27A 86x81, 28 86x75, 26 72x65). Say "deep roof, do not flatten" and the target box in the prompt.
14. Never force GPT's drawing into the rule box: a forced 4:1 box turned sheds into towers. Fit the width and
    stretch the height at most 15% towards the rule (`process4.py` `fitted`).
15. Farm buildings: 5 px/m (exaggerated less than houses, otherwise plots overflow); they keep their real
    orientation relative to the house (long sheds perpendicular to the road show their gable end as the front);
    visible width = max(length along road, 0.6 x depth). Street View is 50-60 m away and mostly blocked, so the
    satellite carries most of the shape.
16. No Street View within 90 m: generate from satellite only (close + wide crop + 2 anchors) and invent plausible
    simple walls; redo when real photos exist (Tomek, iteration 4).
17. Tomek keeps reviewing every batch; each correction becomes a numbered rule here before the next batch.
18. Do not regenerate a drawing Tomek liked when he only asks for a size/thickness change: reuse its raw and
    stretch (max 15%). 28 iteration 3 was "super, just thicker"; iteration 4 regenerated it and lost it.
19. Angle comes from the satellite, not OSM: the OSM footprints here are axis-aligned import templates (farm behind
    27A is 90 deg in OSM, 117 deg on the satellite). Measure with an edge-direction histogram on a z20 crop and
    verify with guide lines drawn on the crop (`angle_check_*.png`). Houses along the main road use the road
    angle (Tomek's choice); every other building uses its own satellite angle.
20. GPT cannot hit an exact angle: "same angle as the anchor" gave 8-18 deg for a 23 deg target (measured on the
    bottom edge). NEVER rotate, shear or skew a GPT drawing afterwards (Tomek, iterations 5-6: full shear looked
    flat, residual shear to 23 deg also rejected). GPT's own rotation stays as drawn (variant A). If a building
    must be shown differently, regenerate it with a new prompt.
    For buildings away from the main road: choose the turn relative to their own road/house, still drawn by GPT.
21. Satellite-only buildings: draw only what the satellite shows (roof shape, ridge, colour, chimneys, annexes);
    walls plain, NO windows, doors, stairs, balconies or plants (Tomek).
22. Placement: an automatic solver keeps every building's ground off every other building's ground (shift up to
    +-16 px, then scale 0.9/0.8, smallest change wins, printed per building). If it still overlaps, the
    neighbouring old building has to be redrawn in the same batch (whole yards, not single buildings).
23. Whole yards (Tomek, iteration 6): a batch = house + every outbuilding of its plot. Outbuildings keep their
    real orientation relative to the house (satellite), drawn by GPT in the same projection. Yard 28 complete:
    house 28 + farm 909988763 + L-shaped farm 909988358, no overlaps.
24. SIZE BUG (Tomek, iteration 7: "houses too big, too little space"): the map is 2 px per metre, but rules 13/15
    used 7.5 / 5 px/m = 3.6x real size; the old procedural houses were ~2.4x and that is what the plot spacing
    fits. New rule: sprite width = OSM footprint width on the map x F, F about 2.2-2.6 for houses, x0.75 of that for
    farm buildings (`process8.py`; F chosen by Tomek from compare8.png). Rules 13/15 px/m values are superseded.

## Decisions

- Characters marked `adjust` get the Sołtys/Zbyszek re-grid recipe (Tomek, 2026-10-02): grandpa, Mateusz done via `gen/sprite_cleanup.py npc`.
- Oaks stay rare in the village (12% of village trees).

## Open questions for Tomek

- Birch/deciduous trees: same treatment as the oak once the oak is approved?
