# FRODO complete behaviour poses

## Owner request

Complete the missing Frodo poses and remove pose-dependent coat darkening (especially lick).
Use the existing approved black/golden-tan dog with pointed ears and a red collar, not WAJPER.

## Reproduce

- `python gen/frodo/generate_poses.py`: six sheets (49 usable poses including the original stand anchor).
  Input: `gen/frodo_sheet_raw.png` only. Prompts/logs and generated images in `raw/`.
- `python gen/frodo/build_poses.py`: 32 px cells, component extraction and one scale per sheet from the
  standing reference. A fixed palette comes from the original walk, with explicit collar/tongue slots.
  Do not learn a separate palette per pose/sheet or infer colours from the rejected old lick sheet.
- Runtime: `docs/img/frodo_poses.png` + `.json`, registry `docs/js/dogs.js`.
  Old `frodo_idle.*` retained for rollback but not loaded by the registry. Original `docs/img/frodo.png`
  walk remains byte-identical to HEAD. WAJPER assets are untouched.

## Outputs

`out/frodo_review.png`, `out/frodo_behaviours.gif`, `out/frodo_ingame.png`, `out/report.json`.
49 poses: stand; pant, scratch, sniff, yawn, head tilt, shake, bark, howl, dig, play bow, lie,
belly-up roll, gallop, jump, beg, tail wag, sleep, stretch, lick and paw lick.
The behaviour library includes run/jump/beg; the existing movement simulation is unchanged.

## Checks

- `python test/frodo_poses_test.py`: complete manifest, palette, hard alpha, no magenta,
  nonempty frames, retained tan markings and original walk bytes.
- `ARK_URL=http://127.0.0.1:<port>/index.html python test/isolated_browser_runner.py test/frodo_poses_browser_test.py`:
  42 active action/frame combinations use the correct actual source cells, with equal draw size
  (lick no longer shrinks); no page/HTTP errors. Passed twice.
- Existing Frodo follow and WAJPER integration tests also pass locally.

Repo note: only scripts, README, prompts (`raw/*.prompt.txt`), `out/report.json` and `out/frodo_review.png` are tracked; the generated sheets (`raw/*.png`) and other review media stay local, as does the WhatsApp sticker export. The shipped assets are `docs/img/frodo_poses.png/.json`.
