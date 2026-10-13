# NPC cast walk sheets

Tomek (2026-10-13): every character we have is selectable for now, including the older NPCs (Wesołych Świąt, Sołtys, Irenka...). These nine had only a single standing sprite in `docs/img/npcs.png`, so each got a BERCIK-style 4x2 walk sheet.

- Identity reference: the NPC's own sprite in `gen/npc_src/` (the art already in the game), never private photos. `halina` uses `irenka.png`, `michal` uses `bukala.png`, `soltys` uses `soltys_raw.png`.
- Generator: `python gen/cast_npc/gen_walk.py [id ...] [--force]` -> openai-codex `gpt-image-2-medium` with `gen/bercik/bercik_walkcycle_raw.png` as layout/style template, 4 in parallel, then `gen/build_cast_walk.py build --height 75` (150 px = BERCIK, 40 colours, hard alpha).
- Raws and manifests: `gen/cast_npc/<id>/`. Atlases shipped as `docs/img/<id>_sheet.png/.json` + `<id>.png`.
- In the world these NPCs still draw from `docs/img/npcs.png` (quest markers stay); the walk sheet is used when you play as them (`PIXEL_CHARACTERS` vs `PIXEL_NPCS` in `docs/js/game.js`).
- Review: `gen/cast_review/2026-10-13_npc_cast_walk_review.png` (old sprite next to the new front/back/side frames).
