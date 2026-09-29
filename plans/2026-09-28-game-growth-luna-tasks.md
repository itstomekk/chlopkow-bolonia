# Chłopków Bolonia: stepwise game-growth implementation plan

> **Superseded as execution queue:** the consolidated task-by-task plan is `plans/2026-09-28-unified-luna-execution-plan.md`. Keep this file as prior architecture/audit context; do not dispatch both queues.

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans, one task at a time. The supervisor reviews each task's diff and test evidence before releasing its successor. Checkboxes are tracking, not authorization to start. Project-specific rule overrides the skill's commit step: **no commit, push or deploy without Tomek's explicit request**.

**Goal:** Grow missions/checkpoints, content and eventually local competitive minigames on the existing-sized map without replacing the engine or breaking existing saves.

**Architecture:** Keep the generated OSM map, Canvas runtime and single overworld hero. Most homes get an outdoor interaction/object; interiors remain bespoke until needed. Give new checkpoints stable IDs and a small mission-state module. Preserve old quest behavior and saves. In a later, separate phase, distinguish local minigame participants and scores without adding networked multiplayer. Nostr high scores are a later protocol, not today's chat feature.

**Tech Stack:** plain browser JS and ordered `<script>` tags, `localStorage`, Python OSM generator/editor, Playwright/Python tests, static GitHub Pages. No new framework or bundler.

**Status:** planning only; Tomek intends to add requirements shortly. Reconcile those requirements and approve the affected task cards **before starting G0**. This plan does not authorize generation, edits to game code, or publication.

## Confirmed product contract

- Keep the map at approximately the present size (`docs/map.json` currently 5143 × 7091). Add and improve houses, scenery, characters and missions *inside* that world; no map-resize project or online world synchronization.
- One selected hero traverses the overworld. Outdoor checkpoints/objects near homes are the default; only selected missions have interiors. Existing quiz boards at 21 homes are optional questions, **not** a quest/interior implementation.
- Missions may combine visiting checkpoints, talking, collecting and finishing a minigame. An individual checkpoint must have an ID independent of its position or array index. Do not force one question per house.
- Later, several people can compete on one machine inside selected minigames using distinct keys (including a fastest-keypress race). This is simultaneous local competition, not multiple world avatars. Preserve ordinary single-player play and touch controls.
- Later still, a Nostr leaderboard; no Nostr-score implementation or claim of tamper-proof scores in this phase.
- Asset visual review is **already** planned as A0–A4 in `plans/2026-09-28-asset-style-roadmap.md`; do not duplicate or bypass Tomek's style approvals. The map editor's unfinished E2 generator integration is in `plans/2026-09-28-map-editor.md`.

## Architecture audit: decisions and evidence

- `docs/js/game.js:217–218,716–745,1406–1414`: legacy mission state, branching and quest HUD are hardcoded in separate locations. Keep legacy missions intact; introduce only a small new checkpoint mission path, then migrate proven patterns incrementally.
- `docs/js/game.js:183–195,707–714` and `docs/js/features.js:35–39`: hooks already permit outdoor interactions. Use that seam, not a wholesale engine split. Missing/mismatched quiz-board `spot` currently silently excludes content; validation must flag missing anchors.
- `docs/js/game.js:233–248`: one local save with `Object.assign`, without schema migration. Old `Q` fields, NPC positions, quiz progress and minigame records must survive; avoid save-key rollover or `localStorage.clear()` outside isolated tests.
- `docs/js/minigames.js:123–130`: duck records currently compare/store time, whereas duck medals and result text expect hit count. Fix and regress this independently.
- `docs/js/game.js:224,496–522` and `docs/js/minigames.js:95–134`: one input Set, one `P`, one record per minigame. Future concurrent competitors need minigame-local participants and per-key input events; no change to the overworld controller yet.
- `osm/edits.py`, `editor/server.py` and `plans/2026-09-28-map-editor.md:98–119`: editor storage exists, but generation does not yet apply edits. E2 must land before relying on map edits as durable game assets. Regeneration rewrites shared `docs/` outputs, so only one writer at a time.
- `docs/js/chat.js`: the Nostr text chat is a separate feature; it does not authenticate gameplay or validate times/hits. Signed self-reported results would be socially ranked, not cheat-proof.

## Execution protocol for **every** Luna card

1. Read `AGENTS.md`, `PLAN.md`, current `HANDOFF.md`, this plan, the linked subplan where relevant, and `git status --short --branch`. Record HEAD and unrelated dirty/untracked files. Never wipe/overwrite them. Assign one writer to each touched path; map generation is always serialized with asset/editor work.
2. Write a focused failing test first (RED), execute it and record the actual failure; implement the smallest change (GREEN); rerun it and the relevant adjacent tests. No silent test updates merely to make a failure disappear. Browser tests need a locally served `docs/`; see `test/run_all.py` for port and test invocation. Use `node --check` on changed JS.
3. Report exact changed files, commands and actual outputs, save compatibility, screenshot when visuals change, and known limitations. Supervisor verifies the diff/test outputs independently. A clean task is accepted before the next starts; a failing baseline is recorded before deciding whether the failure belongs to the card.
4. Never commit, push, deploy or upload private human photos. Leave `references/`, `.env`, browser credentials, and unrelated raw media untouched. Keep safe asset provenance and visual-approval gates in the separate A-series plan.

## File responsibilities to preserve

- `osm/edits.py`: validate and apply geographic map edits; `osm/render_map.py` and `osm/place_items.py`: generated outputs. Do **not** make the public runtime read private editor files.
- `docs/items.json` is generated. A proposed authored (not generated) public file `docs/missions.json` contains mission definitions and stable references to generated `items.json` anchors; validation must run after any regenerated map. `docs/js/missions.js` is proposed as the small *runtime* for new mission state and hook registration. These are new contracts, not existing files/APIs.
- `docs/js/game.js` remains the legacy world/controller/save host; use narrow bridge calls rather than transplanting all NPC/world code. `docs/js/minigames.js` owns minigame lifecycles; a proposed `docs/js/local-competition.js` should only be introduced when a concrete two-person minigame exists.
- New focused tests under `test/` cover mission data, progress, migration and competition; `test/run_all.py` adds tests only when they are stable. The `test/run_all.py` suite currently enumerates 25 game tests, not the historical 11-test count in older notes.

## Tasks, dependencies and proof

### G0 — Baseline and one-writer handoff (read-only; do first)
**Owns:** this plan's execution log / task response only; no code or generated outputs.
- [ ] Capture `git status --short --branch`, HEAD, dimensions/content counts and current changed paths. Compare current code with the audit before trusting line numbers. Check ongoing asset/map worker ownership.
- [ ] Run `for f in docs/js/*.js; do node --check "$f" || exit 1; done`, `python test/edits_test.py`, `python test/editor_test.py`; expected: exit 0, otherwise record which failure pre-existed.
- [ ] Run the complete *local* suite with a server as documented in `test/run_all.py`, without modifying project fixtures. Expected: runner exits 0 and reports its actual passing count (currently 25 entries). If environment/server blocks it, record the exact blocker; do not claim full-suite success. Review generated screenshots so new untracked artifacts are not mistaken for deliverables.
- [ ] Supervisor freezes which paths are owned by the E2 and A-series streams. No downstream execution until this and Tomek's incoming additions are reconciled.

### G1 — Correct duck score semantics (small independent bugfix; after G0)
**Owns:** `docs/js/minigames.js`, `test/minigames_test.py` (or a smaller new test under `test/`). No map or quest files.
- [ ] Add a failing assertion: finish a `ducks` run with known `MG.hits`, then check `__game.Q.mg.ducks.best === hits`, medal comes from the hit thresholds, and a better hit count replaces the old record; a worse one does not. Also assert `skeet` still ranks high scores and `pig`/`race` still rank low times. The existing `test/minigames_test.py:89–99` only checks duck win, so this is new coverage.
- [ ] Run that focused test against local `docs/` and record RED. In `endMG()` (`docs/js/minigames.js:123–130`), treat **both** `skeet` and `ducks` as hit-based for `score` and `better`, while preserving existing time-based logic for the other games; GREEN.
- [ ] Run the focused test and complete `test/minigames_test.py`; `node --check docs/js/minigames.js`. Supervisor checks diff is limited to score behavior and regression test.

### G2 — Make map-editor edits survive regeneration (depends G0; existing E2, not a second implementation)
**Owns:** exactly the files assigned in `plans/2026-09-28-map-editor.md:107–119` (`osm/render_map.py`, `osm/place_items.py`, `test/edits_pipeline_test.py`, fixture). Do not start while another worker generates/replaces map files.
The E2 milestone is **four serialized Luna cards**, each handed off and verified before the next. In every card, use a temporary output route or backup/restore all rewritten `docs/` outputs byte-for-byte; hash-check and review the diff. If the current E2 spec's suggested output-dir flag is absent, implement a safe temporary route or stop before an uncontrolled rebuild. Exact stage names/context follow current `osm/edits.py`, not guessed APIs.
- [ ] **G2a, safe harness:** capture baseline SHA-256 of `docs/map.json`, `docs/items.json` and map PNGs in Hermes scratch, not repo root. Test missing/empty edits with existing generator and prove byte-for-byte equality; add `test/edits_pipeline_test.py` with that assertion and no game-visible fixture. Supervisor accepts the safe test route before any hook is added.
- [ ] **G2b, terrain hooks:** add failing fixture assertions for `forest.add/remove` and `water.add`, then only their `osm/render_map.py` hooks. Test forest pixels and water collision at fixture positions and empty-edit byte equality; `python test/edits_pipeline_test.py`, `python test/edits_test.py`. Supervisor checks all real outputs restored.
- [ ] **G2c, objects/collision hooks:** add failing fixture assertions for explicit tree, cleared generated tree, collision block/free; add only their `osm/render_map.py` hooks. Check generated objects and collision at chosen fixture points, no accidental roadside tree; rerun G2b and empty-edit tests. Supervisor checks restoration and diff.
- [ ] **G2d, entities hook:** add failing fixture for one actual NPC or venue ID; then apply only the corresponding `osm/place_items.py`/venue-stage hook. Check location changed only under fixture, unknown ID fails loudly, and the missing/empty edit reproduces baseline. Run `python test/edits_pipeline_test.py`, `python test/edits_test.py`, `python test/editor_test.py` plus relevant map tests. Supervisor checks all real outputs restored with matching hashes.

### G3 — Mission-data contract and validation, no gameplay yet (depends G0; after G2 if testing against regenerated assets)
**Owns:** new `docs/missions.json`, new `test/mission_data_test.py`, and a small validator in `test/`; no `game.js` yet. `items.json` is read-only.
- [ ] Write a failing validator test for duplicate mission ID, duplicate checkpoint ID, missing board/POI anchor, nonexistent `building_id`, point outside map bounds, and wrong reference to a non-optional prerequisite. Prove it passes for **one** representative existing home board. Do not invent map coordinates or change the total quiz-question requirement.
- [ ] Define the first schema explicitly, e.g. `{"id":"house-intro","steps":[{"id":"visit-house","kind":"interact","anchor":{"boardSpot":"house01"}}]}`. Use actual `items.json` board spots and building IDs verified in this task. Source definitions remain distinct from save-state IDs. Support only `interact`, `talk`, `collect` and `minigameComplete` if there is an immediate test/user requirement; otherwise begin with `interact`. Bad references fail with a clear identifier, never vanish silently.
- [ ] Run `python test/mission_data_test.py` (RED then GREEN), `python test/quiz_expansion_test.py` against the local test server if needed, and existing map/editor validation. Supervisor approves the real schema **before** runtime changes. Do not bulk-create 21 missions in this card.

### G4 — Small runtime for one outdoor checkpoint, behind existing hooks (depends G3)
**Owns:** new `docs/js/missions.js`, minimal script include in `docs/index.html`, narrow integration in `docs/js/game.js` only if the existing `ARK`/`HOOKS` interface cannot provide save-state access; new `test/mission_runtime_test.py`.
- [ ] Add failing browser tests: interact near the known board only once; repeated interactions do not duplicate a checkpoint; walking near without interaction does not count; another home board does not complete the checkpoint. Verify dialogue/quiz still wins interaction priority as documented by `game.js:707–714` (NPC, then hooks, then POI).
- [ ] Load **one** validated definition via `fetch('missions.json')` from the `docs/` public root (confirm URL resolution against the actual page before editing). Register `HOOKS.near` and `HOOKS.questLog` at `ark-ready` following `features.js`/`minigames.js`; progress key is checkpoint ID rather than board index or displayed label. Persist through the narrow save-state bridge defined in G5; until G5, a test-only in-memory checkpoint may be used, but do not release save-dependent gameplay.
- [ ] Run `node --check docs/js/missions.js`, `python test/mission_runtime_test.py`, `python test/quiz_expansion_test.py`, `python test/quest_test.py`; supervisor checks no legacy branch was replaced and both Polish/English UI show sensible text or existing fallback. No universal scripting language or generic room engine.

### G5 — Versioned save compatibility and checkpoint persistence (depends G4; complete before publishing G4)
**Owns:** `docs/js/game.js`, `docs/js/missions.js` save bridge, new `test/save_migration_test.py`. No reset of the existing `SAVE_KEY`.
- [ ] Build isolated localStorage fixtures for: existing v1 shape with `Q.kasia`, quiz flags, `Q.mg` records, NPC positions and name; new shape with one completed checkpoint; missing/corrupt optional mission state. Add failing tests for loading, one reload round-trip, old progress intact, and preserving unknown safe future mission IDs if the store is re-saved. Tests must not clear a real user's browser storage.
- [ ] Add a version field to new payloads; missing version denotes the legacy format. Normalize new mission fields without mutating legacy `Q` quest fields. Invalid optional mission data falls back safely while valid legacy fields remain. Keep the old storage key and avatar/location semantics (`game.js:233–248`). Define and test exactly how future saves are treated (read-only warning or graceful fallback, never silent destructive overwrite).
- [ ] Run `python test/save_migration_test.py`, `python test/mission_runtime_test.py`, `python test/quest_test.py`, `python test/minigames_test.py` and `node --check docs/js/game.js`. Supervisor checks a real-ish fixture's before/after JSON diff and that existing saves are not destroyed by a reload.

### G6 — First complete house mission, then pause for Tomek (depends G2–G5)
**Owns:** `docs/missions.json`, `docs/js/missions.js`, focused tests and only the minimum existing UI/asset files actually required by the chosen house. No mass-population of homes.
- [ ] Pick one home with a real, reachable existing board (confirm its `building_id`, collision and nearby competing NPC interactions). Agree on short Polish/English copy and reward with Tomek; avoid unverified claims about the residents of real houses. Write a failing Playwright scenario: start mission, activate checkpoint, finish it, see quest HUD, reload, revisit and verify no double award.
- [ ] Implement the minimal object/indicator and quest copy at this outdoor spot; preserve existing optional quiz and normal traversal. Run the new scenario, `python test/quest_test.py`, `python test/quiz_expansion_test.py` and full `python test/run_all.py` locally. Check keyboard/touch; provide before/after screenshots and actual test log to Tomek.
- [ ] **Approval gate:** Tomek checks the feel of the first house mission and asset. If rejected, revise that pilot rather than duplicating it. After approval, define repeatable content addition as one independent task **per house/micro-batch**, each with validator + smoke test. Interiors get their own separate specs only if a chosen mission requires one.

### G7 — Local competition foundation (separate later milestone; not required for G6)
**Owns:** `docs/js/minigames.js` and focused test; only introduce `docs/js/local-competition.js` if G8 needs it. No change to overworld movement.
- [ ] Write failing tests for a minigame session with participants `p1` and `p2`: per-participant names/keys/results, repeated keydown (`event.repeat`) not counted as a fresh press, releasing and pressing again counts, keys outside the assigned set ignored, no accidental Space/Escape leaking to world movement. No invented second `P` overworld avatar.
- [ ] Define a narrow session/result schema distinct from `Q.mg[type]`'s legacy single-player record; decide per-session vs stored local names before implementation. Preserve old record semantics and touch/single-player paths. Tests should assert that the winner comparator is explicit for time-based vs hit-based games.
- [ ] Run focused competition tests plus `python test/minigames_test.py`, `python test/character_selection_test.py`; supervisor approves input ownership and no regression in normal controls. This is a foundation, not the simultaneous game yet.

### G8 — One two-person mash-to-run prototype (depends G7; only after separate approval)
**Owns:** one new competition minigame and focused Playwright test in `test/`, minimal registration/UI glue. Do not retrofit all existing minigames.
- [ ] Test two distinct key bindings (e.g. `KeyA`/`KeyL` only if keyboard tests confirm that mapping); both lanes progress independently on key release→press edges, `event.repeat` cannot accelerate, tie is deterministic, Escape aborts without posting a result, retry resets both lanes. Verify one player can enter the minigame from the existing overworld; after exit the hero is still alone on the map.
- [ ] Implement only that prototype. Check simultaneous input on a physical keyboard for ghosting limitations and provide a remapping/fallback decision to Tomek. Test both keyboard and existing single-player/touch paths; capture a playable video or screenshots if useful. Do not claim fair competition across all keyboards without manual verification.
- [ ] Run focused browser test and full local runner. Tomek approves or redirects gameplay before porting participant logic to another minigame.

### G9 — Release and future integration gates (supervisor; never automatic)
- [ ] Re-run `git diff --check`, changed-file syntax checks, all focused tests, and full `python test/run_all.py`; check screenshots, browser console and that `osm/edits.json`/generated outputs are coherent. Compare initial dirty worktree; exclude private references, caches and unrelated raw assets. Record exact tested HEAD and changed-file set.
- [ ] Update `PLAN.md`, `HANDOFF.md` and existing test-count statements **only with verified current results**. Seek Tomek's explicit permission before committing, pushing or deploying; if deployed, verify exact published build and local/live differences.

## Deferred, not currently authorized

- **Nostr leaderboard:** design a distinct result event schema with game/version/run ID, pubkey, comparator, deduplication and local fallback; determine moderation and trust model. Existing Nostr chat (`docs/js/chat.js`) is not score validation; a signed client-generated event can still contain a false result. Decide whether community/honor-system ranking is acceptable before any leaderboard task.
- **More interiors:** build a reusable room registry only when at least two new interiors share real transition/scene behavior. Existing `church.js`/`shop.js` are not a mandate to create 21 room maps.
- **Assets:** A0 review sheet → Tomek's labels → approved style anchors → one house/one tree trial → controlled regeneration. Follow `plans/2026-09-28-asset-style-roadmap.md`; never expose human reference photos. Coordinate G2/E2's generator lock with A-series changes.
- **Incoming requirements:** append new user requests to the approved scope, place each as a narrow card with explicit prerequisites and tests, and re-order **before starting** affected tasks. Keep completed cards' contracts stable unless Tomek explicitly asks to change them.
