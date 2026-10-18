# ZOSIA selected sprite (variant 3)

ZOSIA pushes a bicycle with mushroom baskets and shopping net bags. She has short brown-red hair, a slight hunch, and a plum jacket. Her house by the forest and her quest are deferred.

## Included inputs and rebuild

The eight generated RGBA frames in `rower_prowadzi/wide_<direction>_<a|b>.png` are the selected variant. Rebuild with:

`python gen/zosia/build_sheet.py`

This writes `docs/img/zosia_sheet.png` and `.json`: 640x680 atlas, 160x170 cells, rows down/up/left/right, foot padding 6. Animation contains two unique poses per direction (A/B/A/B), not four unique poses. The wider cell fits the bicycle; the renderer reads frame width from metadata.

## Runtime

`docs/js/zosia.js` adds one NPC on a reachable track about 1 km north of the cemetery, near JAZZ W STODOLE. Her home is (2596,1556), sector F4 on the current map; bounded placement and reachability checks determine it. `game.js` loads her NPC-only sheet and lets her wander within 120 world px (60 m). She is not a selectable character.

## Verification

`ARK_URL=<local-url> python test/isolated_browser_runner.py test/zosia_test.py` checks placement, wandering, rendering, dialogue and reload. `python test/zosia_assets_test.py` checks reproducible generation, hard alpha, key-colour removal, frame bounds and distinct A/B poses. Both tests are registered in `test/run_all.py`.

Only generated game art is included here. Private source photographs and unselected generation experiments are not part of this repository.
