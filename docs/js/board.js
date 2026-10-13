/* Board minigames ("plansze"): a flag on the map opens a full-screen board where up to four
   players (local humans or computer runners) compete. Boards register from docs/js/boards/*.js:
     window.ARK_BOARD_REGISTER({ id, title, venue, keys, score, create, ... })   (see boards/sprint.js)
   The framework owns the map flag, the lobby (4 slots: human / CPU / off, character, controls,
   name), input (keyboard schemes + gamepads, auto-repeat ignored), the fixed 60 Hz loop, the
   count -> run -> done phases, the result table, saves (Q.mg[id]) and a per-device top 10.
   CPU benchmark (plans/2026-10-11-minigame-design-direction.md): a CPU result is the rolling
   average of the last 20 human results on this save, or the board's default when there are none.
   Characters are the side-view BIJATYKA sheets (img/brawl/<id>.webp/.json), read live from
   ARK.brawl when it is loaded so roster changes there carry over. */
'use strict';
window.ARK_BOARDS = window.ARK_BOARDS || {};
window.ARK_BOARD_REGISTER = def => { window.ARK_BOARDS[def.id] = def; };
window.addEventListener('ark-ready', () => {
  const A = window.ARK;
  if (A.__boardInstalled) return; A.__boardInstalled = true;
  const PL = A.LANG === 'pl';
  const W = 960, H = 540, DT = 1 / 60, HISTORY = 20, TOP_N = 10;
  const SLOT_COLORS = ['#e34c4c', '#4aa8e8', '#7cff6b', '#ffd21f'];
  const MEDAL_COL = ['#666', '#cd7f32', '#d8d8e0', '#ffd21f'];
  const T = PL ? {
    type: { human: 'CZŁOWIEK', avg: 'PRZECIĘTNIAK', cpu: 'KOMPUTER', off: '—' }, avgName: 'PRZECIĘTNIAK', start: 'START!', close: 'WYJDŹ', name: 'imię',
    pad: n => `PAD ${n}`, cpuInfo: (v, src) => `PRZECIĘTNIAK = przeciętny gracz (${src === 'global' ? 'średnia ostatnich 200 wyników na świecie' : src === 'local' ? 'średnia wyników z tego komputera' : 'jeszcze brak wyników'}): ${v}. KOMPUTER biega trochę szybciej albo wolniej.`, top: 'REKORDY NA TYM KOMPUTERZE',
    errHuman: 'Dodaj co najmniej jednego człowieka.', errSame: 'Dwóch graczy ma to samo sterowanie: ',
    medal: ['', 'BRĄZ', 'SREBRO', 'ZŁOTO'], record: 'NOWY REKORD!', dnf: 'NIE UKOŃCZYŁ', again: 'ENTER / R — JESZCZE RAZ     ESC — MENU',
    menu: 'ESC — MENU', wins: 'WYGRYWA', place: 'MIEJSCE', best: 'REKORD', pads: 'Pad: LB/RB, spusty albo krzyżak lewo/prawo',
    gbest: 'NAJLEPSI', grecent: 'AKTUALNE', gavg: 'ŚREDNIA', gof: n => `z ${n} wyników`, gtop: 'GLOBALNE REKORDY', gsend: 'Wysyłaj wyniki ludzi do globalnej tablicy (imię jest publiczne)', gload: 'ładuję globalne rekordy…', gerr: 'globalna tablica niedostępna, wyniki zostają na tym komputerze', grank: n => `ŚWIAT #${n}`, gempty: 'jeszcze nikt — bądź pierwszy!',
  } : {
    type: { human: 'HUMAN', avg: 'AVERAGE JOE', cpu: 'COMPUTER', off: '—' }, avgName: 'AVERAGE JOE', start: 'START!', close: 'LEAVE', name: 'name',
    pad: n => `GAMEPAD ${n}`, cpuInfo: (v, src) => `AVERAGE JOE = the average player (${src === 'global' ? 'mean of the last 200 results worldwide' : src === 'local' ? 'mean of this computer\'s results' : 'no results yet'}): ${v}. COMPUTER runs a bit faster or slower.`, top: 'RECORDS ON THIS COMPUTER',
    errHuman: 'Add at least one human player.', errSame: 'Two players share the same controls: ',
    medal: ['', 'BRONZE', 'SILVER', 'GOLD'], record: 'NEW RECORD!', dnf: 'DID NOT FINISH', again: 'ENTER / R — AGAIN     ESC — MENU',
    menu: 'ESC — MENU', wins: 'WINNER', place: 'PLACE', best: 'BEST', pads: 'Gamepad: LB/RB, triggers or d-pad left/right',
    gbest: 'BEST', grecent: 'LATEST', gavg: 'AVERAGE', gof: n => `of ${n} results`, gtop: 'GLOBAL RECORDS', gsend: 'Send human results to the global board (the name is public)', gload: 'loading global records…', gerr: 'global board unavailable, results stay on this computer', grank: n => `WORLD #${n}`, gempty: 'nobody yet — be the first!',
  };
  const readLS = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v && typeof v === 'object' ? v : d; } catch (e) { return d; } };
  const writeLS = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } };
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const opt = (v, label, cur) => `<option value="${esc(v)}"${v === cur ? ' selected' : ''}>${esc(label)}</option>`;
  const keyName = code => !code ? '—' : code.replace(/^Key/, '').replace(/^Digit/, '')
    .replace(/^Arrow(.*)/, (m, d) => ({ Up: '↑', Down: '↓', Left: '←', Right: '→' }[d])).replace(/^Numpad/, 'NUM ').toUpperCase();
  const typing = t => !!(t && t.closest && t.closest('input, textarea, select, [contenteditable="true"], .chat, #player-name-input'));
  const cleanName = s => String(s || '').replace(/[\u0000-\u001f<>]/g, '').trim().slice(0, 14);

  /* ================================================================== characters (BIJATYKA sheets) */
  const FALLBACK_ROSTER = [['arek', 'AREK'], ['edytka', 'EDYTKA'], ['renik', 'DJ RENIK'], ['damian', 'DAMIAN'], ['wesoly', 'WESOŁYCH ŚWIĄT'], ['michal', 'MICHAŁ'], ['soltys', 'SOŁTYS']];
  function roster() {
    const F = A.brawl && A.brawl.FIGHTERS;
    if (F && Object.keys(F).length) return Object.entries(F).map(([id, f]) => ({ id, name: f.name || id.toUpperCase(), atlas: f.atlas || id }));
    return FALLBACK_ROSTER.map(([id, name]) => ({ id, name, atlas: id }));
  }
  const ART = {};
  function atlas(id) {
    if (!ART[id]) {
      const a = ART[id] = { img: null, meta: null };
      a.ready = Promise.all([A.load(`img/brawl/${id}.webp`), fetch(`img/brawl/${id}.json`).then(r => r.json())])
        .then(([img, meta]) => { a.img = img; a.meta = meta; return a; }).catch(() => a);
    }
    return ART[id];
  }
  // Draw one frame of a character sheet with its feet at (x, y). `names` is a preference list,
  // so a renamed or missing frame falls back instead of breaking the board.
  function drawSprite(c, atlasId, names, x, y, face = 1, scale = 1, alpha = 1) {
    const a = ART[atlasId]; if (!a || !a.img || !a.meta || !a.meta.frames) return false;
    const fr = [].concat(names).map(n => a.meta.frames[n]).find(Boolean) || a.meta.frames.stand; if (!fr) return false;
    const s = (a.meta.scale || .5) * scale;
    c.save(); c.globalAlpha = alpha; c.translate(x, y); c.scale(face < 0 ? -s : s, s);
    c.imageSmoothingEnabled = true; c.drawImage(a.img, fr.x, fr.y, fr.w, fr.h, -fr.ax, -fr.ay, fr.w, fr.h);
    c.restore();
    return true;
  }

  /* ================================================================== sound (tiny WebAudio synth) */
  let AC = null;
  function sfx(kind) {
    try {
      if (!AC) AC = new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === 'suspended') AC.resume();
      const t = AC.currentTime, g = AC.createGain(); g.connect(AC.destination);
      const noise = (dur, f0, f1, vol, type = 'lowpass') => {
        const b = AC.createBuffer(1, Math.ceil(AC.sampleRate * dur), AC.sampleRate), d = b.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
        const s = AC.createBufferSource(); s.buffer = b; const fl = AC.createBiquadFilter(); fl.type = type;
        fl.frequency.setValueAtTime(f0, t); fl.frequency.exponentialRampToValueAtTime(f1, t + dur);
        s.connect(fl); fl.connect(g); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + dur); s.start(t); s.stop(t + dur);
      };
      const tone = (dur, f0, f1, vol, type = 'square', at = 0) => {
        const o = AC.createOscillator(), gg = AC.createGain(); o.type = type; o.connect(gg); gg.connect(AC.destination);
        o.frequency.setValueAtTime(f0, t + at); o.frequency.exponentialRampToValueAtTime(f1, t + at + dur);
        gg.gain.setValueAtTime(vol, t + at); gg.gain.exponentialRampToValueAtTime(.001, t + at + dur); o.start(t + at); o.stop(t + at + dur);
      };
      if (kind === 'step') noise(.04, 900, 200, .12);
      else if (kind === 'stumble') noise(.16, 500, 90, .3);
      else if (kind === 'gun') noise(.35, 4000, 150, .6, 'highpass');
      else if (kind === 'false') tone(.35, 180, 120, .14, 'square');
      else if (kind === 'finish') { tone(.14, 1900, 1900, .07, 'triangle'); tone(.3, 1900, 1700, .07, 'triangle', .16); }
      else if (kind === 'tick') tone(.06, 880, 880, .05, 'square');
    } catch (e) { /* audio unavailable */ }
  }

  /* ================================================================== saves, records, CPU average */
  const rec = def => {
    const q = A.Q; q.mg = q.mg || {};
    const r = q.mg[def.id] = q.mg[def.id] || { tries: 0, won: false, best: 0, medal: 0 };
    r.unit = def.score.unit; if (!Array.isArray(r.history)) r.history = [];
    return r;
  };
  const better = (def, a, b) => def.score.lower ? a < b : a > b;
  const medalFor = (def, v) => { let m = 0; def.score.medals.forEach((th, i) => { if (def.score.lower ? v <= th : v >= th) m = i + 1; }); return m; };
  /* ================================================================== global scores (docs/js/scores.js -> cloud/api, Cloudflare) */
  const SC = window.ARK_SCORES || null;
  const SCORES_URL = SC ? SC.url : null;
  const globalOn = () => !!(SC && SC.enabled());
  const gBoard = def => (SC && def.global ? SC.cached(def.id) : null);
  if (SC) SC.onChange(id => { if (ui && !run && ui.def.id === id) rerenderKeepingFocus(); });
  const fetchGlobal = def => (SC && def.global ? SC.board(def.id) : Promise.resolve(null));
  function submitGlobal(def, res) {
    if (!SC || !def.global || !globalOn()) return;
    const mode = `local${run.players.filter(p => !p.cpu).length}`;
    const posts = res.filter(r => !r.player.cpu && r.score != null).map(r => {
      r.global = 'sending';
      return SC.submit(def.id, { name: r.player.name, char: r.player.char, score: r.score, trace: r.trace || null, proof: r.proof || {}, mode })
        .then(b => { r.global = b && b.ok ? b.rank : 'error'; if (b && b.ok) { r.rankWeek = b.rankWeek; r.percentile = b.percentile; } });
    });
    if (posts.length) Promise.all(posts).then(() => fetchGlobal(def));
  }
  // The PRZECIĘTNIAK CPU: the global mean of the last 200 results and their averaged checkpoint trace
  // (cloud/api). Offline it falls back to this save's own history, then to the board's default.
  function cpuRef(def) {
    const g = gBoard(def), n = def.score.traceLen || 0;
    if (g && g.status === 'ok' && g.cpu && Number.isFinite(g.cpu.score)) return { score: g.cpu.score, trace: g.cpu.trace && g.cpu.trace.length === n ? g.cpu.trace : null, source: 'global', count: g.cpu.count };
    const r = (A.Q && A.Q.mg && A.Q.mg[def.id]) || {}, h = r.history || [], tr = (r.traces || []).filter(t => Array.isArray(t) && t.length === n && n);
    if (!h.length) return { score: def.score.cpuDefault, trace: null, source: 'default', count: 0 };
    return { score: h.reduce((s, v) => s + v, 0) / h.length, trace: tr.length ? tr[0].map((_, i) => tr.reduce((s, t) => s + t[i], 0) / tr.length) : null, source: 'local', count: h.length };
  }
  const cpuBase = def => cpuRef(def).score;

  const topKey = def => `ark_board_${def.id}_top_v1`;
  const topList = def => { const l = readLS(topKey(def), []); return Array.isArray(l) ? l.filter(e => e && Number.isFinite(e.score)) : []; };

  /* ================================================================== flags on the map */
  const venues = {};
  queueMicrotask(() => { for (const def of Object.values(window.ARK_BOARDS)) { try { const v = def.venue(A); if (v) venues[def.id] = v; } catch (e) { /* no venue */ } } });
  function drawFlag(def, sx, sy, s) {
    const c = A.ctx, px = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 5);
    px(-1, -30, 2, 30, '#5a3a1e');
    for (let i = 0; i < 12; i++) for (let j = 0; j < 4; j++) px(1 + i, -29 + j * 2 + i * .35 + Math.sin(A.time * 5 + i * .5) * .8, 1, 2, (Math.floor(i / 2) + j) % 2 ? def.flagColors[0] : def.flagColors[1]);
    const r = A.Q && A.Q.mg && A.Q.mg[def.id], label = def.flagLabel + (r && r.medal ? ' ★' : '');
    c.font = `${6 * s}px Silkscreen`; c.textAlign = 'center'; c.textBaseline = 'middle';
    const tw = c.measureText(label).width + 3 * s;
    c.fillStyle = 'rgba(8,12,40,.8)'; c.fillRect(sx - tw / 2, sy - 40 * s, tw, 8 * s);
    c.fillStyle = r && r.medal ? MEDAL_COL[r.medal] : '#fff'; c.fillText(label, sx, sy - 36 * s); c.textAlign = 'left';
  }
  function interact(def) {
    if (def.intro && A.say) A.say(def.host, def.intro(PL), () => open(def.id));
    else open(def.id);
  }
  A.HOOKS.near.push(() => (ui || A.HOOKS.busy.some(f => f()) ? [] : Object.keys(venues).map(id => ({ x: venues[id].x, y: venues[id].y, r: 30, _board: id, onInteract: () => interact(window.ARK_BOARDS[id]) }))));
  A.HOOKS.busy.push(() => !!ui);
  A.HOOKS.world.push((push, S, inView) => {
    for (const id of Object.keys(venues)) { const v = venues[id]; if (inView(v.x, v.y)) push(v.y, () => drawFlag(window.ARK_BOARDS[id], ...S(v.x, v.y), A.zoom)); }
  });
  A.HOOKS.minimap.push(dot => { for (const id of Object.keys(venues)) dot(venues[id].x, venues[id].y, window.ARK_BOARDS[id].flagColors[0]); });
  A.HOOKS.questLog.push(lines => {
    for (const id of Object.keys(venues)) {
      const def = window.ARK_BOARDS[id], r = A.Q && A.Q.mg && A.Q.mg[id]; if (!r || !r.tries) continue;
      lines.push([def.logName(PL) + (r.best ? ` ${def.score.format(r.best)}` : '') + (r.medal ? ` ★${T.medal[r.medal]}` : ''), r.medal >= 3]);
    }
  });

  /* ================================================================== input */
  let ui = null, run = null, raf = 0, last = 0, acc = 0;
  const held = new Set(), events = [], padPrev = {};
  function schemeList(def) { return [...Object.keys(def.keys), 'pad1', 'pad2', 'pad3', 'pad4']; }
  function schemeLabel(def, s) {
    if (s.startsWith('pad')) return T.pad(s.slice(3));
    const k = def.keys[s]; return def.actions.map(a => keyName(k[a])).join(' / ');
  }
  function onKeyDown(e) {
    if (!ui) return;
    if (e.code === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); back(); return; }
    if (!run) { e.stopImmediatePropagation(); return; }   // lobby: let form controls work, keep the village still
    e.preventDefault(); e.stopImmediatePropagation();
    if (run.phase === 'done') { if (run.doneT > .8 && (e.code === 'Enter' || e.code === 'KeyR' || e.code === 'Space')) startRun(); return; }
    if (e.repeat || held.has(e.code)) return;
    held.add(e.code);
    for (const p of run.players) if (!p.cpu && ui.def.keys[p.ctrl]) for (const a of ui.def.actions) if (ui.def.keys[p.ctrl][a] === e.code) events.push({ slot: p.slot, action: a });
  }
  function onKeyUp(e) { if (!ui) return; held.delete(e.code); e.stopImmediatePropagation(); if (run) e.preventDefault(); }
  window.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('keyup', onKeyUp, true);
  window.addEventListener('blur', () => held.clear());
  // Gamepad: LB/RB (4/5), triggers (6/7) or d-pad left/right (14/15) = left/right; A (0) = first action too.
  function pollPads() {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const p of run.players) {
      if (p.cpu || !p.ctrl.startsWith('pad')) continue;
      const n = +p.ctrl.slice(3) - 1, gp = pads && pads[n]; if (!gp) continue;
      const b = i => !!(gp.buttons[i] && gp.buttons[i].pressed), ax = gp.axes[0] || 0;
      const st = { left: b(4) || b(6) || b(14) || ax < -.6, right: b(5) || b(7) || b(15) || ax > .6 }, prev = padPrev[n] || {};
      for (const a of ui.def.actions) if (st[a] && !prev[a]) events.push({ slot: p.slot, action: a });
      padPrev[n] = st;
    }
  }

  /* ================================================================== lobby */
  const slotsKey = def => `ark_board_${def.id}_slots_v1`;
  function defaultSlots(def) {
    const ids = roster().map(r => r.id), me = window.__game && window.__game.playerCharacter;
    const pick = (want, i) => ids.includes(want) ? want : ids[i % ids.length];
    const k = Object.keys(def.keys);
    return [
      { type: 'human', char: pick(me, 0), ctrl: k[0], name: '' },
      { type: 'avg', char: pick('damian', 3), ctrl: k[1], name: '' },
      { type: 'cpu', char: pick('edytka', 1), ctrl: k[2], name: '' },
      { type: 'cpu', char: pick('soltys', 6), ctrl: k[3], name: '' },
    ];
  }
  function loadSlots(def) {
    const d = defaultSlots(def), saved = readLS(slotsKey(def), null), ids = roster().map(r => r.id), schemes = schemeList(def);
    if (!Array.isArray(saved) || saved.length !== 4) return d;
    return saved.map((s, i) => ({
      type: ['human', 'avg', 'cpu', 'off'].includes(s && s.type) ? s.type : d[i].type,
      char: ids.includes(s && s.char) ? s.char : d[i].char,
      ctrl: schemes.includes(s && s.ctrl) ? s.ctrl : d[i].ctrl,
      name: cleanName(s && s.name),
    }));
  }
  function validate() {
    const act = ui.slots.filter(s => s.type !== 'off');
    if (!act.some(s => s.type === 'human')) return T.errHuman;
    const used = {};
    for (const s of act) if (s.type === 'human') { if (used[s.ctrl]) return T.errSame + schemeLabel(ui.def, s.ctrl); used[s.ctrl] = 1; }
    return null;
  }
  const css = {
    btn: 'min-height:40px;padding:6px 14px;border:2px solid #ffd21f;border-radius:6px;background:#263a61;color:#fff;font:bold 14px monospace;cursor:pointer',
    sel: 'min-height:34px;padding:4px;border:1px solid #9ba9c4;border-radius:4px;background:#0f1a33;color:#f8f3df;font:13px monospace;min-width:0;width:100%;box-sizing:border-box',
  };
  function paintPortraits() {
    if (!ui) return;
    const R = Object.fromEntries(roster().map(r => [r.id, r]));
    ui.lobby.querySelectorAll('canvas[data-portrait]').forEach(cv => {
      const r = R[cv.dataset.portrait], a = r && ART[r.atlas], g = cv.getContext('2d'); g.clearRect(0, 0, cv.width, cv.height);
      if (!a || !a.img) return;
      const fr = a.meta.frames.stand, s = cv.height / fr.h;
      g.imageSmoothingQuality = 'high'; g.drawImage(a.img, fr.x, fr.y, fr.w, fr.h, (cv.width - fr.w * s) / 2, 0, fr.w * s, fr.h * s);
    });
  }
  // a late network answer must not steal focus from someone typing a name
  function rerenderKeepingFocus() {
    const a = document.activeElement, slot = a && a.closest && a.closest('.board-slot'), k = a && a.dataset && a.dataset.k;
    const sel = a && a.tagName === 'INPUT' && a.type === 'text' ? [a.selectionStart, a.selectionEnd] : null;
    renderLobby();
    if (slot && k) { const el = ui.lobby.querySelector(`.board-slot[data-slot="${slot.dataset.slot}"] [data-k="${k}"]`); if (el) { el.focus(); if (sel) el.setSelectionRange(...sel); } }
  }
  function renderLobby() {
    if (!ui) return;
    const def = ui.def, R = roster(), schemes = schemeList(def);
    const meName = cleanName(window.__game && window.__game.playerName);   // order per Tomek: name first, then human/CPU
    const rows = ui.slots.map((s, i) => `
      <div class="board-slot" data-slot="${i}" style="display:grid;grid-template-columns:44px repeat(4,minmax(0,1fr));gap:6px;align-items:center;padding:6px;border-left:4px solid ${SLOT_COLORS[i]};background:#1c2b4d;border-radius:4px${s.type === 'off' ? ';opacity:.6' : ''}">
        <div style="position:relative;width:44px;height:56px"><canvas data-portrait="${esc(s.char)}" width="88" height="112" style="width:44px;height:56px"></canvas><strong style="position:absolute;left:0;top:0;color:${SLOT_COLORS[i]};text-shadow:0 1px 2px #000">P${i + 1}</strong></div>
        <input data-k="name" aria-label="name ${i + 1}" maxlength="14" placeholder="${esc(s.type === 'avg' ? T.avgName : s.type === 'cpu' ? ((R.find(r => r.id === s.char) || {}).name || '') : i === 0 && meName ? meName : T.name)}" value="${esc(s.type === 'human' ? s.name : '')}" style="${css.sel}"${s.type !== 'human' ? ' disabled' : ''}>
        <select data-k="type" aria-label="P${i + 1}" style="${css.sel}">${['human', 'avg', 'cpu', 'off'].map(v => opt(v, T.type[v], s.type)).join('')}</select>
        <select data-k="char" aria-label="character ${i + 1}" style="${css.sel}"${s.type === 'off' ? ' disabled' : ''}>${R.map(r => opt(r.id, r.name, s.char)).join('')}</select>
        <select data-k="ctrl" aria-label="controls ${i + 1}" style="${css.sel}"${s.type !== 'human' ? ' disabled' : ''}>${schemes.map(v => opt(v, schemeLabel(def, v), s.ctrl)).join('')}</select>
      </div>`).join('');
    const top = topList(def).slice(0, 5).map((e, i) => `<li>${i + 1}. ${esc(e.name)} — ${esc(def.score.format(e.score))}</li>`).join('');
    const g = gBoard(def), list = l => `<ol style="list-style:none;margin:6px 0 0;padding:0;font-size:13px;line-height:1.5">${l}</ol>`;
    const li = l => l.slice(0, 5).map((e, i) => `<li>${i + 1}. ${esc(e.name)} — ${esc(def.score.format(e.score))}</li>`).join('');
    const col = (id, title, body) => `<div data-list="${id}" style="flex:1 1 150px"><strong style="color:#9fd0f0;font-size:12px">${title}</strong>${body}</div>`;
    const note = (txt, c = '#9aa0c0') => `<p style="margin:6px 0;font-size:12px;color:${c}">${txt}</p>`;
    const gl = !SCORES_URL || !def.global ? '' : `<div id="board-global" data-status="${g ? g.status : 'loading'}" style="flex:3 1 460px"><strong style="color:#9fd0f0;font-size:12px">${T.gtop}</strong>${
      !g || g.status === 'loading' ? note(T.gload) : g.status === 'error' ? note(T.gerr, '#ff9a5e')
      : `<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:4px">${
          col('best', T.gbest, g.best.length ? list(li(g.best)) : note(T.gempty))}${
          col('recent', T.grecent, g.recent.length ? list(li(g.recent)) : note('—'))}${
          col('average', T.gavg, Number.isFinite(g.average.score) ? `<p style="margin:6px 0;font-size:18px;color:#f5f0e0">${esc(def.score.format(g.average.score))}</p>${note(T.gof(g.average.count))}` : note('—'))}</div>`}
      <label style="display:flex;gap:6px;align-items:center;justify-content:center;margin-top:6px;font-size:11px;color:#c8cee0"><input id="board-global-send" type="checkbox"${globalOn() ? ' checked' : ''}> ${T.gsend}</label></div>`;
    ui.lobby.innerHTML = `<section style="box-sizing:border-box;width:min(96vw,780px);max-height:94vh;overflow:auto;padding:clamp(12px,3vw,24px);border:3px solid ${def.flagColors[0] === '#ffffff' ? '#ffd21f' : def.flagColors[0]};border-radius:10px;background:#172442;box-shadow:0 12px 45px #0009">
      <h2 style="margin:0 0 6px;font-size:clamp(20px,5vw,32px);color:#ffd21f;text-align:center;letter-spacing:2px">${esc(def.title(PL))}</h2>
      <p style="margin:0 0 14px;text-align:center;line-height:1.4;color:#c8cee0">${esc(def.sub(PL))}</p>
      <div style="display:grid;gap:6px">${rows}</div>
      <p style="margin:10px 0 0;text-align:center;font-size:12px;color:#9aa0c0">${esc(T.cpuInfo(def.score.format(cpuRef(def).score), cpuRef(def).source))} · ${esc(T.pads)}</p>
      <p id="board-error" role="alert" style="min-height:1.3em;margin:10px 0;color:#ff6b5e;text-align:center"></p>
      <div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
        <button id="board-start" type="button" style="${css.btn};border-color:#7cff6b;font-size:17px">${T.start}</button>
        <button id="board-close" type="button" style="${css.btn}">${T.close}</button>
      </div>
      ${top || gl ? `<div style="display:flex;flex-wrap:wrap;gap:12px;border-top:1px solid #34476e;padding-top:8px;text-align:center">${gl}${top ? `<div style="flex:1 1 220px"><strong style="color:#ffd21f;font-size:12px">${T.top}</strong>${list(top)}</div>` : ''}</div>` : ''}
    </section>`;
    const L = ui.lobby;
    L.querySelectorAll('.board-slot select').forEach(sel => sel.addEventListener('change', () => {
      const i = +sel.closest('.board-slot').dataset.slot; ui.slots[i][sel.dataset.k] = sel.value; writeLS(slotsKey(def), ui.slots); renderLobby();
    }));
    L.querySelectorAll('.board-slot input').forEach(inp => inp.addEventListener('input', () => {
      const i = +inp.closest('.board-slot').dataset.slot; ui.slots[i].name = cleanName(inp.value); writeLS(slotsKey(def), ui.slots);
    }));
    // The Enter that closes the host's dialogue must not also press START in the freshly opened lobby.
    L.querySelector('#board-start').addEventListener('click', e => { if (e.detail === 0 && performance.now() - ui.openedAt < 400) return; startRun(); });
    L.querySelector('#board-close').addEventListener('click', close);
    const gs = L.querySelector('#board-global-send'); if (gs) gs.addEventListener('change', () => SC && SC.setEnabled(gs.checked));
    const err = validate(); L.querySelector('#board-error').textContent = err || '';
    paintPortraits();
  }

  /* ================================================================== open / run / close */
  // The page styles canvases/flex boxes with explicit display values, so the `hidden` attribute alone is not enough.
  function showLobby(on) {
    if (!ui) return;
    ui.lobby.hidden = !on; ui.lobby.style.display = on ? 'flex' : 'none';
    ui.cvs.hidden = on; ui.cvs.style.display = on ? 'none' : 'block';
  }
  function open(id) {
    const def = window.ARK_BOARDS[id]; if (!def || ui) return false;
    const root = document.createElement('div');
    root.id = 'board-overlay'; root.dataset.board = id; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-label', def.title(PL));
    root.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(8,12,24,.92);font:15px monospace;color:#f8f3df';
    const lobby = document.createElement('div'); lobby.id = 'board-lobby';
    lobby.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:8px';
    const cvs = document.createElement('canvas'); cvs.id = 'board-canvas'; cvs.tabIndex = 0; cvs.hidden = true;
    cvs.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;background:#05070d;outline:none;touch-action:none';
    cvs.addEventListener('pointerdown', e => {
      if (!run || run.phase !== 'done' || run.doneT < .8) return;
      e.preventDefault(); if (e.clientX < innerWidth / 2) startRun(); else toLobby();
    });
    root.append(lobby, cvs); document.body.appendChild(root);
    ui = { def, root, lobby, cvs, cx: cvs.getContext('2d'), slots: loadSlots(def), openedAt: performance.now() };
    showLobby(true);
    held.clear(); events.length = 0; if (A.keys && A.keys.clear) A.keys.clear();
    renderLobby(); fetchGlobal(def);
    Promise.all(roster().map(r => atlas(r.atlas).ready)).then(paintPortraits);
    setTimeout(() => { const st = ui && ui.lobby.querySelector('#board-start'); if (st && !run) st.focus(); }, 450);
    return true;
  }
  function startRun() {
    if (!ui) return false;
    const err = validate(); if (err) { const e = ui.lobby.querySelector('#board-error'); if (e) e.textContent = err; return false; }
    const def = ui.def, R = Object.fromEntries(roster().map(r => [r.id, r])), ref = cpuRef(def), base = ref.score;
    const meName = window.__game && window.__game.playerName;
    let cpuN = 0, humanN = 0;
    const players = ui.slots.map((s, i) => [s, i]).filter(([s]) => s.type !== 'off').map(([s, i]) => {
      const r = R[s.char] || roster()[0], cpu = s.type === 'cpu' || s.type === 'avg', avg = s.type === 'avg';
      const name = avg ? T.avgName : cpu ? `${r.name}` : (s.name || (humanN === 0 && meName ? cleanName(meName) : `${PL ? 'GRACZ' : 'PLAYER'} ${i + 1}`));
      if (!cpu) humanN++;
      const p = { slot: i, lane: i, cpu, avg, name, char: r.id, charName: r.name, atlas: r.atlas, color: SLOT_COLORS[i], ctrl: s.ctrl, tag: avg ? (PL ? 'ŚR' : 'AVG') : cpu ? 'CPU' : `P${i + 1}` };
      // PRZECIĘTNIAK replays the average exactly; other computer runners are the same run a little faster or slower
      const k = avg ? 1 : cpu ? [.96, 1.04, .93, 1.07][cpuN++ % 4] * (1 + (Math.random() - .5) * .03) : 1;
      if (cpu) { p.cpuScore = base * k; p.cpuTrace = ref.trace ? ref.trace.map(v => v * k) : null; }
      return p;
    });
    for (const p of players) atlas(p.atlas);
    const r0 = rec(def); r0.tries++; A.save();
    const api = { A, PL, W, H, players, drawSprite, atlas, sfx, keyLabel: (p, a) => (def.keys[p.ctrl] ? keyName(def.keys[p.ctrl][a]) : (a === 'left' ? 'LB' : 'RB')) };
    run = { def, players, game: def.create(api), phase: 'count', t: 0, time: 0, doneT: 0, results: null, cpuBase: base, cpuSource: ref.source, cpuTrace: ref.trace };
    held.clear(); events.length = 0;
    showLobby(false); resize(); ui.cvs.focus();
    last = 0; acc = 0; if (!raf) raf = requestAnimationFrame(loop);
    return true;
  }
  function finish() {
    // scores are shown, ranked and stored at 0.01 (time) precision so the table, record and top list agree
    const def = run.def, res = run.game.results().map(r => ({ ...r, score: r.score == null ? null : Math.round(r.score * 100) / 100, player: run.players.find(p => p.slot === r.slot) }));
    const key = r => (r.score == null ? Infinity : def.score.lower ? r.score : -r.score);
    res.sort((a, b) => key(a) - key(b));
    res.forEach((r, i) => { r.place = r.score == null ? null : i + 1; });
    const R = rec(def), top = topList(def);
    for (const r of res) {
      if (r.player.cpu || r.score == null) continue;
      r.medal = medalFor(def, r.score);
      R.history.push(r.score); if (R.history.length > HISTORY) R.history.splice(0, R.history.length - HISTORY);
      if (Array.isArray(r.trace)) { R.traces = Array.isArray(R.traces) ? R.traces : []; R.traces.push(r.trace.map(v => Math.round(v * 100) / 100)); if (R.traces.length > HISTORY) R.traces.splice(0, R.traces.length - HISTORY); }
      if (!R.best || better(def, r.score, R.best)) { R.best = r.score; r.record = true; }
      R.medal = Math.max(R.medal || 0, r.medal);
      top.push({ name: r.player.name, char: r.player.char, score: r.score, at: Date.now() });
    }
    if (res[0] && res[0].score != null && !res[0].player.cpu) { R.won = true; if (A.celebrate) A.celebrate(); }
    top.sort((a, b) => (def.score.lower ? a.score - b.score : b.score - a.score)); writeLS(topKey(def), top.slice(0, TOP_N));
    A.save();
    run.results = res; run.phase = 'done'; run.doneT = 0;
    submitGlobal(def, res);
  }
  function toLobby() { run = null; held.clear(); events.length = 0; if (raf) cancelAnimationFrame(raf); raf = 0; if (ui) { showLobby(true); renderLobby(); const st = ui.lobby.querySelector('#board-start'); if (st) st.focus(); } }
  function back() { if (run) toLobby(); else close(); }
  function close() {
    run = null; if (raf) cancelAnimationFrame(raf); raf = 0;
    if (ui) ui.root.remove(); ui = null; held.clear(); events.length = 0;
  }

  /* ================================================================== loop */
  function tick() {
    if (!run) return;
    if (run.phase !== 'done') pollPads();
    const ev = events.splice(0);
    run.t += DT;
    if (run.phase === 'count') {
      run.game.update(DT, ev, 'count');
      if (run.t >= run.game.countLen) { run.phase = 'run'; run.t = 0; run.game.go(); }
    } else if (run.phase === 'run') {
      run.time += DT; run.game.update(DT, ev, 'run');
      if (run.game.finished()) finish();
    } else { run.doneT += DT; run.game.update(DT, [], 'done'); }
  }
  function resize() { if (!ui) return; const d = Math.min(2, window.devicePixelRatio || 1); ui.cvs.width = Math.round(innerWidth * d); ui.cvs.height = Math.round(innerHeight * d); }
  window.addEventListener('resize', resize);
  function render() {
    if (!ui || !run) return;
    const c = ui.cx, cv = ui.cvs;
    c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = '#05070d'; c.fillRect(0, 0, cv.width, cv.height);
    const k = Math.min(cv.width / W, cv.height / H);
    c.setTransform(k, 0, 0, k, (cv.width - W * k) / 2, (cv.height - H * k) / 2);
    c.save(); c.beginPath(); c.rect(0, 0, W, H); c.clip();
    run.game.draw(c, run.phase, run.t);
    if (run.phase === 'done' && run.doneT > .6) drawResults(c);
    else { c.font = '10px Silkscreen'; c.textAlign = 'center'; c.fillStyle = 'rgba(255,255,255,.8)'; c.fillText(T.menu, W / 2, H - 6); c.textAlign = 'left'; }
    c.restore();
  }
  function drawMedal(c, x, y, r, m) {
    c.fillStyle = MEDAL_COL[m]; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill();
    c.strokeStyle = 'rgba(0,0,0,.35)'; c.lineWidth = r * .18; c.beginPath(); c.arc(x, y, r * .7, 0, 7); c.stroke();
  }
  function drawResults(c) {
    const def = run.def, rows = run.results, bw = 640, rh = 34, g = gBoard(def), useG = !!(g && g.status === 'ok' && g.best.length);
    const top = (useG ? g.best : topList(def)).slice(0, 5);
    const bh = 112 + rows.length * rh + (top.length ? 26 + top.length * 16 + (useG ? 16 : 0) : 0), bx = (W - bw) / 2, by = Math.max(14, (H - bh) / 2);
    c.fillStyle = 'rgba(8,12,40,.92)'; c.fillRect(bx, by, bw, bh); c.strokeStyle = '#ffd21f'; c.lineWidth = 2; c.strokeRect(bx, by, bw, bh);
    const w = rows[0] && rows[0].score != null ? rows[0].player : null;
    c.textAlign = 'center'; c.font = '20px Silkscreen'; c.fillStyle = w && !w.cpu ? '#7cff6b' : '#ffd21f';
    c.fillText(w ? `${T.wins} ${w.name}${w.cpu && !w.avg ? ' (CPU)' : ''}` : T.dnf, W / 2, by + 32);
    rows.forEach((r, i) => {
      const y = by + 72 + i * rh, p = r.player;
      c.fillStyle = 'rgba(255,255,255,.05)'; if (i % 2) c.fillRect(bx + 10, y - 20, bw - 20, rh);
      c.textAlign = 'left'; c.font = '18px Silkscreen'; c.fillStyle = '#f5f0e0'; c.fillText(r.place ? `${r.place}.` : '—', bx + 20, y);
      c.font = '14px Silkscreen'; c.fillStyle = p.color; c.fillText(`${p.name}${p.avg ? '' : ` ${p.tag}`}`, bx + 62, y);
      c.textAlign = 'right'; c.fillStyle = '#f5f0e0'; c.font = '16px Silkscreen';
      c.fillText(r.score == null ? T.dnf : def.score.format(r.score), bx + 430, y);
      if (r.note) { c.font = '10px Silkscreen'; c.fillStyle = '#ff9a5e'; c.fillText(r.note, bx + 430, y + 12); }
      if (r.medal) { drawMedal(c, bx + 462, y - 6, 9, r.medal); c.textAlign = 'left'; c.font = '11px Silkscreen'; c.fillStyle = MEDAL_COL[r.medal]; c.fillText(T.medal[r.medal], bx + 476, y - 1); }
      if (r.record) { c.textAlign = 'left'; c.font = '10px Silkscreen'; c.fillStyle = '#7cff6b'; c.fillText(`★ ${T.record}`, bx + 476, y + 12); }
      if (Number.isInteger(r.global)) { c.textAlign = 'right'; c.font = '11px Silkscreen'; c.fillStyle = '#9fd0f0'; c.fillText(T.grank(r.global), bx + bw - 16, y); }
    });
    let y = by + 72 + rows.length * rh;
    if (top.length) {
      c.textAlign = 'center'; c.font = '11px Silkscreen'; c.fillStyle = useG ? '#9fd0f0' : '#ffd21f'; c.fillText(useG ? T.gtop : T.top, W / 2, y + 4);
      c.font = '11px Silkscreen'; c.fillStyle = '#c8cee0';
      top.forEach((e, i) => c.fillText(`${i + 1}. ${e.name} — ${def.score.format(e.score)}`, W / 2, y + 22 + i * 16));
      y += 26 + top.length * 16;
      if (useG && g.average && Number.isFinite(g.average.score)) { c.fillStyle = '#9fd0f0'; c.fillText(`${T.gavg}: ${def.score.format(g.average.score)} (${T.gof(g.average.count)})`, W / 2, y + 4); }
    }
    if (run.doneT > .8) { c.font = '12px Silkscreen'; c.fillStyle = Math.floor(run.doneT * 3) % 2 ? '#ffd21f' : '#fff3b0'; c.textAlign = 'center'; c.fillText(T.again, W / 2, by + bh - 12); }
    c.textAlign = 'left';
  }
  function loop(ts) {
    raf = 0; if (!run || !ui) return;
    const dt = Math.min(.1, (ts - (last || ts)) / 1000); last = ts; acc += dt;
    while (acc >= DT) { tick(); acc -= DT; if (!run) return; }
    render();
    raf = requestAnimationFrame(loop);
  }

  /* ================================================================== API + test diagnostics */
  A.board = {
    open, close, start: startRun, toLobby, cpuBase: id => cpuBase(window.ARK_BOARDS[id]), roster,
    press(slot, action) { if (run) events.push({ slot, action }); },
    // deterministic stepping for tests: stop the RAF loop, then advance n fixed ticks
    pause() { if (raf) cancelAnimationFrame(raf); raf = 0; },
    resume() { if (run && !raf) { last = 0; acc = 0; raf = requestAnimationFrame(loop); } },
    step(n = 1) { for (let i = 0; i < n && run; i++) tick(); render(); },
    setSlots(s) { if (!ui) return; ui.slots = s.map(x => ({ ...x, name: cleanName(x.name) })); writeLS(slotsKey(ui.def), ui.slots); renderLobby(); },
    get scoresUrl() { return SCORES_URL; }, global: id => { const g = SC && SC.cached(id); return g ? JSON.parse(JSON.stringify(g)) : null; }, cpuRef: id => cpuRef(window.ARK_BOARDS[id]),
    get venues() { return JSON.parse(JSON.stringify(venues)); },
    get ui() { return ui ? { id: ui.def.id, slots: ui.slots.map(s => ({ ...s })), lobby: !ui.lobby.hidden } : null; },
    get run() { return run; },
    get state() {
      if (!run) return null;
      return { phase: run.phase, t: run.t, time: run.time, cpuBase: run.cpuBase, cpuSource: run.cpuSource, cpuTrace: run.cpuTrace, game: run.game.debug ? run.game.debug() : null,
        results: run.results && run.results.map(r => ({ slot: r.slot, name: r.player.name, cpu: r.player.cpu, score: r.score, place: r.place, medal: r.medal || 0, record: !!r.record, note: r.note || '', global: r.global === undefined ? null : r.global })) };
    },
  };
  window.__board = A.board;
});
