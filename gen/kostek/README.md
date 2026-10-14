# KOSTEK concepts (local, not integrated)

Concept round for a new character, KOSTEK. No game code, atlas, or selector changes.

- Private reference photos: `references/kostek/` (gitignored). Inspected locally only; not sent to the image generator.
- Generator: openai-codex `gpt-image-2-medium` (2026-10-12), style refs `docs/img/renik_sheet.png` + `docs/img/bercik_sheet.png`, text-only appearance description.
- Raw outputs: `concepts/kostek_v1_hoodie_vest.png`, `kostek_v2_summer_tank.png`, `kostek_v3_black_tee.png`, `kostek_v4_farm_work.png` (front / side / back on magenta).
- Review sheet: `concepts/kostek_concepts_review.png`, built by `build_concepts.py` (BERCIK recipe: magenta key, BOX regrid to 75 px, hard alpha, 2x NEAREST, BERCIK front frame for scale).

Request IDs: v1 88e77987-6f75-4083-855e-f317edf74626, v2 87c0edc5-0bdd-4740-96b6-7ce607d79318, v3 e7d95a84-9e6d-4257-901c-bd8af4845cde, v4 909afbfc-3c1d-448a-99a5-bb0454b88376.

Round 2 (Tomek's feedback: face from option 3, clean-shaven, less menacing, green farm dungarees, no phone): img2img edits of `kostek_v3_black_tee.png` -> `concepts/kostek_v5_overalls_white_tee.png` (request d0b963f5-b58a-4027-9637-25200dd3b559) and `kostek_v6_overalls_flannel.png` (request 08a36321-ad18-496f-adc0-16d031085fa6). Review: `concepts/kostek-r2_concepts_review.png` via `python gen/kostek/build_concepts.py kostek-r2`.

Walk sheet (Tomek approved option 5): `walk/kostek_walkcycle_raw.png` (request 6cc5edb3-82f7-49d0-ae85-84dce57700df, Bercik walk raw as layout/scale template) processed by `gen/build_cast_walk.py build --height 80` (BERCIK recipe, content 80 px native vs BERCIK 75, so ~7% taller in game; enclosed-magenta keying) -> `walk/kostek_sheet.png` (520x680, 40 colours, hard alpha), `walk/kostek_sheet.json`, `walk/kostek.png`, `walk/preview.png`. Not yet copied to `docs/img/` or wired into the game. The renderer scales by cell height (`h / (f.h - foot - 14)` in `docs/js/game.js`), so content height differences carry into the game.

Why the concept previews looked smaller and finer than BERCIK: concept raws drew KOSTEK ~690 px tall with a small head (~23% of height) and the preview skipped the 40-colour palette (1453 colours), while BERCIK's raw figures are ~386 px with a ~32% head and a 40-colour palette. Enclosed arm/body magenta also leaked in v5. The walk sheet fixes all three.

Next: Tomek picks a direction, then generate the 4x2 walk sheet (BERCIK layout) and integrate like `docs/js/bercik.js`.
