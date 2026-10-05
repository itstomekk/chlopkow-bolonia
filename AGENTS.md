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
4. Do not publish real-person reference photos. Keep them in gitignored `references/`; do not upload private photos to image-generation services. Avoid unverified or defamatory claims about identifiable residents.
5. Distinguish local changes from the live build. Verify the exact commit/build before describing anything as deployed.

## Feature ownership during local J12 follow-up

| Path | Writer | Rule |
|---|---|---|
| `docs/data/j12-yard-props.json`, `docs/img/j12_prop_*.png` | J12 props generator / interactive J12 worker | Read accepted decisions; never rewrite shared map PNGs. |
| `docs/js/yard-props.js`, `gen/build_j12_props.py` | interactive J12 props worker | Static objects only; keep evidence and user identification separate. |
| `docs/js/world-life.js` | animal-placement worker during this follow-up | No concurrent parent edits; preserve animal identities and saves. |

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
