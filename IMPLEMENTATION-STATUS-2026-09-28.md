# Chłopków Bolonia - implementation status

Updated 2026-09-28. This file records the current local batch and the remaining work. It is a developer handoff, not a deployment claim.

## Completed in this batch

- Added Arek's prototype 8-direction runtime sprite:
  - `docs/img/arek_sheet_8dir.png`
  - `docs/img/arek_sheet_8dir_noglasses.png`
  - matching JSON metadata
  - diagonal input and rendering are covered by `test/eight_direction_test.py`
- Reduced Frodo's licking animation to 80% size.
- Changed Frodo's return from Edytka so he travels toward Arek first, tries a side-step around obstacles, and only uses the old recovery teleport after a grace period.
- Moved Edytka's fixed home to `(120, 3869)` and kept her local walking radius.
- Added seven drifting cloud sprites with translucent terrain shadows. They are visual-only and do not affect collision.
- Michał's reference-based sprite is present in the NPC atlas and is used by the shooting-range NPC. His atlas slot is index 6.
- Confirmed Mateusz and Patryk are present in the atlas, items list, NPC index and wandering profiles.
- Added Wesołych Świąt at `(1692, 650)` in the forest with slow wandering and joke dialogue. No quest is attached.
- Added two field-only, non-drivable Ursus-style tractors with bounded roaming and player avoidance.
- Moved and reduced JAZZ W STODOLE. The generated venue is now near `(2953, 2657)`, with a smaller barn and radius.
- Added regression coverage for the latest NPC, venue, weather and tractor requirements.
- Regenerated the map assets after the venue move.
- Added DJ Renik (from reference photos: red beard, backwards cap with DJ headphones, black graphic tee, jeans):
  - NPC sprite in atlas slot 12 (`gen/npc_src/renik.png` -> `docs/img/npcs.png`)
  - playable 4-direction walk sheet `docs/img/renik_sheet.png` + JSON (diagonals fall back to cardinal rows)
  - fifth button in the title character selector, centred on its own row and kept above the bottom prompt strip
  - NPC stands just east of the football pitch at `(2619, 4730)` and wanders within 56 px
  - six rotating disco polo dialogues (PL + EN), no quest
  - generator: `gen/gen_renik_codex.py` (reference photos stay in gitignored `references/renik/`)
- Trash bags are a plain collectible, like apples and mushrooms:
  - 12 black bags per game: 2 fixed (by the cemetery and the southern shop), 10 scattered on grass and by roads
  - walk over a bag to pick it up; toast `+1 WOREK ŚMIECI n/12`, HUD counter, saved progress; old saves get bags on load
  - removed Mateusz, the clean-up NPC who only stood by the cemetery with no quest

## Already present before this batch

- Main soundtrack and yellow-field music routing.
- Separate forest, shop and special-scene music.
- Frodo dialogue, follow behavior and Edytka quest.
- Straw-bale movement and rotation.
- Colorful butterflies with attraction/repulsion behavior.
- Character selection and NPC replacement behavior.
- Shooting range, duck game, mowing game, wildlife, shop and map expansion.

## Remaining work

- Replace the prototype diagonal rows with bespoke hand-drawn or generated diagonal poses if the visual test shows that the sheared prototype is not good enough. The current sheet has the correct 8-direction runtime structure, but the diagonal artwork is intentionally provisional.
- Add a proper tractor driving/minigame after the Grandpa quest if driveable Ursus gameplay is wanted. The current tractors are ambient NPC vehicles only.
- Perform a visual browser review of Michał and Wesołych Świąt at native game scale and adjust palette or silhouette if needed.
- Decide whether Mateusz and Patryk need individual quests/dialogue. They currently function as wandering NPCs with existing sprites.
- Move Patryk into the relocated JAZZ W STODOLE yard `(2953, 2657)`; he still stands at the old barn spot.
- `test/map_venues_test.py` (not in `run_all.py`) reports 4 failures: old jazz position, Patryk outside the jazz yard, and quiz boards `shrine1`/`shrine2` far from their shrines. Update the test and the placements, then add it to `run_all.py`.
- Decide on a reward for collecting all 12 trash bags (none yet).
- Decide whether Mateusz returns in a different role; his sprite is still in the NPC atlas but unused.
- DJ Renik: optional dedicated 8-direction sheet and a quest (e.g. an evening disco at the pitch) if wanted.

## Verification

- JavaScript syntax checks passed for `game.js` and `world-life.js`.
- Python compilation passed for the new generator and tests.
- Full local regression passed: **19/19** (including DJ Renik selection, sheet, spawn reachability and dialogue).
- Targeted tests passed: character selection, 8-direction Arek, Edytka/Frodo, world life, presentation and latest world requests.
