# Arek w Chłopkowie

A small top-down pixel-art adventure set in the real village of **Chłopków** (gmina Platerów, powiat łosicki).
The map is generated from OpenStreetMap data, so roads, the Białka river, fields, woods and every building
sit where they really are. It covers about 1.95 × 1.35 km: the whole main street, the church quarter, the
riverside farmsteads in the west and Chłopków-Kolonia in the east. It's a prequel to the short film *Grand Theft Tractor*.

**Play:** https://itstomekk.github.io/arek-w-chlopkowie/ (`?lang=en` for English)

It runs in any modern browser, desktop or phone. The game is pure JavaScript with no libraries and no build step.

## Controls

| Action | Keyboard | Touch |
|---|---|---|
| Walk | Arrows / WASD | drag anywhere (virtual joystick) |
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

## What you do

- **Kasia** (far east, in Chłopków-Kolonia) needs **10 apples** for her apple pie. They grow in the orchard in the south and in the gardens along the main street.
- **Damian** (far south, at a farmstead by the village sign) lost his **cap** somewhere in the wheat near him.
- **Marcin** (at the bus stop) wants an **orangeade** from the shop.
- **Grandpa Zbyszek** (by the Koźlak windmill) hands over the **keys to his Ursus** once the whole crew has been helped.
- **Frodo**, Arek's black-and-tan dog, follows him around the village and into the church.

On the way you can jump over garden fences, hay bales and the Białka river.

**The church can be entered:** walk up to its door and press Space/E. Inside is the nave with its pews, the altar, stained glass,
Our Lady's niche and the "100" flowers for the parish centenary. The **Sołtys** (village head) waits by the ambo with the harvest bread. Walk out through the door at the bottom.

### Quiz o Chłopkowie
**Pani Halina**, the village chronicler, waits by the church. She introduces a 13-question ABCD quiz about the real history of Chłopków
(source: [Polish Wikipedia](https://pl.wikipedia.org/wiki/Ch%C5%82opk%C3%B3w_(wojew%C3%B3dztwo_mazowieckie)), CC BY-SA).
Question signboards (red **?**) stand at the places they are about: the church, rectory ("cerkwisko"), cemetery, windmill, shop, bus stops,
the Białka, the pitch, the orchard, the woods and the road east. Each answer reveals a short fact. Finish all 13 and Halina gives you a title based on your score.

### Cemetery archive (after the main quest)
After Arek earns Grandpa's tractor keys, a three-page archive presents pixel-art interpretations of the old cemetery photos supplied for the game. Each page pairs one scene with a short visual note; press **Enter/Space** or tap to continue, **Esc** to skip. The illustrations are generated and pixel-processed; the original photographs are not shipped with the game.

### Minigames (flags on the map)
Every minigame has a 3-2-1 start, **bronze / silver / gold** medals, a personal record and instant retry.
Your best medal shows on the flag and in the quest log.

- 🏁 **Race** (red flag, track in the northern fields, host Damian): 2 laps against Damian. Run with Shift, jump the hay-bale walls.
  Grass slows you down and checkpoints only count on the track. A translucent **ghost** replays your record run. Gold under 14 s.
- 🐷 **Catch Pepa the piglet** (pink flag, corral below the windmill, host Grandpa): 30 seconds. Pepa is fast and jukes sideways at first,
  but tires over time (sweat drops = slowing down). Corner her against the fence. Gold under 8 s.
- 🐕 **Eggs and dogs** (blue flag, meadow south of the main street, host Marcin): collect 6 eggs while 3 dogs guard them.
  A dog growls (**!**) just before it lunges: jump over it or sidestep. Dogs get faster with every egg you take. Gold under 18 s.
- 🎯 **Damian's shooting gallery** (gold flag, the wheat field next to Damian in the south): fairground-style tin *kurki wodne* (moorhen targets)
  fly out of the striped booths. Aim with the mouse or arrows (touch: tap the target), two barrels, then reload. Hit 10 of 15; gold at 14.

You can also read about the church, the rectory, the cemetery, the windmill, the shop, the bus stops and the river.

## How it's built

```
docs/                    ← the game (GitHub Pages serves this folder)
  index.html
  js/game.js             ← core: input, physics, NPC quests, rendering, extension HOOKS (commented)
  js/features.js         ← quiz UI + Pani Halina + signboards (plugs into HOOKS)
  js/minigames.js        ← race / pig / dogs / shooting gallery: medals, records, retry, race ghost (plugs into HOOKS)
  js/quiz.js             ← the 13 quiz questions (PL/EN), each bound to a map spot
  js/church.js           ← church interior room (drawn in code from reference photos, AI sprites auto-load from img/church/) + Sołtys
  map.json               ← map size, y-sortable objects, points of interest, minigame venues, spawn point
  items.json             ← NPC positions, apples, the cap, quiz signboards
  img/map_ground.png     ← ground layer (fields, roads, river, fences)
  img/map_objects.png    ← buildings, trees, bales, landmarks (drawn y-sorted with the characters)
  img/map_collide.png    ← collisions: 255 = tall (walls, trees, ponds), 128 = low (fences, streams, bales; jumpable)
  img/arek_sheet.png/.json ← Arek's walk-cycle atlas (4 directions; left is right mirrored)
  img/npcs.png           ← Kasia, Marcin, Damian, Grandpa, Pani Halina
  img/frodo.png          ← Frodo's 4-direction, 2-frame walking atlas
  img/memories/          ← three keyed pixel-art cemetery archive illustrations
  img/animals.png        ← pig + dog run cycles (side, front, back)
osm/
  chlopkow.json          ← raw OpenStreetMap extract (Overpass API)
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
```

### Rebuilding assets

```bash
python osm/render_map.py      # map layers + map.json  (needs numpy, pillow)
python osm/place_items.py     # items.json
python gen/slice_sheet.py     # Arek atlas (needs scipy)
python gen/build_npcs.py      # NPC atlas
python gen/build_frodo.py     # Frodo atlas (needs numpy, scipy, pillow)
python gen/build_cemetery_memories.py  # key and pixel-grid the generated archive art
```

Local testing: `python -m http.server 8765 --directory docs`, then open http://127.0.0.1:8765.
It has to be served over HTTP, because opening `index.html` from disk blocks `fetch`.

Automated play-tests (Playwright, headless Chromium; the server must be running):

```bash
python test/run_all.py                       # every test below, with a summary
python test/run_all.py https://itstomekk.github.io/arek-w-chlopkowie/   # against the live site
```

`quest_test` (main quest), `jump_test` (river jump), `features_test` (quiz), `minigames_test` (all four games, medals, retry, ghost),
`church_test`, `frodo_test`, `soltys_surprise_test`, `cemetery_memories_test`, `village_sign_test`, `play_test`.

### Design notes

- **Scale:** 1 m = 2 art pixels. Buildings are enlarged around their centre (up to 2.3×) so they read well next to the characters, the usual RPG compromise. Each one shrinks automatically until it overlaps neither a road nor its neighbours.
- **Depth:** everything standing on the ground (buildings, trees, bales, apples, NPCs, Arek) is sorted by its baseline every frame, so Arek walks behind houses and in front of trees correctly.
- **Jumping:** a jump is about 0.5 s long and ignores low collisions. If Arek would land on a fence he glides a bit further; if it's still blocked he hops back to where he took off.
- **Polish text:** dialogue is upper-cased because the Silkscreen pixel font draws lower-case Polish letters too small. The font also has no **Ć** glyph, so `game.js` draws it as a C plus a hand-drawn accent (a `fillText` wrapper).
- **Minigame venues** (track, corral, meadow, shooting range) are drawn by `osm/render_map.py` and exported in `map.json` (`track`, `corral`, `meadow`, `range`).
- **Resizing the map:** change `BBOX` in `osm/geo.py` and re-run both scripts. Hand-placed spots are written in the first map's coordinates and converted with `legacy_i()`, so they stay on the same real-world place.
- **Reachability:** roads and tracks are always walkable (bridges over the Białka), garden fences have a gate every ~55 m, and `place_items.py` flood-fills from the spawn so every quest item is reachable without jumping.
- **Map size vs. phones:** the map image stays under 4096 px wide, and the ground layer is saved as a 256-colour PNG (about 5 MB).

## Wanted: reference photos

See [PHOTOS-WANTED.md](PHOTOS-WANTED.md). Real photos make the landmarks and characters look like the real thing.

## Credits and licences

- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL.
- Font: [Silkscreen](https://fonts.google.com/specimen/Silkscreen) by Jason Kottke, SIL Open Font License.
- Pixel art: generated with GPT Image, then keyed, sliced and composed with the scripts in this repo.
