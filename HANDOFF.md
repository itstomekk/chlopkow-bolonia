# HANDOFF — Chłopków Bolonia

## CURRENT STATE — read before historical notes below
- Current project roadmap: `plans/2026-09-27-chlopkow-bolonia-roadmap.md`, indexed by `PLAN.md`. It includes Tomek's new terrain, player-name, diagonal-animation, duck-hunt, shooting, metadata, README and dialogue requests.
- GitHub repo: https://github.com/itstomekk/chlopkow-bolonia; **published** at commit `ba64220e797adc4bc8842b8f82483c3749bf356d` to https://itstomekk.github.io/chlopkow-bolonia/. The exact-commit Pages build reports `built`; index, scripts, sprites and ground image read back. JSON bytes were minified by Pages but parsed objects match. Public `python test/run_all.py https://itstomekk.github.io/chlopkow-bolonia/index.html` passed 11/11. The old Pages URL has a separate redirect repository.
- Published batch: expanded map (3896×5860), north forest, BUDKA, football pitch, PPM range, Irenka/Kuba/car art, optional Nostr overlay, world-life animals/car, cemetery art, map and navigation changes, Polish README and HTML metadata. This is an interim playable update: mushrooms, new Professor, duck-target replacement, new target range and other roadmap features are NOT yet implemented. Most old facts below describe the previous map and are historical.
- Local `main` and `origin/main` match at `ba64220`; no local gameplay changes remain. Local-only `PLAN.md`, `HANDOFF.md`, roadmap and raw source images remain uncommitted. Do not add private reference photos or raw source images to the public repo. The minigame test prints `FAILED: none` when its failure list is empty and exits 0; this is confusing wording, not a failed assertion.
- Coordinate source for new requests is the *previous* 3897×2698 map. Convert through `osm/geo.py:pre_expansion_i()`: Sołtys near (1887,1237), shrine old (2298,1423) → new (1744,1271), pond near (270,1893), second store near (2150,2506), duck hunt near (3145,2629), pitchfork near (3366,410).
- Michał is the real shooting-range operator and Kuba is also there. Use village flavor in dialogue, but do not attribute wrongdoing, addiction or suicide to named private residents, and independently confirm the municipal status before any factual claim about Platerów.

## HISTORICAL NOTES (earlier planning, superseded where inconsistent above)
- Tomek asked for a batch of changes: rename the game to **CHŁOPKÓW BOLONIA** (and the repo); the river becomes **Melioranka**; Halina becomes **Babcia Irenka** with a new sprite from his photos; the quiz starts without visiting her; slower dogs; lat/lon on the M map; "DUŃCY" on the east edge; the big forest in the north; 5 real points from Google Maps; a gamification plan.
- **Everything is planned in `PLAN-2026-09-28-bolonia.md`** (verified facts, 9 open questions, 4 phases). Read it first. It lives on branch `claude/gifted-goodall-12f9jo`; **`main` is untouched and nothing is deployed.**
- New skill: `.claude/skills/add-real-poi/SKILL.md` (Google link → lat/lon → map).
- **Blocking:** Tomek's answers to Q1–Q9 in the plan. The Irenka photos were given in chat only. Tomek must save them locally to `references/irenka/` (gitignored, never commit, never upload to PPQ).
- Cloud limits hit: Overpass is blocked (use the OSM API or fetch locally); Codex image generation runs only on Tomek's PC.


Last updated: 2026-09-28 (music added; before that: audit + bigger map + minigame overhaul). The earlier per-session notes are in
`_archive/2026-09-27_HANDOFF-before-audit.md`.

## Where things are
- **Live:** https://itstomekk.github.io/arek-w-chlopkowie/ (GitHub Pages from `main:/docs`; every push to `main` redeploys in about 1 minute; browsers cache for 10 minutes).
- **Repo:** https://github.com/itstomekk/arek-w-chlopkowie (public)
- **Local:** `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie\`
- **Local server:** `python -m http.server 8765 --directory docs`. The VibeTV project's `.claude/launch.json` has an `arek-game` entry.
- **Tests:** `python test/run_all.py [URL]` runs all 11 Playwright play-tests. All 11 pass (cloud container, 2026-09-28).

## What the game has
- **Map:** generated from OpenStreetMap, 3897×2698 art px (1 m = 2 px), about 1.95 × 1.35 km. It covers the whole main street, the church quarter, the riverside farmsteads in the west and Chłopków-Kolonia in the east. 93% of it is reachable on foot.
- **Main quest:** Kasia (10 of 16 apples), Damian (cap), Marcin (oranżada), then Grandpa's Ursus keys, then the cemetery memory archive.
- **Quiz:** Pani Halina and 13 signboards (`quiz.js`, `features.js`).
- **Church interior** with the Sołtys (`church.js`). The hidden Sołtys stands by the Białka woods.
- **Frodo** the dog follows Arek.
- **Minigames** (`minigames.js`), all with medals, records and retry:
  - race (with a ghost of your record run);
  - catch the pig;
  - eggs and dogs;
  - Kasia's shooting gallery with tin moorhens.
- Landmarks from photos: church, Koźlak windmill, shop, generic house, 4 wayside shrines, village sign.

## Audit 2026-09-27: what was found and fixed
1. **Skeet minigame was a stub.** It had texts, a flag and a HUD but no setup or update logic. Starting it crashed the game: an undefined intro, reading `MG.skeet.hit` every frame, and undefined `W/H/S` in the key handler. It has been rewritten as a real shooting gallery in `minigames.js`.
2. **The hidden Sołtys stood exactly on the "woods" quiz signboard.** NPCs win interaction priority, so quiz question 12 of 13 could never be answered, and Halina's title was unreachable. He was also hand-edited into `items.json`, so any re-run of `place_items.py` would have deleted him. He's now placed by `place_items.py`, 70 px from the sign, and an assertion stops NPCs landing on signboards.
3. **No bridges.** Roads crossing the Białka kept the river's "low" collision (and the woods' "tall" collision), so the church side of the village was reachable only by jumping. Roads and tracks are now always walkable.
4. **Boxed-in start.** The spawn and Kasia were inside a fenced garden; the garden fences had openings only next to roads. Fences now have a 16 px gate every 110 px. The spawn sits on the path by the shop. `place_items.py` flood-fills from the spawn, so every item is reachable without jumping.
5. The skeet flag sat inside the dog meadow. The shooting range now has its own venue in the new western area.
6. Hardcoded map coordinates were scattered across `render_map.py` and `place_items.py`. Everything now goes through `osm/geo.py` (`BBOX`, `P()`, `legacy_i()`), so the map can be resized safely.
7. Cleanup:
   - `features.js` now holds the quiz only; the minigames moved to `minigames.js`.
   - One `freshQ()` save factory replaces two duplicated copies.
   - A favicon was added (fixes the 404).
   - Full-map numpy arrays became windowed ones (the renderer would otherwise need hundreds of MB).
   - The ground layer is a 256-colour PNG (5.4 MB for 1.8× the area; the old one was 6.4 MB).
   - Tests read `ARK_URL`, and `run_all.py` finds a river column for the jump test automatically.
8. `docs/superpowers/` is untracked planning from another session. It's now in `.gitignore`, so it can't accidentally be published on Pages.

## 2026-09-27 follow-up (Tomek's requests)
- Frodo "blinked": `gen/build_frodo.py` pasted both walk frames into column 0 (missing `col * TILE`), so frame 2 was empty. Fixed and rebuilt.
- Positions: Kasia in far-east Kolonia (lat 52.26261, lon 22.88575); Damian far south by the village sign (52.25980, 22.86990); the shooting range sits next to Damian (hosted by Damian); Pani Halina moved to the church. Damian's cap is now placed 150–450 m from him.
- Wayside shrines/crosses: chosen automatically from real OSM road junctions by farthest-point selection (≥650 px apart, ≥260 px from landmarks/venues). See `SHRINE_NAMES` in render_map.py.
- A coordinate readout sits bottom-left (map x/y + lat/lon). `?x=..&y=..` starts the game at a position.
- Shop sprite remade from Tomek's photo (`references/shop_photo_2026-09-27.*`): peach walls, rust-brown metal roof, dormer, solar panels, SKLEP sign, three bikes and three regulars with beer on the bench. The old generic sprite is kept as `gen/lm_shop_v1_generic.png`.
- Splash/title screen: `docs/img/splash.png` is a pixel-art remake of the classic photo with the "Chłopków" sign, the linden and the church (source `gen/splash_raw.png`, ref `references/splash_sign_church_photo.png`). It is drawn by `drawSplash()` in game.js with a slow drift, sparkles and an outlined title.
- Codex tip: when Hermes reports "No Codex credentials" after a 429, run `hermes auth reset openai-codex` once the cooldown shows "ready to retry".

## Music (added 2026-09-28, `docs/js/music.js`)
- Procedural 8-bit Polish folk chiptune. There are no audio files: WebAudio synthesises pulse leads, a triangle bass, noise drums, a bagpipe drone, an organ and a bell. All six tunes are original.
- Which track plays where (`pick()` in the ark-ready block):

| Where | Track | Notes |
|---|---|---|
| Title | mazurka | |
| Village | krakowiak ↔ mazurka | alternate every 2 passes |
| Village, 25 s of standing still | pastorałka | lullaby |
| Minigames | oberek | |
| Church interior | chorał | organ hymn in D Dorian, 2 bell tolls on entry |
| Cemetery zone and memory archive | nokturn | Chopin-style nocturne in A minor, 1 bell toll |

- The cemetery zone is the OSM landuse rectangle around the cemetery POI (half-size 112×97 px), with hysteresis.
- Scene changes are audible:
  - game start plays the "hej!" fanfare;
  - leaving church or cemetery plays a short upbeat cue;
  - `celebrate()` plays the fanfare and `popToast()` the pickup blip.
- **Adaptive tempo** (the `TEMPO` object):
  - standing still: 0.4× the written BPM;
  - moving: slowly builds up to 1.3× (about 20 s walking, 10 s running);
  - stopping: falls back fast (about 1.5 s);
  - quiet pieces (chorał, nokturn, pastorałka) stay within `song.range` = [0.8, 1];
  - title: 0.8×.
- The scheduler keeps a time↔step frontier (`P.fT`/`P.fS`), so tempo changes never jump.
- **Frodo barks** ("HAU!" sound plus a speech bubble) whenever Arek touches him, with a 0.8 s cooldown. Tomek wrote "Marty"; we assumed the dog Frodo, so confirm.
- **K** or the note icon (bottom-left, above the coordinates) mutes the music. `?music=0` disables it.
- Debug: `MUSIC.tempo`, `MUSIC.current`, `MUSIC.barks`.
- `MUSIC.renderWav(name, passes)` exports a track to WAV at 0.8×.
- Covered by `test/music_test.py`: scene switching, tempo, bark, cemetery.
- Ideas: MIDI import, recognisable public-domain folk tunes (e.g. "Czerwone jabłuszko" for Kasia), accordion timbre, a recorded "hej!".

## Map extension + cemetery sunglasses (2026-09-28)
- **Map:** `osm/geo.py` BBOX grew 10% south (minlat 52.2585 -> 52.25585) and 20% east (maxlon 22.8872 -> 22.89292): 3896x5860 -> 4675x6446 px. The NW corner is the pixel origin, so all existing art coordinates stay valid. New OSM data came from Overpass via `python osm/fetch_osm.py 52.25585 22.8586 52.285 22.89292 --old 52.2585 22.8586 52.285 22.8872`, which merges by (type, id), never removes anything and (with `--old`) leaves the already-drawn area untouched.
- **Sunglasses:** `gen/build_arek_noglasses.py` writes `docs/img/arek_sheet_noglasses.png` (same layout as `arek_sheet.png`, only the glasses are repainted with skin + eyes; back views unchanged). `game.js` draws it while Arek is inside the cemetery zone (same rectangle + hysteresis as the cemetery music). `test/sunglasses_test.py` checks on in village / off in cemetery / on again after leaving.

## Global chat (Nostr, `docs/js/chat.js`) — fixed 2026-09-27
- NIP-28 channel `6432fea6…` (kind 40), messages are kind 42. Opt-in: nothing connects until GLOBAL CHAT is clicked.
- **Bug fixed:** the old code passed an array of filters to `subscribeMany` (nostr-tools 2.x takes one filter object), so relays rejected the request and no history ever showed. It now loads everything since 26 Sep 2026 00:00 Polish time (`HISTORY_SINCE`), up to 500 messages, then stays live.
- Clean display: day separators, grouped consecutive messages, own messages in green, invisible/control characters stripped, same text from the same author within 2 min shown once, messages over 280 chars or dated in the future ignored, one redraw per frame.
- Relays (write + read-back checked 2026-09-27): relay.primal.net, relay.nostr.net, relay.damus.io, plus two small open ones, **relay.chatbett.de** (strfry) and **wheat.happytavern.co** (GRAIN). The existing channel events were copied, unchanged and still signed, to the two small relays. Dropped: relay.nostr.band (dead), nos.lol (502).
- `test/chat_test.py` asserts history loads (needs network; `ARK_CHAT_OFFLINE=1` skips that part).

## Minigame tuning (in `minigames.js`)
- `MEDAL` thresholds (bronze/silver/gold): race — beat Damian / 15.5 s / 14.0 s; pig — 30 s / 15 s / 8 s; dogs — win / 28 s / 18 s; skeet — 10 / 12 / 14 hits.
- Race: Damian needs 8.1 s per lap (about 16.2 s total). Off-track speed is 0.55× (`HOOKS.speed`). The ghost is `Q.mg.race.ghost`, saved on each new record.
- Pig: speed goes from 175 down to 105 over about 26 s, with a sideways juke every 1.2–2 s.
- Dogs: states patrol → chase (92) → windup 0.45 s ("!") → lunge 235 for 0.5 s → rest 0.8 s. Speed rises 7% per egg.
- Skeet: 15 targets (12 launches, 3 of them doubles), 2 barrels, 0.9 s reload. Hit radius is 12 art px in screen space; targets draw at 1.6× size.

## Image generation
- Preferred: Codex GPT Image via Hermes (`gen/codex_gen.py`, run with `hermes-agent\.venv\Scripts\python.exe` and absolute paths). Local reference files only; nothing is uploaded. It hits the ChatGPT image quota (HTTP 429) now and then.
- PPQ (`gen/ppq_gen.py`, about $0.0115/image) needs public URLs. **Never upload real photos of people there.**
- Reference photos live in the gitignored `references/`. Never commit them.

## Next ideas
- Regenerate landmarks from photos as they arrive (`PHOTOS-WANTED.md`). The windmill photos so far came only as chat attachments; save the files for an exact re-render.
- The west and east map extensions have no quest content yet. Candidates: a Kolonia NPC, a second orchard, the świetlica as an interior.
- NPC walk cycles; a tractor-driving minigame after the keys; more sound effects (steps, jump, dog bark); see also `AUDIO.md` in the Grand Theft Tractor video project.
