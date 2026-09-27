# HANDOFF — Arek w Chłopkowie

Last updated: 2026-09-27

## Latest session — 2026-09-27 (cloud, church interior)
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
- **Not done:** AI (GPT) versions of the interior and the Sołtys. The cloud session can't use Codex (OpenAI returns 403 to cloud IPs) and has no PPQ key. The ready prompts and integration steps are in `gen/PROMPTS-church.md`.
- The pasted reference photos were not saved as files. Chat images don't reach the container. Tomek must copy them to `references/` locally.
- "100" = **100 years of the parish** (confirmed by Tomek). The Sołtys agreed to appear in the game.
- **AI art hook:** any PNG in `docs/img/church/<name>.png` replaces the hand-drawn piece. The names and boxes are in `CHURCH_PIECES` (`church.js`). `gen/prep_church_sprite.py` keys, crops and saves the images. **Hermes runbook: `gen/HERMES-PROMPT.md`.**
- Repo skill for adding more rooms: `.claude/skills/add-interior/SKILL.md`.
- The work is on branch `claude/determined-mccarthy-b9096e`. Merging to `main` makes it live on Pages.

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

## Next ideas
- Regenerate landmarks from Tomek's photos as they arrive (list in `PHOTOS-WANTED.md`).
- Add the świetlica (community hall) and wayside shrines as landmarks. The świetlica could be the next interior; see the add-interior skill.
- Put a priest NPC in the church, and add a harvest-festival (dożynki) scene with the Sołtys and Kasia's pie.
- Walk cycles for the NPCs (they are single static poses now).
- Tractor-driving minigame after getting the keys, bridging into the *Grand Theft Tractor* video.
- Sound: the video's `AUDIO.md` brief has the music direction.
