# chlopkow-api: the game server (Cloudflare)

One Worker + one D1 database for the whole Chłopków Bolonia game. Plan and roadmap: `plans/2026-10-12-game-server.md`.

- Live: `https://chlopkow-api.kolotom.workers.dev` (Worker `chlopkow-api`, D1 `chlopkow`, account subdomain `kolotom`, secret `SALT`).
- Code `src/index.js`, schema `schema.sql`, config `wrangler.jsonc`.
- Game client: `docs/js/scores.js` (`ARK.scores`), used by `docs/js/board.js`. URL flags: `?scores=off`, `?scores=<url>`.
- Today: results + leaderboards for the 100 m sprint. Reserved ids for S3: pig, dogs, skeet, ducks, mowing. Later: chat and presence (Durable Objects) on the same Worker.

## API

| Call | Result |
|---|---|
| `GET /health` | `{ ok, service }` |
| `GET /v1/games` | enabled games: id, name, unit, lower, traceLen |
| `GET /v1/games/:id/board?period=all\|week\|day` | `best` (10 players, best result each; player = device + name), `recent` (20 latest), `average` {score, count} = ŚREDNIA of all results, `cpu` {score, count, trace} = mean of the last 200 results and their checkpoint-wise mean trace (PRZECIĘTNIAK), `players` |
| `POST /v1/games/:id/runs` | `{ device, name, char, score, trace, proof, mode, client, version }` -> `{ ok, score, rank, rankWeek, percentile, players, best }` |

Sprint trace = time (s, without penalties) at 10, 20, ... 100 m.

CORS: `https://itstomekk.github.io`, `http://127.0.0.1:*`, `http://localhost:*`.

## Anti-cheat (light for now)

- Sprint: 9.0-75 s, 70-600 strides, every 10 m split at least 0.85 s, trace end within the score minus up to 2 s of penalty.
- Names cleaned (no markup, 14 chars), device id required, scores rounded to 0.01.
- Rate limit 60 results / 10 min per IP; the IP is stored only as a salted SHA-256 prefix.
- A forged request with plausible numbers still gets in. Next: runs signed with the chat's Nostr key, moderation endpoint.

## Operate

Credentials: `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` in the environment; never print them.

```bash
cd cloud/api
python run_local_checks.py      # local wrangler dev + local D1: API test, browser e2e, sprint regression; stops everything
npx wrangler@4 deploy           # production
npx wrangler@4 d1 execute chlopkow --remote --command "SELECT name, score, created FROM runs WHERE game='sprint' ORDER BY score LIMIT 10"
```

`test_api.py` and `e2e_local.py` write rows: local only (`test_api.py` refuses a workers.dev URL). Browser regressions route the live URL to a fake in `test/isolated_browser_runner.py`.
On Windows, stop `wrangler dev` with `taskkill /PID <pid> /T /F`; a plain kill leaves `workerd.exe` children listening and respawning.
