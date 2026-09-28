# PLAN — Arek w Chłopkowie

## Last completed phase: audit, bigger map, minigame overhaul (2026-09-27)
- [x] Audit code and repo; fix the skeet stub, the Sołtys/signboard clash, missing bridges and the boxed-in spawn (details in HANDOFF.md)
- [x] Map enlarged to 3897×2698 px via `osm/geo.py`; all hand-placed spots converted with `legacy_i()`
- [x] Minigames rewritten in `docs/js/minigames.js`: medals, records, retry, race ghost + off-track slowdown, tiring pig, telegraphed dog lunges, working shooting gallery
- [x] `test/run_all.py`: 10/10 pass locally and on the live site

The previous phase's plan (village assets + cemetery archive) is in `_archive/2026-09-27_PLAN-village-assets.md`.

## Active phase: Chłopków Bolonia, staged local integration

The complete requested roadmap, coordinates, prerequisites and release gates are in
[`plans/2026-09-27-chlopkow-bolonia-roadmap.md`](plans/2026-09-27-chlopkow-bolonia-roadmap.md).
The old coordinates refer to the 3897×2698 map before northern expansion; use
`pre_expansion_i()` rather than copying their y values into the expanded map.

- [x] Rename remote repository and establish old Pages URL redirect (remote metadata only).
- [x] Locally integrate expanded map, Irenka/Kuba sprites, car, Nostr overlay,
      cemetery art, NPC randomization and minigame tuning; earlier local test suite 11/11.
- [x] Fast-forward local `main` to `origin/main` at `54fc9ce`, then publish tested gameplay release `ba64220` to `main`/GitHub Pages. Local and live suites: 11/11; targeted chat/world-life/metadata/core checks passed. Pending feature batches remain below.
- [ ] Batch A: README in Polish with separate developer guide, refreshed HTML metadata,
      linear music slowdown beginning at 0.3×, player name + Nostr signature,
      and small terrain-specific walking speeds.
- [x] Batch A partial: Polish player-facing README, English DEVELOPMENT.md,
      HTML description/Open Graph metadata and updated favicon; focused metadata test passed.
- [ ] Batch B: Kasia's 10/15 mushrooms, Sołtys as farmer at old-map (1887,1237),
      relocated shrine/school, pond, second shop and richer varied dialogue.
- [ ] Batch C: Michał and Kuba at a target range, duck hunt, pitchfork throw,
      boundary wrap, diagonal Arek/Frodo animations and art QA.
- [ ] Map editor (local tool in `editor/`, edits in `osm/edits.json` applied by the
      generator, satellite basemap, extensible tool registry). Design and ordered worker
      tasks E1–E7: [`plans/2026-09-28-map-editor.md`](plans/2026-09-28-map-editor.md).
- [x] Publish the current playable batch and verify the Pages build at `ba64220` plus 11/11 tests against the public site. Future batches need their own release gates and fresh remote fetch.
- [x] Local-only character sprite batch: Codex-generated 4-direction sheets for Marcin, Damian and Edytka; title-screen selector with saved selection; NPC atlas includes new Zbyszek and Wesołych Świąt portraits. Targeted selector/start-flow/sprite-key tests pass. Not deployed; full suite still has unrelated failures recorded in `HANDOFF.md`.

Use GPT Luna for narrow implementation tasks and Sol for architecture, integration,
review and deployment. No unverified allegations about identifiable village residents.
