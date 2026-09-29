# Chłopków Bolonia — Unified Luna Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans, **one numbered card at a time**. Supervisor independently reviews changed files, test logs and visuals after each card before releasing the next. Checkboxes do not mean permission to start automatically. Project rule overrides generic skill instructions: no commit, push or deploy without Tomek's explicit request.

**Goal:** Improve world/gameplay quality and safely grow checkpoint missions and, later, local competitive minigames on the current-sized map, without a game-engine rewrite or loss of existing saves.

**Architecture:** Keep plain-JS Canvas, the OSM-generated map, one overworld character and the existing extension hooks. Implement visual/audio/wildlife fixes in narrow file-owned cards; preserve editor changes via its existing E2 pipeline; add a small authored mission catalog and versioned save bridge. Local multi-person play lives only inside a minigame. Nostr scores are a separate future design, not an extension of text chat.

**Tech Stack:** vanilla JS loaded in `docs/index.html`, Python `osm/` renderer/editor, PNG+JSON generated assets, localStorage, Python/Playwright browser tests, GitHub Pages. Do not add a framework, bundler, backend or online multiplayer.

**Project root:** `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie`. This is the **single canonical queue** for this request. Inputs: `plans/2026-09-28-game-growth-luna-tasks.md`, `plans/2026-09-28-map-editor.md` (E2) and `C:\Users\Lenovo\Hermes\.hermes\plans\2026-09-28_150437-temp-gameplay-quality-handoff.md` (15 requirements). A0–A4 asset-style review stays independently gated in `plans/2026-09-28-asset-style-roadmap.md`; do not substitute this queue for that approval process. Tomek's explicit restoration request is a **narrow exception for the verifiably earlier red-car art** (B07), not permission for broader style replacement. The earlier G-plan is superseded **as an execution queue**, not deleted; this document carries its relevant scope.

**Status:** written plan only. No game-code or generated-art changes are authorized by writing it. Where a requirement says “implement”, the assigned Luna worker does so when Tomek starts the queue, under the gates below. Local HEAD, files and test counts must be rechecked then; don't assume this snapshot is still current.

## Product/interpretation contract

- Map stays approximately the current 5143×7091; more and better houses, characters, scenery, checkpoints and minigames are added within it. Existing 21 house quiz markers are questions, not completed missions or rooms.
- Most home interactions use an **outdoor** object/marker. Enterable interiors are special-purpose; do not create 21 rooms. No false assertions about identifiable residents or their homes.
- Hover label in the **normal world**, next to bottom-left coordinates; separate from existing M-map hover. NPCs use displayed/translated names, hero selected name as appropriate. Touch-only users should not see a stuck mouse label.
- Direction text: `← DUŃCY` only west, `WIELKIE KSIĘSTWO LITEWSKIE →` only east. Main HUD has **time, apples, mushrooms**; trash `0–5` appears in quest list with quiz progress. Existing bags, pickups, old saves and side overlays must remain functional.
- Animals persist as continuous world objects. No mouse temporary invisibility/teleport. Mouse art is 25% of former **width and height**, but interaction/chase distances stay unchanged. Chicken/mouse/bird shadows removed in both atlas and fallback paths. Friendly Frodo/dog play must not displace Frodo/mouse chase. Registry is narrow, not a simulation rewrite.
- Make bale art larger/rounder without breaking push physics; red car gets the specific previous artwork located via git history, not a speculative replacement. Cloud linear dimensions ≥5× earlier, lumpy silhouette, shadow roughly 2× contrast but visually capped; culling must account for expanded bounds and 4× CPU performance.
- Forest floor texture improves but differs from meadow/fields. **Do not assume a whole-forest collision mask exists:** `render_map.py` currently labels forest as walkable and uses `forest_mask` for art/terrain while specific trunks set collision. Measure trunk/inter-tree path samples first; change only a confirmed broad block or oversized footprint. Preserve water/building/road/path collision and reachable spawn/venues.
- Main Polka Dziadek Ogg plays in ordinary village, fields and Jazz barn, with activity tempo. Exceptions: forest `pastoralka`, shop `mazurka`, church `choral`, cemetery/end `nokturn`. **Keep existing minigame-only `oberek`** by default, since it is not a geographic zone. Keep boundary hysteresis, mute/audio unlock and no simultaneous Ogg+synth; if Tomek changes the minigame rule, revise Q05 before execution.
- Open-by-default chat on the **right**: readable transparent over-game message text, no boxed panel/background. Retain input/send, accessible controls, minimized preference, reconnect, sanitization and anti-XSS. Minimized launcher may be distinct but must not create a floating opaque chat window.
- One hero traverses world. Future simultaneous local players use different keys inside a minigame and each has own score. Never instantiate more overworld heroes. Nostr leaderboard is later and must not claim client-submitted scores are cheat-proof.

## Ownership, execution and verification protocol

1. **Before every card:** read project `AGENTS.md`, `PLAN.md`, `HANDOFF.md` CURRENT STATE, this plan, relevant source/subplan, `git status --short --branch`, and the diff for owned files. Preserve all unrelated dirty/untracked assets, music, private references, editor basemap/cache. Record exact HEAD. No global reset, `localStorage.clear()` on a real browser, broad staging or publication.
2. **Every card:** write a specific failing test (RED), run it and record failure, implement the smallest change (GREEN), run focused and adjacent tests, inspect diff. For a pure baseline/guard card, assert expected existing behavior instead of forcing an artificial failure. Use `node --check` for changed JS. Existing browser tests require `python -m http.server 8765 --directory docs` (run in a separate terminal) and `python test/<name>.py`; `python test/run_all.py` currently enumerates 25 browser cases. Verify actual count rather than copying historical 11/25 claims. Test in fresh isolated Playwright contexts only.
3. **Luna self-check:** return exact modified file list, RED and GREEN commands/results, save/migration impact, screenshot paths with 1280×720 and 390×844 for UI/visual cards, and any remaining issue. No “looks fine” without evidence. **Supervisor (Sol or assigned reviewer)** independently checks scope, diff, test evidence and interactions; if not accepted, return only that card with concrete changes. Do not auto-run the next card. Do not mark a failing test as solved by weakening its assertion.
4. **One writer per shared file.** `docs/js/game.js` cards are serialized with each other; likewise `world-life.js`, `chat.js`, `music.js`. `osm/render_map.py`, `osm/place_items.py`, `osm/edits.json`, `docs/map.json`, `docs/items.json`, and `docs/img/map_*.png` have an **exclusive generator lock** across E2, forest and asset A-series work. Never test a generator against live outputs without temp output or safe backup/restore and post-run hash verification. No private photos/basemaps/raw reference sheets in deliverables.
5. **Gates:** product/visual approvals remain Tomek's: first house mission, asset-style anchors, and multi-person minigame feel. No commit/push/deploy until separately requested. A worker can add newly stable tests to `test/run_all.py` in its own final integration card; do not run the growing full suite after every tiny graphics adjustment if focused tests suffice, but run at each phase boundary.

## Execution order and narrow Luna cards

**Phase A: baseline and low-risk presentation.** A00 → A01 → A02 → A03 → A04 → A05 → A06. Cards touching `game.js` run one after another. A01 is a guard, not a license to change working signs. A04–A06 can be rescheduled relative to one another if file ownership stays exclusive.

### A00 — Capture baseline (read-only; must precede everything)
**Owns:** no game files. **Depends:** none.
- [ ] Record HEAD/status and current `map.json` dimensions; counts of bales/water/POIs/animals derived from actual files. Confirm map/editor/asset worker ownership, not historical counts in the temporary handoff.
- [ ] Start local HTTP server; run existing `python test/run_all.py`, `python test/edits_test.py`, `python test/editor_test.py` and `for f in docs/js/*.js; do node --check "$f" || exit 1; done`. Capture genuine results and baseline screenshot/5-minute animal observation/`python test/perf_test.py` with 4× CPU. If something fails, identify pre-existing failure before assigning it to a new card.
- [ ] Supervisor checks snapshots of west/east, normal HUD, chat, field/forest, mouse/dog, bale/car/cloud and current audio routing. No screenshot or benchmark script may overwrite unrelated tracked resources.

### A01 — Protect west/east sign semantics
**Owns:** `test/village_sign_test.py` or `test/presentation_changes_test.py`; `docs/js/game.js` **only if guard fails**. **Depends:** A00.
- [ ] Add regression that `directionSignEdges(W)` / world render labels appear only on their correct map edges at desktop and narrow viewport; check movement and M-map leave no wrong-side label.
- [ ] Run focused test. If already GREEN, **do not alter signs**. If RED, repair just the edge gating in `game.js:1122–1129,1488–1496`, rerun focused sign and `test/map_followup_test.py`.

### A02 — Hit-test for normal-world hover labels
**Owns:** `docs/js/game.js`, new `test/hover_labels_test.py`. **Depends:** A01.
- [ ] Add RED cases for world-space and screen-space hit tests: selected hero, named NPC, Frodo, building, tree, apple, mushroom, trash, bale, car, tractor, mouse/bird and empty ground. Use representative visible objects from live `MAP`/`ITEMS`/`__worldLife`, not invented coordinates. Check nearer/front-most object wins when hit regions overlap and localization is PL/EN where existing names exist.
- [ ] Implement a small world hover picker using the actual camera inverse and object draw extents. `mapHoverLabel()` (`game.js:573`) is M-map-specific; keep it independent. If a type is owned by `world-life.js`, expose a small read-only list/hit-test adapter instead of duplicating a second animal/car registry in `game.js`.
- [ ] Run `python test/hover_labels_test.py`, `python test/animals_test.py`, `node --check docs/js/game.js`; supervisor verifies picking is side-effect-free and absent private-person metadata is not invented.

### A03 — Render hover label beside coordinates
**Owns:** `docs/js/game.js`, `test/hover_labels_test.py`. **Depends:** A02.
- [ ] Add RED Playwright cases for label near existing bottom-left coordinates, correct text after pointer moves, hide on `pointerleave`, title/dialogue/big M-map, and no stale label on touch-only/mobile. Assert no pointer/click-to-move interference and viewport-clamped text at 1280×720 and 390×844.
- [ ] Render one small world label in the coordinate HUD using A02 picker; never reuse the large M-map floating label box. Run focused test, `python test/play_test.py`, `node --check docs/js/game.js`; screenshots reviewed by supervisor.

### A04 — HUD: trash moves to task list
**Owns:** `docs/js/game.js`, `test/latest_world_requests_test.py` or `test/presentation_changes_test.py`. **Depends:** A03.
- [ ] RED: primary row contains exactly timer/apple/mushroom; quest list shows trash `0/5`, incremental `1/5` and `5/5` completion, survives reload, quiz rows still render. Use an isolated browser context with a legacy save fixture.
- [ ] Remove only `game.js:1425–1428` trash icon/counter and add localized trash row to the existing `lines` near `:1408–1414` from existing `trashCount()`/`TRASH_TOTAL`; no new persistent counter and no removal of five trash pickup objects.
- [ ] GREEN: focused test plus `python test/quest_test.py`, `python test/quiz_expansion_test.py`; supervisor checks HUD isn't inadvertently expanded by side overlays and legacy save remains intact.

### A05 — Music routing, no track replacement
**Owns:** `docs/js/music.js`, `test/music_test.py`. **Depends:** A00; serialize with other audio editors.
- [ ] RED routing matrix: title/village/field/Jazz barn → main Ogg; forest → `pastoralka`; shop → `mazurka`; church → `choral`; cemetery/end → `nokturn`; minigame → `oberek`. Test enter/leave and hysteresis, tempo while moving/stopping in a field, mute and single audible source.
- [ ] Change `pick()` (`music.js:481–493`) and `tick()` (`:355–363`) so `field`/Jazz no longer route to `krakowiak` or `jazz`; preserve exceptions' precedence and adaptive `MAIN_TRACK` playback rate. Avoid unrelated audio-file changes or unlicensed recordings.
- [ ] GREEN: `python test/music_test.py`, `node --check docs/js/music.js`, listen/observe transitions in browser; supervisor checks no rapid zone flapping or Ogg/synth overlap.

### A06 — Transparent right-side chat
**Owns:** `docs/js/chat.js`, new `test/chat_overlay_test.py`, existing `test/soltys_chat_test.py` only if relevant. **Depends:** A00; no other chat writer.
- [ ] RED: desktop/mobile DOM layout asserts right alignment and transparent panel/no enclosing border; overlay open by default unless minimized preference is set; readable text, form/send/minimize, text focus and keyboard isolation; no overlap with map/minimap, dialogue and right-side touch controls. Use offline/mock relay where possible; no actual Nostr post for layout testing.
- [ ] Adjust chat CSS (`chat.js:72–127`) and `placeChat()` (`:424+`), retaining event sanitization, connection/retry, accessible names/contrast, and persisted minimize. Keep `.arek-chat-day` hidden. Adapt position on dialogue/map, then restore without losing input or messages.
- [ ] GREEN: `python test/chat_overlay_test.py`, relevant `python test/chat_test.py` **only if safe against live relays** (otherwise isolated/mock test plus record limitation), `node --check docs/js/chat.js`; screenshots at both viewports.

**Phase B: wildlife and sprites.** B01 → B02 → B02b → B03 → B04 touch `world-life.js` serially. B05–B06 touch `game.js` serially. B07 requires art provenance before any replacement. No shared generator rebuild in this phase.

### B01 — Small extensible animal-type registry
**Owns:** `docs/js/world-life.js`, `test/animals_test.py`, `test/world_life_test.py`. **Depends:** A00.
- [ ] RED: every current `CRIT` species is enumerated once with category, atlas row/scale, habitat, count, movement/interaction and visibility policy; initial per-kind counts and allowed habitat equal baseline for fixed test seed. Give spawned animals a stable `kind:index` identifier without changing placement. No automatic save-format migration in this card.
- [ ] Consolidate existing ad hoc kind constants/lookup tables (`world-life.js:10,184–269,316–335`) into a small `ANIMAL_TYPES` descriptor; preserve existing species counts/order, spawn positions and saved `Q.worldLife` semantics while adding stable IDs. Use existing behavior handlers, not a generic AI framework.
- [ ] GREEN: `python test/animals_test.py`, `python test/world_life_test.py`, `node --check`; supervisor rejects a broad rewrite or new unexpected species/counts.

### B02 — Mouse continuity under flee and camera changes
**Owns:** `docs/js/world-life.js`, `test/world_life_test.py`, `test/animals_test.py`. **Depends:** B01.
- [ ] RED: capture the same mouse object/ID across near-Frodo flee, >2-second former invisibility interval and leaving/re-entering viewport **within one session**. Assert no `hiddenT`-driven draw suppression and bounded continuous displacement; permit ordinary offscreen culling, not teleports/respawns. Use `__worldLife.animals`/`stepInteractions` where appropriate and verify with a visible browser run. Cross-reload continuity is B02b.
- [ ] Remove `hiddenT` early return and `hiddenT=2` path (`world-life.js:368–376,544`) for mouse; return home with normal movement/target behavior while preserving squeak/flee/chase and stable hit range. Search sibling animal paths for hidden/despawn/teleport and fix the same class only where confirmed.
- [ ] GREEN: both focused animal tests and a five-minute browser observation with persistent ID/count and screenshot snapshots; supervisor checks mouse is visible when onscreen, not frozen or trapped.

### B02b — Preserve animal identity/location across save and reload
**Owns:** `docs/js/world-life.js`, `test/world_life_test.py`; `game.js` only if a narrow existing-save hook is strictly needed. **Depends:** B01–B02. This is not a full simulation save.
- [ ] RED in an isolated browser context: legacy `Q.worldLife` with no animal snapshot still spawns baseline species/count; after ordinary save/reload, each animal has the same `kind:index` ID and a validated nearby position (not a randomized new home); malformed/unknown snapshot IDs, NaN or solid-map positions are ignored safely; car/tractor saves remain unchanged.
- [ ] Persist only stable IDs, kind, bounded x/y and home/target if needed for continuous return; use a bounded save interval and final pagehide/title-save snapshot, not `localStorage` every frame. Restore against freshly built baseline animals by ID after validation, without changing existing quest/save key. Check save payload size and 4× CPU effect.
- [ ] GREEN: `python test/world_life_test.py`, `python test/animals_test.py`, `python test/perf_test.py`, `node --check docs/js/world-life.js` (and `game.js` if touched). Supervisor verifies one save/reload visually and no disappearing/duplication.

### B03 — Mouse sprite ¼ size; three shadow exclusions
**Owns:** `docs/js/world-life.js`, focused visual extension of `test/animals_test.py`. **Depends:** B02b.
- [ ] RED: mouse rendered width and height are each 25% of baseline (not quarter area), hit/chase radii unchanged; chicken/mouse/bird have no `A.shadow` in atlas **or fallback**, while dogs/boars/other species keep normal shadows.
- [ ] Adjust per-kind art size only (current atlas dimensions via `CRIT.mouse`, `world-life.js:545–548`); audit fallback `drawSmallWildlife` around `:580–610` so it cannot restore suppressed shadows. Do not rescale object physics or collision.
- [ ] GREEN: `python test/animals_test.py`, visual screenshots at normal gameplay zoom, `node --check docs/js/world-life.js`. If the 25%-size art is unreadable, preserve the requirement and flag contrast/atlas follow-up for Tomek instead of silently enlarging it.

### B04 — Friendly Frodo/dog interaction
**Owns:** `docs/js/world-life.js`, `test/world_life_test.py`, `test/frodo_test.py`. **Depends:** B02.
- [ ] RED: when Frodo approaches another dog, visible brief greet/sniff/play state and cooldown; both return to prior movement, no aggression/endless chase; Frodo/mouse chase remains possible and unaffected when it has priority. Animal IDs/count unchanged.
- [ ] Add bounded interaction near existing dog behavior in `world-life.js:391+` and Frodo chase sync `:345+`. Reuse existing visual speech/action hooks where feasible; do not create a new NPC or persist an ephemeral greeting in `Q`.
- [ ] GREEN: focused tests, live visual capture and `node --check`. Supervisor checks interactions end in bounded time.

### B05 — Larger, rounder hay bales
**Owns:** `docs/js/game.js`, `test/latest_world_requests_test.py`/new focused bale test. **Depends:** A04.
- [ ] RED: capture old bale geometry at current zoom; new visible bounds are larger, aspect approximately 1.4–1.7 unless Tomek approves another preview; push/roll collision and controls still work. Test contact with single hero and Frodo and a nearby walkable route.
- [ ] Replace only `BALE_PX`/`drawBale` (`game.js:1113–1120`) and adjust cached art/shadow and hit radius `baleAt` (`:855`) together if art exceeds physics. Do not regenerate map bales; count/coordinates remain identical.
- [ ] GREEN: focused test, `python test/play_test.py`, `python test/perf_test.py` before/after, screenshots at gameplay scale and `node --check`. Supervisor checks sprite is rounder rather than merely stretched.

### B06 — Large lumpy clouds with correct culling
**Owns:** `docs/js/game.js`, focused cloud visual test and `test/perf_test.py` execution. **Depends:** B05.
- [ ] RED: baseline and new width/height from `drawClouds()` (`game.js:1130–1147`) show each linear footprint ≥5×; shadows visually about 2× darker but capped; clouds that overlap screen render even when their center is beyond old ±150/±90 culling; no gameplay collision.
- [ ] Use a connected, non-uniform cloud silhouette; recalculate culling margins for new bounds and cache geometry if necessary. Keep cloud count and weather purely visual. Avoid naively multiplying fill calls by area.
- [ ] GREEN: focused screenshot comparison, `python test/perf_test.py` (4× CPU) with baseline delta reported, `python test/play_test.py`, `node --check`. A measurable severe regression blocks acceptance; supervisor decides threshold against baseline before another attempt.

### B07 — Restore previous red car art, not behavior
**Owns:** selected existing red-car source/atlas generator and resulting `docs/img/car_red.png` or `docs/img/vehicles.png` only after identifying actual draw priority; `test/animals_test.py`/`test/world_life_test.py`. **Depends:** A00; coordinate with asset A-series, no private photos.
- [ ] **Read-only discovery first:** `git log --all -- docs/img/car_red.png docs/img/vehicles.png gen/build_vehicles_pixel.py`, then visually inspect actual candidate bytes/revisions with `git show` and current `drawCar` (`world-life.js:612–618`). Current `vehicleImage` may override `carImage`; prove which asset the renderer actually uses. Do not treat untracked raw source as an approved replacement.
- [ ] RED: asset/sprite snapshot checks red car's chosen earlier art and keeps same atlas cell mapping and original vehicle behavior. Restore precise selected revision **only when provenance and render path are verified**; if no exact matching old art exists, stop at preview/approval rather than inventing a car.
- [ ] GREEN: vehicle tests, desktop/mobile screenshot, source/asset hash comparison, `node --check` if JS changed. Preserve car ride, collisions and sprite atlas indices; supervisor checks generated atlas and source stay reproducible. No blanket restore of other sprites.

**Phase C: generator and forest, exclusive map lock.** Finish E2 safe harness and hooks before any forest rerender, then collision verification, then forest art. This is a serialized generator lane; never run it concurrently with A0–A4 asset/map output changes.

### C01 — E2 safe isolated generation harness
**Owns:** new `test/edits_pipeline_test.py`, temporary fixture(s) in `test/fixtures/`, minimal output-route/test support if genuinely required. **Depends:** A00, exclusive lock.
- [ ] Capture hashes/backups for `docs/map.json`, `docs/items.json` and actual generated `docs/img/map_*.png` in Hermes scratch. Compare missing/empty edits to existing generator baseline; inspect `osm/edits.py` stage API and existing `plans/2026-09-28-map-editor.md:107–119` before writing calls.
- [ ] Add a test that can run generator safely with output routed to temp or fully backed-up/restored. If cannot guarantee preservation of concurrent dirty files, stop and report blocker. Verify original hashes after test, not just exit code.
- [ ] Supervisor approves this route before C02 changes generator sources.

### C02 — E2 forest/water hooks
**Owns:** `osm/render_map.py`, `test/edits_pipeline_test.py`, fixture. **Depends:** C01.
- [ ] RED fixture: one forest.add/remove and water.add change their intended ground/collision; empty edits yield byte-identical baseline. Add only corresponding `edits.apply` hooks at actual stages verified against `osm/edits.py`; GREEN.
- [ ] Run `python test/edits_test.py`, `python test/edits_pipeline_test.py`, check original `docs/` hashes restored; supervisor inspects generated diff/fixture map without overwriting real art.

### C03 — E2 trees and collision hooks
**Owns:** `osm/render_map.py`, same test/fixture. **Depends:** C02.
- [ ] RED fixture: explicit tree appears, tree clearing removes only selected generated trees, block/free overrides collision without blocking roads. Install only tree and final collision hooks; GREEN.
- [ ] Repeat pipeline tests and empty-edit equality, review trunk/canopy coordinates, verify output restoration. Do not solve forest path request by blanket-clearing all trees.

### C04 — E2 entity hooks
**Owns:** `osm/render_map.py`/`osm/place_items.py`, same test/fixture. **Depends:** C03.
- [ ] RED fixture for one known NPC/venue anchor override; unknown ID fails loudly; empty edits preserve baseline. Add actual stage hook without changing public runtime; GREEN.
- [ ] Run `python test/edits_test.py`, `python test/edits_pipeline_test.py`, `python test/editor_test.py` and map/venue tests. Supervisor verifies generated-file hash restoration and E2 acceptance, then releases forest cards.

### C05 — Forest path and trunk collision **diagnosis/fix only if proven**
**Owns:** `osm/render_map.py` only if necessary, new `test/forest_path_test.py`, generated outputs under exclusive map lock. **Depends:** C04.
- [ ] Guard tests: sample trunk center solid, between-tree forest floor free, main forest routes reachable from spawn, roads/water/buildings/venues retain collision; compare current PNG values and `render_map.py:332–334,747,755–848,907–916` before assuming a bug. Include nearest-neighbor in-game walk-through.
- [ ] If guards already pass, mark collision change **not needed** and leave generator/collision unchanged. If fail, write RED case for exact obstruction, change only broad forest blocker or oversized trunk footprint (same deterministic tree positions), rerender safely, GREEN. Don't weaken water/building collisions or erase forest terrain class.
- [ ] Check map bbox, actual bale/water/POI counts, spawn and named venues against A00 baseline; run `python test/trees_test.py`, `python test/map_venues_test.py`, `python test/forest_path_test.py`. Supervisor checks accessible routes by browser and output diffs. No hard-coded historical counts such as “86 bales” without remeasurement.

### C06 — Forest-floor texture (visual, deterministic)
**Owns:** `osm/render_map.py`, generated `docs/img/map_ground.png` and corresponding artifacts only if generator output requires; visual regression test. **Depends:** C05, exclusive lock.
- [ ] RED visual crop/property test: forest floor differs clearly from flat solid green, meadows, fields and roads; same input/seed reproducibly yields same output; collision and terrain class unchanged.
- [ ] Replace only forest ground fill/pattern near `render_map.py:785–848` with bounded low-contrast litter/moss/grass marks; do not alter tree count, forest footprint, collision or mask semantics. Regenerate through C01 safe path and inspect 3× nearest-neighbor crops from distinct forest spots plus actual camera view.
- [ ] Run forest/map tests, compare bbox/spawn/POIs/counts and output hashes, `python test/perf_test.py` if loaded PNG weight changes significantly. Supervisor checks texture at gameplay zoom and accepts generated outputs **together** (no half-updated `map.json`/PNG set).

**Phase D: correct scoring and expandable missions.** D01 is independent but done before result-schema design. D02 → D03 → D04 → D05 are serial for mission/save correctness. Do not mix house art-generation work with a map rewrite; reuse existing reachability first.

### D01 — Duck hit-count record correction
**Owns:** `docs/js/minigames.js`, `test/minigames_test.py` or new focused test. **Depends:** A00.
- [ ] RED: with controlled duck hits, `Q.mg.ducks.best` is hit count, medal/`n/15` display agree, better is a **higher** count; `skeet` still ranks higher hits, `pig`/`race` lower time. Current `endMG()` at `minigames.js:123–130` erroneously treats ducks as time-based. Include a legacy fixture whose duck `best` is a time greater than 15: new valid hits must still become a record.
- [ ] Change score choice and comparator for both hit-based games. For a pre-fix duck record with no score-unit marker, preserve `won` and `tries`, archive the old `best`/`medal` under clearly named legacy fields, initialize new hit-based `best`/`medal` safely, and mark the new unit as `hits` so later runs cannot re-migrate it. Test one-time migration and UI display on reload; do **not** cast historical seconds into hit counts. Keep all other score/retry/save behavior unchanged. GREEN with focused test, `python test/minigames_test.py`, `node --check docs/js/minigames.js`.

### D02 — Authored mission contract and validator, no runtime
**Owns:** new authored `docs/missions.json`, new `test/mission_data_test.py` and small validator in `test/`. `docs/items.json` remains generated/read-only. **Depends:** C04, C05 if anchors affected.
- [ ] RED validator inputs: duplicate mission/step IDs, missing board/POI anchor, invalid building ID, out-of-bounds position, broken dependency; valid one-home outdoor checkpoint passes. Inspect actual `docs/items.json` for a reachable home with no conflicting NPC, not assumed `house01`.
- [ ] Use a small explicit contract, e.g. `{"id":"home-example","steps":[{"id":"visit","kind":"interact","anchor":{"boardSpot":"house01"}}]}`; `house01` exists in the audited house quiz set, but verify the **current** `items.json`/building collision before selecting the pilot. Stable IDs independent of array position/display label. No 21-home bulk population or invented author claims. Static `docs/missions.json` is directly `fetch`-able from Pages; validate it against generated map/items after each map rebuild.
- [ ] GREEN: `python test/mission_data_test.py`, `python test/quiz_expansion_test.py`, `python test/map_venues_test.py` as appropriate; supervisor approves schema before runtime. Only add goal kinds when immediately needed by a tested mission.

### D03 — Single outdoor checkpoint runtime via HOOKS
**Owns:** new `docs/js/missions.js`, `docs/index.html` script line, `test/mission_runtime_test.py`, narrow `game.js` bridge only if existing `ARK`/hooks insufficient. **Depends:** D02.
- [ ] RED: correct home's outdoor object reacts to explicit interaction only; nearby walking/another home/repeated activation don't advance; quiz board and NPC interaction priority remain (`game.js:707–714`); quest list gains one row, PL/EN labels valid.
- [ ] Fetch `docs/missions.json` at page path `missions.json` (verify URL), register `HOOKS.near`/`HOOKS.questLog` on `ark-ready`, map progress by stable step ID. Keep legacy hardcoded NPC quests untouched. In-memory test state okay only **until D04**; do not release checkpoint gameplay with unsaved progress.
- [ ] GREEN: `python test/mission_runtime_test.py`, `python test/quiz_expansion_test.py`, `python test/quest_test.py`, `node --check docs/js/missions.js`; supervisor checks no new general quest scripting engine.

### D04 — Versioned save and legacy migration
**Owns:** `docs/js/game.js`, `docs/js/missions.js` bridge, new `test/save_migration_test.py`. **Depends:** D03; required before shipping D03.
- [ ] RED fixtures in **isolated** browser storage: old `arek-chlopkow-save-v1` with character/name, position, NPC states, quiz, trash, `Q.mg`, and old optional fields; new one-checkpoint progress; malformed new mission subtree; future version. Reload round-trip must retain old fields and new step ID, not overwrite a future schema silently.
- [ ] Add explicit payload schema version without changing old storage key or resetting user progress (`game.js:233–248`). Missing version denotes legacy save. Normalize only new mission fields and preserve valid old data. For unknown future version, display a visible warning and disable writing to that save in the session; preserve the raw stored payload byte-for-byte. Test the warning and write guard before GREEN.
- [ ] GREEN: `python test/save_migration_test.py`, `python test/mission_runtime_test.py`, `python test/quest_test.py`, `python test/minigames_test.py`, `node --check docs/js/game.js`; supervisor reviews before/after saved JSON. The D01 one-time duck-score migration, archived legacy values and `hits` unit must survive reload.

### D05 — One complete house mission and user review
**Owns:** `docs/missions.json`, `docs/js/missions.js`, focused test, minimal existing visible object; no broad map expansion. **Depends:** D02–D04 and approved A-series art if it requires new sprite.
- [ ] Pick/verify one reachable board/building and short, sourced or fictional non-defamatory PL/EN text; have Tomek approve mission/copy/reward where not already specified. RED browser scenario: start, trigger, complete, quest-list check, reload, revisit without double award; normal optional quiz still works; mouse and touch both can interact.
- [ ] Implement only this pilot. GREEN with focused and full local suite, desktop/mobile screenshots, and collision/approach check. **Stop for Tomek's feel/art approval**; only then assign one independent house or micro-batch per new task using the validated ID/schema pattern. Rooms get their own spec only for a selected mission requiring one.

**Phase E: later local competition (not needed for quality/house pilot).** Do not preemptively change overworld input or claim Nostr functionality.

### E01 — Per-participant minigame session and keyboard edge tests
**Owns:** narrow `docs/js/minigames.js` extension or new `docs/js/local-competition.js` if concrete reuse warrants it, new focused Playwright test. **Depends:** D01; start only when Tomek approves local multiplayer phase.
- [ ] RED: two distinct participant IDs/names/keys/results, press-release-press increments once per true key edge; `event.repeat`, unrelated keys, focus in chat/input, Escape/cancel do not create false points; normal single-player/touch and `Q.mg` legacy records unchanged.
- [ ] Implement **session-only** participant labels and per-session input/results inside minigames, with explicit comparator for hit/time games; no extra `P` or world avatar and no new persisted player-profile key yet. Leave legacy single-player records intact.
- [ ] GREEN focused test, `python test/minigames_test.py`, `python test/character_selection_test.py`; supervisor verifies no key leakage or global controller rewrite.

### E02 — Playable two-person key-mash race prototype
**Owns:** one new game mode in minigames/local-competition module, focused browser test and minimal UI. **Depends:** E01, separate user approval.
- [ ] RED: two keyboard lanes independent, same distance/run time, deterministic tie, repeated keydown not a speed hack, Escape aborts without a result, retry fully resets, only one hero still walks on map afterward. Use two tested key codes; test physical-keyboard ghosting with Tomek before calling it fair.
- [ ] Implement one simultaneous minigame, not all six existing games. GREEN: focused test, full local runner, 1280×720 and 390×844 screenshots, single-player/touch regression. Stop for Tomek's play approval before additional competition modes.

### Z00 — Integration and optional release (supervisor only)
**Depends:** whichever phases Tomek authorized and whose cards were accepted.
- [ ] Integrate stable focused tests into `test/run_all.py` without deleting earlier cases. Start local HTTP server, run focused tests, `python test/run_all.py`, `python test/edits_test.py`, `python test/editor_test.py`, map/forest pipeline fixtures and `python test/perf_test.py`; record actual pass counts, CPU p95/heap delta and console errors. `node --check` changed JS and `git diff --check`.
- [ ] Compare all 15 quality requirements with Q-card mapping below, map/save compatibility, art preview/provenance, no exposed reference photos/basemaps/secrets/unrelated raw music; verify renderer outputs form a coherent set. Read `git status` and review each changed/untracked file against A00; don't stage the whole worktree.
- [ ] Update `PLAN.md`/`HANDOFF.md` with **verified** local state only. Seek Tomek's explicit permission for commit/push/deploy. If authorized later, verify exact commit/Pages build and live smoke separately. This plan is not publication approval.

## Coverage map: original 15 quality requests

| Request in temporary handoff | Task |
|---|---|
| 1 world hover (buildings, trees, pickups, NPCs, Frodo, animals, bales, vehicles) | A02, A03 |
| 2 country names only at correct edges | A01 |
| 3 chicken/mouse/bird shadows removed | B03 |
| 4 larger rounder bales | B05 |
| 5 mouse width and height 25% | B03 |
| 6 animal continuity and visibility | B02 |
| 7 Frodo greets other dogs safely | B04 |
| 8 extensible animal categories | B01 |
| 9 right transparent default-open chat | A06 |
| 10 forest passable between blocking trunks | C05 |
| 11 only timer/apples/mushrooms on primary HUD, trash in tasks | A04 |
| 12 restore older red-car art | B07 |
| 13 ≥5× clouds and darker shadows | B06 |
| 14 textured forest ground | C06 |
| 15 main track in fields, specific exceptions | A05 |

## Deferred and cross-workstream boundaries

- Asset references/regeneration/style: A0–A4 in `plans/2026-09-28-asset-style-roadmap.md`. Tomek chooses global style anchors; B07's exact, verified old red-car restoration is specifically requested here, but any newly invented replacement still needs preview/approval. Forest texture C06 is a specific polish request, not approval for an overall style reset. No personal reference photos leave the machine. E2 and A-series share a generator lock.
- Nostr results: only after local scoring design/play approval. Need distinct game/version/run ID, participant/pubkey and dedupe/sort rules; preserve local records. Signed self-reported results authenticate a key, **not the run**; agree honor-system versus trusted verification separately. `docs/js/chat.js` remains text chat, not a score API.
- Room system: don't abstract `church.js`/`shop.js` until a concrete new interior needs shared behavior. Existing simple outdoor checkpoints use HOOKS.
- Existing `DEVELOPMENT.md`, historical `HANDOFF.md` sections and old test counts may be stale. Do not assert their historical dimensions/deployment state as live; update documentation only from tested current code and a verified Pages commit if a release is later requested.
