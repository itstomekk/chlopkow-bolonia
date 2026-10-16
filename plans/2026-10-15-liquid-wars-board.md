# WOJNA PŁYNÓW (EN: LIQUID WAR): a minigame (plan, 2026-10-15)

Status: **P1 + v2 (Tomek's playtest changes, section 8) IMPLEMENTED on local branch `feat/liquid-wars-board`** (worktree `arek-w-chlopkowie-liquid`), tested in a browser; no push, no deploy, no merge (Tomek's rule). Name, entry point and level source corrected by Tomek on 2026-10-15 (section 0).

## 0. Corrections by Tomek (override everything below)
1. The name is **WOJNA PŁYNÓW** (EN **LIQUID WAR**), not WOJNA GNOJÓWEK. GNOJÓWKA stays only as one of the six substances.
2. It is a **minigame entered at a place on the village map**: a flag for now, later inside a building. The entry point is ONE descriptor (`VENUE` in `liquid.js`): kind `flag` resolves coordinates from the current `map.json` at runtime (`corral` centre + offset); kind `building` is a documented stub resolver for the later interior hook. `board.js` is reused internally (lobby, input, results, saves); the UI calls it a minigame.
3. The **levels are generated from our own OpenStreetMap-based map data**, not hand-drawn: `gen/build_liquid_maps.py` crops `docs/img/map_collide.png` (the mask the game walks by: houses, walls, fences = walls; roads, grass, yards = open) at several zooms, downsamples to the 160x84 fighter grid, keeps the largest connected open region (islands become wall), picks four start areas in open space, and writes `docs/data/liquid-maps.json`. Shipped levels (zoom, px per cell): CAŁA WIEŚ / WHOLE VILLAGE (coarse, 20), OKOLICE SKLEPU / AROUND THE SHOP (medium, 8), KOŚCIÓŁ I PLEBANIA / CHURCH AND RECTORY (close, 4), CMENTARZ / CEMETERY (close, 5), PODWÓRKA / FARMYARDS (close, 5). The lobby picks a level or LOSOWY / RANDOM. Tests assert one connected region and room for four teams on every level, and that wall cells are the blocked cells of the mask. Note: water is only partly in the collision mask (the sampled map water points are open there), so the levels show houses, walls and fences, not the river.

## 1. Request (Tomek, 2026-10-15)
- Rebuild the Linux game Liquid Wars inside Chłopków Bolonia as one more minigame.
- Gameplay identical to the original. Only the look and theme change: the "liquids" are different village substances.

## 2. Licence rule
Liquid Wars is GPL. The mechanics are reimplemented from the public description. No code, maps, graphics or sounds are copied.

## 3. Gameplay contract (implemented)
- 2 to 4 teams, one cursor each, a fixed army (one fighter per grid cell; about 30 % of the open cells in total, at most 1100 per team).
- Each team has its own distance field flooding outwards from its cursor, **progressively** (a bounded number of cells per tick, like the original's gradient), never a search per fighter.
- A fighter tries the neighbour with the lowest distance first, then the side directions in a fixed order (5 candidates; the original uses 12 directions, this grid has 8). Free cell: move. Friend: no move (tops up its health). Enemy: attack; at 0 health it joins the attacker's team with part of its health. No fighter ever disappears; the total is constant (asserted every run).
- A team with 0 fighters is out. The round ends when one team remains or after 90 s. Ranking by fighter count.
- The cursor cannot enter walls (it slides along them).
- Tunables are constants (`CFG` at the top of `liquid.js`, overridable through `__liquid.tune` for tests): army, attack, defence, regeneration, round time, cursor speed.

## 4. Theme
Six cosmetic substances with PL/EN names and identical stats: GNOJÓWKA (brown), MELIORANKA (blue-green), MLEKO (white), ORANŻADA (orange), KOMPOT (purple), BIMBER (pale yellow). Cursor = the slot's character head in the substance colour. Splash particles at conversions and a synthesised "chlup". Canvas font PixelifySans.

## 5. Implementation (P1, done)
- `docs/js/boards/liquid.js` (registered with `ARK_BOARD_REGISTER`), `docs/data/liquid-maps.json` (lazy-loaded on first lobby), `gen/build_liquid_maps.py`.
- Typed arrays, fixed 60 Hz framework tick, render through an ImageData buffer (2x2 px per cell) scaled 3x with smoothing off.
- `board.js`, strictly additive: `up`/`down` actions with `api.down(player, action)`; gamepad stick and d-pad up/down; keyboard schemes arrows, WASD, IJKL, numpad; `pointer: true` adds a TOUCH / MOUSE scheme (drag your cursor; default on touch devices); `slotOption` (substance select per slot), `options` (level select), `cpuNote`, lazy `def.load/status`. The sprint board uses none of this and its test passes unchanged.
- CPU cursor: samples enemy fighters, scores fronts (few friends nearby, many enemies, low health, near itself), walks toward the best with a full distance field, with a reaction delay. PRZECIĘTNIAK skill follows the averaged past share (default 25 %).
- Score = % of all fighters at the end (0.1 precision); medals 30 / 50 / 75 % (first guesses).
- `window.__liquid`: `sim`, `audit()`, `game`, `tune`, `data`, `status`, `VENUE`; the board state in `__board.state.game` has team counts, cursors, tick, phase and timings.
- Tests: `test/liquid_board_test.py` in `run_all.py`.

## 6. Measured (headless Chromium on this machine)
About 3400 fighters: tick 0.3 to 0.9 ms average; about 5750 fighters: tick 1.5 to 2.8 ms average, p95 2.3 to 3.7 ms, draw 0.6 to 1.1 ms; the loop holds 60 ticks/s. A real laptop was not measured.

## 7. Later (not P1)
- Interior entry (building) instead of the flag; online play over Nostr/game server (`plans/2026-10-04-multiplayer.md`); lobby options (army size, speed, round time); more levels (the generator takes a list); substance-specific art; tuning after Tomek's playtest; portrait phones show the 16:9 board letterboxed (a rotate hint or a taller layout would help).

## 8. v2 after Tomek's playtest (2026-10-16, implemented)
Tomek ("jest super") asked for three things; sections 0 to 7 above describe P1, where they differ this section wins.
1. **No records.** `board.js` has a strictly additive board flag `records: false`; `liquid.js` sets it, `sprint.js` does not (the sprint test passes unchanged and now also asserts it keeps PRZECIĘTNIAK). For a no-records board: no `Q.mg[id]` writes (tries, best, medal, history), no per-device top 10, no global scores calls (no read, no write), no medal/star/NOWY REKORD, no PRZECIĘTNIAK in the lobby (plain KOMPUTER CPUs with the fixed default skill), quest log and flag label without result text. The results screen (`drawRanking`) shows the winner and each team's share with colour bars. Old saved records of the board are deleted when its lobby opens. The 30/50/75 % medals of section 5 no longer exist.
2. **Resolution.** Grid 160x84 -> **320x168** (3 board px per cell, 960x504 field under the 36 px HUD). One canvas pixel per fighter in a 320x168 buffer drawn 3x. Fighters act every tick (was every 2nd) so their speed in board px/s is unchanged; cursor 1.7 cells/tick. Army: `armyFrac` .28 of the open cells, `armyMax` 2000 per team (about 7000 to 8000 fighters in all). Speed work: per-cell neighbour bitmask (`level.nb`), strided visiting order, the flood budget is `open / floodTicks` (8) with head/tail kept in locals, regeneration as a strided sweep. The distance field is still the progressive per-team flood.
   Measured (headless Chromium, 4 teams, 8000 fighters, 41331 open cells): tick avg 2.2 to 2.8 ms (p95 3.3 to 4.3 ms), of which the flood is about 1 ms, draw 0.5 to 0.6 ms, loop 59.8 to 60 Hz. Whole village (7500 fighters): tick avg 1.9 to 2.8 ms. With `Emulation.setCPUThrottlingRate` 4: tick avg 10 to 11 ms (p95 13 to 19), draw about 3 ms, loop 45 to 52 Hz (the loop runs fixed 60 Hz steps, so under heavy slowdown the game runs slower than real time rather than skipping rules). 12000 to 14000 fighters were tried: unthrottled fine (tick 4 to 8 ms) but 35 to 50 Hz at 4x, so the army stays near 8000. Not measured on a real laptop or phone.
3. **Twelve levels** from our map (generator `gen/build_liquid_maps.py`; px per cell in brackets): CAŁA WIEŚ (16), GŁÓWNA ULICA (6), OKOLICE SKLEPU (5), KOŚCIÓŁ I PLEBANIA (3), CMENTARZ (5), PODWÓRKA (3), STAW (6), MELIORANKA (4), SKRAJ LASU (6), BOISKO I ŚWIETLICA (4), CHŁOPKÓW-KOLONIA (5), JAZZ W STODOLE (5). Walls = `map_collide.png` (>64: houses, fences, water-bank samples) plus terrain classes of `map_terrain.png` per level (forest 220, crop fields 160). Specks under 6 cells are removed, the grid border is wall, only the largest connected region stays, and the build fails when the open share is outside 35 to 92 %, when no four start areas with a free neighbourhood exist, or when two start areas are fewer than 60 steps apart by walking. Tuning aid: `--explore`. Encoded as RLE rows (base-36 run lengths, wall run first) in `docs/data/liquid-maps.json`, 50 KB for 12 levels (v1: 70 KB for 5), lazy-loaded; `liquid.js` decodes and validates it (row count, runs, wall border). The lobby shows a 192x101 thumbnail of the chosen level (optional `def.preview` in `board.js`) with the four start dots; RANDOM shows a "?" placeholder.
   Tried and dropped: windmill, shooting range, Wapnica, the meadow around the pig corral and the cemetery at close zoom (nearly empty or nearly solid in the collision mask; graves are not in it). There is no water layer in the terrain classes and `map.json` `water` holds only bank sample points, so no level shows drawn water.
