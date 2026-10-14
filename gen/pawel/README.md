# PAWEŁ concepts (local, not integrated)

Concept round for a new character, PAWEŁ. No game code, atlas, or selector changes.

- Private reference photos: `references/pawel/` (gitignored). Inspected locally only; not sent to the image generator.
- Generator: openai-codex `gpt-image-2-medium` (2026-10-12), style refs `docs/img/renik_sheet.png` + `docs/img/bercik_sheet.png`, text-only appearance description.
- Raw outputs: `concepts/pawel_v1_gingham_shirt.png`, `pawel_v2_jacket_teal_tee.png`, `pawel_v3_olive_sweater.png`, `pawel_v4_farm_bucket.png` (front / side / back on magenta).
- Review sheet: `concepts/pawel_concepts_review.png`, built by `python gen/kostek/build_concepts.py pawel` (shared concept-sheet builder).

Request IDs: v1 f73c10ef-0309-43fc-8f23-22e597714870, v2 f1e1a8b9-ef97-43f7-878d-d48b817f7fea, v3 db0970c1-0bc4-4c5b-8cb8-0c84d05605c1, v4 bf68bc95-d23c-430a-adc7-ddd8d638f0d4.

Next: Tomek picks a direction, then generate the 4x2 walk sheet (BERCIK layout) and integrate like `docs/js/bercik.js`.

## Round 2 walk sheets (2026-10-12)

Tomek: face from concept 2, hair and beard black, bigger and taller; photos may now be sent to the generator. Generated directly as 4x2 walk sheets (layout template `gen/bercik/bercik_walkcycle_raw.png`, identity refs `concepts/pawel_v2_jacket_teal_tee.png` + the three photos), then a black-hair edit, processed with `gen/build_cast_walk.py build --height 82` (BERCIK 75, so ~9% taller in game).

- `walk_jacket/`: brown jacket + teal tee. Raw request 89f34260-de94-4182-a92d-2bb5f79acf5a, black-hair edit 474caf9f-2c04-463b-a8af-62168109d936 (`pawel_walkcycle_raw.png`; pre-edit kept as `pawel_walkcycle_raw_brownhair.png`).
- `walk_gingham/`: navy gingham shirt. Raw c5d12acb-a375-4ba6-831b-65100ec069e8, black-hair edit 9970dcff-385c-446f-b3ac-ae722ae7cb46.
- Lineup with BERCIK and KOSTEK: `gen/cast_review/2026-10-12_kostek_pawel_lineup.png`.

## Round 3: younger and taller (2026-10-12)

Younger edits (fuller black hair, no bald crown) of the black-hair raws, built at content height 86 in 130x180 cells (`gen/build_cast_walk.py build --height 86 --cell-h 180`): `walk_jacket_young/` (request 1ee7ae6b-7dab-4198-8c18-dad0231effda), `walk_gingham_young/` (3d870c0e-6289-440c-95f0-cc2a6fd50fb7). Their JSON carries `"ref_h": 150`: `docs/js/game.js` currently normalises by `f.h - foot - 14`, so integration must use `meta.ref_h` when present or the extra height is lost. Lineup: `gen/cast_review/2026-10-12_pawel_young_lineup.png`.

## Note (2026-10-12, piekarz session)

Tomek (in the PIEKARZ session): "the previous PAWEŁ, the jacket one", not the round 3 young versions. Resolved: `docs/img/pawel_sheet.png` is byte-identical to `walk_face_a/pawel_sheet.png` (face A, jacket), already integrated via `docs/js/friends.js`. Neither jacket build needs `ref_h`.

## Round 4: photo-referenced face attempts (2026-10-12)

Tomek: round-3 faces generic (the younger edit had no photo references). Four attempts with all three photos as references, jacket outfit, ~35, black hair and beard, `--height 86 --cell-h 180`:
- `walk_face_a/` edit of `walk_jacket` raw, face redrawn from photos: e7006a5a-7c1e-4052-aa82-d49ad093d55d
- `walk_face_b/` fresh, BERCIK walk template + photos: f0f11c61-f9f7-4433-ae44-00ee33248cbd
- `walk_face_c/` fresh, KOSTEK walk template + photos: dd3b3a55-2ded-4fa8-96ed-0e652ff36a32
- `walk_face_d/` photo as the main image, BERCIK template as style ref: 5e66cc8f-081f-44aa-ba77-393fe57d840c
Review: `gen/cast_review/2026-10-12_pawel_faces_closeup.png`, `2026-10-12_pawel_faces_lineup.png`.

Tomek approved face A. Rebuilt `walk_face_a/` at `--height 80` in standard 170 px cells (160 px, same as KOSTEK; no `ref_h` needed). Heights lineup: `gen/cast_review/2026-10-12_cast_heights_lineup.png`.
