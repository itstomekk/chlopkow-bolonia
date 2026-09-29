# Map editor — design and worker task list

Status: editor core, server, UI and tools implemented and pushed (commit `43db4e2`,
`editor/README.md`); tests `test/edits_test.py` 24/24 and `test/editor_test.py` pass.
**Still to do: E2 generator hooks** (render/place_items applying `osm/edits.json`) and
game-side zones (music areas, animal/people spawn areas) in later versions. Satellite
tiles in `editor/basemap/` may be committed (Tomek approved public imagery in repo).

Original status: planned. Requested by Tomek on 2026-09-28 after comparing a
Google aerial screenshot with the game map around the road/river crossing at (949,4665):
riverside tree rows in the game are too dense, real copses sit where the game has open
meadow, and the big dark wood east of the crossing does not exist there.

Goal: a local, comfortable editor for fixing the generated map against reality (trees,
woods, water, collision, positions of NPCs/venues), built so it never blocks ongoing
game work and so new tools/layers can be added later with little friction.

## 1. Architecture decisions (binding for all workers)

1. **The map stays generated.** `osm/render_map.py` + `osm/place_items.py` remain the only
   producers of `docs/map.json`, `docs/items.json` and `docs/img/map_*.png`. The editor never
   paints the PNGs directly; hand-painted pixels would be erased by the next render.
2. **Edits are data, applied on top of OSM.** All manual changes live in one file,
   `osm/edits.json` (committed). The render pipeline reads it and applies it at fixed hook
   points. Empty/missing `edits.json` must reproduce today's output exactly.
3. **Geographic coordinates are canonical.** Every edit stores `lat`/`lon` (points and
   polygon vertices), never raw art pixels. The bbox has already changed twice
   (`legacy_i`, `pre_expansion_i`); lat/lon edits survive the next resize for free. The
   editor shows and accepts game x/y (and sector) and converts via the same formulas as
   `osm/geo.py` (`P`, `to_latlon`), ported 1:1 to JS and covered by a parity test.
4. **The editor is outside `docs/`.** It lives in `editor/` at project root, so GitHub Pages
   never publishes it and the public game gains no code, weight or risk. It is served by a
   small local stdlib server that also serves `docs/` read-only, so it reuses the real game
   assets and `map.json`.
5. **Zero changes to game runtime.** Workers do not touch `docs/js/*.js` or
   `docs/index.html`. Pipeline integration is limited to a few one-line hook calls in
   `render_map.py` / `place_items.py`; all logic sits in `osm/edits.py`. This keeps merge
   conflicts with parallel gameplay/map work minimal.
6. **Extensible by registry, both sides.**
   - Python: `osm/edits.py` has `LAYERS = {name: LayerSpec(validate, apply_hook, stage)}`.
     A new edit type = one schema entry + one apply function registered to a stage.
   - JS: `editor/tools/*.js` each call `Editor.registerTool({id, label, key, layer,
     cursor, onPointerDown/Move/Up, drawOverlay, panel})`. The core never hardcodes tools.
     New feature = new file + one `<script>` line in `editor/index.html`.
7. **Schema is versioned.** `edits.json` has `"version": 1`; `edits.py` migrates older
   versions forward. Unknown layers are preserved (not dropped) with a warning, so an older
   editor cannot destroy data written by a newer one.
8. **Satellite imagery is a private local aid.** Basemaps (Esri World Imagery export,
   Geoportal ORTO WMS when reachable, user screenshots) are fetched/cached only under
   `editor/cache/` (gitignored). No imagery is committed or shipped. Attribution shown in
   the editor UI.

## 2. `osm/edits.json` v1 format

```json
{
  "version": 1,
  "meta": {"updated": "2026-09-28T12:00:00Z", "note": "free text"},
  "layers": {
    "trees":     {"add": [{"lat": 0, "lon": 0, "r": 11, "dark": false}],
                  "clear": [{"poly": [[lat, lon], ...]}]},
    "forest":    {"add": [{"poly": [[lat, lon], ...]}], "remove": [{"poly": [...]}]},
    "water":     {"add": [{"poly": [...], "name": "Staw Strażacki"}]},
    "collision": {"block": [{"poly": [...]}], "free": [{"poly": [...]}]},
    "entities":  {"npc:soltys": {"lat": 0, "lon": 0},
                  "venue:football_pitch": {"lat": 0, "lon": 0, "w": 110, "h": 190},
                  "landmark:bus_budka": {"lat": 0, "lon": 0}}
  }
}
```

Semantics and pipeline stage for each layer:

| Layer | Meaning | Stage in `render_map.py` / `place_items.py` |
|---|---|---|
| `forest.add/remove` | OR / AND-NOT into `forest_mask` | right after `forest_mask = mask_of(...)` |
| `trees.clear` | drop generated `tree_pts` inside polygon (river rows, gardens, orchards) | after tree candidates, before thinning |
| `trees.add` | explicit trees, always kept (skip thinning), still avoid roads/buildings | same place |
| `water.add` | pond fill + collide 255, walkable margin kept | with ponds, before roads |
| `collision.block/free` | final override of collide values | just before collide PNG is saved; roads stay free |
| `entities.*` | position/size override of NPC spawn anchors, venues, landmarks | venues in render, NPCs/landmarks in `place_items.py` |

Rules: roads/tracks always stay walkable; overrides that make a quest target unreachable
must fail the build with a clear message (existing flood-fill asserts in `place_items.py`).

## 3. Worker tasks (in order)

Model: GPT Luna for implementation tasks; Sol (or the orchestrator) plans, reviews,
integrates and deploys. Check the current Luna model id before launching
(`gpt-5.6-luna` returned 404 on 2026-09-28; delegation used `gpt-6-luna-900k`).

Every worker brief must include: project path
`C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie`, this file, the file ownership
line, "test first (RED→GREEN)", "no commit/push/deploy", "do not touch files outside
ownership", "report exact commands and outputs". Map rebuilds are serialized: only one
worker at a time may run `render_map.py` (they rewrite shared generated files).

### E1 — edits core (Python, no pipeline changes)
- Owns: `osm/edits.py`, `test/edits_test.py`, `osm/edits.example.json`.
- Build: load (missing file = empty), validate v1 schema with readable errors, migration
  stub, preserve unknown layers, lat/lon↔art px via `geo.py`, polygon→numpy mask in a
  window (reuse the `mask_win` approach), `LAYERS` registry and `apply(stage, ctx)`.
- Tests: validation errors, round-trip, unknown-layer preservation, geo conversion
  against `geo.P`, mask of a known square.
- Done when: `python test/edits_test.py` passes; no other file changed.

### E2 — pipeline hooks (depends on E1; exclusive lock on `osm/render_map.py`, `osm/place_items.py`)
- Owns: one-line hook calls in `render_map.py` and `place_items.py`,
  `test/edits_pipeline_test.py`, fixture `test/fixtures/edits_sample.json`.
- Add `EDITS = edits.load(os.environ.get('ARK_EDITS', 'osm/edits.json'))` and
  `edits.apply('<stage>', locals-like ctx)` at the stages in section 2.
- **Baseline gate:** before editing, render with current code and store SHA-256 of
  `map.json`, `items.json`, the three PNGs in the scratch dir; after hooks with empty
  edits, hashes must match exactly.
- Fixture test (render into a temp output via `ARK_EDITS` + an output-dir env or by
  backing up/restoring `docs/` files): tree add appears in `objects` and collide, `clear`
  removes river-row trees in the polygon, forest add changes ground, water add collides,
  `npc:soltys` override moves him, unreachable override fails loudly.
- Must restore the real generated files at the end and prove it with hashes.

### E3 — local editor server (depends on E1; parallel with E2)
- Owns: `editor/server.py`, `test/editor_server_test.py`, `.gitignore` line for `editor/cache/`.
- stdlib `http.server`, bind `127.0.0.1` only, port 8770 default.
- Routes: `/` → `editor/index.html`; `/game/*` → `docs/*` read-only;
  `GET /api/edits`; `PUT /api/edits` (validate via `edits.py`, atomic write via temp file +
  rename, keep last 20 backups in `editor/cache/history/`); `POST /api/rebuild` (runs
  `render_map.py` then `place_items.py`, one at a time with a lock, returns exit code +
  log tail); `GET /api/basemap?src=esri&bbox=...&w=&h=` (fetch + disk cache, timeout,
  clean error when offline); `GET /api/geo` (bbox, W, H, A, MX, MY from `geo.py`).
- Tests with urllib against a live instance: path traversal blocked, invalid edits → 400
  and file unchanged, concurrent rebuild → 409.

### E4 — editor UI shell (depends on E3)
- Owns: `editor/index.html`, `editor/editor.css`, `editor/core.js`, `editor/geo.js`,
  `test/editor_ui_test.py`.
- Canvas viewer: pan (drag / space), zoom (wheel, 0.1×–4×), loads `map_ground.png`,
  `map_objects.png`, optional collide overlay; layer toggles; basemap with opacity slider;
  readout of x/y, lat/lon, sector (500 px grid, same scheme as the game plan).
- Core services for tools: `registerTool`, command stack with undo/redo (Ctrl+Z/Y),
  dirty flag, save (PUT), rebuild button with log panel and image reload after success,
  "Zagraj tutaj" opening `/game/index.html?x=..&y=..`.
- `geo.js` parity test: 20 random points JS vs Python `geo.py` within 0.01 px.
- Overlay drawing of existing edits from `edits.json` (so edits are visible before rebuild).

### E5 — tools (depends on E4; one worker per tool, parallel, each owns only its file + test)
- `editor/tools/trees.js`: click to add tree (radius slider, dark toggle), lasso "clear
  generated trees here", right-click removes an added tree.
- `editor/tools/forest.js`: polygon draw for add/remove, vertex drag, delete.
- `editor/tools/water.js`: polygon pond with optional name.
- `editor/tools/collision.js`: block/free polygons, red/green overlay.
- `editor/tools/entities.js`: drag NPC/venue/landmark markers from `items.json`/`map.json`,
  writes `entities.*`; warns when target is on collision.
- Each tool test: Playwright draws a shape, saves, asserts resulting `edits.json` content.

### E6 — reference overlay and first real use (depends on E5)
- Owns: `editor/tools/refimage.js`, test.
- Drop a screenshot (e.g. Google Maps), click 2 points on it and the same 2 points on the
  map → similarity transform (scale, rotation, offset); opacity; stored only in
  `editor/cache/refs/`. This solves the "unknown scale" problem of user screenshots.
- Acceptance scenario (with Tomek): around the crossing (949,4665) thin the riverside tree
  rows, add the real copses north and south of the river, remove the non-existent wood
  east of the crossing; rebuild; `test/run_all.py` passes; Tomek approves visually.

### E7 — docs and release gate (orchestrator)
- `DEVELOPMENT.md`: how to run `python editor/server.py`, workflow edit → save → rebuild
  → play → commit `osm/edits.json` + regenerated files.
- `HANDOFF.md` pointer, full `python test/run_all.py`, `git diff --check`, confirm
  `editor/cache/` and imagery are not staged; then normal deploy flow.

## 4. Later features (not scheduled)
- Ground paint layer (field/grass/road/yard types) that also feeds terrain walking speeds.
- Auto-suggest tree canopy from orthophoto (NDVI/CIR when Geoportal works) as a
  candidate layer to accept/reject, never auto-applied.
- Quiz boards, apples, mushrooms, trash spawn zones, animal habitats as entity layers.
- Road graph / NPC traffic waypoints for the planned people and cars on roads.
- Buildings: hide/add generic houses, mark shop/school footprints.
- Multi-user: none planned; single local editor, git is the sync.
