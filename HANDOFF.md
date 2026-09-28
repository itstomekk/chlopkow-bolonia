# HANDOFF — Arek w Chłopkowie

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
- Procedural 8-bit Polish folk chiptune. There are no audio files: WebAudio synthesises pulse leads, a triangle bass, noise drums and a bagpipe drone.
- Four original tunes in the tracker format (`"NOTE:len"`, where len is in 16th steps, plus one chord symbol per bar):
  - village: **krakowiak** (2/4, G major, Góral C# in part B), alternating with a **mazurka** (3/4); the mazurka also plays on the title;
  - minigames: **oberek**;
  - church and memories: **pastorałka**.
- **Adaptive tempo** (the `TEMPO` object in `music.js`):
  - standing still: 0.5× the written BPM;
  - moving: the tempo builds up to 1.5× (about 14 s walking, 7 s running with Shift);
  - after stopping: it calms back to 0.5× in about 4 s;
  - the church lullaby is capped at 1×;
  - title and memory screens: a steady 0.8×.
- The scheduler keeps a time↔step frontier (`P.fT`/`P.fS`), so tempo changes never jump. `MUSIC.tempo` shows the current factor; `renderWav` renders at 0.8×.
- Every pass is re-arranged at random: section form, a second fiddle in thirds, grace notes, an octave-up part B, drum fills.
- `celebrate()` plays a "hej!" fanfare and `popToast()` plays a pickup blip; the music ducks under both.
- **K** mutes the music (remembered in `localStorage`); on touch screens, tap the note icon at the bottom left. `?music=0` disables the music for a session.
- Audio starts on the first key press or tap (browser autoplay rule).
- `MUSIC.renderWav(name, passes)` renders a track offline to WAV (for previews and videos).
- `test/music_test.py` is part of `run_all.py` (11 tests).
- Next: "swojski" sound upgrades (accordion/fiddle timbres, real public-domain folk tunes, optional MIDI import). See the options discussed in the session.

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
