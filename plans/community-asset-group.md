# Community asset group (decided 2026-10-10)

Idea (Tomek): a separate Telegram group where community members give feedback on generated game assets
(houses, village recreation from procedural to generated art). Hermes posts proposals, members comment, Hermes iterates.

## Decisions so far
- Start as a TEST group with Tomek only, to iterate on the mechanics before inviting anyone.
- Member scope: ASSETS ONLY (buildings, village recreation, improving existing ones).
  Members have NO say over missions, quests, mechanics or other big design. Tomek is final judge.
- Lore pop-ups are a later question; anything mentioning real people or addresses is checked with Tomek first.

## Proposed mechanics (to test, not final)
- 1 question per post, 3 to 4 numbered variants shown in context on the map.
- Fixed voting window (e.g. 10:00 to 22:00), reactions or poll; Hermes tallies next morning.
- Facts (colour, position) need evidence/local knowledge; taste can be voted.
- Cadence 3 to 4 posts a week to start, not daily.
- Decision log kept in this folder (question, result, change applied).
- Weekly summary to the Arek topic in HERMES CONTROL CENTER.

## Status (2026-10-10)
- Group created via Tomek's Telegram user session: "Arek w Chłopkowie - wioska (test)", forum, Bot API chat id -1004470765332.
- @hermestomek_bot added as admin (manage topics verified via Bot API). Topic "Testy assetów" = thread 3, first message sent.
- Only Tomek is a member. Do not add anyone until the mechanics are tested.
- config.yaml allowed_chats / group_allowed_chats updated (backup config.yaml.bak-20261010-arek-group); takes effect after gateway restart, which needs Tomek's yes.
- Per-topic project binding for this group is not set yet; add a channel_overrides entry for the asset topic after restart.
