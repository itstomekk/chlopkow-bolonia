# Sprint board minigame + shared board framework (plan, 2026-10-12)

Status: P1 IMPLEMENTED and included in the release commit 2026-10-12. D1b: remove the 2P prototype (yes). D6: flag at the old race-flag spot next to Damian, may move later. Medals 16/13/11 s and CPU default 15 s are first guesses, tune after Tomek's playtest.

## 1. Request (Tomek, 2026-10-12)
- Remove the running game.
- New pattern: the player visits a point on the map and a minigame **board** (full-screen
  scene) opens. Eventually most games work this way.
- First board: a straight sprint. Run as fast as possible by alternately pressing LEFT and
  RIGHT buttons.
- Up to 4 players, each slot local human or CPU.

## 2. What gets removed
| Item | Where | Action |
|---|---|---|
| Lap race vs Damian (checkpoints, bale jumps, ghost, off-track slowdown, `HOOKS.speed`) | `docs/js/minigames.js` (`race` type, texts, `MEDAL.race`, venue row, update/draw/HUD branches) | Delete the code. Keep the other five minigames unchanged. |
| 2P key-mash prototype (E02, A vs L, DOM overlay, `2P` sign) | `docs/js/local-competition.js` + script tag in `docs/index.html` | Delete file and tag; the new board supersedes it. Git history keeps it. |
| Tests for both | `test/minigames_test.py`, `test/features_test.py` race sections; `test/local_competition_test.py`, `test/local_competition_race_test.py`; `test/run_all.py` entries | Remove/replace with sprint tests. "All six minigames won" becomes five + sprint. |
| Old saves | `Q.mg.race` | Leave untouched (no migration, no delete). Quest log stops listing the race. |
| Oval track on the map | baked in `map_*.png` via `osm/render_map.py`, `map.json.track`, 6 baked bales, label `TOR WYŚCIGOWY` in `game.js` place names | **Remove** (D4) with a map re-render: only the oval and its 6 bales, NOT the dirt roads (they share terrain class `track`/DROGA POLNA). Before rendering: merge origin/main (church sign, see PLAN) and wait until no other session has dirty map PNGs. Update `map_venues_test.py` (no race bales) and the place-name list. |

`game.js` `drawArekPose` (only used by the ghost) stays; `game.js` is shared and dirty.

## 3. Shared board framework (`docs/js/board.js`, new)
Most future minigames will be boards, so the lobby/players/results part is built once.

`ARK.board.register({ id, title, host, venue, scoreKind: 'time'|'points', actions: ['left','right'], defaultCpuScore, create(api) })`

Framework provides:
- Map entry: flag at `venue`, `HOOKS.near` prompt, `HOOKS.world` flag, minimap dot, `HOOKS.busy` while open.
- Lobby: 4 slots (CZŁOWIEK / KOMPUTER / —), character pick, control scheme, START. Remembers last setup in localStorage.
- Input abstraction: per-player action events (`left`, `right`, later `a`/`b`) from keyboard schemes, gamepads and touch; ignores key auto-repeat; blocks game controls while open.
- Countdown 3-2-1, pause (Esc), results table (place, name, score, medal, NOWY REKORD), retry / leave.
- Scores: `Q.mg.<id> = { tries, won, best, medal, history[], unit }`; per-device top-10 board with names (`ark_board_<id>_v1`). Global leaderboard stays deferred (design doc pillar 3).
- CPU benchmark per `plans/2026-10-11-minigame-design-direction.md`: CPU result = rolling average of the last 20 human results; with no history, the game's default. Several CPUs spread around it (about -5%, 0, +5%).
- Diagnostics: `window.__board` (state, players, positions, times) for Playwright.

BIJATYKA keeps its own lobby for now; moving it onto `board.js` is a later, optional step.

## 4. Sprint board (`docs/js/boards/sprint.js`, new)
- Name: **BIEG NA 100 METRÓW** (host Damian, at the old TOR flag).
- Flag: where the oval track was, near Damian (D6 to confirm).
- Background: village road with real houses, `docs/img/brawl/stage_road.webp` (D2), a 100 m slice at 7 px/m, parallax.
- View: side-scrolling, 4 stacked lanes in slot colours, camera follows the leader, finish tape, distance marks every 10 m.
- Runners: existing side-view BIJATYKA atlases (`docs/img/brawl/*.webp/json`, 7 characters: stand, walk, run, fall, win poses). Read-only reuse, no new art needed for v1.
- Mechanics:
  - A valid stride = pressing the opposite key to the previous one. Each stride adds speed; speed decays every frame, so you must keep alternating. Max-speed cap.
  - Same key twice = stumble: short speed loss, small stumble animation (not a full stop).
  - Animation speed follows running speed.
  - False start (D3): first press before GO = warning for that player; second = +2.0 s added to that player's time.
  - Target times after tuning: casual 15-17 s, good 12-13 s, very fast about 10-11 s.
  - Score = time to 100 m (0.01 s). Medals tuned after the first playtest.
- CPU runner: smooth speed curve that finishes at its target time, small wobble; never reads human input.
- Default keys (rebindable):
  - P1 `Q` / `W` (far left)
  - P2 `V` / `B` (bottom middle)
  - P3 `O` / `P` (right)
  - P4 `←` / `→`
  - Gamepad: LB / RB (or d-pad left/right), one pad per player.
  - Touch (phase 2): two big buttons per player in the four screen corners, so 4 people can play around one tablet.
- Sound: footstep tick per stride, start gun, finish whistle (synth, like BIJATYKA).

## 5. Phases
- **P0 (now):** Tomek answers section 8.
- **P1:** `board.js` + sprint with 1-4 keyboard players + CPU + results/records; remove race and prototype; tests; docs (README PL, DEVELOPMENT, PLAN, HANDOFF). Local only.
- **P2:** gamepads, touch corners, key rebinding UI, photo-finish freeze frame, polish after Tomek's playtest.
- **Later:** second board game on the same framework; global leaderboard (Nostr) when designed.

Implementation can go to a GPT Luna worker with parent verification (syntax, focused Playwright, full minigames regression). No commit/push/deploy without Tomek's explicit go.

## 6. Tests (P1)
- `test/sprint_board_test.py`: flag reachable, lobby opens, 4 slots (2 human + 2 CPU), synthetic alternating presses advance, same-key presses stumble, auto-repeat ignored, false start rule, finish order and times, record saved, CPU target = history average, Esc pause/leave restores normal walking, `HOOKS.busy` true only while open.
- Negative: old race flag/prompt/ghost/`2P` sign absent; `HOOKS.speed` no longer slows off-track.
- Regression: remaining five minigames, map venues, BIJATYKA, church, save migration.
- Public Nostr isolated in all browsers (existing `run_all.py` rule).

## 7. Risks
- The worktree has uncommitted BIJATYKA work from today touching `docs/index.html`, `docs/js/game.js`, `test/minigames_test.py`, `PLAN.md`, `HANDOFF.md`. Sprint edits to those files must be small and must not overwrite that work (decision D5).
- Keyboard ghosting: some laptop keyboards drop keys when many are pressed together. Alternating presses mostly avoid it; test 4 players on Tomek's ThinkPad.
- The BIJATYKA atlases may be renamed by the parallel session; load them through their JSON, not hard-coded frame offsets.

## 8. Decisions for Tomek
- D1: Remove the lap race vs Damian: **yes**.
- D1b (open): the 2P prototype (`local-competition.js`, yellow `2P` sign next to the track, A vs L key mash to 12 presses, DOM overlay, built 2026-09-30 as E02 and never reviewed). Recommended: remove, the sprint replaces it.
- D2: Background: **village road with real houses** (BIJATYKA `stage_road.webp`).
- D3: False start: **first = warning, second = +2 s penalty**.
- D4: Oval track: **remove from the map** (re-render).
- D5: BIJATYKA session is **not done**: wait before editing `docs/index.html`, `docs/js/game.js`, `test/minigames_test.py`.
- D6 (open): flag spot after the track is gone. Recommended: same area, next to Damian.

## 9. Coach suggestions (not part of P1)
- Lore hook: a second sprint variant "Bieg do sklepu przed zamknięciem" - same mechanics, the finish line is the shop door.
- Shareable moment: photo-finish freeze frame saved as PNG/GIF with names and times.
- Handicap toggle: "w gumiakach" (rubber boots) for the person who keeps winning.
