# WALDEK walk sheets (integrated locally 2026-10-13, not committed)

New character WALDEK; estrada is his trade (teaches dancing and singing, florist, MC of stage events). Tomek's brief (2026-10-13): much slimmer and taller than the photos suggest, BLACK hair (not grey), navy blazer, vivid blue shirt, microphone in hand. Game code: `docs/js/friends.js` + id lists in `docs/js/game.js` (see the decision below).

- Private reference photos: `references/waldek/waldek_01..05.png` (gitignored). Tomek approved sending them to openai-codex for likeness (2026-10-13, recorded in `AGENTS.md`); they never go to git or public hosts.
- An earlier text-only round in chat (1024x1536 illustrations, no photo refs, no game grid) was rejected: wrong face and far too detailed for the game. Not kept here.
- Generator: `bash gen/waldek/gen_walk.sh [hair_a hair_b hair_c]` -> openai-codex `gpt-image-2-medium` via `gen/codex_gen.py`. Same flow as PIEKARZ face D: photos 02, 01, 04 first, BERCIK walk raw (`gen/bercik/bercik_walkcycle_raw.png`) as layout/style/scale template.
- Processing: `python gen/build_cast_walk.py build --name waldek --raw gen/waldek/<v>/waldek_walkcycle_raw.png --out gen/waldek/<v> --height 75 --colors 32` (BERCIK height, 150 px in game, 32 colours, hard alpha, 0 magenta pixels verified).

## Round 1 (2026-10-13)

Variants differ only in the hairstyle; outfit, microphone and build are identical.
- `walk_hair_a/`: photo hairline (bald crown), side hair black.
- `walk_hair_b/`: short full black hair, slightly receding temples.
- `walk_hair_c/`: short black hair, side part, a bit of volume on top.

Review: `gen/cast_review/2026-10-13_waldek_lineup.png` (with BERCIK, PIEKARZ D2 h70, DAREK H), `gen/cast_review/2026-10-13_waldek_heads_closeup.png` (heads 2x: front, right, back). Private photo-vs-sprite check: `references/waldek/_faces_vs_photos_private.png`.

Next: Tomek picks a hairstyle / face, then adjust height and integrate like `docs/js/bercik.js`.

**Decision (2026-10-13): Tomek chose B (`walk_hair_b/`, 150 px, 32 colours).** Copied to `docs/img/waldek_sheet.png`, `waldek_sheet.json`, `waldek.png` and wired in: `docs/js/friends.js` (fixed target (2143,4490), between the barns behind the house next to the bus shelter north of Dom Muchy, opposite the świetlica; `radius` 24, no road preference, tight clearance) and the six id lists in `docs/js/game.js`. Verified by `test/friends_test.py` (isolated runner).
