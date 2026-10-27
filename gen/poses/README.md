# Human pose sets 🧍

41 poses + a select-screen portrait for each of 24 characters (talk, wave, laugh, think, surprised, sad, angry, point, cheer, sit, sleep, run, jump, hurt, KO, dig, crouch, pick up, throw). Same idea as the dog pose sheets.

- Shipped output: `docs/img/poses/<id>_poses.png` (strip of 130x190 cells, facing right), `<id>_poses.json` (`cell`, `facing`, `poses`, `anims`), `<id>_portrait.png` (128x176). **Not wired into the game yet.**
- Generate: `python gen/poses/gen_poses.py <id>` (Codex GPT Image; the only reference is the character's own shipped walk sheet, never private photos) -> `<id>/raw/`.
- Build: `python gen/poses/build_poses.py <id>` -> `<id>/out/` (scale = standing figure matches the walk sprite's height).
- Audit: `python gen/poses/audit_poses.py` (empty / edge-touching / duplicate / odd-scale cells, all 24 must be 41 poses with a portrait).
- Not covered: PATRYK (needs real photos), the small NPCs in `npcs.png`, dogs (own sets).
- Known limit: pose quality was checked by the audit script and coarse visual review, not frame by frame.
