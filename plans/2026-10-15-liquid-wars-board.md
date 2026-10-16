# WOJNA PŁYNÓW (EN: LIQUID WAR): a minigame (plan, 2026-10-15)

Status: **P1 IMPLEMENTED on local branch `feat/liquid-wars-board`** (worktree `arek-w-chlopkowie-liquid`), tested in a browser; no push, no deploy, no merge (Tomek's rule). Name, entry point and level source corrected by Tomek on 2026-10-15 (section 0).

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
