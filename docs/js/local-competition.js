/* E01: session-only local competition input and score bookkeeping.
   No extra hero, save key, Q mutation, or changes to the single-player controls. */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK;
  const PL = A.LANG === 'pl';
  const SCORE_KINDS = new Set(['hits', 'time']);
  let active = null;
  let race = null;
  let overlay = null;
  const held = new Set();

  const typing = target => !!(target && target.closest && target.closest(
    'input, textarea, select, [contenteditable="true"], .chat, #player-name-input'));

  function createSession({ id, scoreKind, participants }) {
    if (typeof id !== 'string' || !id.trim()) throw new Error('session id is required');
    if (!SCORE_KINDS.has(scoreKind)) throw new Error('scoreKind must be hits or time');
    if (!Array.isArray(participants) || participants.length !== 2) throw new Error('exactly two participants are required');
    const ids = new Set(), keys = new Set();
    const players = participants.map(p => {
      if (!p || typeof p.id !== 'string' || !p.id.trim() || typeof p.name !== 'string' || !p.name.trim()
          || typeof p.key !== 'string' || !p.key.trim()) throw new Error('participant id, name, and key are required');
      if (ids.has(p.id) || keys.has(p.key)) throw new Error('participant ids and keys must be unique');
      ids.add(p.id); keys.add(p.key);
      return { id: p.id, name: p.name, key: p.key, result: 0 };
    });
    const session = {
      id, scoreKind, participants: players, cancelled: false,
      reset() { for (const p of players) p.result = 0; this.cancelled = false; active = this; held.clear(); return this; },
      cancel() { this.cancelled = true; if (active === this) active = null; held.clear(); },
      record(id) { if (this.cancelled) return false; const p = players.find(x => x.id === id); if (!p) return false; p.result++; return true; },
      setResult(id, value) { if (this.cancelled || !Number.isFinite(value)) return false; const p = players.find(x => x.id === id); if (!p) return false; p.result = value; return true; },
      winner() {
        if (this.cancelled) return null;
        const [a, b] = players;
        if (a.result === b.result) return null;
        if (scoreKind === 'hits') return a.result > b.result ? a.id : b.id;
        return a.result < b.result ? a.id : b.id;
      },
    };
    if (active) active.cancel();
    active = session;
    held.clear();
    return session;
  }

  function raceLocation() {
    const t = A.MAP.track, ox = t.cx - t.rx - 72, oy = t.cy;
    for (let r = 0; r < 500; r += 18) for (let a = 0; a < Math.PI * 2; a += .45) {
      const x = ox + Math.cos(a) * r, y = oy + Math.sin(a) * r;
      if (x > 30 && y > 30 && x < A.MAP.w - 30 && y < A.MAP.h - 30 && !A.blocked(x, y)) return { x, y };
    }
    return { x: ox, y: oy };
  }
  const racePoint = raceLocation();
  function makeOverlay() {
    overlay = document.createElement('div');
    overlay.id = 'local-race-overlay'; overlay.setAttribute('role', 'dialog'); overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', PL ? 'Wyścig dwóch graczy' : 'Two-player race');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;padding:12px;background:rgba(8,12,24,.82);font:16px monospace;color:#f8f3df;';
    const title = PL ? 'WYŚCIG WE DWOJE' : 'TWO-PLAYER KEY RACE';
    const hint = PL ? 'Naciskaj szybko swój klawisz. Kto pierwszy do mety?' : 'Mash your own key. First to the finish wins.';
    overlay.innerHTML = `<section style="box-sizing:border-box;width:min(92vw,560px);padding:clamp(16px,4vw,28px);border:3px solid #ffd21f;border-radius:10px;background:#172442;box-shadow:0 12px 45px #0009;text-align:center"><h2 style="margin:0 0 12px;font-size:clamp(18px,5vw,28px)">${title}</h2><p style="margin:0 0 18px;line-height:1.5">${hint}</p><div id="local-race-lanes" style="display:grid;gap:12px;text-align:left"></div><p id="local-race-status" aria-live="polite" style="min-height:1.5em;margin:16px 0"></p><div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap"><button id="local-race-start" type="button"></button><button id="local-race-retry" type="button"></button><button id="local-race-leave" type="button"></button></div></section>`;
    document.body.appendChild(overlay);
    overlay.querySelector('#local-race-start').textContent = 'START';
    overlay.querySelector('#local-race-retry').textContent = PL ? 'JESZCZE RAZ' : 'RETRY';
    overlay.querySelector('#local-race-leave').textContent = PL ? 'WYJDŹ' : 'LEAVE';
    for (const b of overlay.querySelectorAll('button')) b.style.cssText = 'min-height:44px;padding:8px 16px;border:2px solid #ffd21f;border-radius:6px;background:#263a61;color:#fff;font:bold 15px monospace;cursor:pointer';
    overlay.querySelector('#local-race-start').addEventListener('click', startRace);
    overlay.querySelector('#local-race-retry').addEventListener('click', resetRace);
    overlay.querySelector('#local-race-leave').addEventListener('click', closeRace);
  }
  const raceStatus = text => { const el = overlay && overlay.querySelector('#local-race-status'); if (el) el.textContent = text; };
  function drawRace() {
    if (!overlay || !race) return;
    overlay.querySelector('#local-race-lanes').innerHTML = race.participants.map((p, i) => {
      const pct = Math.round(p.result / race.target * 100);
      return `<div><div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:4px"><strong>${p.name}</strong><span>${p.key.replace('Key', '')}</span><span>${p.result}/${race.target}</span></div><div style="height:18px;background:#0a1120;border:1px solid #9ba9c4;border-radius:4px;overflow:hidden"><div style="width:${pct}%;height:100%;background:${i ? '#4aa8e8' : '#e34c4c'}"></div></div></div>`;
    }).join('');
    overlay.querySelector('#local-race-start').hidden = race.state !== 'ready';
    overlay.querySelector('#local-race-retry').hidden = !['finished', 'cancelled'].includes(race.state);
    if (race.state === 'ready') raceStatus(PL ? 'Jesteście gotowi?' : 'Ready?');
    else if (race.state === 'running') raceStatus(PL ? 'START! Naciskajcie swoje klawisze.' : 'GO! Press your own key.');
    else if (race.state === 'cancelled') raceStatus(PL ? 'Wyścig przerwany - bez wyniku.' : 'Race cancelled - no result.');
    else if (race.state === 'finished') raceStatus(race.winner === 'tie' ? (PL ? 'REMIS!' : 'TIE!') : (PL ? `WYGRYWA ${race.participants.find(p => p.id === race.winner).name}!` : `${race.participants.find(p => p.id === race.winner).name} WINS!`));
  }
  function openRace() {
    if (active) active.cancel(); active = null;
    if (race && race.state !== 'closed') closeRace();
    race = { state: 'ready', target: 12, startAt: null, winner: null, participants: [
      { id: 'p1', name: PL ? 'GRACZ 1' : 'PLAYER 1', key: 'KeyA', result: 0, finishedAt: null },
      { id: 'p2', name: PL ? 'GRACZ 2' : 'PLAYER 2', key: 'KeyL', result: 0, finishedAt: null },
    ] };
    held.clear(); makeOverlay(); drawRace(); return race;
  }
  function startRace() {
    if (!race || !['ready', 'cancelled'].includes(race.state)) return;
    race.state = 'running'; race.startAt = performance.now(); race.winner = null;
    race.participants.forEach(p => { p.result = 0; p.finishedAt = null; }); held.clear(); drawRace();
  }
  function resetRace() {
    if (!race || !['finished', 'cancelled'].includes(race.state)) return;
    race.state = 'ready'; race.startAt = null; race.winner = null;
    race.participants.forEach(p => { p.result = 0; p.finishedAt = null; }); held.clear(); drawRace();
  }
  function closeRace() {
    if (race) race.state = 'closed'; race = null; held.clear();
    if (overlay) overlay.remove(); overlay = null;
  }
  function completeLane(p) {
    if (p.result >= race.target && p.finishedAt === null) p.finishedAt = Math.floor((performance.now() - race.startAt) / 100) * 100;
    if (race.participants.every(x => x.finishedAt !== null)) {
      race.state = 'finished'; const [a, b] = race.participants;
      race.winner = a.finishedAt === b.finishedAt ? 'tie' : (a.finishedAt < b.finishedAt ? a.id : b.id);
    }
    drawRace();
  }

  function onKeyDown(e) {
    if (race && race.state !== 'closed') {
      if (typing(e.target) || typing(document.activeElement)) { e.preventDefault(); e.stopImmediatePropagation(); return; }
      if (e.code === 'Escape') {
        if (race.state === 'running' || race.state === 'ready') {
          race.state = 'cancelled'; race.winner = null;
          race.participants.forEach(p => { p.result = 0; p.finishedAt = null; }); drawRace();
        } else if (race.state === 'finished' || race.state === 'cancelled') closeRace();
        e.preventDefault(); e.stopImmediatePropagation(); return;
      }
      if (e.repeat || held.has(e.code)) { e.preventDefault(); e.stopImmediatePropagation(); return; }
      held.add(e.code);
      if (race.state === 'running') { const p = race.participants.find(x => x.key === e.code); if (p && p.finishedAt === null) { p.result++; completeLane(p); } }
      e.preventDefault(); e.stopImmediatePropagation(); return;
    }
    if (!active || active.cancelled || typing(e.target) || typing(document.activeElement)
        || e.ctrlKey || e.altKey || e.metaKey) return;
    if (e.code === 'Escape') { active.cancel(); e.preventDefault(); e.stopImmediatePropagation(); return; }
    if (e.repeat || held.has(e.code)) return;
    held.add(e.code);
    const p = active.participants.find(x => x.key === e.code);
    if (p) { active.record(p.id); e.preventDefault(); e.stopImmediatePropagation(); }
  }
  function onKeyUp(e) { held.delete(e.code); }
  window.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('keyup', onKeyUp, true);

  A.HOOKS.near.push(() => race && race.state !== 'closed' ? [] : [{ x: racePoint.x, y: racePoint.y, r: 30, _localRace: true, onInteract: openRace }]);
  A.HOOKS.busy.push(() => !!(race && race.state !== 'closed'));
  A.HOOKS.world.push((push, S, inView) => {
    if (!inView(racePoint.x, racePoint.y)) return;
    push(racePoint.y, () => {
      const [x, y] = S(racePoint.x, racePoint.y), c = A.ctx;
      c.fillStyle = '#263a61'; c.fillRect(x - 9 * A.zoom, y - 25 * A.zoom, 18 * A.zoom, 25 * A.zoom);
      c.fillStyle = '#ffd21f'; c.font = `${Math.max(8, 9 * A.zoom)}px monospace`; c.textAlign = 'center'; c.fillText('2P', x, y - 12 * A.zoom); c.textAlign = 'left';
    });
  });
  A.HOOKS.minimap.push(dot => dot(racePoint.x, racePoint.y, '#ffd21f'));

  A.localCompetition = { createSession, openRace, get activeSession() { return active; }, get race() { return race; }, get racePoint() { return { ...racePoint }; } };
});
