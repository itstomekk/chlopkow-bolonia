/* D03 - outdoor mission checkpoints (docs/missions.json, D02 contract).
   One small HOOKS.near + HOOKS.questLog registration per authored mission
   step; no general quest engine. The interact point sits 50 px below the quiz
   board (past its r=30 claim), so the quiz keeps priority on the board itself
   and the mission answers only to its own marker. Progress is stored in
   Q().missions (persisted through the existing save; D04 versions the save). */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK, { HOOKS, ITEMS } = A;
  const Q = () => A.Q;
  const PL = A.LANG === 'pl';
  const LBL = PL ? 'ZADANIE' : 'TASK';
  const DONE_TXT = PL ? 'ZADANIE WYKONANE' : 'TASK DONE';

  fetch('missions.json')
    .then(r => { if (!r.ok) throw new Error('missions.json HTTP ' + r.status); return r.json(); })
    .then(list => {
      if (!Array.isArray(list)) throw new Error('missions.json: expected a JSON list');
      if (!Q().missions) Q().missions = {};
      const missionsOf = () => (Q().missions || (Q().missions = {}));
      const done = (mid, sid) => { const ms = missionsOf(); return !!(ms[mid] && ms[mid][sid]); };
      const anchorPt = a => {
        if (a && a.boardSpot) {
          const b = (ITEMS.boards || []).find(x => x.spot === a.boardSpot);
          return b ? { x: b.x, y: b.y + 50 } : null;   // below board marker, past the quiz r=30
        }
        return (a && a.x != null && a.y != null) ? { x: a.x, y: a.y } : null;
      };

      for (const m of list) {
        if (!m || !Array.isArray(m.steps)) continue;
        for (const st of m.steps) {
          const mid = m.id, sid = st && st.id;
          if (!mid || !sid || done(mid, sid)) continue;
          const pt = anchorPt(st.anchor);
          if (!pt) continue;
          HOOKS.near.push(() => (done(mid, sid) ? [] : [{
            x: pt.x, y: pt.y, r: 30, _mission: true, label: LBL,
            onInteract() {
              if (done(mid, sid)) return;             // explicit interaction only, once
              const ms = missionsOf();
              if (!ms[mid]) ms[mid] = {};
              ms[mid][sid] = true;
              A.save();
              A.popToast(DONE_TXT);
              A.celebrate();
            },
          }]));
        }
      }

      const missionTitle = m => {
        const t = m && m.title;
        if (t && typeof t === 'object') return (PL ? t.pl : t.en) || m.id;
        return m.id;
      };
      HOOKS.questLog.push(lines => {
        for (const m of list) {
          if (!m || !Array.isArray(m.steps) || !m.id) continue;
          const all = m.steps.every(st => st && st.id && done(m.id, st.id));
          lines.push([`${LBL}: ${missionTitle(m)}`, all]);
        }
      });
    })
    .catch(e => console.warn('missions.js:', e));
});