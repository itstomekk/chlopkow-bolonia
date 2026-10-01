/* E01: session-only local competition input and score bookkeeping.
   No extra hero, save key, Q mutation, or changes to the single-player controls. */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK;
  const SCORE_KINDS = new Set(['hits', 'time']);
  let active = null;
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

  function onKeyDown(e) {
    if (!active || active.cancelled || typing(e.target) || typing(document.activeElement)
        || e.ctrlKey || e.altKey || e.metaKey) return;
    if (e.code === 'Escape') {
      active.cancel();
      e.preventDefault(); e.stopImmediatePropagation();
      return;
    }
    if (e.repeat || held.has(e.code)) return;
    held.add(e.code);
    const p = active.participants.find(x => x.key === e.code);
    if (p) {
      active.record(p.id);
      e.preventDefault(); e.stopImmediatePropagation();
    }
  }
  function onKeyUp(e) { held.delete(e.code); }
  window.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('keyup', onKeyUp, true);

  A.localCompetition = { createSession, get activeSession() { return active; } };
});
