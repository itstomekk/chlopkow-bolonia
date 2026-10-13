/* Global scores client for every Chłopków Bolonia game (server: cloud/api, Cloudflare Worker `chlopkow-api`).
   ARK.scores.board(game)          -> Promise<{ status, best, recent, average, cpu, players }> (cached per game)
   ARK.scores.cached(game)         -> last board or null
   ARK.scores.submit(game, run)    -> Promise<{ ok, rank, rankWeek, percentile, ... } | null>
   ARK.scores.enabled()            -> sending switched on (lobby checkbox) and a server is configured
   ARK.scores.device               -> random id of this browser; a player = device + name
   URL flags: ?scores=off disables, ?scores=<url> points at another server (a local `wrangler dev`).
   Offline or blocked: games keep their local records and nothing throws. Tests route the URL to a fake
   (test/isolated_browser_runner.py), so regressions never write to production. */
'use strict';
(() => {
  const DEFAULT_URL = 'https://chlopkow-api.kolotom.workers.dev';
  const LS_SEND = 'ark_scores_send_v1', LS_DEVICE = 'ark_device_v1';
  const read = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } };
  const URL_ = (() => {
    const q = new URLSearchParams(location.search).get('scores');
    if (q === 'off') return null;
    if (q && /^https?:\/\//.test(q)) return q.replace(/\/$/, '');
    return (window.ARK_SCORES_URL || DEFAULT_URL).replace(/\/$/, '');
  })();
  function device() {
    let d = read(LS_DEVICE, null);
    if (typeof d !== 'string' || !/^[A-Za-z0-9-]{8,64}$/.test(d)) {
      d = (crypto.randomUUID ? crypto.randomUUID() : `d-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`);
      write(LS_DEVICE, d);
    }
    return d;
  }
  function call(path, body) {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), 6000);
    return fetch(URL_ + path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ctl.signal } : { signal: ctl.signal })
      .then(r => r.json()).finally(() => clearTimeout(t));
  }
  const cache = {}, listeners = new Set();
  const notify = game => listeners.forEach(f => { try { f(game); } catch (e) { /* listener */ } });
  function board(game) {
    if (!URL_) return Promise.resolve(null);
    const c = cache[game] = cache[game] || { status: 'loading', best: [], recent: [], average: { score: null, count: 0 }, cpu: { score: null, count: 0, trace: null }, players: 0 };
    if (c.status !== 'ok') c.status = 'loading';
    return call(`/v1/games/${encodeURIComponent(game)}/board`).then(b => {
      if (!b || !b.ok) throw new Error('board');
      const fin = l => (Array.isArray(l) ? l.filter(e => e && Number.isFinite(e.score)) : []);
      Object.assign(c, { status: 'ok', best: fin(b.best), recent: fin(b.recent), average: b.average || c.average, cpu: b.cpu || c.cpu, players: b.players || 0 });
      return c;
    }).catch(() => { c.status = 'error'; return c; }).finally(() => notify(game));
  }
  function submit(game, run) {
    if (!URL_ || !enabled()) return Promise.resolve(null);
    return call(`/v1/games/${encodeURIComponent(game)}/runs`, { device: device(), client: 'chlopkow-web', version: 1, ...run }).catch(() => null);
  }
  const enabled = () => !!URL_ && read(LS_SEND, true) !== false;
  window.ARK_SCORES = {
    url: URL_, board, submit, enabled, cached: game => cache[game] || null,
    setEnabled(on) { write(LS_SEND, !!on); },
    get device() { return device(); },
    onChange(f) { listeners.add(f); return () => listeners.delete(f); },
  };
  window.addEventListener('ark-ready', () => { if (window.ARK) window.ARK.scores = window.ARK_SCORES; });
})();
