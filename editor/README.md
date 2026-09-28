# Map editor — Chłopków Bolonia

A local tool for correcting the game map by hand: trees, woods, water, collision, positions
of characters and minigames, and zones (music, animals, people). It runs on your computer
and is **not part of the published game** — GitHub Pages serves only `docs/`.

## Why it exists

The game map is generated from OpenStreetMap by `osm/render_map.py` and
`osm/place_items.py`. OSM does not know where every tree, copse or pond in Chłopków is,
so the generator guesses some of it. Painting over the generated PNGs by hand would be
erased by the next render. Instead, the editor stores corrections as **data** in
`osm/edits.json`, and the generator applies them on top of OSM on every render.

- Coordinates are saved as **lat/lon**, not game pixels, so edits survive future map
  resizes (the map has already been enlarged twice).
- An empty or missing `osm/edits.json` means the map is exactly what OSM produces.

## Run it

```bash
python editor/server.py                   # http://127.0.0.1:8770/
python editor/server.py --allow-rebuild   # also enables the "Przebuduj mapę" button
```

Needs Python 3 with numpy and Pillow (already required by the map generator). The server
binds to `127.0.0.1` only.

## What you can do

| Tool | Key | Writes to `edits.json` |
|---|---|---|
| Rączka (pan) | 1 | – |
| Drzewo — add a single tree, right-click removes | 2 | `trees.add` |
| Usuń drzewa — area where generated trees are dropped | 3 | `trees.clear` |
| Las + / Las − — add or remove woodland | 4 / 5 | `forest.add` / `forest.remove` |
| Woda — pond with collision and optional name | 6 | `water.add` |
| Blokada / Przejście — collision override (roads always stay walkable) | 7 / 8 | `collision.block` / `collision.free` |
| Strefy — music / animals / people / custom zones with JSON props | 9 | `zones.items` |
| Postacie — drag NPCs, landmarks and minigame venues | – | `entities["kind:id"]` |
| Obraz — overlay your own screenshot, calibrate it with 2 point pairs | – | nothing (stays in the browser) |

Layers: game map, buildings/trees, collision, edits, entities, sector grid (A1…, 500 px
cells), satellite basemap with opacity (`esri`, `geoportal`), own reference image.

Shortcuts: wheel = zoom, right/middle drag or Space+drag = pan, Enter/double-click = close
polygon, Backspace = remove last point, Delete = remove selected, Ctrl+Z / Ctrl+Y =
undo/redo, Ctrl+S = save, P = open the game at the cursor, C = copy coordinates, ? = help.
The position box accepts `x,y`, `lat,lon` or a sector like `B10`.

## Workflow

1. Edit, then **Zapisz** (Ctrl+S). The server validates and writes `osm/edits.json`; the
   previous version goes to `editor/history/` (last 30, not committed).
2. **Przebuduj mapę** (with `--allow-rebuild`) runs the generator, which rewrites
   `docs/map.json`, `docs/items.json` and `docs/img/map_*.png`.
3. **Zagraj tutaj** opens the game at that spot to check it.
4. Commit `osm/edits.json` together with the regenerated files.

## Status

| Part | State |
|---|---|
| `osm/edits.py` — format, validation, lat/lon geometry, stage appliers | done, `test/edits_test.py` |
| `editor/server.py` — API, basemap tiles, history, rebuild | done |
| Editor UI and all tools above | done, `test/editor_test.py` |
| **Generator hooks** (render/place_items actually applying edits) | **not yet** — edits are saved but do not change the map until this lands |
| Zones read by the game (music changes, animal/people spawns) | planned, next versions |

Plan and ordered tasks: `plans/2026-09-28-map-editor.md` (local).

## Extending

- **New edit type:** add a `LayerSpec(validate, stage, apply)` entry to `LAYERS` in
  `osm/edits.py`, then a tool file. Unknown layers are preserved, so an older editor never
  deletes data written by a newer one.
- **New polygon tool:** add one entry to `TOOLS` in `editor/tools/polygons.js`.
- **New tool of any kind:** new file in `editor/tools/`, call `Editor.registerTool({...})`
  (interface documented at the top of `editor/core.js`), add one `<script>` line to
  `editor/index.html`.
- **New zone kind:** add it to `ZONE_KINDS` in `osm/edits.py` and a colour in `polygons.js`.

## `osm/edits.json` format (v1)

```json
{
  "version": 1,
  "meta": {"updated": "2026-09-28T12:00:00Z"},
  "layers": {
    "trees":     {"add": [{"lat": 52.2639, "lon": 22.8655, "r": 11, "dark": false}],
                  "clear": [{"poly": [[52.26, 22.86], [52.26, 22.87], [52.25, 22.87]]}]},
    "forest":    {"add": [{"poly": [...]}], "remove": [{"poly": [...]}]},
    "water":     {"add": [{"poly": [...], "name": "Staw Strażacki"}]},
    "collision": {"block": [{"poly": [...]}], "free": [{"poly": [...]}]},
    "entities":  {"npc:soltys": {"lat": 52.27, "lon": 22.87}},
    "zones":     {"items": [{"id": "jazz-w-stodole", "kind": "music", "poly": [...], "props": {"track": "jazz"}}]}
  }
}
```

## Tests

```bash
python test/edits_test.py    # format, validation, geometry, stage appliers
python test/editor_test.py   # server API + browser UI; uses a temp edits file, never touches the game
```

## Imagery

Satellite tiles are fetched on demand and cached in `editor/basemap/<source>/bbox_<map bbox>/`.
The cache is keyed by the map bbox, so after the map is extended the editor fetches a
fresh, correctly aligned tile set automatically.

The editor reads the map size and bbox from `osm/geo.py` at start (`/api/geo`) and edits
are stored in lat/lon, so extending the map (e.g. further south or east) needs no editor
change: existing edits stay on the same real-world spot.
Esri: Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community.
Geoportal: Ortofotomapa © GUGiK. Both are shown as the basemap source hint in the UI.
