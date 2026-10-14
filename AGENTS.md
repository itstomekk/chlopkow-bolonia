# CHŁOPKÓW BOLONIA — project context

This is Tomek's active browser game project. The canonical folder is
`C:\Users\Lenovo\Hermes\projects\games\arek-w-chlopkowie`.

## Names and routing

- Canonical project ID: `chlopkow-bolonia`.
- “Chłopków Bolonia”, “Arek game”, and “Arek w Chłopkowie” all refer to this project.
- It is a browser-based pixel-art village adventure set in Chłopków, with a generated OSM map, JavaScript game systems, Python map/build tools, and Playwright tests.
- Live game: https://itstomekk.github.io/chlopkow-bolonia/
- GitHub repository: https://github.com/itstomekk/chlopkow-bolonia

## Before working

1. Read the hub files `C:\Users\Lenovo\.agents\WORKSPACE.md`, `PORTFOLIO.md`, and `PROJECT-ROUTING.md`.
2. Read `PLAN.md` and `HANDOFF.md`, then the relevant roadmap under `plans/`. The HANDOFF has historical sections: use its **CURRENT STATE** section and the active roadmap, not historical notes, when facts conflict.
3. Check `git status` before edits. This project has concurrent work; preserve unrelated dirty and untracked files. Never commit, push, or deploy unless Tomek explicitly asks.
4. Do not publish real-person reference photos. Keep them in gitignored `references/`; do not upload private photos to image-generation services. Exception (Tomek, 2026-10-12): reference photos of KOSTEK, PAWEŁ, DAREK, PIEKARZ, MAREK and WALDEK (PIEKARZ and MAREK added 2026-10-12, WALDEK 2026-10-13, same flow) may be sent to the openai-codex image generator for likeness; they still never go to git or public hosts. The loose `references/1.png`-`4.png` (copies in `references/arek/`) are photos of AREK, not PATRYK: the 2026-09-28 PATRYK rebuild was wrongly made from them (Tomek, 2026-10-13); PATRYK has no reference photos yet. Avoid unverified or defamatory claims about identifiable residents.
5. Distinguish local changes from the live build. Verify the exact commit/build before describing anything as deployed.

## Feature ownership during local J12 follow-up

| Path | Writer | Rule |
|---|---|---|
| `docs/data/j12-yard-props.json`, `docs/img/j12_prop_*.png` | J12 props generator / interactive J12 worker | Read accepted decisions; never rewrite shared map PNGs. |
| `docs/js/yard-props.js`, `gen/build_j12_props.py` | interactive J12 props worker | Static objects only; keep evidence and user identification separate. |
| `docs/js/world-life.js` | animal-placement worker during this follow-up | No concurrent parent edits; preserve animal identities and saves. |

## Board minigames and the game server

- Full-screen overlays: the page CSS sets explicit `display` on canvases/flex boxes, so the `hidden` attribute alone is not enough; set `style.display` too.
- An overlay opened from an NPC dialogue receives the same Enter that closed the dialogue: focus its primary button late and ignore keyboard clicks for ~400 ms after opening.
- Global scores live on Cloudflare (game server `cloud/api/README.md`, plan `plans/2026-10-12-game-server.md`). Browser tests must never write there: `test/isolated_browser_runner.py` routes the live URL to a fake; focused tests override it with a stateful fake. Test the server on `wrangler dev --local`; against production only reads and rejected writes.
- Run every browser test through `python test/isolated_browser_runner.py test/<name>_test.py`, never `python test/<name>_test.py` directly: direct runs publish "Test" arrivals to public Nostr and some tests (bercik/wiesio/iwona) fail on the loading splash without the runner's wait.

## Quiz and local knowledge

- Do not estimate quiz potential only by counting unused map landmarks. The project has accumulated researched/imported Chłopków history, place names, local facts, and cultural material across `docs/js/quiz.js`, `PLAN-2026-09-28-bolonia.md`, roadmaps, and prior sessions.
- Before proposing quiz content, inventory those existing facts as well as the map anchors. Separate source-verified facts from local recollections and folklore; retain citations and uncertainty, and do not attach claims to a particular private resident or home without evidence.
- Houses and other recognizable map spots can provide contextual quiz stops, but quiz content need not be limited to a one-question-per-landmark model.

## Recent related sessions

Use these transcripts for details that are not captured in the project files:

- [@session:default/20260927_230528_590855] — built and opened the local map editor; its edits were not yet integrated into map generation at that point.
- [@session:default/20260927_194752_ac9954] — broad game implementation session and handoff; contains recent player requests and implementation details.
- [@session:default/20260927_235050_218296] — Sokół Chłopków grass watermark; separate clean commit was reported deployed, while other local changes remained uncommitted.
- [@session:default/20260927_235836_22b75a] — question about character reference sprites; follow-up asked about generating more sprites and character selection, with answers still needed.

These are pointers, not a substitute for checking the current worktree and current project files.
