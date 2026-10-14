# MAREK walk sheets (integrated locally, not committed)

New character MAREK. No game code, atlas, or selector changes.

- Private reference photos: `references/marek/marek_01..02.png` (gitignored). Sent to openai-codex for likeness, same flow as PIEKARZ (recorded in `AGENTS.md`); never to git or public hosts.
- Generator: `bash gen/marek/gen_walk.sh [variant ...]` -> openai-codex `gpt-image-2-medium` via `gen/codex_gen.py`, template `gen/bercik/bercik_walkcycle_raw.png` + both photos.
- Processing: `python gen/build_cast_walk.py build --name marek --raw gen/marek/<v>/marek_walkcycle_raw.png --out gen/marek/<v> --height 78` (standard 130x170 cells, no `ref_h`).

## Round 1 (2026-10-12)

Clean-shaven, short brown hair greying at the temples, stocky, about 50, no glasses.
- `walk_tee/`: light grey-blue T-shirt, jeans, belt, grey sneakers (riverside photo).
- `walk_henley/`: dark charcoal henley with brown buttons, brown trousers (second photo).
- `walk_flannel/`: red-navy flannel over a T-shirt, olive work trousers asked for; the model drew shorts.

Lineup with BERCIK and PIEKARZ 1: `gen/cast_review/2026-10-12_marek_lineup.png`.

Next: Tomek picks a variant, then integrate like `docs/js/bercik.js`.

## Round 2: variant 1, slimmer and a bit shorter (2026-10-12)

Tomek picked variant 1 (`walk_tee`), a bit slimmer and a bit shorter than BERCIK. `bash gen/marek/gen_slim.sh` = two img2img edits of the `walk_tee` raw (photos as likeness refs). The `walk_tee` raw had denim shorts in the front/back frames and long jeans in the side frames, so `bash gen/marek/gen_slim.sh --jeans` fixed both edits to long jeans in all eight frames (pre-fix raws kept as `marek_walkcycle_raw_shorts.png`). Built at `--height 72`, 40 colours. Front frame in game px (BERCIK 150 tall, 80 wide):
- `walk_tee_slim/` (1a): 144 tall, 74 wide.
- `walk_tee_slimmer/` (1b): 144 tall, 70 wide.
(`walk_tee` was 156 x 86.) Lineup with PIEKARZ D2: `gen/cast_review/2026-10-12_marek_slim_lineup.png`.

**Decision (2026-10-12): Tomek chose 1b, `walk_tee_slimmer/` (144 x 70 px).**

## Integration (2026-10-13, local, not committed)

`walk_tee_slimmer/` copied to `docs/img/marek_sheet.png/.json` + `marek.png`. Playable selector card and fixed NPC via `docs/js/friends.js`, anchored on the `river` POI (offset -100,-15; Tomek: by the river like his photo); placed at (2258,5009), E10, road at the bridge, 17 px from the water. Calm riverside dialogue, PL/EN. `marek` added to the game.js id lists.
