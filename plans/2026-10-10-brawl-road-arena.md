# BIJATYKA scrolling arena: main road, west entrance to Świetlica

Reconstructed from Google Street View (101 panoramas on the main road, `chlopkow-streetview-tour/data/panos_all.json`),
sampled every 50 m by `references/brawl-road-2026-10-10/` (gitignored; stations.json, sheet_0..3.jpg, sheet_extra.jpg).
Distances are along the road from the westernmost panorama (lng 22.85932). There is no church on this stretch.

| Screen | Road metres | North side (back of the stage) | South side |
|---|---|---|---|
| 1. Wjazd od zachodu | 0–150 | cereal field, willows, flowering shrubs; at ~150 m first house: cream/orange two-storey, balcony, solar panels, conifers, grey wall + wire fence | ripening cereal, maize, thistles, hedge |
| 2. Pierwsze domy | 245–400 | yellow wooden single-storey house with apple tree and satellite dish; pink two-storey house, concrete-panel fence, boulder; cream house with red roof, balcony, iron gate | meadow, pasture, orchard rows, distant farm |
| 3. Kapliczka | ~480 | hedge, wire fence, dirt track | white roadside shrine with green roof, metal cross, glazed niche; red-roofed building and conifers behind |
| 4. Budki / przystanek | 530–590 | two blue wooden booths (closed booth + open shelter with bench), rusty roofs, overgrown; house with blue metal roof; brick pillars + wrought-iron fence with thuja hedge (track north to Chata) | dense trees, brick building with light roof |
| 5. Brama z wieżyczką | 700–900 | wooden gatehouse with red tiled roof, red brick wall, dark gate; large two-storey house with dark roof and dormers | stubble field, willow, bare sand |
| 6. Świetlica | 970–1170 | mint-green house with rust roof; white house with balcony; wooden-clad house; at the bend the Świetlica: long low cream building behind a fenced gate with banners, tall wooden cross, big linden, bike | stubble, diamond priority sign, beige house with blue gate |

Next: confirm order with Tomek, then generate six seamless pixel-art panels (same style as current stages, Street View as composition reference only) and add a scrolling camera to `docs/js/brawl.js`.

## Update 2026-10-12 (Tomek's corrections)

- Kapliczka is on the NORTH side (OSM 52.265937, 22.8658023, 3 m off the road, ~475 m). It stands in front of the fences between nr 20 and nr 19. Street View fronts were blocked by trees; drawn from a partial crop (white pillar, green roof, cross, glazed niche).
- Boisko added after the świetlica as the east end (not visible from Street View; generic village pitch).
- Long gaps shortened: up to 50 m to scale, longer gaps count 35% (`eff()` in build_road_stage.py).
- Ground: asphalt road next to the houses, meadow on the lower half (`raw/road/bg2_raw.png`).
- Result: 11513x720 px, ~8635 game px (~9 screens). Full image: gen/brawl/arena_droga_do_swietlicy.png.

## Update 2026-10-12 b

- Kapliczka scaled to 0.6 (`SIZE`), świetlica regenerated as a long low building (`raw/road/hall_raw.png`, old one kept as `hall_v1_raw.png`), boisko kept clear of the hall (`SPREAD`).
- Missing building at ~60 %: the wooden house with a red-tiled gate tower, black iron gate and red brick wall (~780-816 m, OSM house 1095382322 sits 69 m back so the first filter skipped it) added as `h12b`.
- Strip 12116x720 px, world 9087 game px.

## Update 2026-10-12 c (Tomek's review of the numbered sheet)

- Real distances: 12 px per metre, houses pushed apart only where vignettes would overlap (MINSEP); side roads keep 330 px clear.
- Side roads from OSM: track 96 m, asphalt road at the kapliczka 469 m, track 569 m (after the booths); plus a track at ~626 m from Tomek ("droga w prawo", not in OSM).
- Removed the ruin (old #7). nr 26 at 80 %. nr 25 regenerated wide and complete (old nr 24 kept, its wide redraw parked as image-gen/2026-10-12-brawl-road-v2/h04_wide_unused_raw.png). New: orange house (~652 m, from Tomek's description, not confirmed on Street View), PKS bus stop sign before the green-gate cottage, big gate (~921 m, from Street View 915 m), gate-tower house redrawn from closer Street View crops.
- Mint house (#25) set back (smaller, higher). East end: T-junction with the paved road running north (satellite + Street View 1140 m): meadow left, tree row right.
- Unsure: which real house is the "drewniany w krzakach" (placed at ~600 m) and where exactly the orange house stands.
- Review sheet: `python gen/brawl/number_road_stage.py` -> arena_numerowana_rzedy.jpg / _preview.jpg (numbers from raw/road/layout.json).
