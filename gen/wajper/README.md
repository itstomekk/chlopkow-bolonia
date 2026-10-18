# WAJPER (selectable starting dog)

Tomek, 2026-10-17: new dog WAJPER, chosen at the start of the game (dog-companion start, see
`plans/2026-10-17-kierunek-gry-legends.md` section 3). Real dog: small Skye-terrier-type (Tomek's call), shaggy,
COOL silver-white lights (not cream), charcoal drop ears and saddle, plumed tail curled over the back, no collar.
Fringe sometimes over the eyes, sometimes parted. Slightly smaller than Frodo.

- Reference photos: `references/wajper/wajper_01..13.png` (gitignored). Round 2 used 01, 08, 06, 04, 12.
- `gen_wajper.sh [walk idle yawn fun dig run sleep portrait]` -> `raw2/` (openai-codex gpt-image-2, Frodo raw as template).
  Every animation is one row of one sheet; row 1 of each pose sheet starts with a standing side anchor.
- `build_wajper.py` -> `out/` (candidates, not wired): `wajper.png` (Frodo 64x128 contract), `wajper_walk4.png`
  (4-frame walk), `wajper_poses.png/.json` (49 poses facing right + anims), `wajper_portrait.png`, `review.png`,
  `anim.gif`, `report.json` (scales, colour count, per-anim motion, frame heights).
  Size: side walk 22x19 px vs Frodo 26x20, front 23 vs 26 tall. Shared 32-colour palette, added 1 px outline.
- Round 1 (rejected: warm cream colours, yawn/tilt zoomed because their frames came from different sheets):
  `gen_wajper_r1.sh`, `build_wajper_r1.py`, `raw/`, `out_r1/`.

Status: round 2 wired into the game as a second dog (docs/js/dogs.js, ?dog=wajper). Not live.

Repo note: only this README and the round-2 scripts are tracked. `raw/`, `raw2/`, `out/`, `out_r1/` (generated candidates) and the round-1 scripts stay local; the shipped assets are `docs/img/wajper*.png/.json`.
