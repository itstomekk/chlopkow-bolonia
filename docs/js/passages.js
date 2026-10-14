/* PASSAGES ENGINE: data-driven, lazy-loaded secret links between two places (tunnels now; forest paths, an underground village,
   quiz-gated doors, secret-society cellars later). This is the ONLY passage file loaded at startup; everything heavy is fetched on first need.

   Files
     docs/data/passages.json   registry (tiny, fetched here at startup): id, kind, module, data, gate, ends{room, mouth/poi, arrive}, text keys.
     docs/js/<kind>.js         lazy module (e.g. underground-tunnel.js): calls PASSAGES.defineKind(kind, { build(def, data, ctx) -> room }).
     docs/data/<passage>.json  lazy data for that module: layout + lore; its optional `text:{pl:{},en:{}}` is merged into ARK.T on load.

   Rooms and the stack (game.js, ARK.rooms): descend(room, at, back) / ascend(roomId, at) / surface(x, y, dir). village -> church -> crypt -> tunnel
   is a stack; the village (OUT) is always underneath, so save() writes village coordinates at any depth and a reload never strands Arek.

   Gates: evaluated by PASSAGES.gate(descriptor) -> { open, reason }.
     { type:'always' }                          open.
     { type:'flag', key:'tunnelOpen' [,value] } open when Q[key] equals value (default true).
     { type:'all'|'any', of:[gate,...] } / { type:'not', gate }   combinators.
     { type:'quiz', quiz:'<id>' }   STUB: always locked, reason 'TODO ...'. Plug in later: PASSAGES.defineGate('quiz', (g, ctx) => ...).
     { type:'mission', mission:'<id>', step:'<id>' }   STUB, same.
   Gates only decide whether a passage may be USED; whether it is VISIBLE on the village side is a separate `visible` descriptor on the end.

   Public API (window.PASSAGES): list(), get(id), gate(g), defineGate(type, fn), defineKind(kind, impl), preload(id) -> Promise,
   enter(id, endName), leave(id, endName), state() (registry + load status, for tests). */
'use strict';
(() => {
  const S = { registry: null, error: null, byId: {}, kinds: {}, scripts: {}, jsons: {}, loads: {}, status: {}, entering: false, installed: false };
  const TODO = what => `TODO: ${what} gate is not wired yet (see DEVELOPMENT.md, Passages engine)`;
  const gateTypes = {
    always: () => true,
    flag: (g, c) => !!c.Q[g.key] === (g.value === undefined ? true : !!g.value),
    all: (g, c) => (g.of || []).every(x => evalGate(x, c).open),
    any: (g, c) => (g.of || []).some(x => evalGate(x, c).open),
    not: (g, c) => !evalGate(g.gate, c).open,
    quiz: () => ({ open: false, reason: TODO('quiz') }),        // STUB: later read Q.quiz / quiz.js
    mission: () => ({ open: false, reason: TODO('mission') }),  // STUB: later read Q.missions[mission][step]
  };
  function evalGate(g, ctx) {
    ctx = ctx || { Q: (window.ARK && window.ARK.Q) || {} };
    if (!g) return { open: true, reason: '' };
    const fn = gateTypes[g.type];
    if (!fn) return { open: false, reason: `unknown gate type "${g.type}"` };
    try { const r = fn(g, ctx); return typeof r === 'object' ? { open: !!r.open, reason: r.reason || '' } : { open: !!r, reason: r ? '' : `gate ${g.type} not met` }; }
    catch (e) { return { open: false, reason: String(e && e.message || e) }; }
  }

  /* ---------- lazy loading (promises are cached; a failure is not cached, so the player can retry) ---------- */
  const once = (cache, key, make) => cache[key] || (cache[key] = make().catch(e => { delete cache[key]; throw e; }));
  const loadScript = src => once(S.scripts, src, () => new Promise((res, rej) => {
    const s = document.createElement('script'); s.src = src; s.async = true;
    s.onload = () => res(src); s.onerror = () => { s.remove(); rej(new Error('script ' + src)); };
    document.head.appendChild(s);
  }));
  const loadJSON = src => once(S.jsons, src, () => fetch(src).then(r => { if (!r.ok) throw new Error(src + ' HTTP ' + r.status); return r.json(); }));
  const registryReady = () => S.ready || (S.ready = fetch('data/passages.json')
    .then(r => { if (!r.ok) throw new Error('passages.json HTTP ' + r.status); return r.json(); })
    .then(j => { S.registry = j; for (const p of j.passages || []) S.byId[p.id] = p; return j; })
    .catch(e => { S.error = String(e.message || e); console.warn('passages.js:', e); S.ready = null; return null; }));

  function load(id) {
    return once(S.loads, id, async () => {
      await registryReady(); const def = S.byId[id]; if (!def) throw new Error('unknown passage ' + id);
      S.status[id] = 'loading';
      try {
        const [data] = await Promise.all([def.data ? loadJSON(def.data) : {}, loadScript(def.module)]);
        if (!S.kinds[def.kind]) throw new Error(`module ${def.module} did not define kind ${def.kind}`);
        const A = window.ARK; if (data && data.text && data.text[A.LANG]) Object.assign(A.T, data.text[A.LANG]);
        S.status[id] = 'ready'; return { def, data };
      } catch (e) { S.status[id] = 'failed'; throw e; }
    });
  }
  const fail = (def, e) => { console.warn('passages.js:', e); const A = window.ARK; if (A) A.popToast(A.T[(def && def.text && def.text.fail) || 'passageFail'] || 'PASSAGE FAILED'); };

  /* ---------- crossing ---------- */
  function villagePoint(def, endName, which) {
    const end = def.ends[endName], poi = window.ARK.MAP.pois.find(p => p.key === end.poi); if (!poi) return null;
    const o = end[which]; return { x: poi.x + o.dx, y: poi.y + o.dy, dir: o.dir };
  }
  function enter(id, endName) {
    const A = window.ARK; if (!A || S.entering || A.rooms.busy) return false;
    const def = S.byId[id]; if (!def) { registryReady(); return false; }
    const end = (def.ends || {})[endName];
    const g = evalGate(end && end.gate || def.gate);
    if (!g.open) { A.popToast(A.T[(def.text && def.text.locked) || 'passageLocked']); if (g.reason) console.info('passage', id, 'locked:', g.reason); return false; }
    S.entering = true;
    load(id).then(({ data }) => {
      const room = S.kinds[def.kind].build(def, data, { ARK: A, PASSAGES: api });
      room.rid = room.rid || id; room.passageId = id;
      const at = (room.spawns || {})[endName]; if (!at) throw new Error('tunnel has no spawn for end ' + endName);
      const back = def.ends[endName].arrive;   // where the room we leave will put Arek if he walks back
      if (def.seen) { A.Q[def.seen] = true; A.save(); }
      A.rooms.descend(room, at, back);
    }).catch(e => fail(def, e)).then(() => { S.entering = false; });
    return true;
  }
  function leave(id, endName) {
    const A = window.ARK, def = S.byId[id]; if (!A || !def || A.rooms.busy) return false;
    const end = def.ends[endName];
    if (end.room === 'village') { const p = villagePoint(def, endName, 'surface'); if (!p) return false; return A.rooms.surface(p.x, p.y, p.dir); }
    return A.rooms.ascend(end.room, end.arrive);
  }

  /* ---------- per-frame: walking into a passage mouth (crypt side from the registry, tunnel side from room.portals) ---------- */
  const inRect = (P, r) => P.x >= r.x0 && P.x <= r.x1 && P.y >= r.y0 && P.y <= r.y1;
  function portalCheck() {
    const A = window.ARK, room = A.room; if (!room || A.scene !== 'play' || A.rooms.busy || S.entering || A.talk) return;
    const P = A.P; if (P.air) return;
    for (const pt of room.portals || []) if (inRect(P, pt.rect) && (!pt.active || pt.active())) { pt.go(); return; }
    if (!room.openPassages) return;
    for (const def of S.registry ? S.registry.passages : []) for (const [name, end] of Object.entries(def.ends || {}))
      if (end.room === room.rid && end.mouth && room.openPassages[def.id] && inRect(P, end.mouth)) { enter(def.id, name); return; }
  }

  /* ---------- village side: the hidden slab (invisible and not interactable until `visible` is true) ---------- */
  function drawSlab(sx, sy, s, w, h, def) {
    const A = window.ARK, ctx = A.ctx, r = (x, y, ww, hh, c) => { ctx.fillStyle = c; ctx.fillRect(Math.round(sx + x * s), Math.round(sy + y * s), Math.max(1, Math.round(ww * s)), Math.max(1, Math.round(hh * s))); };
    r(-w / 2 - 1, 1, w + 2, 2, 'rgba(40,52,40,.35)');                 // contact shadow
    r(-w / 2, -h + 1, w, h, '#3f4847'); r(-w / 2 + 1, -h + 2, w - 2, h - 2, '#8f978c');   // slab and its lighter face
    r(-w / 2 + 1, -h + 2, w - 2, 2, '#aab1a6');                        // worn upper edge
    r(-w / 2 + 1, -2, w - 2, 1, '#6a736d');
    for (const [x, y] of [[-2, -9], [-1, -8], [0, -7], [-1, -6], [1, -5], [2, -4], [3, -3]]) r(x, y, 1, 1, '#2f3736');   // the fresh crack
    r(-6, -9, 2, 1, '#697866'); r(5, -4, 2, 1, '#697866');             // moss
    r(-w / 2 - 2, -2, 2, 1, '#71816b'); r(w / 2, -3, 3, 1, '#7e8b72');   // grass tufts touching the stone
  }
  function install() {
    const A = window.ARK; if (!A || S.installed) return; S.installed = true;
    const { HOOKS } = A;
    const slabs = () => (S.registry ? S.registry.passages : []).map(def => {
      const end = Object.entries(def.ends || {}).find(([, e]) => e.slab && e.room === 'village'); if (!end) return null;
      if (!evalGate(end[1].visible || null).open) return null;                       // no spoilers before the secret is found
      const poi = A.MAP.pois.find(p => p.key === end[1].poi); if (!poi) return null;
      return { def, name: end[0], end: end[1], x: poi.x + end[1].slab.dx, y: poi.y + end[1].slab.dy };
    }).filter(Boolean);
    HOOKS.near.push(() => slabs().map(s => ({
      x: s.x, y: s.y, r: s.end.slab.r || 22, _passage: true, label: A.T[s.def.text.label] || 'TUNEL',
      onInteract() {
        const lines = A.T[s.def.text.slab];
        const go = () => { enter(s.def.id, s.name); };
        if (lines) A.say('arek', lines, go); else go();
        preload(s.def.id);                                                            // start fetching while the lines are read
      },
    })));
    HOOKS.world.push((push, Sx, inView) => {
      for (const s of slabs()) if (inView(s.x, s.y)) push(s.y - 2, () => drawSlab(...Sx(s.x, s.y), A.zoom, s.end.slab.w, s.end.slab.h, s.def));
    });
    HOOKS.update.push(portalCheck);
  }
  function preload(id) { return load(id).catch(e => { console.info('passages.js: preload failed', id, e && e.message); return null; }); }

  const api = window.PASSAGES = {
    list: () => (S.registry ? S.registry.passages.map(p => p.id) : []),
    get: id => S.byId[id] || null,
    gate: g => evalGate(g),
    defineGate: (type, fn) => { gateTypes[type] = fn; },
    defineKind: (kind, impl) => { S.kinds[kind] = impl; },
    preload, enter, leave,
    state: () => ({
      registryLoaded: !!S.registry, error: S.error, passages: Object.keys(S.byId), status: { ...S.status },
      kinds: Object.keys(S.kinds), scripts: Object.keys(S.scripts), data: Object.keys(S.jsons), entering: S.entering,
    }),
  };
  registryReady();
  window.addEventListener('ark-ready', install);
  if (window.ARK) install();
})();
