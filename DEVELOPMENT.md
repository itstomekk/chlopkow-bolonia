# Development

This document keeps the technical notes for CHŁOPKÓW POLONIA (the repository and its GitHub Pages address keep the older `chlopkow-bolonia` name on purpose). The game runs in a modern browser on desktop or phone. Its game logic is plain JavaScript without a build step. Entering play starts the Nostr arrival log and loads pinned nostr-tools from a CDN, even if the chat panel is minimized. The name form explains that the name and arrival become public.

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
  js/minigames.js        ← pig / dogs / shooting gallery / ducks / mowing: medals, records, retry (plugs into HOOKS)
  js/scores.js           ← ARK.scores client for the shared Cloudflare game server (global best / recent / average, averaged CPU traces)
  js/board.js            ← shared full-screen board framework: map flag, 4-player lobby, input, loop, results and local records
  js/boards/sprint.js    ← BIEG NA 100 METRÓW: alternate left/right on asphalt + grass; PRZECIĘTNIAK replays last-200 global mean
  js/quiz.js             ← the 13 quiz questions (PL/EN), each bound to a map spot
  js/church.js           ← church interior room (drawn in code from reference photos, AI sprites auto-load from img/church/) + Sołtys
  js/crypt.js            ← secret crypt under the church (room drawn in code), the confessional cipher + cryptex overlay, sign-order puzzle, hidden chamber
  js/passages.js         ← PASSAGES engine (the only eager passage file): registry, gate evaluator, lazy loader, village-side slab, portal checks
  js/underground-tunnel.js ← LAZY: the church-cemetery tunnel room (drawn in code); fetched on first need, never listed in index.html
  data/passages.json     ← passage registry (ids, endpoints, gates, lazy module/data paths); data/tunnel-church-cemetery.json ← LAZY: tunnel layout + PL/EN lore
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

### Wapnica (dump decal, roadside track)

Wapnica is a hand-placed GPT Image pixel-art ground decal (`gen/wapnica/ground.png`, see `gen/wapnica/README.md`) laid on the
satellite-traced outline `local_features.json` id -9000020. There is no separate Wapnica track any more: the decal sits next to the existing dirt road (OSM way 1102348330). `render_map.py` was changed so that
**the rest of the map stays identical to the layout released before the decal** (commit 40c9aa3): a re-render now differs from it
only inside `WAP_REGION` (printed as `wapnica region`, about x 492-981, y 2068-2580). How that is kept:

- **Random streams.** Placement and `rnd` consumption still read the old footprint: id -9000022 (`ark:keepout`, never drawn) is the
  former dump outline and keeps trees/bales/props off it, `dm_old` is the dirt-road mask without the new track, and the shrine
  anchor uses the old centre. Trees or bales that would land on the new decal (`WAP_ZONE`) are drawn and then undone (or dropped
  after their random draws), so no later tree, forest species, bale or item moves.
- **Palette.** `osm/quantize_ground.py` keeps the released palette indices of `map_ground.png` outside the region and maps the region
  through the released RGB -> index table; the decal's 8 colours use palette slots the released image left empty. It reads the baseline
  from git (`BASE_REF`), so it needs full history; without it the old global MEDIANCUT runs and the whole ground is recoloured slightly.
- **Items.** `osm/pinned_items.json` pins Damian's cap: its wheat-pixel scan is strided in row order, and the decal sits in a wheat field,
  so without the pin the cap jumps across the map. The Wapnica landmark access point is the only other item that moves.
- **Position.** `WAP_SHIFT = (-32, -83)` in `render_map.py` is one rigid translation of the whole group (decal, three heaps, skip, the
  `wapnica` landmark/access point, the `gravel` venue); the keep-out -9000022 is deliberately NOT shifted. It came from a least-squares
  fit of the removed roadside track onto the existing road: 60 px perpendicular to the road (vector 27,-54; the track was ~9.5 deg flatter
  than the road, so rms residual 13 px, max 24 px along the decal), plus a 66 px slide west along the road (does not change the fit) so
  the decal leaves the two oaks that stood beside the old track. The decal's top edge is still 43-73 px (about 20-35 m) below the road
  centreline, because the removed track lay about that far above the decal; shift the decal ~45 px up-right to make it touch the road.
- Expected diff against 4999177 (the pre-alignment release) after `render_map.py` + `place_items.py`: `map_ground.png` x 580-916, y 2165-2477
  (43,699 px); `map_objects.png` x 634-856, y 2224-2392; `map_collide.png` x 638-851, y 2241-2393; `map_terrain.png` x 145-228, y 548-575
  (the dirt-track class 100 of the removed track); `map.json` only the 4 shifted Wapnica props (3 heaps, skip), `gravel` and the `wapnica` landmark;
  `items.json` only the `wapnica` landmark. Nothing else moves: no tree, bale, apple, NPC, board or cap.
- Expected diff against 40c9aa3 (before any decal): `map_ground.png` x 589-893, y 2165-2492; `map_objects.png` x 634-874, y 2224-2442;
  `map_collide.png` x 638-869, y 2241-2443; `map_terrain.png` identical; `map.json` the Wapnica props, `gravel` and the landmark;
  `items.json` only the landmark. When the Wapnica map is itself the baseline, set `BASE_REF` to the commit that contains it.

## Local testing

Run `python -m http.server 8765 --directory docs`, then open http://127.0.0.1:8765.
It has to be served over HTTP, because opening `index.html` from disk blocks `fetch`.

Automated play-tests use Playwright and headless Chromium. The server must be running:

```bash
python test/run_all.py                       # every test below, with a summary
python test/run_all.py https://itstomekk.github.io/chlopkow-bolonia/   # against the live site
```

`quest_test` (main quest), `jump_test` (river jump), `features_test` (quiz), `minigames_test` (all four games, medals, retry, ghost),
`church_test`, `crypt_test` (confessional riddle, cryptex, crypt, reload mid-crypt), `tunnel_test` (loose brick, lazy-loaded tunnel, cemetery slab shortcut, room stack, gates, load failure), `frodo_test`, `soltys_surprise_test`, `cemetery_memories_test`, `village_sign_test`, `play_test`, `branding_flow_test` (title sequence: pixel reveal, name + character picker, sign phase, reduced motion), `site_metadata_test`.

The full runner isolates public Nostr sockets and disables the CDN module for every browser, so test names never enter the public arrival history. For individual regressions use `python test/isolated_browser_runner.py test/branding_flow_test.py`; `arrival_log_test.py` overrides the disabled module with a controlled transport and tests submission, history, deduplication, retries and mobile disclosure. A successful controlled transport is not proof of persistence on public relays.

### Passages engine (secret tunnels and doors)

A *passage* links two places and is data, not code in `game.js`. Everything lives in `docs/data/passages.json` (registry, fetched at startup, tiny) plus two lazy files per passage.

- **Add one:** (1) append an entry to `passages.json`: `id`, `kind`, `module` (lazy JS), `data` (lazy JSON), `seen` (optional Q flag set on first use), `gate`, and `ends{name:{room, mouth|poi, arrive, gate, visible, slab, surface}}`. (2) Write `js/<kind>.js` that calls `PASSAGES.defineKind('<kind>', { build(def, data, ctx) { return room; } })`; the room has the usual crypt-style shape plus `spawns{endName:{x,y,dir}}` and `portals[{rect, go}]`, and optional `interact(poi, api)`, `tick(dt)`, `labelKey`. (3) Put layout and PL/EN strings (`text:{pl:{},en:{}}`, merged into `ARK.T` on load) in the data file. (4) Hook the physical entrance: an indoor room publishes `room.openPassages[id] = true` and the registry `mouth` rect (walking into it calls `PASSAGES.enter`); an outdoor end uses `slab` + `visible` (a `HOOKS.near` + `HOOKS.world` pair, invisible until `visible` passes). (5) Add a case to `test/tunnel_test.py`.
- **Gates** (`PASSAGES.gate(descriptor)` -> `{open, reason}`): `always`, `flag` (`Q[key]`), `all`, `any`, `not`, and two documented stubs, `quiz` and `mission`, that stay locked with a `TODO` reason until wired (`PASSAGES.defineGate('quiz', fn)`). `gate` decides whether a passage can be used; `visible` decides whether its village-side marker exists at all, so there are no spoilers.
- **Lazy loading rules:** only `passages.js` and `passages.json` are eager. The module and data are fetched on first need (a gating event such as the loose brick or the slab calls `PASSAGES.preload(id)`, `enter` calls `load`), the promise is cached, a failure shows the `passageFail` toast, is not cached (retry works) and never throws into the game loop. `PASSAGES.state()` reports registry, load status, scripts and data for tests. Keep one canvas under about 2000 px tall and draw per segment.
- **Room stack** (`game.js`, `ARK.rooms`): `OUT` is always the village; `STACK` holds the rooms above the current one (church -> crypt -> tunnel = `[church, crypt]`). `rooms.descend(room, at, back)` pushes, `rooms.ascend(roomId, at)` pops (and rebuilds the church/crypt chain when the player arrived from the village), `rooms.surface(x, y, dir)` clears the stack and puts Arek in the village. `leaveRoom()` pops one level, so church and crypt exits behave as before. A room with no `exit` has no plain exit; saves written at any depth hold the village door, so a reload never strands Arek.

### Public village arrival log

`game.js` dispatches `ark-player-arrived` after a named player enters play. `chat.js` queues one notice per loaded document, signs a NIP-28 kind-42 event in the existing chat channel with `arrival=v1` and a random `session` tag, and renders it as a turquoise timestamped line alongside normal messages. Returning from a dialogue or reopening the panel does not create another visit; reloading and entering again does. The arrival log is history, not an online-player count. Publication never blocks play. A failed write reuses its event on online/reconnection/manual reopen, with at most three attempts; no local success row is inserted before relay acceptance. Public relays control retention, and guest names are self-reported, not authenticated real-world identities.

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
