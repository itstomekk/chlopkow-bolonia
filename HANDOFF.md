# HANDOFF — Arek w Chłopkowie

Last updated: 2026-09-27 (audit + bigger map + minigame overhaul). The earlier per-session notes are in
`_archive/2026-09-27_HANDOFF-before-audit.md`.

## Where things are
- **Live:** https://itstomekk.github.io/arek-w-chlopkowie/ (GitHub Pages from `main:/docs`; every push to `main` redeploys in about 1 minute; browsers cache for 10 minutes).
- **Repo:** https://github.com/itstomekk/arek-w-chlopkowie (public)
- **Local:** `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie\`
- **Local server:** `python -m http.server 8765 --directory docs`. The VibeTV project's `.claude/launch.json` has an `arek-game` entry.
- **Tests:** `python test/run_all.py [URL]` runs all 10 Playwright play-tests. All 10 pass locally as of this update.

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
- NPC walk cycles; a tractor-driving minigame after the keys; sound (see `AUDIO.md` in the Grand Theft Tractor video project).
