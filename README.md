# Arek w Chłopkowie

A small top-down pixel-art adventure set in the real village of **Chłopków** (gmina Platerów, powiat łosicki).
The map is generated from OpenStreetMap data, so roads, the Białka river, fields, woods and every building
sit where they really are. It's a prequel to the short film *Grand Theft Tractor*.

**Play:** https://itstomekk.github.io/arek-w-chlopkowie/ (`?lang=en` for English)

It runs in any modern browser, desktop or phone. The game is pure JavaScript with no libraries and no build step.

## Controls

| Action | Keyboard | Touch |
|---|---|---|
| Walk | Arrows / WASD | drag anywhere (virtual joystick) |
| Run | hold Shift | push the joystick to the edge |
| Talk / read | Space (next to someone or something) · E · Enter | **A** button |
| Jump | Space (when nobody is near) · X · J | **A** button |
| Map | M | tap the minimap |
| New game | N on the title screen | — |

Progress saves automatically in the browser (localStorage).

## What you do

- **Kasia** (next to the shop) needs **10 apples** for her apple pie. They grow in the orchard in the south and in the gardens along the main street.
- **Damian** (at the sports pitch in the north) lost his **cap** somewhere in the wheat.
- **Marcin** (at the bus stop) wants an **orangeade** from the shop.
- **Grandpa Zbyszek** (by the Koźlak windmill) hands over the **keys to his Ursus** once the whole crew has been helped.

On the way you can jump over garden fences, hay bales and the Białka river.
You can also read about the church, the rectory, the cemetery, the windmill, the shop, the bus stops and the river.

## How it's built

```
docs/                    ← the game (GitHub Pages serves this folder)
  index.html
  js/game.js             ← the whole game: input, physics, quests, rendering (commented)
  map.json               ← map size, y-sortable objects, points of interest, spawn point
  items.json             ← NPC positions, apples, the cap
  img/map_ground.png     ← ground layer (fields, roads, river, fences)
  img/map_objects.png    ← buildings, trees, bales, landmarks (drawn y-sorted with the characters)
  img/map_collide.png    ← collisions: 255 = tall (walls, trees, ponds), 128 = low (fences, streams, bales; jumpable)
  img/arek_sheet.png/.json ← Arek's walk-cycle atlas (4 directions; left is right mirrored)
  img/npcs.png           ← Kasia, Marcin, Damian, Grandpa
osm/
  chlopkow.json          ← raw OpenStreetMap extract (Overpass API)
  render_map.py          ← OSM → pixel-art map + collision mask + map.json
  place_items.py         ← places NPCs, apples and the cap on reachable spots → items.json
gen/
  model_sheet_v1.png, walk_sheet_v1.png ← AI-generated sprite sheets of Arek (GPT Image, magenta background)
  lm_church.png, lm_windmill.png, lm_shop.png ← landmark sprites
  slice_sheet.py         ← chroma-key + slicing + feet-aligned atlas for Arek
  build_npcs.py          ← NPC atlas
  codex_gen.py / ppq_gen.py ← image-generation helpers (local tooling, need the author's accounts)
```

### Rebuilding assets

```bash
python osm/render_map.py      # map layers + map.json  (needs numpy, pillow)
python osm/place_items.py     # items.json
python gen/slice_sheet.py     # Arek atlas (needs scipy)
python gen/build_npcs.py      # NPC atlas
```

Local testing: `python -m http.server 8765 --directory docs`, then open http://127.0.0.1:8765.
It has to be served over HTTP, because opening `index.html` from disk blocks `fetch`.

### Design notes

- **Scale:** 1 m = 2 art pixels. Buildings are enlarged around their centre (up to 2.3×) so they read well next to the characters, the usual RPG compromise. Each one shrinks automatically until it overlaps neither a road nor its neighbours.
- **Depth:** everything standing on the ground (buildings, trees, bales, apples, NPCs, Arek) is sorted by its baseline every frame, so Arek walks behind houses and in front of trees correctly.
- **Jumping:** a jump is about 0.5 s long and ignores low collisions. If Arek would land on a fence he glides a bit further; if it's still blocked he hops back to where he took off.
- **Polish text:** dialogue is upper-cased because the Silkscreen pixel font has no lower-case Polish glyphs. It also has no **Ć**, so the Polish strings avoid that letter.

## Wanted: reference photos

See [PHOTOS-WANTED.md](PHOTOS-WANTED.md). Real photos make the landmarks and characters look like the real thing.

## Credits and licences

- Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL.
- Font: [Silkscreen](https://fonts.google.com/specimen/Silkscreen) by Jason Kottke, SIL Open Font License.
- Pixel art: generated with GPT Image, then keyed, sliced and composed with the scripts in this repo.
