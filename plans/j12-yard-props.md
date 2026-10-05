# J12 yard props

## Decision contract

Source review: `plans/yard-evidence-j12-decisions.json`, an exact byte copy of Tomek's supplied export. The original OneDrive file is not modified. Five `add` choices and one `skip` were supplied. User strings (including `belki siana jak na polu` and `krzewy / żywopło`) remain literal in provenance; the normalized runtime categories are separate.

Identification comes from **Tomek's review/local knowledge**, not independent recognition by the satellite vision model. Three small bushes, a parked truck and a cylindrical grain silo belong to yard 15. Two short hedge segments and three stationary hay bales belong to yard 18. The unidentified yard-18 object is omitted. The hay-bale bitmap is extracted from the game's exact existing `BALE_PX` runs/palette, at 24x16 world pixels. These yard bales are stationary storage props, not additional rolling field bales.

Approximate review centers intersect some enlarged game building sprites. Placement is therefore adapted to the nearest clear ground in the same yard, not a photogrammetric claim. The builder checks complete sprite clearance against the existing object/collision layers, adds a small gap, excludes roads/tracks/forest, and preserves space between new props. The two southern bales at the north edge and one at the south edge are deliberately spread rather than covering a house or access route.

## Build and runtime

### Cylindrical-bale follow-up

The user requested straight cylindrical barrel sides instead of the old peaked/croissant silhouette. A single Codex-generated replacement was reduced to the **unchanged 24x16 dimensions and original six straw colours**. The field `BALE_PX` bitmap and `docs/img/hay_bale.png` are verified pixel-identical, and this builder extracts those new runs for J12. No J12 positions, decision strings, save IDs or rolling physics are changed by this redraw. `gen/build_hay_bale.py RAW_PNG` emits the bitmap and an explicit V4A engine patch for review/application. Source/preview: `C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-cylindrical-bale/`. New `test/cylindrical_bale_test.py` checks barrel contours, palette, hard alpha and exact field/yard identity; existing `bale_styles_test.py` checks the live canvas and both hero/Frodo pushing. Both pass. The existing map rebuild had 83 field bales before this art change; a stale style-test expectation of 86 was replaced by exact current-map count/coordinate checks.

```
python gen/build_j12_props.py --raw C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-j12-props/props-raw.png --decisions C:/Users/Lenovo/OneDrive/---temporary---/yard-evidence-j12-decisions.json
python gen/build_yard_evidence_review.py --decisions plans/yard-evidence-j12-decisions.json
```

The sprite sheet is split by its **actual** dimensions (1536x1024), not the requested 1024x1024. Magenta is keyed, the dominant object retained, BOX resized to the world grid, then quantized without dithering and given hard alpha. Outputs: five `docs/img/j12_prop_*.png` files and `docs/data/j12-yard-props.json`. No shared map PNG or building placement output is rewritten.

`docs/js/yard-props.js` loads the manifest, checks image dimensions and renders y-sorted sprites with smoothing off. It registers one conservative footprint callback in the new `HOOKS.solidAt` list, used by real engine physics. Truck/silo are tall blockers; bushes/hedges/bales can be jumped. Collision and rendering are disabled indoors. No quests, NPCs, save fields or existing bale identities are changed. A save/debug coordinate inside a new blocker uses the existing `unstick()` escape search.

## Art provenance

One native Hermes `image_generate` edit call through **openai-codex**, requested `gpt-image-2-medium`. Returned quality `medium`, backend `reported_quality=low`; actual image 1536x1024. Request ID: `44c0ff5a-18a0-49b2-8be5-15be65af4594`.

Raw/references: `C:/Users/Lenovo/Hermes/image-gen/2026-10-04-chlopkow-j12-props/`. Style reference uses the accepted stone-shrine/iron-cross images, source reference uses real satellite crops. No private-person photographs were uploaded. Four new generated sprites plus reused field-bale art. Estimated incremental charge: **$0 per generated sprite, $0 total**, within ChatGPT subscription quota. Generation consumed quota; this is not a claim that the subscription itself is free.

## Review HTML

Every decision sheet includes **Kopiuj JSON** and **Pobierz decyzje JSON**, both using the same validated payload. Clipboard denial/file-URL restrictions trigger a selected manual-Ctrl+C field, never a false success. `--decisions` preloads the supplied review. A seed-specific localStorage key avoids stale pending answers while preserving subsequent edits. Review exports still say `gameChangesApplied:false`: the portable HTML never applies game edits; implementation status lives here and in the runtime manifest.

## Verification

- `node --check docs/js/game.js` and `docs/js/yard-props.js`.
- `test/yard_evidence_review_test.py`: choices/persistence/filter/import/export/copy success/manual fallback.
- `test/j12_yard_props_test.py`: accepted/skipped IDs, ten props, exact source strings, hard alpha/palette/keying, clear placements, live rendering with smoothing disabled, real engine collision and indoor exclusion.
- `test/hud_sector_test.py` and `test/hover_label_render_test.py`: desktop/mobile coordinate HUD and hover behavior.
- Live north/south screenshots inspected. Existing buildings and entrances remain unobstructed; no magenta or floating/roof-mounted props found. Early southern hedge placement was tightened to a short roadside strip.

All changes are local; no commit, push or deployment is implied.

## Domestic-life follow-up

`world-life.js` now gives part of the existing chicken/dog population a preference for the densest real `yard_building` clusters. Grass/reachability/engine collision and expanded building-front clearance are required. The initial quota is five chickens and three dogs; remaining domestic animals retain rural scatter. Counts/order/IDs remain 81 total, 12 chickens and 7 dogs. Existing valid saved animal coordinates override the preference, so this is not a forced relocation of an old save.

Parent verification against the integrated prop build: `farmyard_animals_test.py` PASS (37 farmyard buildings, 19 domestic animals, five chickens/one dog within the test's J12 radius, saved `chicken:0` restored). `animals_test.py` PASS (81 animals, stable seeded reboot, atlas/fallback and vehicle contracts). The new focused tests are runnable directly with `ARK_URL`; `test/run_all.py` was not edited in this workstream. Full suite not rerun.
