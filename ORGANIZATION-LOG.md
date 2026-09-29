# ORGANIZATION-LOG — arek-w-chlopkowie

## 2026-09-27
- Created as `Hermes\image-gen\2026-09-27-arek-pixel-game\` (sprite generation for Arek).
- Renamed `game/` -> `docs/` so GitHub Pages can serve it from `main:/docs`.
- Moved the whole folder to `Hermes\projects\games\arek-w-chlopkowie\`.
- 2026-09-27: added docs/js/church.js (interior room), gen/PROMPTS-church.md, test/church_test.py, .claude/skills/add-interior/.
- 2026-09-27 (audit): archived HANDOFF.md -> `_archive/2026-09-27_HANDOFF-before-audit.md` and PLAN.md -> `_archive/2026-09-27_PLAN-village-assets.md`; wrote a consolidated HANDOFF.md and PLAN.md.
- 2026-09-27 (audit): split minigames out of `docs/js/features.js` into `docs/js/minigames.js`; added `osm/geo.py` (shared map geometry) and `test/run_all.py`.

## 2026-09-28
- Added project-local `AGENTS.md` with project aliases, safe working rules, and pointers to recent related sessions.
- Registered `chlopkow-bolonia` under `personal-life` in the hub portfolio and project routing so “Chłopków Bolonia”, “Arek game”, and “Arek w Chłopkowie” resolve to this folder.
- Cleaned `docs/audio/` to final playable assets only: retained Ogg/Opus files used by the game, removed duplicate download/encoding variants, and archived source/intermediate files under `_archive/2026-09-28-audio-source-files/`.
- Reworked the recorded soundtrack policy in `docs/js/music.js`: the printed Polka Dziadek is the entrance-screen track only (`TITLE_TRACKS`), village and field share one default zone that picks randomly from `DEFAULT_TRACKS` (six tracks, never repeating back to back), and the default playlist speed follows activity linearly from 0.4x to 1.3x. Added `track-ona-tanczy.ogg` (492 KB, 16 kbps/24 kHz mono) and archived its 1.0 MB uncompressed master.
