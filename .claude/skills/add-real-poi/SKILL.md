---
name: add-real-poi
description: Add a real-world point of interest (from a Google Maps link, OSM id or lat/lon) to the Chłopków game map — resolve coordinates, check it falls inside the map BBOX, place it via add_poi / place_items, optionally give it a landmark sprite and a postcard. Use when Tomek pastes maps.app.goo.gl links or says "add this place to the map".
---

# Add a real point of interest to the map

## 1. Resolve coordinates
- Google short link: `curl -sS -o /dev/null -w '%{redirect_url}\n' https://maps.app.goo.gl/<id>`. The pin is the `!3d<lat>!4d<lon>` pair in the redirect URL. **Don't** use the `@lat,lon` value: that's the camera centre, not the pin.
- Look for the same place in `osm/chlopkow.json` (Overpass `out geom` format: `geometry` and `bounds` on ways). If OSM has a polygon (e.g. `leisure=pitch`), draw the polygon; don't just drop a point.
- OSM access: Overpass is blocked from the cloud container; the OSM API `https://api.openstreetmap.org/api/0.6/map.json?bbox=minlon,minlat,maxlon,maxlat` works, but returns the raw format (node refs). Overpass works on Tomek's PC.

## 2. Check it's inside the map
- `python -c "import sys; sys.path.insert(0,'osm'); import geo; print(geo.BBOX, geo.P(LAT, LON))"`: x in 0..W and y in 0..H means it's inside.
- If it's outside, BBOX must grow (`osm/geo.py`). `legacy_i()` keeps the old hand-tuned spots on their real places. Re-fetch the OSM extract for the new bbox, then re-render.

## 3. Place it
- Hotspot or label: `add_poi(key, lat, lon, ...)` in `osm/render_map.py`. Add dialogue text under `T.hot`/POI texts in `docs/js/game.js`, in both PL and EN.
- Sprite: `gen/lm_<key>.png` + `add_generated_sprite(name, cx, foot_y, width)`, with the width in `LM_SIZE`.
- NPCs, items and quiz boards: `osm/place_items.py`. It flood-fills from the spawn (the point must be reachable) and asserts that no NPC lands on a signboard.
- Re-run `python osm/render_map.py && python osm/place_items.py`, then `python test/run_all.py`.

## 4. Images (local PC only)
- References go in `references/poi/<key>/`, which is gitignored and **never committed**: Tomek's photos, his own Google Maps/Street View screenshots, Mapillary, or the Geoportal orthophoto.
- **Never upload photos of people to PPQ.** Use `gen/codex_gen.py` with local files.
- Log each prompt in `gen/PROMPTS-landmarks.md`.

## 5. Record it
- Add a row to the POI table in the current PLAN/HANDOFF (key, lat, lon, source link, OSM id, sprite status).

## Known points (2026-09-28)
kapliczka 52.265937,22.8658023 · Chata za wsią 52.2669308,22.8674792 · PPM Strzelectwo 52.2736642,22.867767 (OSM ways 1453546275, 1453549547) · świetlica 52.2641139,22.8754946 · Cmentarz 52.2685251,22.8772688 (OSM way 318005531).
