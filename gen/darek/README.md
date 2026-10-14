# DAREK concepts (local, not integrated)

Concept round for a new character, DAREK: about 170 cm (shorter than the cast), likes to dress well, car body painter. No game code, atlas, or selector changes.

- Private reference photos: `references/darek/` (gitignored). Inspected locally only; not sent to the image generator.
- Generator: openai-codex `gpt-image-2-medium` (2026-10-12), style refs `docs/img/renik_sheet.png` + `docs/img/bercik_sheet.png`, text-only appearance description (clean-shaven, shaved/balding head, round-oval smiling face).
- Raw outputs: `concepts/darek_v1_cream_suit.png`, `darek_v2_white_shirt.png`, `darek_v3_painter_coverall.png`, `darek_v4_pink_aviators.png` (front / side / back on magenta).
- Review sheet: `concepts/darek_concepts_review.png`, built by `python gen/kostek/build_concepts.py darek`. Height preview uses 70 px content instead of the cast's 75 px to show his shorter stature.

Request IDs: v1 c7af921f-7f1c-4094-95cc-4d9cdbe8b2f7, v2 1f66da30-85c0-40a8-aa54-935be31dab19, v3 f5df71c5-3d59-4432-b8d3-74c440d2e7f5, v4 e0dacf67-1c53-4e43-bc33-123425c774fa (round 1, rejected as too heavy; sheet `concepts/darek-r1_concepts_review.png`).

Round 2 (Tomek: much slimmer, young, gelled hair): `darek_v5_slim_suit.png` (61f3ccdc-8342-47df-8bd4-c717a39e211e), `darek_v6_slim_white_shirt.png` (f26ed182-1b4e-4230-84a4-854ca20a7986), `darek_v7_slim_painter.png` (c47baab0-4f28-49ef-8a40-315455049ff5), `darek_v8_slim_pink.png` (5d91a160-0673-462e-85fa-987113c45f88). Sheet: `concepts/darek_concepts_review.png`.

Next: Tomek picks a direction, then generate the 4x2 walk sheet (BERCIK layout) and integrate like `docs/js/bercik.js`.

## Round 3 walk sheets (2026-10-12)

Tomek: round 2 did not resemble Darek (photos had not been used), outfits looked cheap, pixels too fine. Now generated directly as 4x2 walk sheets with the four photos as likeness references (template `gen/bercik/bercik_walkcycle_raw.png`), slim, young, gelled short hair, premium outfits, processed with `gen/build_cast_walk.py build --height 70` (BERCIK 75: shorter, same 2x pixel size, 40 colours).

- `walk_navy/` navy blazer + white shirt: a258c0c4-b98e-4288-951a-9c98ccec5f39
- `walk_cream/` cream suit + purple tie: 137b8b32-1791-4d42-b83e-dfdf4f1c64ed
- `walk_linen/` white linen shirt + navy chinos: b0fd530e-dcfe-427c-a74e-7a3abb55a512
- `walk_painter/` black paint-shop coverall + spray gun: 4abfff7d-ad71-4b02-974f-35c97db61c47
- Lineup with BERCIK: `gen/cast_review/2026-10-12_darek_lineup.png`.

## Round 4: face attempts, linen outfit (2026-10-12)

Tomek: outfit like the linen version (white shirt, sunglasses hooked on the shirt), face too realistic, try several faces. Four attempts, all `--height 70`:
- `walk_face_a/` edit of `walk_linen` raw toward BERCIK's simple face style: 44fed56a-fffe-45c0-9a32-d7a836f6386a
- `walk_face_b/` edit of `walk_linen` raw toward KOSTEK's face style: af4f487b-2355-4f0b-9920-b345765ae1d3
- `walk_face_c/` fresh, BERCIK walk template + photos: e9d19ee2-0fc0-43a5-9d05-efc7794317b9
- `walk_face_d/` fresh, KOSTEK walk template + photos: 44b18580-72b0-4fd3-80a5-dc3ccf5bf897
Review: `gen/cast_review/2026-10-12_darek_faces_closeup.png` (6x heads) and `2026-10-12_darek_faces_lineup.png`.

## Round 5: Bercik height, more photo faces (2026-10-12)

Tomek: Darek as tall as BERCIK. All `walk_face_*` sheets rebuilt at `--height 75` (150 px, same as BERCIK). New photo-referenced face attempts, same linen outfit:
- `walk_face_e/` edit of face C raw, face redrawn from photos: c2a5ea8a-64ee-4c27-a944-76bbc8175bb1
- `walk_face_f/` PAWEŁ A walk raw as style template + photos: 18aef4e7-e55f-4378-8773-30f76231893d
- `walk_face_g/` BERCIK walk template + photos: 49aa0225-04c2-45f6-af2b-08de12e0c747 (first try with the photo as main image was rejected by the safety filter, 13f124c6-2f90-470f-9570-9c8378f9ea16)
- `walk_face_h/` edit of `walk_linen` raw, face redrawn from photos, eyes visible: 5133bf69-998c-4a3e-ba4f-1c359f9c90c2
Face sheet without photos: `gen/cast_review/2026-10-12_darek_faces_AH_closeup.png`; with photos (private, gitignored): `references/darek/2026-10-12_darek_faces_vs_photos.png`.

Tomek selected face H (`walk_face_h/`, 150 px) on 2026-10-12. Final in-game height pending the cast-wide `height_cm` decision.
