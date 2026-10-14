---
name: add-interior
description: Add an enterable interior room (church, shop, świetlica, a house) to Arek w Chłopkowie, or add art and NPCs to one. Use when Tomek sends photos of an inside space or asks to "wejść do środka" or "enter" a building.
---

# Add an interior room

The church (`docs/js/church.js`) is the working template. A room is a function returning:
`{ w, h, top, ground, obj, objects, solid, pois, candles, spawn, exit:{x0,x1,y}, soltys }`.

1. **Layout first.** Width about 320, so it fits the 640-unit view and gets centred. Characters are 40 units tall.
   Put a tall back wall at the top, and the door gap in the bottom wall with the exit a few px above `h`.
   Put the spawn about 15 px above the exit, so Arek doesn't walk straight back out.
2. **Draw** with `R(ctx,x,y,w,h,col)`. Floor and walls go on `ground`. Anything Arek can walk *behind* goes on `obj`,
   and each piece needs `put(x,y,w,h,baseY)` so it is depth-sorted. Mark collisions with `block()` (2 = solid).
3. **Palette** comes from the photos. No people from the photos go into the art. Sprites of real people (like the Sołtys) are
   caricatures made only with Tomek's OK.
4. **Wire it up in `game.js`:** copy `enterChurch()` (with fade, `OUT` backup and `ROOM` swap). Trigger it from the building's
   POI in `interact()`. Add PL and EN texts for every interior POI and NPC to `T`.
5. **Test:** copy `test/church_test.py`. It enters, talks to the NPC, reads a POI, exits, and asserts that Arek returns to the door.
   On the cloud container, run it with `CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome` after starting
   `python3 -m http.server 8765 --directory docs`. Also re-run `quest_test.py` and `jump_test.py 1662 1747`.
6. **AI art (optional, local PC only):** `gen/codex_gen.py`, or PPQ as a fallback. Copy the prompt pattern in `gen/PROMPTS-church.md`.
   Codex login does not work from cloud sessions (OpenAI returns 403 to datacenter IPs).

## Lessons

- Images pasted into chat are visible to the model but are NOT files in the container. To use them as references, Tomek must
  put them on disk: the local PC, or a Google Drive folder the session can download into the gitignored `references/`.
- The camera centres rooms that are smaller than the viewport (the `MAP.w < vw` check in `render`).
- Rooms can nest (church -> crypt, `docs/js/crypt.js`): `OUT` always stays the village so `save()` writes the right door coordinates at any depth; `PARENT` holds the room to climb back to. `leaveRoom()` checks `PARENT` first. Give a nested room `kind:'crypt'` and pick its music in `music.js` `pick()`.
- A dark room can set `lights` (additive pools, flickering) and `vignette:true`; game.js draws both after the candle flames. Carve walkable floor out of a fully solid `solid` array (`openRect`) instead of blocking walls one by one, and hide secret areas by drawing them only when unlocked (the returned `objects`/`pois`/`lights` arrays are shared by reference, so they can grow after entry).
- Rooms nest through a room STACK (`game.js`, `ARK.rooms.descend/ascend/surface`); `PARENT` no longer exists (`ARK.parentRoom` is the top of the stack). Give each room an id (`room.rid`) so `ROOM_BUILD`/`ROOM_CHAIN` can rebuild it after a deep entry.
- Secret links to further places (tunnels, forest paths, an underground village) are NOT built as new rooms in `game.js`: add a passage in `docs/data/passages.json` with a lazy module (`PASSAGES.defineKind`) and lazy data, see DEVELOPMENT.md 'Passages engine'. Only `passages.js` is eager.
- A room without an `exit` (passage rooms) uses `portals[{rect, go}]`; with `interact(poi, api)` and `tick(dt)` it brings its own POI logic, and `labelKey` names it in the HUD.
- Run Playwright through `python test/isolated_browser_runner.py test/<name>.py` so test names never reach the public Nostr arrival log. If port 8765 is taken by another checkout's server, serve the worktree on another port and set `ARK_URL`.
