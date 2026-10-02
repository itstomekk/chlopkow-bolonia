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
- [x] Compress the existing Polka Dziadek chiptune asset to mono Ogg Opus for the game (356 KB, down from 1.43 MB); archive the WAV source outside `docs/audio/`.
- [x] Download five requested YouTube sources as final mono Ogg Opus files below 500 KB each; the printed Polka Dziadek is now the entrance-screen track alone and village/field share a random default playlist, with a linear 0.4x-1.3x activity tempo. Duplicate MP3/Opus variants were removed from `docs/audio/` and source files archived; nothing is published until rights and final track selection are reviewed.
- [ ] Batch B: Kasia's 10/15 mushrooms, Sołtys as farmer at old-map (1887,1237),
      relocated shrine/school, pond, second shop and richer varied dialogue.
- [ ] Batch C: Michał and Kuba at a target range, duck hunt, pitchfork throw,
      boundary wrap, diagonal Arek/Frodo animations and art QA.
- [ ] Map editor (local tool in `editor/`, edits in `osm/edits.json` applied by the
      generator, satellite basemap, extensible tool registry). Design and ordered worker
      tasks E1–E7: [`plans/2026-09-28-map-editor.md`](plans/2026-09-28-map-editor.md).
- [ ] Asset consistency, **planning stage**: refine the existing pixel-art look, with
      Tomek choosing which existing assets are style anchors and which need changes.
      GPT Luna's first asset-style task is A0 (safe inventory + review sheet); wait for
      Tomek's labels before a style guide, generation or implementation. Ordered
      gates A0–A4: [`plans/2026-09-28-asset-style-roadmap.md`](plans/2026-09-28-asset-style-roadmap.md).
- [x] Canonical Luna queue implementation: P10 and D01–D05 are verified and fast-forwarded into local `main` at `e93ed11` (not pushed or deployed). D05 is one `home-example` outdoor pilot; do not scale it without Tomek's acceptance.
- [x] E01 session-only participant/input model is implemented on `luna/2026-09-30-phase-de` (`771aced`); E02 has a playable two-key race prototype and focused tests, with the full integrated suite currently running. Await Tomek's playability review before any additional competition modes.
- [ ] Z00: after E02 review, finish local test integration/quality audit, update verified handoff, and do not push/deploy without explicit permission.
- The unified queue remains [`plans/2026-09-28-unified-luna-execution-plan.md`](plans/2026-09-28-unified-luna-execution-plan.md); previous G0–G9 is historical context. Nostr scores and mass-populating houses remain deferred.
- [x] Publish the current playable batch and verify the Pages build at `ba64220` plus 11/11 tests against the public site. Future batches need their own release gates and fresh remote fetch.
- [x] Character selector and sprite batch for Arek, Marcin, Damian, Edytka and Renik are live at `d34ff94`. Local follow-up: rebuilt Patryk's NPC sprite from four private reference photos; not deployed.

Use GPT Luna for narrow implementation tasks and Sol for architecture, integration,
review and deployment. No unverified allegations about identifiable village residents.
