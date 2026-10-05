# Development

This document keeps the technical notes for CHŁOPKÓW POLONIA (the repository and its GitHub Pages address keep the older `chlopkow-bolonia` name on purpose). The game runs in a modern browser on desktop or phone. Its game logic is plain JavaScript without a build step; the optional chat loads nostr-tools from a CDN after opt-in.

## Controls

| Action | Keyboard | Touch |
|---|---|---|
| Walk | Arrows / WASD or click a destination | drag anywhere (virtual joystick) |
| Run | hold Shift | push the joystick to the edge |
| Talk / read | Space (next to someone or something) · E · Enter | **A** button |
| Jump | Space (when nobody is near) · X · J | **A** button |
| Quiz answer | 1–4 or arrows + Space | tap an answer |
| Minigame: retry / leave | R or Space / Esc | tap left / right half of the result panel |
| Shooting gallery: aim / shoot | mouse or arrows / Space or click | tap the target |
| Map | M | tap the minimap |
| Position | shown bottom-left: map x/y + latitude/longitude; start anywhere with `?x=1243&y=901` | — |
| New game | N on the title screen | — |

Progress saves automatically in the browser (localStorage).

## Project layout

```
docs/                    ← the game (GitHub Pages serves this folder)
  index.html
  brand-guidelines.html  ← visual brand guide (logo, wordmark, palette, opening sequence, usage rules)
  js/game.js             ← core: input, physics, NPC quests, rendering, extension HOOKS (commented)
  js/features.js         ← quiz UI + Babcia Irenka + question markers (plugs into HOOKS)
  js/minigames.js        ← race / pig / dogs / shooting gallery: medals, records, retry, race ghost (plugs into HOOKS)
  js/quiz.js             ← the 13 quiz questions (PL/EN), each bound to a map spot
  js/church.js           ← church interior room (drawn in code from reference photos, AI sprites auto-load from img/church/) + Sołtys
  map.json               ← map size, y-sortable objects, points of interest, minigame venues, spawn point
  items.json             ← NPC positions, apples, the cap, quiz signboards
  img/map_ground.png     ← ground layer (fields, roads, river, fences)
  img/map_objects.png    ← buildings, trees, bales, landmarks (drawn y-sorted with the characters)
  img/map_collide.png    ← collisions: 255 = tall (walls, trees, ponds), 128 = low (fences, streams, bales; jumpable)
  img/arek_sheet.png/.json ← Arek's walk-cycle atlas (4 directions; left is right mirrored)
  img/npcs.png           ← Kasia, Marcin, Damian, Grandpa, Irenka, Kuba
  img/frodo.png          ← Frodo's 4-direction, 2-frame walking atlas
  img/memories/          ← three keyed pixel-art cemetery archive illustrations
  img/animals.png        ← pig + dog run cycles (side, front, back)
osm/
  chlopkow.json          ← raw OpenStreetMap extract (Overpass API)
  local_features.json    ← real features missing from OSM (same format, negative ids), merged by render_map.py;
                           ponds/orchard/Wapnica dump outline traced from Esri imagery, cemetery grave_area polygons limit where graves go
  real_trees.json        ← real tree positions outside forests (fetch_trees.py); replaces random garden/riverbank trees
  fetch_trees.py         ← one-off: Meta/WRI 1 m canopy height × Esri imagery → real_trees.json (needs rasterio, see docstring)
  geo.py                 ← bounding box, scale and legacy-coordinate conversion shared by both scripts
  render_map.py          ← OSM → pixel-art map + collision mask + map.json
  place_items.py         ← places NPCs, apples, the cap and signboards on spots reachable on foot → items.json
gen/
  model_sheet_v1.png, walk_sheet_v1.png ← AI-generated sprite sheets of Arek (GPT Image, magenta background)
  lm_church.png, lm_windmill.png, lm_shop.png ← landmark sprites
  frodo_sheet_raw.png    ← GPT Image 2 sprite sheet based on local Frodo reference photos
  slice_sheet.py         ← chroma-key + slicing + feet-aligned atlas for Arek
  build_npcs.py          ← NPC atlas
  build_frodo.py         ← key and pack Frodo's 8-frame atlas into docs/img/frodo.png
  codex_gen.py / ppq_gen.py ← image-generation helpers (local tooling, need the author's accounts)
  brand/build_brand_assets.py ← brand sign: cuts gen/brand/emblem-source.png (GPT Image art with the pixel wordmark baked in), writes docs/img/chlopkow-polonia-*.png, the favicon and the share card
```

### Rebuilding assets

```bash
python osm/render_map.py      # map layers + map.json  (needs numpy, pillow)
python osm/place_items.py     # items.json
python gen/slice_sheet.py     # Arek atlas (needs scipy)
python gen/build_npcs.py      # NPC atlas
python gen/build_frodo.py     # Frodo atlas (needs numpy, scipy, pillow)
python gen/build_cemetery_memories.py  # key and pixel-grid the generated archive art
python gen/brand/build_brand_assets.py # logo lockup, favicon, share card (needs pillow, numpy, playwright)
```

## Local testing

Run `python -m http.server 8765 --directory docs`, then open http://127.0.0.1:8765.
It has to be served over HTTP, because opening `index.html` from disk blocks `fetch`.

Automated play-tests use Playwright and headless Chromium. The server must be running:

```bash
python test/run_all.py                       # every test below, with a summary
python test/run_all.py https://itstomekk.github.io/chlopkow-bolonia/   # against the live site
```

`quest_test` (main quest), `jump_test` (river jump), `features_test` (quiz), `minigames_test` (all four games, medals, retry, ghost),
`church_test`, `frodo_test`, `soltys_surprise_test`, `cemetery_memories_test`, `village_sign_test`, `play_test`, `branding_flow_test` (title sequence: pixel reveal, name + character picker, sign phase, reduced motion), `site_metadata_test`.

### Design notes

- **Scale:** 1 m = 2 art pixels. Buildings are enlarged around their centre (up to 2.3×) so they read well next to the characters, the usual RPG compromise. Each one shrinks automatically until it overlaps neither a road nor its neighbours.
- **Depth:** everything standing on the ground (buildings, trees, bales, apples, NPCs, Arek) is sorted by its baseline every frame, so Arek walks behind houses and in front of trees correctly.
- **Jumping:** a jump is about 0.5 s long and ignores low collisions. If Arek would land on a fence he glides a bit further; if it's still blocked he hops back to where he took off.
- **Title sequence:** `drawSplash` runs a clock (`openingT`) that only advances on the title screen: pixel reveal of `img/splash.png` (1.7 s), then the picker and a docked name form, then after 5.2 s the village dims and `img/chlopkow-polonia-logo.png` fades in. The sequence is cosmetic: it never auto-starts the game or steals focus on touch screens, and `prefers-reduced-motion` jumps straight to the final state (`__game.openingStage` exposes `reveal` / `selector` / `emblem` for tests).
- **Polish text:** dialogue is upper-cased because the Silkscreen pixel font draws lower-case Polish letters too small. The font also has no **Ć** glyph, so `game.js` draws it as a C plus a hand-drawn accent (a `fillText` wrapper).
- **Minigame venues** (track, corral, meadow, shooting range) are drawn by `osm/render_map.py` and exported in `map.json` (`track`, `corral`, `meadow`, `range`).
- **Resizing the map:** change `BBOX` in `osm/geo.py` and re-run both scripts. The oldest hand-placed spots use `legacy_i()`; user-supplied coordinates from the later 3897×2698 map use `pre_expansion_i()`.
- **Reachability:** roads and tracks are walkable across the river called Melioranka in-game; garden fences have gates, and `place_items.py` flood-fills from the spawn to check quest items.
- **Map size vs. phones:** current map width is 3896 px, height 5860 px. The 256-colour ground PNG exceeds 10 MB; tiling and mobile load-time checks remain future work.

## Wanted: reference photos

See [PHOTOS-WANTED.md](PHOTOS-WANTED.md). Real photos make the landmarks and characters look like the real thing.

## Credits and licences

- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL.
- Font: [Silkscreen](https://fonts.google.com/specimen/Silkscreen) by Jason Kottke, SIL Open Font License.
- Pixel art: generated with GPT Image, then keyed, sliced and composed with the scripts in this repo.
