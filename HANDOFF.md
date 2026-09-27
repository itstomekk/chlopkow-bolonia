# HANDOFF — Arek w Chłopkowie

Last updated: 2026-09-27

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
- Add the świetlica (community hall) and wayside shrines as landmarks.
- Walk cycles for the NPCs (they are single static poses now).
- Tractor-driving minigame after getting the keys, bridging into the *Grand Theft Tractor* video.
- Sound: the video's `AUDIO.md` brief has the music direction.
