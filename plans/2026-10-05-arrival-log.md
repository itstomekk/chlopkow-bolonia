# Village arrival log: approved design and implementation plan

## Approved scope

Tomek chose to add arrival notices alongside ordinary chat messages, not replace chat. Confirming a player name and entering play produces a signed public Nostr notice in the existing NIP-28 channel. Notices appear in turquoise with a timestamp, in the same rolling history as chat. Several Polish village greetings use the actual sanitized player name, without guessing gender. Reopening the panel, reconnecting or returning from a dialogue must not generate more notices. Reloading and entering again is a new visit. The log is an arrival history, not proof that somebody remains online.

Use the existing guest identity and pinned nostr-tools dependency. Do not publish test visitors to public relays. The name form must clearly disclose that the name and arrival are public via Nostr. Preserve chat, saves, title/character picker, minimized preference, keyboard isolation and map/dialogue overlay behavior. Publish even when the panel is minimized; do not reopen it. Failed publication must not block play or claim a successful persisted log; retry the same signed event on a later connection/online event, bounded and without an endless retry loop. Avoid storing private keys anywhere new.

## Ownership and files

One implementation worker owns `docs/js/chat.js`, the minimal lifecycle event and disclosure in `docs/js/game.js`, `test/arrival_log_test.py`, and registration in `test/run_all.py`. Parent owns this plan, `PLAN.md`, `HANDOFF.md`, `DEVELOPMENT.md`, review and independent verification. No edits to map/imagery/world-life or unrelated untracked artifacts. Tomek subsequently authorized push in this conversation. After independent verification, the parent may commit and push only this feature's files, then verify the exact remote commit and Pages build. The implementation worker must not commit or push.

## Ordered implementation

- [x] Add a browser regression using the real name form and a controlled Nostr-tools transport, isolated from public relays. Cover title/blank names, actual submit, two clients, historic replay, minimized panel, duplicate relay echoes, regular chat, offline/failure then retry, reload/resume, and desktop/mobile styling. Verify RED before implementation.
- [x] Dispatch a narrow game-entry event after valid entry into play. Keep identity sanitized by existing code and announce once per document visit, including saved-name continuation. Handle the legacy missing-name continuation form without accidental duplicate notices.
- [x] Extend current kind-42 events with explicit arrival and session tags. Preserve ordinary messages. Render validated arrival data with its own class, one line with timestamp, never trusted HTML. Require explicit arrival marker and valid nonempty name. Do not classify ordinary text by phrase matching.
- [x] Queue one stable signed arrival event while transport initializes. Publish independently of panel state, coalesce in-flight attempts, show only confirmed accepted events, reuse the event for retry and deduplicate echoes/history by ID. Retry only on explicit reconnection/online triggers with bounded attempts.
- [x] Add the public-Nostr disclosure to the form; retain its responsive layout. Register the focused test. Run syntax, focused arrival, existing chat overlay, name/save and title/branding regressions with page-error capture.
- [x] Parent reviews exact diff, independently reruns tests and visually checks desktop/mobile screenshots. Update PLAN then HANDOFF and DEVELOPMENT with actual verification and local-only status.

## Verification commands

Serve this repository's `docs/` on a dedicated loopback port; health-check `index.html`, `js/chat.js`, `js/game.js` and `map.json`. Run `node --check docs/js/chat.js`, `node --check docs/js/game.js`, and `ARK_URL=http://127.0.0.1:8797/index.html python test/arrival_log_test.py`. Regressions: `chat_overlay_test.py`, `save_name_test.py`, `branding_flow_test.py` and `character_selection_test.py`. Evidence must distinguish controlled transport acceptance from live public relay persistence. Public relay publication is deferred until authorized release.
