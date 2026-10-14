/* chlopkow-api: one Cloudflare Worker (+ D1 `chlopkow`) for the whole Chłopków Bolonia game.
   Today: results, leaderboards and the average-player CPU for every minigame. Later: global chat and
   live presence (Durable Objects) on the same Worker — see plans/2026-10-12-game-server.md.

   GET  /health
   GET  /v1/games                         registry of games that accept results
   GET  /v1/games/:id/board?period=all|week|day
        -> { best: [...10 best players], recent: [...20 latest runs], average: { score, count },
             cpu: { score, count, trace }, players, period }
        best    = one row per player (device + name), their best result
        average = mean of ALL results in the period ("ŚREDNIA")
        cpu     = mean of the last 200 results and their checkpoint-by-checkpoint mean trace,
                  which the game's PRZECIĘTNIAK CPU replays
   POST /v1/games/:id/runs  { device, name, char, score, trace, proof, mode, client, version }
        -> { ok, score, rank, rankWeek, players, percentile, best }
   Anti-cheat is light on purpose (per-game plausibility + run proof + rate limit); see README.md.

   Separate from the game: a tiny private review store (art review pages on https://itstomekk.pages.dev).
   GET  /review/:id            -> { ok, id, rev, updated_at, doc }       header X-Review-Key required
   PUT  /review/:id  <json>    -> { ok, rev, updated_at }                 header X-Review-Key required, optional X-Base-Rev
   GET  /review/:id/history[?rev=N] -> last 20 saves (list, or one document)
   The key is per review; only its SHA-256 is stored (table `reviews`). Wrong/missing key or unknown id -> 401. */

const SPRINT_SPLITS = 10;
const GAMES = {
  sprint: {
    name: 'BIEG NA 100 METRÓW', unit: 'time', lower: true, min: 9.0, max: 75, traceLen: SPRINT_SPLITS,
    // trace = time (s, without penalties) at 10, 20, ... 100 m; proof = strides, false starts
    validate(score, trace, proof) {
      if (!Number.isInteger(proof.strides) || proof.strides < 70 || proof.strides > 600) return 'implausible run';
      if (!Array.isArray(trace) || trace.length !== SPRINT_SPLITS || !trace.every(Number.isFinite)) return 'bad trace';
      for (let i = 0; i < trace.length; i++) if (trace[i] - (i ? trace[i - 1] : 0) < .85) return 'implausible trace';
      const last = trace[trace.length - 1];
      if (last > score + .02 || last < score - 2.02) return 'trace does not match score';
      return null;
    },
  },
  // Map minigames join in step S3 (plans/2026-10-12-game-server.md); listed so ids are reserved.
  pig: { name: 'ŚWINKA PEPA', unit: 'time', lower: true, enabled: false },
  dogs: { name: 'JAJKA I PSY', unit: 'time', lower: true, enabled: false },
  skeet: { name: 'TARCZA', unit: 'hits', lower: false, enabled: false },
  ducks: { name: 'KACZKI', unit: 'hits', lower: false, enabled: false },
  mowing: { name: 'KOSZENIE BOISKA', unit: 'time', lower: true, enabled: false },
};
const ORIGINS = [/^https:\/\/itstomekk\.github\.io$/, /^http:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/];
const REVIEW_ORIGIN = 'https://itstomekk.pages.dev', REVIEW_MAX = 256 * 1024, REVIEW_KEEP = 20;
const BEST_N = 10, RECENT_N = 20, CPU_N = 200, RATE_N = 60, RATE_WINDOW_MS = 10 * 60 * 1000;
const PERIOD_MS = { all: 0, week: 7 * 864e5, day: 864e5 };

const cleanName = s => String(s || '').normalize('NFC').replace(/[\u0000-\u001f\u007f<>"'`\\]/g, '').replace(/\s+/g, ' ').trim().slice(0, 14);
const cleanChar = s => (/^[a-z0-9_-]{1,20}$/.test(String(s || '')) ? String(s) : '');
const okDevice = s => /^[A-Za-z0-9-]{8,64}$/.test(String(s || ''));
const round2 = v => Math.round(v * 100) / 100;

function cors(req) {
  const o = req.headers.get('Origin') || '';
  const h = { 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type', 'Access-Control-Max-Age': '86400', Vary: 'Origin' };
  if (ORIGINS.some(r => r.test(o))) h['Access-Control-Allow-Origin'] = o;
  return h;
}
const json = (req, body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...cors(req) } });

async function ipHash(req, env) {
  const ip = req.headers.get('CF-Connecting-IP') || 'unknown';
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${env.SALT || 'chlopkow'}|${ip}`));
  return [...new Uint8Array(d)].slice(0, 12).map(b => b.toString(16).padStart(2, '0')).join('');
}
const gameOf = id => (GAMES[id] && GAMES[id].enabled !== false ? GAMES[id] : null);

async function board(req, env, id, url) {
  const g = gameOf(id); if (!g) return json(req, { ok: false, error: 'unknown game' }, 404);
  const period = PERIOD_MS[url.searchParams.get('period')] !== undefined ? url.searchParams.get('period') : 'all';
  const since = PERIOD_MS[period] ? Date.now() - PERIOD_MS[period] : 0, ord = g.lower ? 'ASC' : 'DESC';
  const [best, recent, avg, players, last] = await env.DB.batch([
    env.DB.prepare(`SELECT name, char, score, at FROM (
        SELECT name, char, score, created AS at, ROW_NUMBER() OVER (PARTITION BY device, name ORDER BY score ${ord}, created ASC) AS rn
          FROM runs WHERE game = ?1 AND created >= ?2) WHERE rn = 1 ORDER BY score ${ord}, at ASC LIMIT ?3`).bind(id, since, BEST_N),
    env.DB.prepare('SELECT name, char, score, created AS at FROM runs WHERE game = ?1 AND created >= ?2 ORDER BY created DESC LIMIT ?3').bind(id, since, RECENT_N),
    env.DB.prepare('SELECT AVG(score) AS score, COUNT(*) AS count FROM runs WHERE game = ?1 AND created >= ?2').bind(id, since),
    env.DB.prepare("SELECT COUNT(DISTINCT device || '|' || name) AS n FROM runs WHERE game = ?1 AND created >= ?2").bind(id, since),
    env.DB.prepare('SELECT score, trace FROM runs WHERE game = ?1 ORDER BY created DESC LIMIT ?2').bind(id, CPU_N),
  ]);
  // CPU benchmark: mean of the last 200 results and the checkpoint-by-checkpoint mean of their traces
  const rows = last.results, cpu = { score: null, count: rows.length, trace: null };
  if (rows.length) {
    cpu.score = rows.reduce((s, r) => s + r.score, 0) / rows.length;
    const traces = rows.map(r => { try { return JSON.parse(r.trace); } catch (e) { return null; } }).filter(t => Array.isArray(t) && t.length === g.traceLen);
    if (traces.length) cpu.trace = Array.from({ length: g.traceLen }, (_, i) => round2(traces.reduce((s, t) => s + t[i], 0) / traces.length));
    cpu.score = round2(cpu.score);
  }
  const a = avg.results[0] || {};
  return json(req, { ok: true, game: id, period, best: best.results, recent: recent.results,
    average: { score: a.count ? round2(a.score) : null, count: a.count || 0 }, cpu, players: (players.results[0] || {}).n || 0 });
}

async function submit(req, env, id) {
  const g = gameOf(id); if (!g) return json(req, { ok: false, error: 'unknown game' }, 400);
  let b; try { b = await req.json(); } catch (e) { return json(req, { ok: false, error: 'bad json' }, 400); }
  const name = cleanName(b && b.name), device = String(b && b.device || ''), score = Number(b && b.score);
  const trace = Array.isArray(b && b.trace) ? b.trace.map(Number) : null, proof = b && b.proof && typeof b.proof === 'object' ? b.proof : {};
  if (!okDevice(device)) return json(req, { ok: false, error: 'device required' }, 400);
  if (!name) return json(req, { ok: false, error: 'name required' }, 400);
  if (!Number.isFinite(score) || score < g.min || score > g.max) return json(req, { ok: false, error: 'implausible score' }, 422);
  const bad = g.validate(score, trace, proof); if (bad) return json(req, { ok: false, error: bad }, 422);
  const ip = await ipHash(req, env), now = Date.now();
  const recent = await env.DB.prepare('SELECT COUNT(*) AS n FROM runs WHERE ip = ?1 AND created > ?2').bind(ip, now - RATE_WINDOW_MS).first();
  if (recent && recent.n >= RATE_N) return json(req, { ok: false, error: 'slow down' }, 429);
  const s = round2(score), cmp = g.lower ? '<' : '>', agg = g.lower ? 'MIN' : 'MAX';
  await env.DB.prepare('INSERT INTO runs (game, device, name, char, score, trace, proof, mode, created, ip, client, version) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12)')
    .bind(id, device, name, cleanChar(b.char), s, JSON.stringify(trace.map(round2)),
      JSON.stringify({ strides: proof.strides, falseStarts: Number.isInteger(proof.falseStarts) ? proof.falseStarts : null }),
      String(b.mode || '').slice(0, 20), now, ip, String(b.client || '').slice(0, 40), Number.isInteger(b.version) ? b.version : 1).run();
  const rankQ = since => env.DB.prepare(`SELECT COUNT(*) AS n FROM (SELECT ${agg}(score) AS b FROM runs WHERE game = ?1 AND created >= ?2 AND NOT (device = ?3 AND name = ?4) GROUP BY device, name) WHERE b ${cmp} ?5`).bind(id, since, device, name, s);
  const [rAll, rWeek, worse, total, players, best] = await env.DB.batch([
    rankQ(0), rankQ(now - PERIOD_MS.week),
    env.DB.prepare(`SELECT COUNT(*) AS n FROM runs WHERE game = ?1 AND score ${g.lower ? '>' : '<'} ?2`).bind(id, s),
    env.DB.prepare('SELECT COUNT(*) AS n FROM runs WHERE game = ?1').bind(id),
    env.DB.prepare("SELECT COUNT(DISTINCT device || '|' || name) AS n FROM runs WHERE game = ?1").bind(id),
    env.DB.prepare(`SELECT ${agg}(score) AS b FROM runs WHERE game = ?1 AND device = ?2 AND name = ?3`).bind(id, device, name),
  ]);
  const n = x => (x.results[0] || {}).n || 0, tot = n(total);
  return json(req, { ok: true, score: s, rank: n(rAll) + 1, rankWeek: n(rWeek) + 1, players: n(players),
    percentile: tot > 1 ? Math.round(n(worse) / (tot - 1) * 100) : 100, best: (best.results[0] || {}).b });
}

// ---- review store (separate from the game scores) ----
function reviewCors(req, env) {
  const o = req.headers.get('Origin') || '';
  const h = { 'Access-Control-Allow-Methods': 'GET, PUT, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, X-Review-Key, X-Base-Rev', 'Access-Control-Max-Age': '86400', Vary: 'Origin' };
  if (o === REVIEW_ORIGIN || (env.REVIEW_EXTRA_ORIGIN && o === env.REVIEW_EXTRA_ORIGIN)) h['Access-Control-Allow-Origin'] = o;   // REVIEW_EXTRA_ORIGIN: local dev only (.dev.vars)
  return h;
}
const rjson = (req, env, body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex', ...reviewCors(req, env) } });
async function sha256hex(s) {
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
}
function sameHex(a, b) { if (a.length !== b.length) return false; let x = 0; for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i); return x === 0; }

async function review(req, env, id, history, url) {
  try {
    const key = req.headers.get('X-Review-Key') || '';
    const row = key && key.length <= 200 ? await env.DB.prepare('SELECT key_hash, doc, rev, updated_at FROM reviews WHERE id = ?1').bind(id).first() : null;
    if (!row || !sameHex(row.key_hash, await sha256hex(key))) return rjson(req, env, { ok: false, error: 'unauthorized' }, 401);
    if (history) {
      if (req.method !== 'GET') return rjson(req, env, { ok: false, error: 'method not allowed' }, 405);
      const rev = url.searchParams.get('rev');
      if (rev !== null) {
        const h = await env.DB.prepare('SELECT rev, saved_at, doc FROM review_history WHERE review_id = ?1 AND rev = ?2').bind(id, Number(rev)).first();
        return h ? rjson(req, env, { ok: true, rev: h.rev, saved_at: h.saved_at, doc: JSON.parse(h.doc) }) : rjson(req, env, { ok: false, error: 'not found' }, 404);
      }
      const l = await env.DB.prepare('SELECT rev, saved_at, LENGTH(doc) AS bytes FROM review_history WHERE review_id = ?1 ORDER BY rev DESC LIMIT ?2').bind(id, REVIEW_KEEP).all();
      return rjson(req, env, { ok: true, history: l.results });
    }
    if (req.method === 'GET') return rjson(req, env, { ok: true, id, rev: row.rev, updated_at: row.updated_at, doc: JSON.parse(row.doc) });
    if (req.method !== 'PUT') return rjson(req, env, { ok: false, error: 'method not allowed' }, 405);
    const declared = Number(req.headers.get('Content-Length'));
    if (declared > REVIEW_MAX) return rjson(req, env, { ok: false, error: 'too large' }, 413);
    const text = await req.text();
    if (new TextEncoder().encode(text).length > REVIEW_MAX) return rjson(req, env, { ok: false, error: 'too large' }, 413);
    let doc; try { doc = JSON.parse(text); } catch (e) { return rjson(req, env, { ok: false, error: 'bad json' }, 400); }
    if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return rjson(req, env, { ok: false, error: 'document must be a JSON object' }, 400);
    const base = req.headers.get('X-Base-Rev'), now = Date.now(), body = JSON.stringify(doc);
    const [upd] = await env.DB.batch([
      env.DB.prepare('UPDATE reviews SET doc = ?2, rev = rev + 1, updated_at = ?3 WHERE id = ?1 AND (?4 IS NULL OR rev = ?4)').bind(id, body, now, base === null || base === '' ? null : Number(base)),
      env.DB.prepare('INSERT INTO review_history (review_id, rev, doc, saved_at) SELECT id, rev, doc, updated_at FROM reviews WHERE id = ?1 AND updated_at = ?2 AND doc = ?3').bind(id, now, body),
      env.DB.prepare('DELETE FROM review_history WHERE review_id = ?1 AND rev <= (SELECT rev FROM reviews WHERE id = ?1) - ?2').bind(id, REVIEW_KEEP),
    ]);
    if (!upd.meta.changes) {
      const cur = await env.DB.prepare('SELECT rev, updated_at FROM reviews WHERE id = ?1').bind(id).first();
      return rjson(req, env, { ok: false, error: 'conflict', rev: cur.rev, updated_at: cur.updated_at }, 409);
    }
    const cur = await env.DB.prepare('SELECT rev, updated_at FROM reviews WHERE id = ?1').bind(id).first();
    return rjson(req, env, { ok: true, rev: cur.rev, updated_at: cur.updated_at });
  } catch (e) {
    return rjson(req, env, { ok: false, error: 'server error' }, 500);
  }
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: url.pathname.startsWith('/review/') ? reviewCors(req, env) : cors(req) });
    try {
      if (url.pathname === '/health') return json(req, { ok: true, service: 'chlopkow-api' });
      if (url.pathname === '/v1/games' && req.method === 'GET') {
        return json(req, { ok: true, games: Object.entries(GAMES).filter(([, g]) => g.enabled !== false).map(([id, g]) => ({ id, name: g.name, unit: g.unit, lower: g.lower, traceLen: g.traceLen || 0 })) });
      }
      const rm = url.pathname.match(/^\/review\/([a-z0-9][a-z0-9-]{0,39})(\/history)?$/);
      if (rm) return await review(req, env, rm[1], !!rm[2], url);
      const m = url.pathname.match(/^\/v1\/games\/([a-z0-9_-]{1,20})\/(board|runs)$/);
      if (m && m[2] === 'board' && req.method === 'GET') return await board(req, env, m[1], url);
      if (m && m[2] === 'runs' && req.method === 'POST') return await submit(req, env, m[1]);
      return json(req, { ok: false, error: 'not found' }, 404);
    } catch (e) {
      return json(req, { ok: false, error: 'server error' }, 500);
    }
  },
};
