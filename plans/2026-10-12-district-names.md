# Local district names

## Approved scope

Tomek approved names on the M map and a subtle current-area name during outdoor play. The attachment `image_5971c1.png` is a local customary-area reference, not official administrative boundaries. Preserve Polish names in both language modes. No quests, discovery progress, terrain changes, collision changes, save-schema changes, commit, push or deployment.

## Architecture and ownership

- `docs/data/districts.json`: approximate WGS84 polygons, interior label anchors, original source-image vertices and registration provenance. Calibration worker owns this new file and `plans/districts-source-registration.md`.
- `docs/js/districts.js`: additive plugin installed after `ark-ready`. Convert WGS84 to art pixels from the current MAP bbox/scale, spatial lookup without assigning uncovered land, a compact badge below the minimap, and collision-avoiding name labels with leaders on the full map. Use existing HOOKS.update/hud; do not modify game.js or generated maps.
- `docs/index.html`: one script tag immediately before game.js. Re-read immediately before patching, preserving concurrent changes.
- `test/districts_geometry_test.js`: deterministic point-in-polygon, projection and malformed-data tests with synthetic test-only fixtures.
- `test/districts_test.py`: isolated real-browser integration test, drawn-text proof, desktop/mobile bounds and visibility, movement between regions, interiors/dialogue/minigame hiding, outside-area behavior and failed-data response.
- `test/run_all.py`: register only the new browser test, preserving concurrent entries.

## Execution and verification

- [x] Write geometry contract test; verify missing-plugin RED, implement the minimal geometry API, verify GREEN.
- [x] Tentatively place the source using four labeled OSM landmarks and document uncertainty. Imagery registration was NOT achieved; this is a local-review draft, not a precise georeferenced boundary dataset. Never fabricate anchors or extend districts beyond source shading.
- [x] Write browser acceptance test before UI implementation and verify missing integration RED.
- [x] Install plugin: nonblocking one-time fetch, strict data validation, deterministic overlap resolution, show no guessed name outside covered areas. Badge is hidden in title/end, room, dialogue, full map and busy minigames. On the M map, names have legible outlines and leader lines, avoid one another, stay inside the map, and retain the existing player/cursor markers. Show the approximate-boundary note. No additional NPC markers or minimap district clutter.
- [x] Test loading failure: game still boots/plays; M map reports names unavailable without false area labels.
- [x] Run Node syntax/geometry tests and repeated isolated browser checks, then relevant HUD/hover/map/room/save regressions and the full suite. Capture and visually inspect desktop/mobile screenshots. Full suite was not all green; see results below.
- [x] Update PLAN.md then HANDOFF.md with exact local verification and limitations. No public deployment.

## Verification results and remaining review

- Nine source-map areas. Unknown historical origins and administrative status are not inferred. Sułów is retained as a source area, not asserted to be an official district. Zagumienie and point labels remain provenance-only until a distinct boundary is supplied.
- Geometry/syntax PASS; real browser district tests PASS repeatedly, including touch, outdoor badge, all available areas, actual arrow movement, M/tap opening, 390x320 resize, all visibility gates and nonblocking HTTP 503 handling. Actual drawn-text tracer confirms the nine names; source polygons and label anchors validate.
- Hover labels, hover label rendering and sector HUD PASS separately. Full isolated suite returned **43/45**, with music and sprint CPU precision assertions failing. Music failure reproduced twice in a feature-disabled baseline and again enabled. Sprint's exact mean assertion failed once more enabled and subsequently passed enabled and both disabled follow-ups; its 1e-6 comparison does not allow rounding the server mean to 0.01 s. No changes to those unrelated paths and no full-suite-green claim.
- Parent source audit: matching original/copy SHA; source vertices reproduce world coordinates within 0.127 art px; recalculated label-fit RMS 59.9 m. Visual source-vs-game overlay is plausible at area scale, but does not establish exact alignment. North-up rotation remains an assumption, with 60-100 m typical and 150-200 m edge uncertainty.
- Review artifacts under `asset-review/districts/`: map/walk screenshots for desktop and phone, short-viewport screenshot, `source-game-overlay.png`. Colored fills/numbered pins occur only in that review image, not gameplay.
- Remaining: Tomek's local review of borders, especially the label-only placement uncertainty and Sułów. No commit/push/deploy authorized.
