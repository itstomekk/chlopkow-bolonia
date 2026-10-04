# CHŁOPKÓW BOLONIA: architecture + asset audit (2026-10-02)

Scope: runtime JS (`docs/js/`), Python pipeline (`osm/`, `gen/`, `editor/`, `test/`) and every image the game loads.
Method: full read-through, Playwright probes, the full suite, PIL measurements. Baseline before changes: `test/run_all.py` 33/33 pass;
all 6 protected generator outputs match the `edits_pipeline_test.py` SHA-256 baseline.

This document is the A0 deliverable of `plans/2026-09-28-asset-style-roadmap.md` plus an architecture review.
No style anchor is chosen here. Tomek's labels come from the review sheet (`python gen/build_asset_review.py`, output in gitignored `asset-review/`).

## 1. Verdict

The game is in good shape for its size: zero runtime errors, stable 60 fps, O(1) collision, deterministic map builds, a working hook bus.
It scales **additively** for animals, playable characters and passive NPCs. It scales **with friction** for minigames and quest NPCs
(several places to edit per item). It does **not** yet scale to a second outdoor map. The biggest technical risk is **mobile memory/startup**
from the single 5143x7091 map. The biggest art risk is that the shipped "pixel art" is mostly high-colour AI raster, mixed with flat procedural
geometry, so it reads as three different styles.

| Axis | Verdict | What you touch to add one |
|---|---|---|
| Playable character | Good | `PLAYABLE_CHARACTERS` (game.js:34), `img/<id>_sheet.png/.json` via `gen/build_walk_cycles.py`, names in `T.pl/T.en` |
| Passive NPC | Good | atlas cell (`gen/build_npcs.py ORDER`) + `NPC_IDX` (game.js:174) in lockstep, `osm/place_items.py` or `edits.json`, names, `WANDER` |
| Quest NPC | Medium | the above + `talkNpc` if/else (game.js:~839-868), `freshQ()` key, HUD quest row |
| Animal | Best | one entry in `ANIMAL_TYPES` (world-life.js:24-41) + critters atlas row |
| Tree / house variant | OK | `tree()` / house block in `osm/render_map.py`; new random draws must use a local RNG or the whole map re-rolls |
| Minigame | Medium | 8 places in `minigames.js` (FLAGS, texts x2 langs, MEDAL, start/update/draw/HUD/questLog branches) |
| Interior | OK | new `buildX()` room module + `interact()` POI branch + music zone |
| Second outdoor map | Weak | single global MAP/GROUND/OBJ/SOLID, cloud literals, place names, minimap, spawn assume one village |

## 2. Fixed in this session (safe, no visual/gameplay change)

1. **Save loss for players named "Arek"** (HIGH). `loadSave()` blanked any name equal to AREK and returned "no save", so the title showed START
   and a new game overwrote the progress. Now only legacy v1 saves blank the old default AREK name, and a blank name no longer hides the save;
   `startGame(false)` re-asks the name and keeps progress. Save coordinates are also finite-checked. Test: `test/save_name_test.py`.
2. **Clouds drawn over interiors** (church/shop). `drawClouds` now runs only outdoors (the cloud *sound* was already room-gated).
3. **Duplicate full-size decode of `map_collide.png`** in `world-life.js`. It is now loaded only as a fallback when `map.json` lacks water points.

## 3. Open bugs and inconsistencies (not fixed, need a decision or bigger change)

- Clouds are placed with the old map size (`% 4675`, `% 5800`, game.js:216): no clouds in the southern ~18% of the map. Fix = derive from `MAP.w/h` (changes cloud positions, so tests/visuals shift slightly).
- Doc drift: HANDOFF race medals 15.5/14.0 s vs code `[Infinity, 18.5, 16.5]` (minigames.js:60); HANDOFF says 11 tests, suite has 33.
- Dead/latent: `NPC_IDX.mateusz` with no placement, atlas cells 9 (zbyszek) and 13 (soltys) unused, atlas slot 4 is named `irenka` in the builder but `halina` in the game; `interactionCooldown` (world-life.js:53), `historyShown` (chat.js), `L.names` (features.js).
- Jump frame frozen while airborne (game.js `P.air ? 2 % ...`); run multiplier 1.5 for jumps vs 1.8 for walking.
- Save merge type-checks only `missions`; a corrupt `Q.mg` string would throw in minigames.js. Normalize all Q sub-objects like `normalizeMissions`.
- `critters.json`, `vehicles.json`, `trash.json`, `frodo_idle.json` are never read at runtime; rows/poses are hardcoded in JS (world-life.js:31-40, game.js frodo poses). A rebuild that reorders rows silently misdraws animals.
- Editor `buildings` edits validate and save but no pipeline stage applies them (`osm/edits.py` `_a_buildings` has no caller). `editor/README.md` "hooks not yet done" is stale for the other layers.
- `osm/render_map.py`: global numpy RNG shared by water sparkles/ground noise/crops (insert one draw and everything downstream changes); footprint shrink loop can leave a building over a road with no assert; `CUSTOM_HOUSE_WAY_ID` raises if OSM data changes.
- No `requirements.txt`; map bytes depend on numpy/PIL/scipy versions (items.json already drifted once on a numpy sort tie). Machine-specific absolute paths in `gen/codex_gen.py`, `gen/ppq_gen.py`, `gen/gen_soltys_codex.py`.
- Chroma-key/background removal implemented 7+ times across `gen/` with different thresholds.
- `gen/lm_shop.png` and `gen/lm_shop_raw_v2.png` are byte-identical.
- First-ever spawn is now random over the reachable map, so a new player may start far from the quest chain.

## 4. Performance

- Runtime frame cost is fine (median 16.7 ms, no frames >32 ms, heap ~57 MB). Not a priority.
- **Startup memory is the #1 mobile risk:** `map_ground.png` 15.5 MB download, 3 full-size 5143x7091 layers decode to ~146 MB each, plus the forest bake canvas: transient peak ~480-520 MB. Low-end phones will crash or stall; there is no loading screen.
- Options, cheapest first: lossless WebP ground (measured ~2.3x smaller, no visual change); bake the C06 forest texture in the build instead of the browser; 512 px ground tiles with camera culling (download ~100-300 KB per view, decode ~25-50 MB).

## 5. Recommended refactors (ordered)

1. **Loading screen + WebP/tiled ground + build-time forest bake.** Biggest player-visible win on phones.
2. **Character/NPC registry** (`docs/data/characters.json`: id, names pl/en, sheet, atlas cell *by name*, wander/fixed/zone). Validate atlas cells at load. Ends the 4-file edit and the `NPC_IDX` slot coupling.
3. **Minigame registry:** one file per game exporting `{id, venue, medals, texts, start, update, drawWorld, drawHud}`; `minigames.js` iterates the registry.
4. **Scene abstraction:** `Scene {map layers, solid, pois, spawn, music, minimap}` replacing the `ROOM/OUT` global swap and POI branches. Prerequisite for new maps and cleaner interiors.
5. **Asset manifest** (`gen/assets.json`: id, path, kind, grid, foot, builder, inputs, runtime refs, source status, review label) feeding the review sheet and a parity test (atlas order vs `NPC_IDX`, critters rows vs `ANIMAL_TYPES`, church manifest vs `CHURCH_PIECES`). Private source filenames go to a gitignored `assets.local.json`.
6. Pipeline hygiene: `requirements.txt` pinned to the baseline versions, one shared `gen/keying.py`, local RNGs per feature in `render_map.py`, wire or reject editor `buildings` edits.

## 6. Asset audit (measured)

Three art families are mixed today:

| Family | Examples | Measured traits |
|---|---|---|
| A. AI raster "pixel-look" sprites | player sheets, NPC atlas, church furniture, landmarks, minigame pig/dog | 1,500-14,500 colours per sheet, 10-58% semi-transparent edge pixels; landmarks downscaled ~10x with LANCZOS (1448 px -> 90-150 px), so edges are soft, not a pixel grid |
| B. Procedural PIL geometry | houses, trees, ground, fences, tractors, critter rows 5-9 | flat fills, crisp hard alpha, few colours per object, low detail; trees are ellipses/triangles |
| C. True low-palette pixel art | cemetery memories (36-43 colours), church Sołtys (37), Frodo, trash, critters | hard alpha (0% semi-transparent), small palettes |

Specific outliers worth Tomek's eye: `animals.png` is drawn with image smoothing on (minigames.js:335, looks blurry next to everything else);
`car_red.png` is a smooth-shaded single image vs the pixel tractors; `church/backwall` and `flowers100` read as painterly; the village sign
lettering is cleaner/flatter than the photo-based landmarks; Kasia and Marcin are ~134-136 px tall in a 150 px standard and Edytka is much wider than Arek.

### Draft standard (to be confirmed only after Tomek picks anchors)

Measurable facts any new asset must already respect: humanoids use 130x170 cells, feet 6 px above the bottom, ~150 px content height, drawn at 40 world px;
landmarks have a fixed world width in `render_map.py`; everything is y-sorted by its foot/base line.
Proposed direction for the A1 style guide (needs approval): generate with GPT Image from approved anchors, then **downscale with nearest/box to the
real world size, quantize to one shared "Bolonia palette", harden alpha, add a 1 px dark outline**, so families A and B converge on family C.
Prompt + recipe + anchor IDs get recorded per asset in the manifest.

## 7. Next steps

1. Tomek labels assets in the review sheet (wzór stylu / zostaw / popraw / od nowa / usuń).
2. A1 style guide from the chosen anchors + one-house/one-tree pilot (A2).
3. Engineering in parallel, each its own small task: loading screen, WebP ground, character registry, minigame registry.
