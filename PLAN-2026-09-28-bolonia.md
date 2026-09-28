# PLAN 2026-09-28: "Chłopków Bolonia" update

Status: **PLAN ONLY.** Nothing here is built or deployed yet. Tomek said "plan, save handoffs, don't build or deploy".
Written from a cloud session on branch `claude/gifted-goodall-12f9jo`. `main` is untouched, so GitHub Pages is untouched.
The next agent executes this plan phase by phase, and only once Tomek says go (see "Open questions" first).

Tomek's requests, in his words (2026-09-28):
1. The river is called **"Melioranka"**.
2. Add a **coordinates check on the map view** too.
3. Take the locations and **prepare images of the points of interest** from their OpenStreetMap and Google Maps photos.
4. Add the **big forest in the north** (it can come from the map).
5. **Adapt the game map** to include these points (5 Google Maps links).
6. Suggest a **gamification plan** and what could be done better.
7. "Quiz można zacząć bez wizyty u babci Halinki" (the quiz can be started without visiting Granny Halinka). See Q2 for the interpretation.
8. Rename Granny Halinka to **Irenka** and **generate her look from the photos Tomek provided** (saved as a new asset).
9. **The dogs in the minigame run too fast** once they see you.
10. Show on the map that **east is "DUŃCY"**.
11. Rename the game to **CHŁOPKÓW BOLONIA** (and the repo too).

---

## 0. Facts verified in this session (don't re-research)

### The 5 Google Maps links, resolved via their 302 redirects
| key | Google name | lat | lon | In OSM? | x,y in the current map | x,y if maxlat = 52.2800 |
|---|---|---|---|---|---|---|
| `kapliczka` | kapliczka (wayside shrine) | 52.265937 | 22.8658023 | no | 981, 1053 | 981, 3110 |
| `chata` | Chata za wsią | 52.2669308 | 22.8674792 | no | 1210, 834 | 1210, 2890 |
| `strzelnica` | PPM Strzelectwo | 52.2736642 | 22.867767 | **yes**: `leisure=pitch sport=shooting`, way 1453546275 "oś krótka" (52.2727–52.2740) + way 1453549547 "oś długa" (52.2685–52.2708, lon 22.8674–22.8680) | **outside, north** (y = −656) | 1249, 1401 |
| `swietlica` | świetlica wiejska | 52.2641139 | 22.8754946 | no | 2302, 1457 | 2302, 3513 |
| `cmentarz` | Cmentarz | 52.2685251 | 22.8772688 | **yes**: landuse=cemetery way 318005531 "Cmentarz parafialny w Chłopkowie" | 2544, 481 | 2544, 2538 |

Short links: fkvSdas6z635At75A (kapliczka), bqF1zYqVcwZpmZze6 (Chata), F4DgjjeypKGY5m5B7 (PPM), 3aZk664T1w8maxFs6 (świetlica), 94HLAAeE1KQpmKeW9 (cmentarz).
Pixel maths: `osm/geo.py` `P()` (A = 2 px/m). Only the y value changes when maxlat changes.

### Current map
- `BBOX = (52.2585, 22.8586, 52.2707, 22.8872)`, 3897 × 2698 px.
- The "long axis" of PPM Strzelectwo (way 1453549547) is already inside the map at its north edge. The short axis and the Google pin are outside.

### The big forest to the north (from the OSM API, 2026-09-28)
- The largest `landuse=forest` ways north of the map are 228878198 (52.2762–52.2797), 228878180 (52.2796–52.2838), 228878174, 228878170, 228875322 (to 52.2919), 228878197 (from 52.2742) and 228878194 (from 52.2728, east side).
- There are also Lasy Państwowe multipolygons: relation 3067203 (ref 274) and relation 3067204 (ref 284B).
- **The forest edge starts about 52.274–52.276.** Moving maxlat to 52.2800 shows the edge plus a solid band of forest. Moving it to 52.2850 shows most of the forest.

| maxlat | map H (px) | forest shown | cost |
|---|---|---|---|
| 52.2707 (now) | 2698 | none | — |
| **52.2800 (recommended)** | 4754 (+76%) | edge + ~500 m of forest, the PPM range, the northern tracks | ground PNG ~5.4 → ~8–9 MB unless tiled (see §3) |
| 52.2850 | 5860 (+117%) | most of the forest block | ~11 MB+; tiling becomes mandatory |

### River name
- In OSM the main stream is **"Rzeka Białka"** (ways 289264721, 318005364–368, 413730590–591).
- Separate, unnamed streams (1323878340–342) and a ditch (525046890) are in the east. "Melioranka" (from melioracja, land drainage) sounds like the local name of a drainage channel. **See Q1.**
- In-game mentions of the Białka: `docs/js/game.js:45,94` (river dialogue), `docs/js/quiz.js:55` (quiz question text), plus comments in `osm/render_map.py` and `osm/place_items.py`. There are 15 hits in total (`grep -rn "Białk" docs osm`).

### Quiz gate (request 7)
The code **already locks** the signboards until the player has met her: `docs/js/features.js:148` (`if (Q().halina === 0) A.say('arek', L.boardLocked)`). The same `Q().halina` check also:
- colours the boards (`:164`);
- shows board dots on the minimap (`:175`);
- shows the quiz line in the log (`:177`).

### Dogs (request 9), `docs/js/minigames.js:250–260`
- Arek walks at `SPEED = 110` (`game.js:159`).
- The dogs chase at `92 * angry`, where `angry = 1 + 0.07 × eggs taken`. **After 3 eggs the chase speed is 112, faster than Arek.**
- Detection radius is 210. Wind-up is only 0.45 s, then the lunge runs at `235 * angry` for 0.5 s.
- So "they run too fast once they see me" is accurate: the chase itself out-runs the player after a few eggs, and the lunge gives little warning.

### Other facts
- Save key: `arek-chlopkow-save-v1` (`game.js:29`). Mute key: `arek-music-muted`. **Keep both** on rename, or old saves are lost.
- Title strings: `docs/index.html:6` `<title>`; `game.js:35` PL `title: 'AREK W CHŁOPKOWIE'`; `game.js:84` EN `'AREK IN CHŁOPKÓW'`; header comment `game.js:1`; `README.md:8`; HANDOFF links.
- Halina appears in: NPC names (`game.js:37,86`), `NPC_IDX` (`game.js:134`), `freshQ` (`game.js:162`), all of `features.js`, `quiz.js:4,9` (`spot: 'halina'`), `osm/place_items.py:76`, `gen/build_npcs.py:4` ORDER, and `test/features_test.py`.
- **Overpass is blocked from the cloud container** (connection reset). `https://api.openstreetmap.org/api/0.6/map.json?bbox=…` **works** from the cloud, but returns the raw format (node refs, no `geometry`/`bounds`). `osm/chlopkow.json` is in Overpass `out geom` format. So either re-fetch from Overpass **locally** (Tomek's PC works) or write a small converter.
- An old branch, `claude/determined-mccarthy-b9096e`, is **behind** main (stale). Ignore it; don't merge it.

---

## Open questions for Tomek (answer before Phase 1)
- **Q1, Melioranka:** rename the whole river (everything that now says Białka), or only the eastern unnamed stream or ditch? The recommended default is to rename the in-game river to "Melioranka" everywhere and keep a quiz fact noting that maps call it the Białka. The name "Białka" does still appear in the church quiz question and in history.
- **Q2, quiz:** "Quiz można zacząć bez wizyty u babci Halinki" can mean two things:
  - (a) a feature request: *let the quiz start without visiting her*, i.e. remove the gate;
  - (b) a bug report: *it can be started without her*, which is wrong.
  
  The code already enforces the gate, so this plan assumes **(a): remove the gate**. If (b), the gate works in code; ask how it was reproduced.
- **Q3, the photos:** photo 1 (white sweater, straighter darker hair) looks like it may be a **different person** from photos 2–4 (curly brown hair). Are all four Irenka? The plan uses photos 2–4, mainly the full-body photo 4. Also confirm she's OK with being in the game (the same consent rule as for Grandpa).
- **Q4, Irenka's title:** PL "BABCIA IRENKA" (EN "GRANNY IRENKA")? Or "PANI IRENKA"?
- **Q5, north extension:** maxlat 52.2800 (recommended) or 52.2850 (most of the forest, a much larger file)?
- **Q6, shooting range:** move Kasia's/Damian's skeet minigame venue to the **real PPM Strzelectwo** range? It's currently in the wheat field by Damian in the south. Recommended: yes, with Damian standing there as host.
- **Q7, DUŃCY:** only a label on the map view, or also an in-world road sign ("DUŃCY →") at the eastern exit road? Recommended: both.
- **Q8, repo name:** `chlopkow-bolonia` (recommended), `chlopkow-bolonia-game`, or something else? And keep a redirect stub at the old URL?
- **Q9, kapliczka:** which of the 4 existing shrine sprites (`cross_iron`, `shrine_stone`, `shrine_white`, `shrine_fenced`) is the one at the kapliczka pin, so it can be pinned to its real location?

---

## Phase 1: quick fixes (one session, low risk, no map re-render)

### 1.1 Rename the game → CHŁOPKÓW BOLONIA
- `docs/index.html` `<title>`, the `game.js:1` comment, `game.js:35` (PL title) and `game.js:84` (EN: keep "CHŁOPKÓW BOLONIA", it's a name).
- README heading and play link; HANDOFF; PHOTOS-WANTED intro; `test/*` only if they assert the title.
- **Keep** `SAVE_KEY` and `MUTE_KEY` unchanged (players keep their progress).
- The title screen may need a smaller font or two lines: the name is longer. Check at 360 px width.

### 1.2 Rename the GitHub repo (Tomek does this in the browser, then the agent updates the links)
- GitHub → repo Settings → General → Repository name → `chlopkow-bolonia` (Q8).
- **Effect:** GitHub redirects git and web URLs of the repo, **but the Pages URL changes** to `https://itstomekk.github.io/chlopkow-bolonia/`, and the old `…/arek-w-chlopkowie/` URL **stops working** (Pages doesn't redirect renamed project sites).
- Options for people who have the old link:
  - (A) accept the breakage;
  - (B) after renaming, create a new tiny repo named `arek-w-chlopkowie` whose `index.html` meta-refreshes to the new URL. This breaks GitHub's git redirect for the old name, which is fine because nobody clones it.

  Recommended: B.
- Then update: `git remote set-url origin https://github.com/itstomekk/chlopkow-bolonia`, the README link, HANDOFF, the VibeTV `.claude/launch.json` `arek-game` entry (local), and the default `ARK_URL` in tests if one is hardcoded. The local folder name can stay.
- Optionally rename the internal `ark-ready` event / `__game`. **Not needed**, so leave it.

### 1.3 River → Melioranka (after Q1)
- Change the dialogue text at `game.js:45` and `:94` and the quiz text at `quiz.js:55`. Check the other quiz questions and answers for "Białk".
- Comments in `render_map.py` and `place_items.py` are optional.
- Also: the POI label shown on hover, and the minimap tag, if they print the name (grep for `river`).
- Polish declension: Melioranka / Melioranki / Meliorance / Meliorankę / Melioranką. Example: "nad Melioranką".

### 1.4 Halina → Irenka (text part; the sprite is Phase 3)
- Recommended low-risk approach: **change the display names and texts only** and keep the internal id `halina` (save field `Q.halina`, `spot: 'halina'`, `NPC_IDX.halina`). Add a comment `// displayed as Irenka since 2026-09-28`.
- The alternative, a full rename of the id plus save migration (`if (s.Q.halina !== undefined) s.Q.irenka = s.Q.halina`), is cleaner but touches about 30 lines and the tests. Do it only if Tomek wants the code tidy.
- Texts: `features.js:15–32` (PL and EN). "Jestem Halina" → "Jestem Irenka"; "z panią Haliną" → "z babcią Irenką"; toast `WRÓĆ DO PANI HALINY` → `WRÓĆ DO BABCI IRENKI`. `game.js:37,86` names.

### 1.5 Quiz without visiting her (after Q2; assuming "remove the gate")
- `features.js:148`: drop the `boardLocked` branch, so boards open the quiz directly. Keep `L.boardLocked` unused, or delete it.
- `:164` board colour: always the "active" red. `:175` minimap dots: show without the `Q().halina` condition. `:177` quiz log line: show once `answered() > 0 || Q().halina`.
- Irenka stays the scorekeeper. Her first question `king` (`spot: 'halina'`) is still asked by her. Her end dialogue (`halinaEnd`) should trigger when `answered() >= QZ_ALL` **regardless of whether she was met first**. Change `:138` to `q.halina !== 2 && answered() >= QZ_ALL`.
- `:58` toast "go back to Irenka" when everything is answered: drop the `Q().halina === 1` condition (`!== 2` instead).
- Update `test/features_test.py`: a board should now open the quiz before she is met.

### 1.6 Dogs slower and fairer (`minigames.js:250–260`)
Proposed values, with the rule that **a chasing dog must always be slower than Arek (110)**:
| param | now | proposed |
|---|---|---|
| chase speed | 92 | **70** |
| anger per egg | +7% | **+4%, capped at ×1.20** (so the max chase is 84) |
| detection radius | 210 | **160** |
| "noticed you" pause | none | **0.35 s** "?" before the first chase step (dog stops, bark bubble) |
| wind-up before a lunge | 0.45 s | **0.65 s** |
| lunge speed / duration | 235 / 0.5 s | **190 / 0.4 s** |
| rest after a lunge | 0.8 s | 0.8 s (keep) |
- Afterwards, re-check the `MEDAL.dogs` thresholds (win / 28 s / 18 s). The easier dogs probably need gold at about 15 s. Run `test/minigames_test.py`.
- Optional: an "easy mode" toggle for kids that multiplies all dog speeds by 0.8.

### 1.7 Coordinates on the map view (M)
- In the big map (`showMap`, `game.js:634–650`):
  - print the player's lat/lon under the map;
  - on mouse hover or tap, show the lat/lon and map x/y of the cursor point (convert map-view px → art px → `to_latlon`; port `geo.py`'s `to_latlon` to JS using `MAP.bbox`);
  - click to copy "lat, lon" to the clipboard.
- Already available: `map.json` exports `bbox` and `scale`, and `game.js:527–531` has the lat/lon formula for the bottom-left readout. Pull it out into a `toLatLon(x, y)` helper and reuse it.
- Also add `?lat=..&lon=..` next to the existing `?x=..&y=..` start parameter (handy for testing POIs).

### 1.8 East = "DUŃCY"
- Map view: an arrow and label at the middle of the right edge: `DUŃCY →`. On the minimap, just a small `→ D` or nothing (too small). Optionally a compass "N" at the top.
- In the world (Q7): a road signpost sprite (`drogowskaz`) at the east end of the main street, with text "DUŃCY →". It can be drawn in JS like `drawBoard`, so it doesn't need an image.

**Phase 1 done when:** `python test/run_all.py` passes all 11 tests (plus any updated), a manual smoke test works on desktop and 360 px mobile, and the changes are merged to `main` **only when Tomek says deploy**.

---

## Phase 2: map extension + real points of interest (map re-render; one session)

### 2.1 Fetch the bigger OSM extract
- New `BBOX = (52.2585, 22.8586, 52.2800, 22.8872)` (Q5) in `osm/geo.py`. `legacy_i()` keeps every hand-tuned spot on the same real place, so venues and shrines don't move. **Only y shifts by +2057 px.** Double-check `?x=&y=` examples and any test with hardcoded coordinates.
- Re-fetch `osm/chlopkow.json` with Overpass **locally** (the cloud gets a reset). Use the same query as before, with the new bbox, `out geom;`. Include the forest relations 3067203 and 3067204 (`relation["landuse"="forest"]` + `>;` or `out geom`).
- The renderer currently treats ways; check that it handles multipolygon relations or add that. Otherwise draw the forest from its member ways (228878198, 228878180, …), which also works.

### 2.2 The northern forest
- It's already drawn as "forests: dense canopy drawn on ground layer, solid" (`render_map.py` ~line 456). The new area gets that automatically.
- Improve it for a *big* forest:
  - walkable forest tracks: tracks already cut through collision because roads are always walkable;
  - a soft edge with scattered single trees;
  - a couple of clearings (polany);
  - make the interior **"tall" collision except on tracks**, so the forest is a maze of paths rather than an open area.
- Gameplay hooks are in §4: mushroom picking and the forest quiz sign.

### 2.3 Add the 5 points (all via `add_poi` in `render_map.py` + `place_items.py`, using real lat/lon)
| key | what to add | gameplay use |
|---|---|---|
| `kapliczka` | Pin one existing shrine sprite (Q9) to 52.265937, 22.8658023 instead of an automatic junction. Keep the other three automatic, but exclude this spot from the farthest-point choice. | A quiz board here? A prayer/“candle” interaction. |
| `chata` | New landmark "Chata za wsią". Until the sprite exists, draw a procedural wooden cottage or use `lm_house_generic`. Hotspot text. | A small NPC side quest (e.g. an owner asks for firewood from the forest). |
| `strzelnica` | Draw both OSM pitch polygons (the long and short axes) as a range: earth berm, target stands, a firing line. | **Move the skeet venue here (Q6).** Damian waits at the firing line. |
| `swietlica` | New landmark building (see PHOTOS-WANTED #4). Hotspot. | A future interior via the `add-interior` skill (dance night / dożynki / table tennis). |
| `cmentarz` | Already mapped. Add the gate sprite at the Google pin side, plus znicze. | Hook the existing "memory archive" ending to a visible gate. |
- Use the new repo skill `.claude/skills/add-real-poi/SKILL.md` (written in this session) for each point.
- `place_items.py` flood-fills from the spawn. Make sure every new point is reachable. Its assertion stops NPCs landing on signboards.

### 2.4 File size of the bigger map
- The ground PNG grows about 1.8× (to ~8–9 MB). Options:
  - (A) accept it;
  - (B) **split the ground into 1024-px tiles, lazy-loaded around the camera** (the best long-term fix; needed for 52.2850);
  - (C) render the forest interior as a flat colour so it compresses well.

  Recommended: C now, B when the map grows again.

**Phase 2 done when:** the tests pass (`run_all.py` finds the river column automatically; check the jump test still finds one), every new POI is reachable, the minimap is readable, and load time on 4G is measured.

---

## Phase 3: images (local only, Tomek's PC: Codex needs the Hermes venv)

### 3.1 Irenka sprite and portrait (from Tomek's photos)
- **Photos:** 4 were given in chat on 2026-09-28. They are **not** in the repo (the rule: real photos are never committed). They were copied to this cloud session's scratchpad (`references/irenka/1.webp, 2.png, 3.webp, 4.png`), which is **temporary**. Tomek must save them locally to `references/irenka/`, which is gitignored.
- **Never upload these to PPQ** (`gen/ppq_gen.py` needs public URLs). Use `gen/codex_gen.py` with local files only.
- Look to extract (photos 2–4, pending Q3):
  - an older woman with short, curly, dark-brown hair and a round face;
  - fair skin, a calm, slightly serious expression;
  - a thin gold necklace and small earrings;
  - full-body reference (photo 4): a navy blouse with a white and light-blue flower print, cream straight trousers, beige strappy sandals, a wristwatch on the left wrist;
  - alternative outfits: a blue blazer (photo 2), a cream jacket with a beige pattern (photo 3).
- Prompt skeleton (put it in `gen/PROMPTS-npcs.md`, following the style of `gen/HERMES-PROMPT.md`): "Top-down 3/4 view 16-bit pixel art sprite of an elderly Polish village grandmother, short curly dark-brown hair, navy blouse with white flower print, cream trousers, beige sandals, gold necklace, friendly; same style, outline and palette as the reference NPC sheet; transparent background; full body, 40 px tall character scale" + the references `gen/npc_src/kasia.png` (style) and the local `references/irenka/4.png` (likeness).
- Output: `gen/npc_src/irenka.png`. In `gen/build_npcs.py`, replace `'halina'` in ORDER with the Irenka source (keep index 4, or rename, see 1.4), then rebuild `docs/img/npcs.png`.
- Keep the old `gen/npc_src/halina.png` (don't delete; it's history).
- Bonus: a dialogue **portrait** (a bust, 64×64) for the future portraits feature (asset list #29).

### 3.2 Point-of-interest images ("from OSM and Google Maps photos")
What's actually available:
- **OSM** has no photos for these points (no `image`, `wikimedia_commons` or `mapillary` tags in the extract). It gives exact positions and outlines only.
- **Google Maps photos** are user or Google copyright, and scraping them breaks Google's terms. The Places API (Place Photos) needs an API key and billing, and its terms forbid storing the photos. The cloud container can't reach them anyway.
- **Legit reference sources**, best first:
  1. Tomek's own phone photos (PHOTOS-WANTED).
  2. Tomek **looking at Google Maps / Street View himself and saving screenshots privately** to `references/poi/<key>/`. These are used only as a *reference* for a re-drawn pixel-art sprite, never shipped or committed. This is the same rule as the other reference photos.
  3. **Mapillary** street-level imagery (CC BY-SA, has an API).
  4. **Geoportal.gov.pl orthophoto** (open data): top-down, so great for footprints and yard layout.
  5. Wikimedia Commons (search "Chłopków").
- Pipeline per point:
  1. references go in `references/poi/<key>/` (gitignored);
  2. write a prompt in `gen/PROMPTS-landmarks.md`;
  3. `codex_gen.py` → `gen/lm_<key>_raw.png`;
  4. key out the background, then save `gen/lm_<key>.png`;
  5. `add_generated_sprite(...)` in `render_map.py`, with the width in `LM_SIZE`.
- **Also make a "postcard" version** of each point (a 256×160 pixel-art scene) for the collection album in §4. The same references give two assets.
- Order: strzelnica (it becomes a minigame venue) → świetlica → chata → kapliczka (possibly already covered by an existing shrine sprite) → cemetery gate.

---

## Phase 4: gamification plan + what could be done better

### 4.1 Ideas, ranked by fun per effort
| # | Idea | Effort | Why |
|---|---|---|---|
| 1 | **"Pocztówki z Chłopkowa" album**: visiting each real point (church, windmill, shop, kapliczka, chata, świetlica, cemetery, strzelnica, Melioranka bridge, the forest, the DUŃCY sign) unlocks a pixel-art postcard with one true fact. Progress shows as 0/12. | S–M | It reuses the §3.2 images, rewards exploring the bigger map, and teaches village history. **Quick win.** |
| 2 | **Grzybobranie** (mushroom hunt) in the new northern forest: 90 s, find boletes (prawdziwki) and avoid fly agarics (muchomory), with medals. | M | It gives the forest a purpose and fits the existing minigame framework (`MG`, `MEDAL`). |
| 3 | **Shooting at the real PPM range** (move skeet) + a "strzelec wyborowy" (marksman) badge for gold. | S | A real place; the minigame already exists. |
| 4 | **Badges / odznaki screen** (e.g. "Wszystkie jabłka", "Pogromca psów", "Kronikarz", "Nocny marek"). | S | Cheap and replayable; the data is already in `Q`. |
| 5 | **Tractor minigame** after Grandpa's keys: drive the Ursus to the field without hitting fences. | L | It's the natural climax of the main quest (already in "Next ideas"). |
| 6 | **Shop economy**: apples and minigame medals earn złotówki (coins), spent at the SKLEP on oranżada, lody (ice cream) or a hat for Frodo. | M | It gives the collectibles a use. |
| 7 | **Quest journal + map markers** ("!" on the M map for the current goal). | S | Players get lost on a map 1.8× bigger. |
| 8 | **Events**: dożynki at the świetlica, odpust (parish fair) at the church, with a date-based or random trigger. | M | Local colour; uses the świetlica. |
| 9 | **Cerkwisko secret**: an archaeological site in OSM (way 1323397547, 52.2606–52.2610 / 22.8770–22.8775). A hidden relic plus a fact about the old Orthodox church. | S | A secret for explorers; the data is already there. |
| 10 | **Fishing on the Melioranka**, on the bridge | M | A relaxing minigame, more music moments. |
| 11 | **Local leaderboard** (a best-times board in the świetlica). An online version needs a backend (Pages is static), so skip for now. | S | Replay value between siblings/friends. |

### 4.2 What could be done better (found while reading the code)
- **Onboarding:** the first 30 s have no hints for jump, map or minigame flags. Add a 3-tip intro, dismissed by keypress.
- **Direction:** with a larger map, add an arrow at the screen edge pointing to the current quest target.
- **Difficulty:** tuning is by hand (the dogs were too hard). Add a quick "tuning playtest" harness to `test/` that simulates a straight-line player vs a chasing dog and asserts the player can escape. That would have caught the dog bug.
- **Map size and performance:** tiled, lazy-loaded ground (§2.4).
- **Mobile:** check the M-map tap and the new coordinate tap don't clash with the joystick zone.
- **Save:** export/import the save (a copy-paste string), so progress survives a browser change. Save slots for siblings.
- **Accessibility:** a text-size option; colour-blind check on the medal colours (bronze vs gold).
- **Content consistency:** a single `pois.json` (name, lat/lon, facts, postcard, quiz id) feeding the map, quiz and album, instead of facts spread over `game.js`, `quiz.js` and `render_map.py`.

---

## Execution order (summary)
1. Tomek answers Q1–Q9.
2. Phase 1 (code only). Tests, then a PR to `main` → **deploy only on Tomek's OK**.
3. Tomek renames the repo (1.2), then the agent fixes the links.
4. Phase 2 (map). It needs a **local** Overpass fetch, or a converter from the OSM API format.
5. Phase 3 (images), **local only** (Codex/Hermes). Tomek saves the Irenka photos and POI screenshots to `references/`.
6. Phase 4: pick 2–3 ideas (recommended: album, grzybobranie, PPM range).
