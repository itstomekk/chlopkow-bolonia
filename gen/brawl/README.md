# BIJATYKA art pipeline

Runtime: `docs/js/brawl.js`. Art: `docs/img/brawl/`. Test: `test/brawl_test.py`.

## Adding a fighter

1. Reference = the fighter's existing walking sheet (`docs/img/<name>_sheet.png`), never a private photo from `references/`.
   Build a 4x enlarged right + front cell (see `Hermes/image-gen/2026-10-09-chlopkow-brawl-sprites/make_refs*.py`).
2. Generate 3 sheets with Codex `image_generate`, 4x3 poses on flat `#FF00FF`, facing right. Prompts: `raw/prompts_round1.json`.
   - `s1`: `image_url` = character ref, `reference_image_urls` = `raw/arek_s1.png` (the approved style anchor).
   - `s2`, `s3`: `image_url` = the character's own `s1`, reference = character ref. Pose order must match `SHEETS` in `build_fight_sprites.py`.
3. Save as `raw/<name>_s1..s3.png`, add the name to the fighter loop in `build_fight_sprites.py`, run it, inspect `preview_<name>.png`.
4. Add an entry to `FIGHTERS` in `brawl.js` (`atlas`, `ball`, `spin`), extend `test/brawl_test.py`.

## Per-fighter beam look

A fighter with `power.el === 'beam'` may add `core` (CSS colour of the beam centre and charge orb, default white) and `size` (width multiplier, default 1)
to the `power` object in `brawl.js`. ARTUR uses `core: '#0b0b10', size: .6` for his thin black beam; damage and reach are unchanged.

## Frame overrides (later edits)

- `raw/<name>_s3beer.png`: only its drinking cell is used (Łomża instead of milk).
- `raw/<name>_s3carry.png`: only its carry cell is used (empty raised hands). The game draws every carried
  item (kamień, bańka, opona, wiadro, grabie, łopata, kosa) over the hands, so new heavy items need only an item sprite.
- Small projectiles (vinyl, football, hammer, szarlotka, pieczarka) are drawn in `build_fight_sprites.py` (`PROC_ITEMS`).

## Held weapons (s4 + cyan grip marker)

- `raw/<name>_s4.png`: 4x2 weapon poses (stand, walk, thrust, swing, jump-stab, throw, shoot, case) where the
  character holds a flat CYAN (#00FFFF) stick / block instead of a weapon. `take_grip()` fits a line to the cyan
  pixels, takes the hand from the gap the fist leaves in it, writes `grip {hx, hy, tx, ty}` into the atlas JSON and
  erases the marker. `drawWeapon()` in brawl.js draws any weapon sprite there (`WGRIP` = where the hand holds it).
- A new weapon = one sprite in `raw/weapons.png` (handle left, business end right) + `ITEM_DEF` + `WGRIP`.
- Michał starts with the paintball pistol (`start: 'pistol'`, D>A volley of orange balls), Sołtys with his teczka.

## Slicing rules (why the builder looks the way it does)

- Codex does not keep a strict grid. Take the 12 largest connected components as figures, assign them to cells by centroid,
  then attach smaller pieces (stars, motion lines) to the nearest figure by bbox gap.
- Drop large detached pieces (thrown apple, stone, pitchfork): the game spawns those as separate entities.
  A plain per-cell crop leaks neighbouring props into frames.
- Frames are scaled so `stand` is 200 px tall and drawn at 0.5; anchor = bottom + mean x of the lowest 35 %.

## Tests

Combat checks are deterministic: the test sets `fight.paused = true` and advances with `ARK.brawl.step(n)`.
Wall-clock waits made punch/dizzy checks flaky (fall meter decays per tick).
