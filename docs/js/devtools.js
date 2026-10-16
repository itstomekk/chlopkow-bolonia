/* DEVTOOLS — quick test access for Chłopków Bolonia. Inert unless one of these URL params is present:
     ?dev=1            dev panel (F2 or the DEV badge): searchable places / districts / NPCs / minigames / interiors,
                       click = teleport (minigames start); click on the minimap / M-map teleports. Implies a throwaway save.
     ?play=<id>        start straight in the world and launch a minigame (pig dogs skeet ducks mowing brawl, every board
                       registered in window.ARK_BOARDS such as sprint, or `world` for no minigame). Throwaway save.
     ?go=<place>       teleport by place name, diacritics ignored (?go=kosciol = Kościół). Real save, like ?x=&y=.
     ?save=real        with ?dev=1 / ?play= : use the real localStorage save instead of the throwaway one.
   Precedence: ?x=&y= (game.js) beat ?go; ?play=<minigame> beats both (the minigame teleports to its own venue).
   Throwaway save = localStorage is replaced by an in-memory store BEFORE any other script runs, so the real browser save is
   never read or written; sending scores to the global board is switched off in it and the "player arrived" Nostr event is
   swallowed. Boards are generic: anything in ARK_BOARDS is listed and launchable with no code here.
   Edits outside this file: one script tag in index.html. Minigames are started through the existing window.__features.startMG. */
'use strict';
(() => {
  const q = new URLSearchParams(location.search);
  const DEV = q.get('dev') === '1', PLAY = (q.get('play') || '').trim(), GO = (q.get('go') || '').trim();
  const REAL = q.get('save') === 'real', LOBBY = q.get('lobby') === '1';
  if (!DEV && !PLAY && !GO) return;                       // default URL: this file does nothing at all
  const SANDBOX = (DEV || !!PLAY) && !REAL;

  /* ---------- throwaway save: must be installed before game.js (and every other plugin) touches localStorage ---------- */
  if (SANDBOX) {
    const mem = new Map([['ark_scores_send_v1', 'false']]);   // never post sandbox runs to the global leaderboard
    const fake = {
      getItem: k => (mem.has(String(k)) ? mem.get(String(k)) : null),
      setItem: (k, v) => { mem.set(String(k), String(v)); },
      removeItem: k => { mem.delete(String(k)); },
      clear: () => { mem.clear(); },
      key: i => ([...mem.keys()][i] ?? null),
      get length() { return mem.size; },
    };
    try { Object.defineProperty(window, 'localStorage', { configurable: true, get: () => fake }); }
    catch (e) { console.warn('devtools: could not replace localStorage, sandbox save is OFF', e); }
    // the game announces "player arrived" to public Nostr relays; a dev session must not (we run before chat.js's listener)
    window.addEventListener('ark-player-arrived', e => e.stopImmediatePropagation());
  }

  const D = window.__devtools = { dev: DEV, play: PLAY, go: GO, sandbox: SANDBOX, ready: false, playStatus: PLAY ? 'pending' : null, message: '', goTarget: null };
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/[^a-z0-9]+/g, '');
  D.norm = norm;
  let A = null, G = null, panel = null, badge = null, msgEl = null, keepOpen = false;

  function say(text, ms = 9000) {
    D.message = text; console.info('devtools:', text);
    if (!msgEl) {
      msgEl = document.createElement('div'); msgEl.id = 'dev-message'; msgEl.setAttribute('role', 'alert');
      msgEl.style.cssText = 'position:fixed;left:50%;top:10px;transform:translateX(-50%);max-width:92vw;z-index:10060;background:#7a1f1f;color:#fff;border:2px solid #ffd21f;border-radius:4px;padding:8px 14px;font:13px/1.35 monospace;white-space:pre-wrap;text-align:center';
      document.body.appendChild(msgEl);
    }
    msgEl.textContent = text; msgEl.style.display = 'block';
    clearTimeout(say.t); say.t = setTimeout(() => { msgEl.style.display = 'none'; }, ms);
  }

  const F = () => window.__features;
  // Where each flag minigame lives (display + ?go only: startMG teleports the player to the real spot itself).
  function mgSite(t) {
    const M = A.MAP, c = M.corral, m = M.meadow, r = M.range, f = M.football_pitch;
    if (t === 'pig') return { x: c.cx, y: c.cy };
    if (t === 'dogs') return { x: (m.x0 + m.x1) / 2, y: (m.y0 + m.y1) / 2 };
    if (t === 'skeet') return { x: r.x, y: r.y };
    if (t === 'mowing') return { x: f.cx, y: f.cy };
    // ducks: same search as minigames.js freeVenue(MAP.w * .78, MAP.h * .78)
    const x = M.w * .78, y = M.h * .78;
    for (let rad = 0; rad < 500; rad += 18) for (let a = 0; a < Math.PI * 2; a += .45) {
      const px = x + Math.cos(a) * rad, py = y + Math.sin(a) * rad;
      if (px > 30 && py > 30 && px < M.w - 30 && py < M.h - 30 && !A.blocked(px, py)) return { x: px, y: py };
    }
    return { x, y };
  }
  D.mg = () => (F() && F().MG ? { type: F().MG.type, phase: F().MG.phase } : null);

  // District label points can lie outside the playable map (Dolina's does), so each district gets the walkable
  // point inside both its polygon and the map that is closest to its label. Cached once the data has loaded.
  let distCache = null;
  function districtSpots() {
    const regions = (window.__districts && window.__districts.regions) || [];
    if (!regions.length) return [];
    if (distCache && distCache.n === regions.length) return distCache.list;
    const M = A.MAP, out = [];
    for (const d of regions) {
      const [x0, y0, x1, y1] = d.bounds; let best = null, bd = Infinity;
      for (let y = Math.max(40, y0); y <= Math.min(M.h - 40, y1); y += 40) for (let x = Math.max(40, x0); x <= Math.min(M.w - 40, x1); x += 40) {
        if (!window.ARK_DISTRICTS.contains(d.polygon, x, y) || A.blocked(x, y)) continue;
        const dd = Math.hypot(x - d.label[0], y - d.label[1]); if (dd < bd) { bd = dd; best = { x, y }; }
      }
      if (best) out.push({ id: d.id, name: d.name, x: best.x, y: best.y });
    }
    distCache = { n: regions.length, list: out }; return out;
  }

  /* ---------- registry: every place the panel / ?go / ?play can reach, built from live game data ---------- */
  const VENUE_KEYS = ['corral', 'meadow', 'range', 'football_pitch', 'jazz', 'gravel', 'sprint'];
  const MG_TYPES = ['pig', 'dogs', 'skeet', 'ducks', 'mowing'];
  const MG_LABEL = { pig: 'Świnka Pepa — catch the pig', dogs: 'Pastwisko — eggs and dogs', skeet: 'PPM Strzelectwo — skeet', ducks: 'Kaczki — duck hunt', mowing: 'Boisko — mowing' };
  const KIND_ORDER = { place: 0, district: 1, npc: 2, minigame: 3, interior: 4 };

  function buildRegistry() {
    const M = A.MAP, E = [];
    const near = (a, b, d) => Math.hypot(a.x - b.x, a.y - b.y) < d;
    const add = e => {
      e.norm = norm(e.name); e.search = norm(`${e.name} ${e.id || ''} ${e.kind} ${e.sub || ''}`);
      if (e.kind === 'place' && E.some(o => o.kind === 'place' && ((o.norm === e.norm && near(o, e, 200)) || near(o, e, 4)))) return;   // landmark + poi of the same spot
      E.push(e);
    };
    for (const l of M.landmarks || []) if (l.name) add({ kind: 'place', name: l.name, x: l.x, y: l.y });
    for (const p of M.pois || []) { const name = p.name || G.mapPlaceName(p.x, p.y) || p.key; add({ kind: 'place', name, id: p.key, x: p.x, y: p.y }); }
    for (const k of VENUE_KEYS) {
      const v = M[k]; if (!v) continue;
      const x = v.cx != null ? v.cx : v.x0 != null ? (v.x0 + v.x1) / 2 : v.x, y = v.cy != null ? v.cy : v.y0 != null ? (v.y0 + v.y1) / 2 : v.y;
      add({ kind: 'place', name: G.mapPlaceName(x, y) || k, id: k, x, y });
    }
    (M.shrines || []).forEach((s, i) => add({ kind: 'place', name: `Kapliczka ${i + 1}`, id: s.spot, sub: s.kind, x: s.x, y: s.y }));
    for (const d of districtSpots()) add({ kind: 'district', name: d.name, id: d.id, x: d.x, y: d.y });
    for (const n of (A.ITEMS && A.ITEMS.npcs) || []) add({ kind: 'npc', name: (A.T.names && A.T.names[n.id]) || n.id, id: n.id, sub: n.secret ? 'hidden' : '', pos: () => { const c = A.ITEMS.npcs.find(v => v.id === n.id) || n; return { x: c.x + 22, y: c.y + 8 }; }, x: n.x, y: n.y });
    // minigames: the five flag games (ARK.minigames), BIJATYKA (ARK.brawl) and every board in ARK_BOARDS
    if (F() && F().startMG) for (const t of MG_TYPES) { const v = mgSite(t); add({ kind: 'minigame', name: MG_LABEL[t], id: t, x: v.x, y: v.y, start: () => F().startMG(t) }); }
    if (A.brawl && A.brawl.venue) add({ kind: 'minigame', name: 'BIJATYKA — brawl', id: 'brawl', x: A.brawl.venue.x, y: A.brawl.venue.y, start: startBrawl });
    for (const [id, def] of Object.entries(window.ARK_BOARDS || {})) {
      const v = (A.board && A.board.venues && A.board.venues[id]) || (() => { try { return def.venue(A); } catch (e) { return null; } })() || {};
      let title = id; try { title = def.title(false); } catch (e) { /* keep id */ }
      add({ kind: 'minigame', name: `${title} (board)`, id, sub: 'board', x: v.x, y: v.y, start: () => startBoard(id) });
    }
    const ch = (M.pois || []).find(p => p.key === 'church'), cem = (M.pois || []).find(p => p.key === 'cemetery');
    if (ch) { add({ kind: 'interior', name: 'Wnętrze kościoła — church interior', id: 'church-inside', x: ch.x, y: ch.y, enter: () => openRoom('church') });
      add({ kind: 'interior', name: 'Krypta — crypt', id: 'crypt', x: ch.x, y: ch.y, enter: () => openRoom('crypt') }); }
    if (cem) add({ kind: 'interior', name: 'Tunel — tunnel', id: 'tunnel', x: cem.x, y: cem.y, enter: () => openRoom('tunnel') });
    return E;
  }
  D.entries = () => (A ? buildRegistry().map(e => ({ kind: e.kind, name: e.name, id: e.id || null, x: Math.round(e.x), y: Math.round(e.y) })) : []);

  // ?go=<name>: exact (name or id) > prefix > substring; then kind order, then the shortest name
  function resolve(query, reg = buildRegistry()) {
    const nq = norm(query); if (!nq) return null;
    let best = null, bs = 9;
    for (const e of reg) {
      const idn = norm(e.id);
      const tier = e.norm === nq || idn === nq ? 0 : e.norm.startsWith(nq) ? 1 : e.search.includes(nq) ? 2 : 9;
      if (tier === 9) continue;
      const better = !best || tier < bs || (tier === bs && (KIND_ORDER[e.kind] < KIND_ORDER[best.kind] || (KIND_ORDER[e.kind] === KIND_ORDER[best.kind] && e.norm.length < best.norm.length)));
      if (better) { best = e; bs = tier; }
    }
    return best;
  }
  D.resolve = query => { const e = A && resolve(query); return e ? { kind: e.kind, name: e.name, id: e.id || null, x: Math.round(e.x), y: Math.round(e.y) } : null; };

  /* ---------- actions ---------- */
  const stopActivities = () => {
    if (F() && F().MG) window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Escape', key: 'Escape' }));   // minigames.js hook: Escape = leave
    try { if (A.board && A.board.ui) A.board.close(); } catch (e) { /* none */ }
    try { if (A.brawl && A.brawl.ui) A.brawl.close(); } catch (e) { /* none */ }
    A.keys.clear(); G.showMap = false;
  };
  async function settle(max = 5000) { const t0 = performance.now(); await wait(80); while (A.rooms.busy && performance.now() - t0 < max) await wait(50); await wait(80); }
  async function toVillage(x, y) {
    if (A.rooms.depth > 0) { A.rooms.surface(x, y, 'down'); await settle(); return; }
    A.teleport(x, y);
  }
  async function teleportTo(x, y) { stopActivities(); await toVillage(x, y); }
  async function openRoom(id) {
    stopActivities();
    const M = A.MAP, ch = M.pois.find(p => p.key === 'church'), cem = M.pois.find(p => p.key === 'cemetery');
    if (id === 'tunnel') {
      if (!A.Q.tunnelOpen) { if (SANDBOX) A.Q.tunnelOpen = true; else { say('Tunnel is locked in your real save (Q.tunnelOpen is false). Use the throwaway save (drop ?save=real).'); return; } }
      await toVillage(cem.x, cem.y + 20); window.PASSAGES.enter('church-cemetery', 'cemetery');
      for (let i = 0; i < 100 && A.rooms.id !== 'church-cemetery'; i++) await wait(50);
      await settle(); return;
    }
    if (A.rooms.id !== 'church' && A.rooms.id !== 'crypt') { await toVillage(ch.x, ch.y + 30); G.enterChurch(); await settle(); }
    if (id === 'crypt' && A.rooms.id !== 'crypt') { G.enterCrypt(); await settle(); }
    if (id === 'church' && A.rooms.id === 'crypt') { A.rooms.surface(ch.x, ch.y + 30, 'down'); await settle(); G.enterChurch(); await settle(); }
  }
  async function startBrawl() {
    stopActivities(); await toVillage(A.brawl.venue.x, A.brawl.venue.y);
    A.brawl.open(); try { await A.brawl.loaded(); } catch (e) { /* art optional */ }
    if (!LOBBY && !A.brawl.start()) say('BIJATYKA: the lobby is invalid, fix the slots there.');
  }
  async function startBoard(id, lobbyOnly = LOBBY) {
    stopActivities(); const v = A.board.venues[id]; if (v) await toVillage(v.x, v.y);
    if (!A.board.open(id)) { say(`Board '${id}' did not open.`); return; }
    // boards with on-demand data (def.load / def.status, e.g. WOJNA PŁYNÓW levels) cannot start until it has loaded
    const def = (window.ARK_BOARDS || {})[id];
    if (def && def.load) { try { await def.load(); } catch (e) { say(`Board '${id}': data failed to load.`); return; } }
    if (!lobbyOnly && !A.board.start()) say(`Board '${id}': lobby is invalid (see the message in the lobby).`);
  }
  async function activate(e, lobbyOnly) {
    if (A.scene !== 'play') { say('Start the game first (title screen), or reload with ?dev=1 only (auto-start with a throwaway save).'); return; }
    if (e.kind === 'minigame') {
      if (e.id === 'brawl') return startBrawl();
      if (e.sub === 'board') return startBoard(e.id, lobbyOnly);
      stopActivities(); if (A.rooms.depth > 0) { A.rooms.surface(e.x, e.y, 'down'); await settle(); }
      return e.start();
    }
    if (e.kind === 'interior') return e.enter();
    const p = e.pos ? e.pos() : e;
    return teleportTo(p.x, p.y);
  }
  D.activate = async (idOrName, lobbyOnly) => { const e = resolve(idOrName); if (!e) return false; await activate(e, lobbyOnly); return true; };

  /* ---------- ?play=<id> ---------- */
  async function runPlay(raw) {
    const id = norm(raw);
    const known = () => ['world', 'brawl', 'bijatyka', ...MG_TYPES, ...Object.keys(window.ARK_BOARDS || {})];
    try {
      if (id === 'world') { D.playStatus = 'started'; return; }
      if (MG_TYPES.includes(id) && F() && F().startMG) { F().startMG(id); D.playStatus = 'started'; return; }
      if (id === 'brawl' || id === 'bijatyka') { await startBrawl(); D.playStatus = 'started'; return; }
      const bid = Object.keys(window.ARK_BOARDS || {}).find(b => norm(b) === id);
      if (bid) { await startBoard(bid); D.playStatus = 'started'; return; }
      D.playStatus = 'unknown';
      say(`?play=${raw}: unknown minigame.\nAvailable: ${known().filter(k => k !== 'bijatyka').join(', ')}`, 20000);
    } catch (err) { D.playStatus = 'error'; console.error('devtools play failed', err); say(`?play=${raw} failed: ${err && err.message}`); }
  }

  /* ---------- ?go=<place> ---------- */
  async function runGo() {
    if (q.has('x') && q.has('y')) { D.goStatus = 'ignored-xy'; console.info('devtools: ?x=&y= take precedence over ?go'); return; }
    let e = resolve(GO);
    for (let i = 0; !e && i < 50 && (!window.__districts || window.__districts.status === 'loading'); i++) { await wait(100); e = resolve(GO); }   // district names load asynchronously
    if (!e) { D.goStatus = 'unknown'; say(`?go=${GO}: no such place. Try the dev panel (?dev=1, F2) for the list.`); return; }
    const p = e.pos ? e.pos() : e;   // minigames / interiors: teleport to the venue only, ?play starts games
    D.goStatus = 'ok'; D.goTarget = { name: e.name, x: p.x, y: p.y };
    await goApply();
  }
  async function goApply() { if (D.goTarget && A.rooms.depth === 0) A.teleport(D.goTarget.x, D.goTarget.y); }

  /* ---------- panel ---------- */
  const CSS = `
  #dev-badge{position:fixed;left:8px;bottom:8px;z-index:10055;background:rgba(8,12,40,.88);color:#ffd21f;border:1px solid #ffd21f;border-radius:3px;font:11px monospace;padding:3px 7px;cursor:pointer;opacity:.85}
  #dev-badge.static{cursor:default;pointer-events:none}
  #dev-badge:focus-visible,#dev-panel button:focus-visible,#dev-search:focus-visible{outline:2px solid #7cd0ff;outline-offset:1px}
  #dev-panel{position:fixed;top:0;right:0;bottom:0;width:min(360px,100vw);z-index:10050;background:rgba(10,14,40,.95);color:#f5f0e0;font:13px monospace;display:none;flex-direction:column;border-left:2px solid #ffd21f;box-sizing:border-box}
  #dev-panel.open{display:flex}
  #dev-panel.open ~ #dev-badge{display:none}
  #dev-close{background:#05070d;color:#ffd21f;border:1px solid #ffd21f;border-radius:3px;font:bold 13px monospace;padding:2px 9px;cursor:pointer}
  #dev-panel header{padding:8px 10px;border-bottom:1px solid #394070;display:flex;flex-direction:column;gap:6px}
  #dev-panel h1{margin:0;font:bold 13px monospace;color:#ffd21f;display:flex;justify-content:space-between;gap:8px}
  #dev-panel h1 span{font-weight:normal;color:#9fb0ff}
  #dev-search{width:100%;box-sizing:border-box;background:#05070d;color:#fff;border:1px solid #6a74c0;border-radius:3px;padding:6px 8px;font:14px monospace}
  #dev-panel label{font-size:11px;color:#9fb0ff;display:flex;gap:6px;align-items:center}
  #dev-list{flex:1;overflow-y:auto;padding:4px 6px 12px}
  #dev-list h2{margin:10px 2px 3px;font:bold 11px monospace;color:#7cd0ff;letter-spacing:.08em;text-transform:uppercase}
  #dev-panel .dev-item{display:flex;justify-content:space-between;gap:8px;width:100%;text-align:left;background:transparent;color:#f5f0e0;border:0;border-bottom:1px solid #1d2350;padding:6px 4px;font:13px monospace;cursor:pointer;min-height:30px}
  #dev-panel .dev-item:hover,#dev-panel .dev-item:focus-visible{background:#232a66}
  #dev-panel .dev-item small{color:#8a94d6;white-space:nowrap}
  #dev-panel footer{padding:6px 10px;border-top:1px solid #394070;font-size:11px;color:#9fb0ff;line-height:1.35}
  @media (max-width:640px){#dev-panel{top:auto;left:0;right:0;width:auto;height:64vh;border-left:0;border-top:2px solid #ffd21f}#dev-panel .dev-item{min-height:38px;font-size:14px}}`;
  const KIND_TITLE = { minigame: 'Minigames', interior: 'Interiors', place: 'Places', district: 'Districts', npc: 'NPCs' };
  const KIND_SEQ = ['minigame', 'interior', 'place', 'district', 'npc'], KIND_SEARCH_SEQ = ['place', 'district', 'npc', 'minigame', 'interior'];
  let shown = [];

  function buildPanel() {
    const st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    badge = document.createElement('button'); badge.id = 'dev-badge'; badge.type = 'button';
    badge.textContent = `DEV · ${SANDBOX ? 'throwaway save' : 'REAL save'}${DEV ? ' · F2' : ''}`;
    if (DEV) badge.addEventListener('click', () => toggle()); else badge.classList.add('static');
    if (!DEV) { document.body.appendChild(badge); return; }
    panel = document.createElement('div'); panel.id = 'dev-panel'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Developer quick access');
    panel.innerHTML = `<header><h1>DEV QUICK ACCESS <span>${SANDBOX ? 'throwaway save' : 'REAL SAVE'}</span><button id="dev-close" type="button" aria-label="Close dev panel">✕</button></h1>
      <input id="dev-search" type="search" placeholder="search: kosciol, pig, sprint, kasia…" aria-label="Search places, NPCs and minigames" autocomplete="off" spellcheck="false">
      <label><input id="dev-keep" type="checkbox"> keep panel open after a click</label></header>
      <div id="dev-list" tabindex="0" role="list" aria-label="Results"></div>
      <footer>Enter = first result · Shift+click on a board = lobby only · Esc / F2 = close · click the minimap or M-map to teleport</footer>`;
    document.body.append(panel, badge);   // badge after panel: `#dev-panel.open ~ #dev-badge` hides it while the panel is up
    const search = panel.querySelector('#dev-search');
    search.addEventListener('input', renderList);
    search.addEventListener('keydown', e => { if (e.key === 'Enter' && shown[0]) { e.preventDefault(); pick(shown[0], e.shiftKey); } });
    panel.querySelector('#dev-close').addEventListener('click', () => toggle(false));
    panel.querySelector('#dev-keep').addEventListener('change', e => { keepOpen = e.target.checked; });
    // typing in the panel must never reach the game's window key handlers (M, K, E, WASD ...)
    for (const t of ['keydown', 'keyup', 'keypress']) panel.addEventListener(t, e => { if (e.key === 'Escape' && t === 'keydown') toggle(false); e.stopPropagation(); });
    panel.addEventListener('pointerdown', e => e.stopPropagation());
    panel.querySelector('#dev-list').addEventListener('click', e => {
      const b = e.target.closest('.dev-item'); if (b) pick(shown[+b.dataset.i], e.shiftKey);
    });
  }
  function renderList() {
    const nq = norm(panel.querySelector('#dev-search').value), reg = buildRegistry();
    const seq = nq ? KIND_SEARCH_SEQ : KIND_SEQ;   // searching: places first (kosciol -> Kościół before its interior); browsing: minigames first
    shown = reg.filter(e => !nq || e.search.includes(nq)).sort((a, b) => seq.indexOf(a.kind) - seq.indexOf(b.kind) || a.name.localeCompare(b.name, 'pl'));
    const list = panel.querySelector('#dev-list'); list.textContent = '';
    let last = '';
    shown.forEach((e, i) => {
      if (e.kind !== last) { last = e.kind; const h = document.createElement('h2'); h.textContent = KIND_TITLE[e.kind]; list.appendChild(h); }
      const b = document.createElement('button'); b.type = 'button'; b.className = 'dev-item'; b.dataset.i = i; b.dataset.kind = e.kind; b.dataset.id = e.id || ''; b.setAttribute('role', 'listitem');
      const n = document.createElement('span'); n.textContent = e.name;
      const c = document.createElement('small'); c.textContent = Number.isFinite(e.x) ? `${Math.round(e.x)},${Math.round(e.y)}` : '';
      b.append(n, c); list.appendChild(b);
    });
    if (!shown.length) { const p = document.createElement('p'); p.textContent = 'No match.'; p.style.padding = '8px'; list.appendChild(p); }
  }
  function toggle(on) {
    if (!panel) return false;
    const open = on == null ? !panel.classList.contains('open') : on;
    panel.classList.toggle('open', open);
    if (open) { A.keys.clear(); renderList(); const s = panel.querySelector('#dev-search'); s.focus({ preventScroll: true }); s.select(); }
    else if (document.activeElement && panel.contains(document.activeElement)) document.activeElement.blur();
    return open;
  }
  D.toggle = toggle; D.isOpen = () => !!(panel && panel.classList.contains('open'));
  async function pick(e, lobbyOnly) {
    if (!e) return;
    if (!keepOpen) toggle(false);
    try { await activate(e, lobbyOnly); } catch (err) { console.error('devtools action failed', err); say(`Action failed: ${err && err.message}`); }
  }

  /* ---------- click on the minimap / M-map = teleport (dev panel mode only) ---------- */
  function installMapClicks() {
    const cvs = document.getElementById('game');
    window.addEventListener('pointerdown', e => {
      if (e.target !== cvs || A.scene !== 'play' || A.room || A.talk || A.HOOKS.busy.some(f => f())) return;
      const r = cvs.getBoundingClientRect(), px = (e.clientX - r.left) / r.width * cvs.width, py = (e.clientY - r.top) / r.height * cvs.height;
      const W = cvs.width, H = cvs.height, U = Math.min(W, H * 1.6) / 100, M = A.MAP;   // same geometry as the HUD in game.js
      const big = G.showMap, mw = big ? Math.min(W * .8, H * .8 * M.w / M.h) : U * 16, mh = mw * M.h / M.w;
      const mx = big ? (W - mw) / 2 : W - mw - U * 2, my = big ? (H - mh) / 2 : U * 2;
      if (px < mx || px > mx + mw || py < my || py > my + mh) return;
      e.stopImmediatePropagation(); e.preventDefault();
      const x = (px - mx) / mw * M.w, y = (py - my) / mh * M.h;
      G.showMap = false; A.teleport(x, y); say(`teleported to ${Math.round(x)},${Math.round(y)}`, 1800);
    }, true);
  }

  // F2 is registered at load time, before board.js / brawl.js add their own capture-phase key handlers (they would swallow it mid-run).
  if (DEV) window.addEventListener('keydown', e => { if (e.key === 'F2' && panel) { e.preventDefault(); e.stopImmediatePropagation(); toggle(); } }, true);

  /* ---------- boot ---------- */
  // loading-splash.js swallows keys until the boot overlay is gone; a minigame started under it would burn its countdown unseen.
  async function splashDone() { for (let i = 0; i < 160 && window.__arkBoot && !['ready', 'error'].includes(window.__arkBoot.stage); i++) await wait(50); }
  async function boot() {
    A = window.ARK; G = window.__game;
    if (!A || !G) { setTimeout(boot, 50); return; }
    buildPanel();
    if (DEV) installMapClicks();
    if (SANDBOX || PLAY) {
      // skip the title: default character (stored choice or Arek) + its default name, no startGame() => no save wipe, no arrival event
      if (!A.Q.playerName) A.Q.playerName = 'Arek';
      G.scene = 'play';
    }
    if (GO) {
      // on the title screen the first Enter runs startGame(), which picks its own spawn: re-apply once when play begins
      if (!SANDBOX) window.addEventListener('ark-player-arrived', () => { goApply(); }, { once: true });
      runGo();
    }
    if (PLAY) { await splashDone(); await runPlay(PLAY); }
    D.ready = true;
  }
  window.addEventListener('ark-ready', () => queueMicrotask(boot), { once: true });
})();
