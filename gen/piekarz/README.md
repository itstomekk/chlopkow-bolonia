# PIEKARZ walk sheets (integrated locally, not committed)

New character PIEKARZ (that is his name; he drives long-haul trucks). Tomek: show him without glasses. No game code, atlas, or selector changes.

- Private reference photos: `references/piekarz/piekarz_01..05.png` (gitignored). Tomek approved sending them to openai-codex for likeness (2026-10-12, recorded in `AGENTS.md`); they never go to git or public hosts.
- Generator: `bash gen/piekarz/gen_walk.sh [variant ...]` -> openai-codex `gpt-image-2-medium` via `gen/codex_gen.py`. Template `gen/bercik/bercik_walkcycle_raw.png` (4x2 BERCIK layout) + photos 01, 05, 03, 02. All paths passed absolute because `codex_gen.py` chdirs into hermes-agent.
- Processing: `python gen/build_cast_walk.py build --name piekarz --raw gen/piekarz/<v>/piekarz_walkcycle_raw.png --out gen/piekarz/<v> --height 78` (BERCIK 75, so slightly taller and stocky; standard 130x170 cells, no `ref_h` needed).

## Round 1 (2026-10-12)

No glasses in any variant (checked on the raws).
- `walk_polo/`: white polo with navy trim, gold chain, watch, navy trousers (his trucker outfit from the cab photos).
- `walk_leather/`: black leather biker jacket over white graphic tee, jeans, boots.
- `walk_tee/`: black tee with small red logo, olive cargo trousers, silver chain, boots.

Lineup with BERCIK and PAWEŁ (jacket): `gen/cast_review/2026-10-12_piekarz_lineup.png`.

Next: Tomek picks a variant, then integrate like `docs/js/bercik.js`.

## Round 2: faces (2026-10-12)

Tomek: variant 2 (leather) looks good, but his hair is darker in reality and the face is not similar enough. Four attempts with `bash gen/piekarz/gen_faces.sh`, all leather outfit, dark brown hair, likeness refs = face crops `references/piekarz/face_01.png`, `face_05.png` (private) + `piekarz_01.png`, built at `--height 78`:
- `walk_face_a/`: edit of the `walk_leather` raw, only heads redrawn.
- `walk_face_b/`: fresh, BERCIK walk template.
- `walk_face_c/`: fresh, KOSTEK walk template (its face style).
- `walk_face_d/`: face photo as the main image, BERCIK template as style ref.

Review: `gen/cast_review/2026-10-12_piekarz_faces_closeup.png` (heads 4x, front + profile), `2026-10-12_piekarz_faces_lineup.png`. Private photo-vs-sprite check: `references/piekarz/_faces_vs_photos_private.png` (gitignored; vision ranking D > A > B > C).

## Round 3: D, shorter and a bit simpler (2026-10-12)

Tomek: D is OK, but shorter and slightly more simplified. Same raw (`walk_face_d/piekarz_walkcycle_raw.png`), rebuilt lower with a smaller palette. `--colors` is a new `build_cast_walk.py` option (`build_bercik.PALETTE_COLORS`, default 40, so BERCIK builds are unchanged). Measured front-frame heights in game px (BERCIK 150):
- `walk_face_d_h72/`: `--height 72 --colors 32` -> 144 px.
- `walk_face_d_h70/`: `--height 70 --colors 32` -> 140 px.
- `walk_face_d_h70s/`: `--height 70 --colors 24` -> 140 px, flattest shading.
Review: `gen/cast_review/2026-10-12_piekarz_d_lower_closeup.png`, `2026-10-12_piekarz_d_lower_lineup.png`.

Tomek: D2 is great, but the same height (read as: same as BERCIK). Final candidate `walk_face_d_h75/`: `--height 75 --colors 32` -> 150 px in all four directions, identical to BERCIK. Lineup: `gen/cast_review/2026-10-12_piekarz_d2_h75_lineup.png`. Not yet copied to `docs/img/` or wired into the game.

**Decision (2026-10-12): Tomek chose D2 at 70, i.e. `walk_face_d_h70/` (140 px, 32 colours).** The h75 build is not used.

## Integration (2026-10-13, local, not committed)

`walk_face_d_h70/` copied to `docs/img/piekarz_sheet.png/.json` + `piekarz.png`. Playable selector card and fixed NPC via `docs/js/friends.js`: target (2040,680) on the main dirt road north out of the village where it leaves the forest (Tomek: "przy lesie, głównym wjeździe na północ"); placed at (2040,680), D2, track. Truck-driver dialogue, PL/EN. `piekarz` added to the game.js id lists. Selector labels now shrink to fit the card (long names).
