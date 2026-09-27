# HANDOFF — Arek w Chłopkowie

Last updated: 2026-09-27

## 2026-09-27 (cloud, church interior)
- **You can now enter the church.** Space/E at its door fades into `docs/js/church.js`, a 320×440 room drawn in code from Tomek's interior photos:
  - pews, red aisle carpet, marble presbytery and steps;
  - altar with lace cloth, four gold candles (animated flames), ambo and a processional cross;
  - Sacred Heart painting, stained glass and murals;
  - Lourdes Mary niche, flags, bishop's banner, confessional, holy water font;
  - jubilee "100" flowers.
  Walk out through the bottom door to get back to the church door.
- **New NPC: the Sołtys** (village head), drawn in code from Tomek's photo: grey hair, glasses, brown pinstripe suit, harvest bread. He stands by the ambo and his lines depend on Kasia's quest.
- `Q.churchSeen` shows the intro line once. Saving while inside stores the outdoor position.
- Tests: `test/church_test.py` is new. `quest_test.py` and `jump_test.py 1662 1747` still pass.
- **AI art complete:** Codex GPT Image 2 medium generated `backwall`, `altar`, `candles`, `cross`, `ambo`, `banner`, `mary`, `flags`, `flowers100`, `pew`, `confessional`, `font`, and `soltys`. `gen/prep_church_sprite.py` processed them into `docs/img/church/`; the game loads the manifest automatically. Raw outputs are in ignored `gen/raw/`.
- Visual QA passed in the local room screenshots; the pew was regenerated to fit its wide, low game box. Tests: `church_test.py`, `quest_test.py`, and `jump_test.py 1662 1747` each end with `errors []`.
- Six church interior photos and the Sołtys photo are in ignored `references/`; never commit them. The Sołtys photo is used only with Codex, not PPQ.
- Codex did not report USD pricing. Sixteen successful generations (including three replacement drafts) were logged with `cost_usd: null` in Hermes image telemetry; actual cost is unknown.
- "100" = **100 years of the parish** (confirmed by Tomek). The Sołtys agreed to appear in the game.
- **AI art hook:** any PNG in `docs/img/church/<name>.png` replaces the hand-drawn piece. The names and boxes are in `CHURCH_PIECES` (`church.js`). `gen/prep_church_sprite.py` keys, crops and saves the images. **Hermes runbook: `gen/HERMES-PROMPT.md`.**
- Repo skill for adding more rooms: `.claude/skills/add-interior/SKILL.md`.
- **Merged to `main` and live (2026-09-27).** Merged alongside the quiz/minigames work: quiz signs, flags and minigame draws are hidden inside the church.
  The church door stays shut while a quiz or minigame runs (`HOOKS.busy`).
- AI church art loads only the names listed in `docs/img/church/manifest.json`, so there are no 404s. `prep_church_sprite.py` keeps the list updated.
- `test/features_test.py` reports one 404 that already exists on `main` (not from the church, probably a favicon).

## Latest session — 2026-09-27 (Frodo companion)
- Frodo's first-pass procedural atlas was replaced with a GPT Image 2 pixel-art sheet based on six supplied local reference photos (`gen/frodo_sheet_raw.png` → `gen/build_frodo.py` → `docs/img/frodo.png`). The reference photos remain outside the repo.
- Frodo follows Arek with collision-aware movement, appears in the y-sorted scene, and repositions safely when entering or leaving the church. His location is not added to save data.
- Verified with `test/frodo_test.py` (following, rendering, church transition), `test/quest_test.py`, and `test/jump_test.py 1312 1670`; no browser errors in these runs.

## Latest session — 2026-09-27 (village house + wayside shrines)
- Generated one generic house sprite plus four distinct cross/shrine sprites with Codex GPT Image 2 (`gen/lm_house_generic.png`, `gen/lm_cross_iron.png`, `gen/lm_shrine_stone.png`, `gen/lm_shrine_white.png`, `gen/lm_shrine_fenced.png`). The house is not a literal copy of any one reference house.
- `osm/render_map.py` replaces OSM house way 1095382322 with the generic sprite and places shrines at four nearby-road junctions. The user photos have no GPS metadata; these locations are approximate, not verified real sites.
- Rebuilt the entrance sign from a GPT Image 2 medium pixel-art draft (`gen/lm_village_sign_raw.png`), then keyed the magenta background and overlaid exact `CHŁOPKÓW` bitmap lettering in `gen/build_village_sign.py`. The in-game sign now has the reference's green upper panel, pale lower skyline panel, metal frame, and two posts. Codex did not report a USD cost.
- Regenerated the map and checked the house, four shrines/crosses, and sign in a local browser at gameplay zoom. The sign is legible and beside the road; the landmarks remain readable and no visible road/player-route obstruction was found. The house remains consistent with nearby rural homes. Shrine locations are still approximate because the photos lack GPS metadata.
- `test/village_sign_test.py`, `quest_test.py`, `features_test.py`, `church_test.py`, `frodo_test.py`, and `jump_test.py 1312 1670` all pass locally; browser error arrays were empty. No commit or push has been made.

## Latest session — 2026-09-27 (cemetery archive + deploy prep)
- Generated three respectful cemetery-memory illustrations from the user-supplied old photos with Codex GPT Image 2 medium (all responses reported `low` quality). The scenes avoid recognizable faces and readable inscriptions. `gen/build_cemetery_memories.py` removes the magenta background, crops, palette-reduces and nearest-neighbor pixelates them into `docs/img/memories/`; original photographs are not shipped.
- After Arek receives the tractor keys, the end screen now shows the illustrations one at a time with short photo-grounded trivia. Enter/Space or tap advances; Escape skips. English and Polish copy are included.
- `test/cemetery_memories_test.py` drives the actual win transition, verifies all three slides render in order, then verifies return to play. Visual review of the 1280×720 screens found no clipping. Cost was not reported by Codex; it is unknown, not estimated.
- Along with this archive work, the previously approved generic house and four wayside shrine assets are rendered in the map. Renderer, `features_test.py`, `quest_test.py`, `jump_test.py 1662 1747`, `church_test.py`, `frodo_test.py`, `play_test.py`, and `cemetery_memories_test.py` have passed locally. `git diff --check` passes. No commit or push has been made; several unrelated Frodo changes were already pending and must not be swept in inadvertently.

## Where things are
- Live: https://itstomekk.github.io/arek-w-chlopkowie/ (GitHub Pages, branch `main`, folder `/docs`). Every push to `main` redeploys.
- Repo: https://github.com/itstomekk/arek-w-chlopkowie (public)
- Local: `C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie\`
- Local server: `python -m http.server 8765 --directory docs`. The VibeTV project's `.claude/launch.json` has an `arek-game` entry.

## State
- Done and verified by headless play-tests (`test/quest_test.py`, `test/jump_test.py`, also run against the live URL):
  - map from OSM;
  - Arek 4-direction walk cycle;
  - NPCs Kasia, Marcin, Damian and Grandpa;
  - apples, cap and orangeade quests plus the ending;
  - jumping over low obstacles;
  - minimap, autosave, touch controls, PL/EN.
- Reference photos of Arek (4 new + 7 older) and the church live in `references/`. That folder is **gitignored and must never be committed**.

## Image generation
- Preferred: Codex GPT Image via Hermes (`gen/codex_gen.py`, run with the Hermes venv python). Local reference files, nothing uploaded. It hits the ChatGPT image quota (HTTP 429) now and then.
- Fallback: PPQ (`gen/ppq_gen.py`, about $0.0115/image). It needs a public URL for references (Blossom upload). **Do not upload real photos of people that way.** The auto-mode classifier blocked it, and Tomek chose Codex for photos.
- OpenRouter had no credits (HTTP 402) on 2026-09-27.

## 2026-09-27 (later): quiz + minigames
- `docs/js/quiz.js` holds 13 questions from pl.wikipedia (Chłopków, mazowieckie), each bound to a board spot in `items.json`.
- `docs/js/features.js` covers Pani Halina (new NPC, `gen/npc_src/halina.png`), the signboards, the quiz modal, and the minigames race/pig/dogs. It plugs into `HOOKS` in game.js.
- Venues are drawn by render_map.py: TRACK (north oval, bale walls at 200°/330°), CORRAL (below the windmill), MEADOW (south of the street).
- The windmill sprite was regenerated from a text description of Tomek's photos (the photos came only as chat attachments, not files). The old generic version is `gen/lm_windmill_v1_generic.png`.
- Tests: `test/features_test.py` (quiz and minigames), `quest_test.py`, and `jump_test.py 1340 1645` (use a river column without a riverside tree).

## Next ideas
- Regenerate landmarks from Tomek's photos as they arrive (list in `PHOTOS-WANTED.md`).
- Add the świetlica (community hall) and wayside shrines as landmarks. The świetlica could be the next interior; see the add-interior skill.
- Put a priest NPC in the church, and add a harvest-festival (dożynki) scene with the Sołtys and Kasia's pie.
- Walk cycles for the NPCs (they are single static poses now).
- Tractor-driving minigame after getting the keys, bridging into the *Grand Theft Tractor* video.
- Sound: the video's `AUDIO.md` brief has the music direction.
