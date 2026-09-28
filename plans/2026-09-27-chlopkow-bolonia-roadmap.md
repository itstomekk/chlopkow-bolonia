# Chłopków Bolonia — staged roadmap

Status: interim gameplay release `ba64220` is live at https://itstomekk.github.io/chlopkow-bolonia/; many features below remain unimplemented. Coordinates below refer to the preceding 3897×2698 art-pixel map (bbox 52.2585,22.8586,52.2707,22.8872) and must be converted with `osm/geo.py:pre_expansion_i()`; positions mean nearby reachable sites, not exact pixels. Keep existing save key. GitHub repo is `itstomekk/chlopkow-bolonia`; the old Pages URL has a separate redirect repo.

## Already published in interim build

- Extended northern map and seven reachable landmark access points; BUDKA, football pitch, real PPM range, relocated oval. 11/11 existing play-tests passed in the previous session after regeneration.
- Irenka, Kuba and red-car sprites; simple global opt-in Nostr chat; cars and animals; easier dogs/race; cemetery gate/graves; map coordinates and click movement; new-game NPC randomization. Separate focused tests passed in the previous session.
- Local game title and HTML title say CHŁOPKÓW BOLONIA. The local README still mixes stale technical information with public-facing copy.
- The interim batch is published at `ba64220`. `main` matches `origin/main`; test suite passed 11/11 against live. Do not treat items below as published.

## Batch A — low-risk, individually testable

1. Music (`docs/js/music.js`, `test/music_test.py`): user changed idle lower bound to **0.2×**. Remove automatic switch to `pastoralka` after ~25 s idle in village; keep church/cemetery cues. Make acceleration slower and stopping slowdown linear without fast exponential catch-up. Preserve scheduler continuity and test long idle without track change.
2. Player name (`docs/js/game.js`, `docs/js/chat.js`, splash UI and tests): ask for a short, safe display name on title screen; use a default if skipped, save it separately/with backward-compatible migration, reuse it in dialogues, HUD and Nostr nickname unless changed explicitly in chat. Render text only (no HTML injection); never publish personal details without opt-in.
3. Metadata and splash (`docs/index.html`, splash art/rendering): align favicon, title, description, social sharing tags and visible game title to CHŁOPKÓW BOLONIA. Respect narrow mobile screens. Only use GPT Image if a new asset materially helps; local references stay out of git and final report must disclose image costs or unknown pricing.
4. Public README in Polish: invite the player into the Chłopków universe; move controls/build/test/license/technical explanations to `docs/DEVELOPMENT.md` or `DEVELOPMENT.md` at project root; preserve valid credits and live URL. Verify both links. No outdated apple quest or old village names.
5. Terrain (`docs/js/game.js`, generated map ground/collision as appropriate, tests): modest walking modifiers, fastest road, normal grass, slowest yellow field. Apply to mouse/keyboard/touch consistently, compose safely with car/minigame speed hooks, do not change jumping or collision; test boundaries and ensure small but perceptible differences.

## Batch B — quest, world and locations

6. Kasia quest (`docs/js/game.js`, `osm/place_items.py`, `docs/items.json`, tests): change requirement to 10 champignon mushrooms; keep apples collectable and car economy independent. Place 15 mushrooms on reachable green terrain sampled for each new game, persist positions/collection across reload, migrate old saves without silently auto-completing or resetting other quests. Add mushroom art, pickup animation and counter in HUD/quest log. Seed/test reachability and regeneration.
7. Sołtys: move outdoor hidden NPC from its existing spot near the woods sign to a reachable spot around old-map (1887,1237); keep indoor church role and secret-save behavior. Create a farmer-clothed pixel-art likeness without ceremonial bread using `references/soltys.png` for face only; never commit the reference photo. Do not accidentally turn quiz marker inaccessible.
8. Map edits (`osm/geo.py`, `osm/render_map.py`, `osm/place_items.py`, generated map/assets, reachability test): move shrine near old-map (2298,1423) to near (1744,1271); reuse former site for a school-shaped building called Świetlica wiejska, without leaving contradictory duplicate label at the earlier POI. Add Staw Strażacki near (270,1893), to the right of the actual road after visual/map inspection, with collision and walkable approach. Mark building near (2150,2506) as second shop with seated neighbors and beer; keep original shop tied to Marcin's orangeade. Avoid implying a user's rough coordinates are exact geographic facts.
9. Store visits / village dialogue (`docs/js/game.js`, optional small text module, tests): vary lines on repeat visits, including two separate lines on consecutive shop visits with saved visit count. Use local color ("po zagumieniu" for the lane behind barns, "sąsiedzie", tractors, shop credit, village/Parish Council, nostalgia for Polonez and motorbikes, road/fiber complaints, elections and jealousy around parish roles, market trips to Łosice, a priest and a schoolteacher/shopkeeper). Area names for atmospheric dialogue: Adamowo, Peryczówka, Kolonia od Szpak, Kolonia od Lasu, Kolonia za Rzeką. Named residents Jurek, Janek, Henio, Miecho, Borsuk, Kryszka, Wackowa, Bożenka, Alicja and Waldek are dialogue palette, not a license to invent accusations about actual people. Waldek can arrange church flowers and Bożenka can bring sweets to her children only if these are deliberately fictionalized or approved depictions. A local nicknamed "Wesołych Świąt" can be a harmless invented cameo. Dark humor may be about generic situations; do not attribute alcoholism, suicide or electoral misconduct to identifiable people. Michał runs the range in reality; Kuba is also met there. Portray that hierarchy in game. **Fact check:** the municipality's [official locality list](https://www.platerow.com.pl/asp/miejscowosci,16) records Chłopków within Gmina Platerów as of 2025-12-31; do not claim that it has left the gmina unless the setting is explicitly alternate fiction or newer official evidence arrives.

## Batch C — minigames / navigation / art

10. Shooting range (`docs/js/minigames.js`, map venue, tests): Michał owns/hosts the range, Kuba appears there too. Add a **separate** target-hit game with deliberately drifting sight; retain accessible mouse, keyboard and touch aiming and fair difficulty.
11. Duck hunt: **replace the existing flying-tin-moorhen game** with the same mechanics, duck targets and new location around old-map (3145,2629). Migrate/preserve existing medal record key intentionally; decorative hens remain harmless. Keep non-graphic.
12. Pitchfork throw near old-map (3366,410): standalone timing/accuracy minigame with safe grounded art and existing medal/record hooks; check reachable arena and mobile controls.
13. Boundary wrap: entering east reappears west and vice versa; north/south likewise. Preserve motion/companion and camera; search for nearest reachable point to exit rather than spawning in solid/water. Exempt interiors and active minigames; test all four transitions plus old saves.
14. Eight-way Arek/Frodo directions: inspect current 4-way sprite atlases, choose true diagonal frames only if visually coherent; otherwise blend/mirror existing frames temporarily without claiming new sprites. Preserve hitboxes, following, touch and facing interactions; visual checks at gameplay zoom.
15. Refresh world/POI art with GPT Image only where references and rights permit. Use sourced photos solely as private references, not shipped assets. Require visual QA, transparent sprite bounds and an actual cost report per image and total when available.

## Release gates and open decisions

- Each batch: targeted RED→GREEN regression tests, `node --check`, full `python test/run_all.py` against a local HTTP server, visual desktop/mobile smoke, clean `git diff --check`, secret/photo exclusion, and review of changed files.
- Before a deployment, reconcile the one remote music commit, re-run the complete suite on the exact commit, commit only intended files, push to `itstomekk/chlopkow-bolonia` and verify GitHub Pages plus redirect by HTTP readback; tell Tomek the exact deployed commit and remaining gaps. Do not report local changes as live.
- Duck-hunt decision resolved: replacement for flying-target mode, while target shooting at Michał's range is separate. Do local residents' names represent real people with permission for depiction, or should they be fictionalized? The claimed gmina change requires independent verification before factual use.
- The phrase "linear decay" is interpreted as tempo energy declining linearly to 0.2× idle after motion stops, not a volume fade. If Tomek meant music volume, adjust specification before implementation.

## September 28 follow-up — ordered, testable releases

The player has confirmed the interim live build and pointed out its visible omissions. Work in independent batches; **do not describe planned features as shipped**. Finish each batch with tests, in-game visual checks, git review and verified GitHub Pages build. Avoid rerendering the map while other workers edit its generated JSON/PNGs.

**Release 1, fixes and navigation (priority):**
- Music: remove idle-driven random switch to the lullaby, use lower bound 0.2× and slower acceleration; test 30+ s idle and continuing movement.
- Sołtys: current outdoor NPC is still generated beside `woods` marker (`osm/place_items.py`), not near old-map (1887,1237). Move to a reachable nearby place, preserve indoor counterpart and quiz access, regenerate `docs/items.json`, test spawn and reload.
- Northern forest: current `osm/render_map.py` sets `collide |= forest_mask`, blocking the whole woodland. Keep tree trunks and structures collidable, allow movement between trees like by the village sign; regenerate layers and test flood-fill/access.
- Boundary wrap: currently absent. Implement only outdoors, all four edges with nearest reachable opposite-side landing, companion and camera reposition, save/load-safe behavior, no water/solid or active minigames. No naive modulo.
- Eight visual directions: `docs/img/arek_sheet.png` has only front/back/profile poses and Frodo has four cardinal directions. New diagonal art for both and direction selection for keyboard, joystick, click navigation and companion follow; test 8 vectors and visually inspect atlases. Diagonal movement exists but is displayed as a cardinal pose.
- Ground speeds: currently no `HOOKS.speed` terrain classifier, so only car/race change speed. Add small modifiers road > grass > yellow field with consistent mouse/keyboard/touch and tests.

**Release 2, map/readouts/quest:**
- Render both `DUŃCY` (arrow west, midpoint of west edge) and `Wielkie Księstwo Litewskie` (arrow east, midpoint of east edge) as matching directional signs; separate actual map boundary from story direction. Inspect game map HUD and world rendering, not just OSM metadata.
- Overlay sectors A1... using fixed map-grid cells (proposed 500 art-pixels). Include player and cursor sector in map coordinate readout, and show grid labels on M map; keep x/y and lat/lon copy functionality. Test boundary cells and resize.
- Rotate procedural football pitch 90° by swapping w/h, move center +200 art-pixels x/y from its current position, update map landmark and walkable access; regenerate and visually inspect. Expose its rectangle for starter quest.
- Starter mowing quest: on new game guide Arek to the pitch, cover pitch via footfall grid; walking back and forth turns dark grass light, persists coverage across saves, completes only after coverage threshold (not an impossible continuous per-pixel requirement). Preserve existing old saves and avoid counting teleport or car driving.
- Kasia: 15 reachable green-ground mushrooms per fresh save, 10 collected for her quest, visible mushroom counter from the start. Apples and car purchase remain a separate economy.

**Release 3, life/art/knowledge:**
- Expand ambient animal population roughly 3× with sparse placement across empty northern/eastern accessible areas; birds flee player, stork walks/hops by river on green ground, and the requested 'Liz' is provisionally interpreted as **lis/fox** running between building vicinities until confirmed. No spawning inside obstacles or farming interactions. Commission coherent pixel sprites with real movement frames for hen, dog, birds, stork and fox; originals are referenced privately, publish only rendered sprites, cost disclosure required.
- Darek Kostek ('big farmer'): two newly supplied close portraits appear suitable as face references; keep originals private and make a stylized farmer NPC with harmless farm/trailer/pitch dialogue, reachable position and source-bound rendering. Do not invent personal wrongdoing. Professor from previous message remains a separate pending NPC.
- Ursus C-330: intermittent field-only NPC vehicle crossing back and forth on safe drivable corridors without running over/intersecting player; distinct from later road traffic. Preserve Grandpa quest and avoid implying driveability until implemented.
- Weather: occasional clouds with soft moving terrain shadows, visual-only and performance-bounded (no weather changes to collision); verify mobile FPS. Later traffic architecture: reserve route graph for roads, waypoint/spawn/despawn boundaries, lane avoidance and player/NPC collision rules before adding moving people/cars; no traffic is promised in this batch.
- Expand quiz with several sourced Chłopków questions at additional accessible building `?` anchors and dialog facts at the matching place. Source and uncertainty notes for grodzisko, church, old names, windmill and wartime history; legend of buried bells explicitly presented as legend, not a proven archaeological find. No defamatory claims about real people.

## Map editor (tooling, parallel track)

Local-only editor for correcting the generated map against reality (trees, woods, water,
collision, NPC/venue positions) over a satellite basemap. Edits are stored as lat/lon data
in `osm/edits.json` and applied by `render_map.py`/`place_items.py`; the editor lives in
`editor/` outside `docs/`, so it is never published and does not touch game runtime.
Full design and ordered GPT Luna worker tasks (E1–E7): `plans/2026-09-28-map-editor.md`.
First real use: fix trees around the road/river crossing at (949,4665).

**Open wording:** confirm whether transcribed animal 'Liz' means *lis* (fox). Ask only if this changes art/behavior; provisional fox is the low-risk interpretation.
