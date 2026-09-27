# PLAN — Arek w Chłopkowie

## Active phase: village assets + cemetery archive

### Approved scope
- [x] Add a skeet shooting (strzelnica - kurka wodna) minigame at the meadow near the river.
- [x] Generate three pixel-art cemetery-memory illustrations from the newly supplied archival photos, without copying recognizable faces or inscriptions.
- [x] Show them as a three-page trivia archive after Arek wins the main quest; keyboard, touch and skip paths are implemented.
- [x] Generate one generic, non-literal rural house sprite using the house photos as broad style/material references.
- [x] Generate four distinct pixel-art roadside cross/shrine sprites from the supplied photos.
- [x] Place the generic house on one existing OSM building footprint and shrines beside deterministic OSM road junctions.
- [x] Keep original reference photos out of the repository; record prompts and generated source assets only.
- [x] Review the rendered game in a browser at gameplay zoom and correct any visual/collision issues.
- [ ] After final review, commit/push only the approved changes to `main` for GitHub Pages deployment; preserve unrelated pending Frodo changes unless separately approved.

### Current decisions
- House photos have no assigned real-world locations. The generated house is a generic composite, not a claim that a specific photographed house is at its selected OSM footprint.
- The shrine photos contain no EXIF/GPS data. Shrine placements are approximate roadside sites selected from actual OSM junction geometry; they can be moved when Tomek supplies exact locations.
- No push or deployment has been performed. The current repository already had unrelated local Frodo work; preserve it.

### Verification targets
- `python osm/render_map.py`
- `test/cemetery_memories_test.py`, `test/quest_test.py`, `test/features_test.py`, `test/jump_test.py`, `test/church_test.py`, `test/frodo_test.py`, `test/village_sign_test.py`
- `test/play_test.py` plus visual inspection of the rendered map and roadside locations.
