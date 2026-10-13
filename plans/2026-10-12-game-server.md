# Game server for the whole Chłopków Bolonia (plan, 2026-10-12)

Status: S1 + S2 DONE 2026-10-12 (Tomek chose: CPU = mean of the last 200 results, ŚREDNIA = all results). `chlopkow-api` is live and empty; the old `chlopkow-scores` is deleted. Sprint client is included in the release commit; remaining: S3, then S4 (own plan).

## Goal (Tomek, 2026-10-12)
One Cloudflare server for the whole game, not per feature. Every game that has a result gets:
- **NAJLEPSI** (best results, one row per player),
- **AKTUALNE** (latest results, a live feed, plus where your current result ranks),
- **ŚREDNIA** (average of all results), which one CPU always represents by replaying an average run.
Later the same server takes over the global chat (now Nostr) and live multiplayer.

## How the sprint works today (answer to Tomek's question)
- Score = time to 100 m, lower is better.
- Each correct LEFT/RIGHT alternation adds speed; speed drops a little every moment, so you must keep pressing.
- At a steady pace each press is worth about 1 metre (1.05 m), so 100 m is about 95 presses. Pressing faster = more metres per second, up to 11 m/s (about 10 presses/s). Same key twice = stumble (speed -30%).
- So yes: in practice one press ≈ one metre, the only skill is pressing fast and alternating cleanly. A "how far in 10 seconds" variant is possible on the same mechanics.

## Server shape: one Worker `chlopkow-api` + one D1 database `chlopkow`
| Path | Purpose | When |
|---|---|---|
| `GET /v1/games` | registry: id, name, unit, lower-is-better, limits | S1 |
| `GET /v1/games/:id/board?period=all\|week\|day` | `best` (per player), `recent` (latest 20), `average` {score, count, trace} | S1 |
| `POST /v1/games/:id/runs` | submit a result + trace + run proof, returns rank and percentile | S1 |
| `GET /v1/players/:deviceId` | your results across games | S3 |
| `/v1/chat` (Durable Object WebSocket room) | global chat moved from Nostr, history in D1 | later, own plan |
| `/v1/presence` (Durable Object) | who is in the village, positions for multiplayer | later, `plans/2026-10-04-multiplayer.md` |

Tables: `runs (id, game, device, name, char, score, trace, proof, mode, created, ip_hash, client, version)`, later `players`, `chat_messages`.

Identity: a random device id in localStorage now (so renaming keeps your history); later the Nostr key from the chat signs runs (stronger anti-cheat).

## The average CPU ("PRZECIĘTNIAK")
- Every run sends a short **trace**: fixed checkpoints of progress. Sprint: time at 10, 20, ... 100 m. Shooting: hits after each target. Pig / dogs / mowing: time of each step (catch, egg, strip %).
- The server averages each checkpoint over all results. The CPU replays that averaged trace, so it moves like a typical player (slow start, fast middle), not on a smooth line.
- In every board lobby one CPU slot is always PRZECIĘTNIAK (the global average); the other CPUs are spread around it (faster / slower).
- Map minigames (pig, dogs, skeet, ducks, mowing) show the average as a rival: a ghost or a bar "PRZECIĘTNY: 12.3 s".

## Client: one module `docs/js/scores.js`
Used by `board.js` and `minigames.js` (and later the quiz, BIJATYKA stats): `ARK.scores.board(id)`, `ARK.scores.submit(id, result)`, `ARK.scores.average(id)`. Offline or blocked = local records only, no errors. Tests always route the server to a fake.

## Lobby (done now)
Each player row: **name first**, then human / CPU, then character and keys.

## Steps
- **S1** server v2 `chlopkow-api` (registry, runs with traces, best / recent / average + average trace, device id, periods), local tests, deploy; retire the empty `chlopkow-scores`.
- **S2** `scores.js` + sprint: PRZECIĘTNIAK slot replaying the average trace, lobby/results with NAJLEPSI / AKTUALNE / ŚREDNIA.
- **S3** the five map minigames send results and show the average rival.
- **S4** separate plan: chat and presence on the same server.

## Open decisions
- Average over **all** results forever, or the last N (e.g. 200) so it follows how good players are now? (proposal: all-time mean for ŚREDNIA, last 200 for the CPU so it stays a fair rival)
- Moderation: a private delete endpoint for cheaters/offensive names (proposal: yes, token in the Hermes credential store).
