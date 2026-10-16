/* WOJNA PŁYNÓW (EN: LIQUID WAR) — a minigame on docs/js/board.js (plan: plans/2026-10-15-liquid-wars-board.md).
   Four village substances fight over the village. You only steer a cursor; every fighter of your substance flows towards it
   along the shortest way around the walls. Written from scratch from the public description of the Liquid War idea (no code,
   maps, graphics or sounds of the GPL game are used); the levels come from this game's own OpenStreetMap-based village map
   (gen/build_liquid_maps.py -> docs/data/liquid-maps.json).

   Rules (the contract of the original):
   * 2-4 teams, one cursor each, a fixed army of fighters (one fighter per grid cell, 320x168 cells, 3 board px each).
   * Each team has a distance field ("gradient") over the open cells, flooding outwards from its cursor. The flood is progressive: a
     bounded number of cells per tick (like the original), so a wave needs a few ticks to cross the level and cells it has not reached
     yet keep the previous values. Fighters never run a search of their own, they only read the field.
   * A fighter looks at its 8 neighbours, picks the one with the lowest distance and tries it first, then the neighbours next to that
     direction in a fixed order (side steps may also keep the same distance). Free cell: move. Friend: no move, top up its health, try the
     next direction. Enemy: attack, its health drops; at 0 it turns into the attacker's substance with part of its health.
     Nobody ever disappears, the total number of fighters never changes.
   * A team with no fighters is out. The round ends when one team is left or the timer runs out. Score = % of all fighters at the end.
   Everything about the look is cosmetic (substances differ only in colour and name). Entry point: the VENUE descriptor below. */
'use strict';
(() => {
  /* ------------------------------------------------------------------ tunables */
  const GW = 320, GH = 168, N = GW * GH;
  const CELL = 3, FX = 0, FY = 36;               // a cell is 3 board px (320x3 = 960, 168x3 = 504); the field starts under the 36 px HUD strip
  // render buffer: one pixel per cell, drawn 3x on the 960x540 board with smoothing off
  const CFG = {
    roundSec: 90,        // round length
    armyFrac: .28,       // fighters = this share of the open cells in total ...
    armyMax: 2000,       // ... but at most this many per team (8000 in all: what holds 60 ticks/s, see plans/2026-10-15-liquid-wars-board.md)
    hp: 60, attack: 5, defence: 1, regenEvery: 6, convertHp: 30, topUp: 1,
    moveEvery: 1,        // a fighter acts every tick (60 steps/s = 180 board px/s, the same speed as the old 160x84 grid with 2 ticks per step)
    cursorSpeed: 1.7,    // cells per tick (102 cells/s = 306 board px/s)
    floodTicks: 8,       // a flood wave from a moved cursor needs about this many ticks to cross the level
    floodBudget: 0,      // cells flooded per team and tick; 0 = open cells / floodTicks
    level: null,         // test hook: force a level id
  };
  const COUNT_LEN = 3.4;

  /* ------------------------------------------------------------------ venue (data-driven entry point)
     One descriptor says where the minigame is entered. Today: a flag next to the pig corral, resolved from the CURRENT map.json at
     runtime. Later it can be a building: add a resolver for kind 'building' that returns { x, y } of the door (and opens the interior
     instead of the flag); board.js only needs the point. */
  const VENUE = { kind: 'flag', anchor: { key: 'corral', x: 'cx', y: 'cy' }, offset: { dx: 160, dy: 0 } };
  const VENUE_RESOLVERS = {
    flag(A, v) {
      const a = A.MAP[v.anchor.key]; if (!a || !Number.isFinite(a[v.anchor.x]) || !Number.isFinite(a[v.anchor.y])) return null;
      return { x: Math.round(a[v.anchor.x] + v.offset.dx), y: Math.round(a[v.anchor.y] + v.offset.dy) };
    },
    building() { return null; },   // TODO(later): door of a building / interior hook, needs the building's id in map.json
  };

  /* ------------------------------------------------------------------ substances (cosmetic) */
  const SUBS = [
    { id: 'slurry', pl: 'GNOJÓWKA', en: 'SLURRY', col: [118, 74, 30] },
    { id: 'melior', pl: 'MELIORANKA', en: 'MELIORANKA', col: [48, 190, 214] },
    { id: 'milk', pl: 'MLEKO', en: 'MILK', col: [244, 240, 228] },
    { id: 'orange', pl: 'ORANŻADA', en: 'ORANGEADE', col: [255, 158, 16] },
    { id: 'compote', pl: 'KOMPOT', en: 'COMPOTE', col: [176, 70, 204] },
    { id: 'moonshine', pl: 'BIMBER', en: 'MOONSHINE', col: [232, 224, 120] },
  ];
  const SUB = Object.fromEntries(SUBS.map(s => [s.id, s]));
  const hex = c => `#${c.map(v => v.toString(16).padStart(2, '0')).join('')}`;
  // level names are listed here (not loaded) so the lobby can show them before the bitmaps arrive; the test compares them with the data file
  const LEVELS = [
    { id: 'village', pl: 'CAŁA WIEŚ', en: 'WHOLE VILLAGE' },
    { id: 'street', pl: 'GŁÓWNA ULICA', en: 'MAIN STREET' },
    { id: 'shop', pl: 'OKOLICE SKLEPU', en: 'AROUND THE SHOP' },
    { id: 'church', pl: 'KOŚCIÓŁ I PLEBANIA', en: 'CHURCH AND RECTORY' },
    { id: 'cemetery', pl: 'CMENTARZ', en: 'CEMETERY' },
    { id: 'farmyard', pl: 'PODWÓRKA', en: 'FARMYARDS' },
    { id: 'pond', pl: 'STAW', en: 'THE POND' },
    { id: 'river', pl: 'MELIORANKA', en: 'MELIORANKA RIVER' },
    { id: 'forest', pl: 'SKRAJ LASU', en: 'FOREST EDGE' },
    { id: 'pitch', pl: 'BOISKO I ŚWIETLICA', en: 'PITCH AND COMMUNITY HALL' },
    { id: 'kolonia', pl: 'CHŁOPKÓW-KOLONIA', en: 'CHŁOPKÓW-KOLONIA' },
    { id: 'barn', pl: 'JAZZ W STODOLE', en: 'JAZZ IN THE BARN' },
  ];

  /* ------------------------------------------------------------------ level data (loaded on first use) */
  let DATA = null, status = 'idle', loading = null;
  // rows are run-length encoded by gen/build_liquid_maps.py: per row the alternating run lengths (wall first, base 36), rows joined with ';'
  function decodeRle(s) {
    const rows = s.split(';'), walk = new Uint8Array(N); if (rows.length !== GH) throw new Error('bad level rows');
    for (let y = 0; y < GH; y++) {
      let x = 0, open = 0;
      for (const r of rows[y].split(',')) { const n = parseInt(r, 36); if (!(n >= 0) || x + n > GW) throw new Error('bad level run'); if (open) walk.fill(1, y * GW + x, y * GW + x + n); x += n; open ^= 1; }
      if (x !== GW) throw new Error('bad level row length');
    }
    for (let x = 0; x < GW; x++) if (walk[x] || walk[N - GW + x]) throw new Error('level border must be wall');
    for (let y = 0; y < GH; y++) if (walk[y * GW] || walk[y * GW + GW - 1]) throw new Error('level border must be wall');
    return walk;
  }
  // per cell: bit k set = a fighter may step in direction k (target open, and for a diagonal both side cells open)
  function neighbourMask(walk) {
    const nb = new Uint8Array(N);
    for (let y = 1; y < GH - 1; y++) for (let x = 1; x < GW - 1; x++) {
      const c = y * GW + x; if (!walk[c]) continue; let m = 0;
      for (let k = 0; k < 8; k++) { if (!walk[c + OFF[k]]) continue; if (k & 1 && !(walk[c + SIDEX[k]] && walk[c + SIDEY[k]])) continue; m |= 1 << k; }
      nb[c] = m;
    }
    return nb;
  }
  function load() {
    if (loading) return loading;
    status = 'loading';
    loading = fetch('data/liquid-maps.json').then(r => { if (!r.ok) throw new Error(`liquid-maps.json ${r.status}`); return r.json(); }).then(d => {
      if (!d || !Array.isArray(d.levels) || !d.levels.length || d.grid.w !== GW || d.grid.h !== GH) throw new Error('bad liquid-maps.json');
      for (const l of d.levels) { l.walk = decodeRle(l.rle); l.nb = neighbourMask(l.walk); }
      DATA = d; status = 'ok'; return d;
    }).catch(e => { status = 'error'; loading = null; throw e; });
    return loading;
  }

  /* ------------------------------------------------------------------ simulation */
  const DX = [1, 1, 0, -1, -1, -1, 0, 1], DY = [0, 1, 1, 1, 0, -1, -1, -1];
  const OFF = DX.map((dx, k) => DY[k] * GW + dx);
  const SIDEX = DX.map(dx => dx), SIDEY = DY.map(dy => dy * GW);   // the two orthogonal cells a diagonal step squeezes between
  let seedState = 1;
  const rng = () => { seedState = (seedState * 1664525 + 1013904223) >>> 0; return seedState / 4294967296; };

  function makeSim(level, nTeams, cfg) {
    const walk = level.walk, nb = level.nb;
    let openN = 0; for (let i = 0; i < N; i++) openN += walk[i];
    const per = Math.max(20, Math.min(cfg.armyMax, Math.floor(openN * cfg.armyFrac / nTeams)));
    const total = per * nTeams;
    const fpos = new Int32Array(total), fteam = new Uint8Array(total), fhp = new Int16Array(total);
    const occ = new Int32Array(N);                 // fighter index + 1, 0 = free
    const counts = new Int32Array(nTeams);
    const D = [], SEEN = [], FL = [];
    const budget = cfg.floodBudget || Math.ceil(openN / Math.max(1, cfg.floodTicks));
    for (let t = 0; t < nTeams; t++) { D.push(new Uint16Array(N).fill(65535)); SEEN.push(new Uint32Array(N)); FL.push({ id: 0, head: 0, tail: 0, src: -1, q: new Int32Array(N) }); }
    const cur = [];                                // cursors in cell units
    const dmg = Math.max(1, cfg.attack - cfg.defence);
    // spawn: team t takes the `per` open cells nearest (by walking) to its start area
    const taken = new Uint8Array(N), qs = new Int32Array(N); let f = 0;
    for (let t = 0; t < nTeams; t++) {
      const [ax, ay] = level.anchors[t]; const a = ay * GW + ax; cur.push({ x: ax + .5, y: ay + .5 });
      let h = 0, tl = 0; const mark = new Uint8Array(N); qs[tl++] = a; mark[a] = 1; let got = 0;
      while (h < tl && got < per) {
        const c = qs[h++];
        if (!taken[c]) { taken[c] = 1; fpos[f] = c; fteam[f] = t; fhp[f] = cfg.hp; occ[c] = f + 1; f++; got++; }
        const m = nb[c];
        for (let k = 0; k < 8; k++) {
          if (!(m & (1 << k))) continue; const n = c + OFF[k]; if (mark[n]) continue;
          mark[n] = 1; qs[tl++] = n;
        }
      }
      if (got < per) throw new Error(`level ${level.id}: no room for team ${t} (${got}/${per})`);
      counts[t] = per;
    }
    const sim = { level, walk, nTeams, per, total, fpos, fteam, fhp, occ, counts, D, cur, tick: 0, conv: [], convCount: 0, convTick: 0, openN, cfg, floodSum: 0, out: new Array(nTeams).fill(false), outAt: new Array(nTeams).fill(-1) };

    function flood(t, n) {   // progressive wavefront from the team's cursor cell
      const fl = FL[t], d = D[t], seen = SEEN[t], q = fl.q;
      if (fl.head >= fl.tail) {
        const c = (cur[t].y | 0) * GW + (cur[t].x | 0);
        if (c === fl.src) return;
        fl.id++; fl.src = c; q[0] = c; fl.head = 0; fl.tail = 1; d[c] = 0; seen[c] = fl.id;
      }
      let k0 = 0, head = fl.head, tail = fl.tail; const id = fl.id;
      while (head < tail && k0 < n) {
        const c = q[head++], dc = d[c] + 1, m = nb[c]; k0++;
        for (let k = 0; k < 8; k++) {
          if (!(m & (1 << k))) continue; const x = c + OFF[k]; if (seen[x] === id) continue;
          seen[x] = id; d[x] = dc; q[tail++] = x;
        }
      }
      fl.head = head; fl.tail = tail;
    }
    sim.floodAll = () => { for (let t = 0; t < nTeams; t++) if (!sim.out[t]) { FL[t].head = FL[t].tail; flood(t, N); } };
    sim.floodAll();

    const P = 7919 % total;   // a prime step (the army is smaller than 7919): a fixed scramble of the visiting order, re-offset every tick
    sim.step = () => {
      const tick = ++sim.tick, me = cfg.moveEvery, regen = cfg.regenEvery, hpMax = cfg.hp;
      const f0 = performance.now();
      for (let t = 0; t < nTeams; t++) if (!sim.out[t]) flood(t, budget);
      sim.floodSum += performance.now() - f0; sim.convTick = 0;
      if (regen) for (let q = (regen - (tick % regen)) % regen; q < total; q += regen) if (fhp[q] < hpMax) fhp[q]++;   // every `regen` ticks each fighter heals 1
      let i = (((tick * 2654435761) >>> 0) % total);
      for (let j = 0; j < total; j++, i += P) {
        if (i >= total) i -= total;
        if (me > 1 && (i + tick) % me !== 0) continue;
        const c = fpos[i], t = fteam[i], d = D[t], dc = d[c], r = (tick + i) & 7, m = nb[c];
        let bk = -1, bd = 65535;
        for (let jj = 0; jj < 8; jj++) {
          const k = (jj + r) & 7; if (!(m & (1 << k))) continue;
          const nd = d[c + OFF[k]]; if (nd < bd) { bd = nd; bk = k; }
        }
        if (bk < 0) continue;
        // priority list: the best direction, then its two neighbours (alternating which side first), then the two beyond
        const s = (r & 1) ? 1 : -1;
        for (let p = 0; p < 5; p++) {
          const k = (bk + (p === 0 ? 0 : p === 1 ? s : p === 2 ? -s : p === 3 ? 2 * s : -2 * s) + 8) & 7;
          if (!(m & (1 << k))) continue;
          const n = c + OFF[k], nd = d[n]; if (p === 0 ? nd >= dc : nd > dc) continue;
          const o = occ[n];
          if (o === 0) { occ[c] = 0; occ[n] = i + 1; fpos[i] = n; break; }
          const e = o - 1;
          if (fteam[e] === t) { if (fhp[e] + 2 < fhp[i] && fhp[i] > 2) { fhp[e] += cfg.topUp; fhp[i] -= cfg.topUp; } continue; }
          fhp[e] -= dmg;
          if (fhp[e] <= 0) {   // converted: same cell, same fighter, new substance
            const old = fteam[e]; fteam[e] = t; fhp[e] = cfg.convertHp; counts[old]--; counts[t]++;
            sim.convTick++; sim.convCount++; if (sim.conv.length < 64) sim.conv.push(n, t);
            if (counts[old] === 0) { sim.out[old] = true; sim.outAt[old] = tick; }
          }
          break;
        }
      }
    };
    sim.alive = () => { let a = 0; for (let t = 0; t < nTeams; t++) if (counts[t] > 0) a++; return a; };
    sim.cursorCell = t => (cur[t].y | 0) * GW + (cur[t].x | 0);
    sim.open = (x, y) => x >= 0 && y >= 0 && x < GW && y < GH && walk[(y | 0) * GW + (x | 0)] === 1;
    sim.moveCursor = (t, dx, dy, sp) => {   // cursors never enter walls; they slide along them
      const l = Math.hypot(dx, dy); if (!l || sim.out[t]) return;
      const c = cur[t], nx = c.x + dx / l * sp, ny = c.y + dy / l * sp;
      if (sim.open(nx, ny)) { c.x = nx; c.y = ny; } else if (sim.open(nx, c.y)) c.x = nx; else if (sim.open(c.x, ny)) c.y = ny;
    };
    sim.bfs = (src, out) => {   // plain full distance field (computer cursors steer by it)
      out.fill(65535); const q = qs; let h = 0, tl = 0; q[tl++] = src; out[src] = 0;
      while (h < tl) {
        const c = q[h++], dc = out[c] + 1, m = nb[c];
        for (let k = 0; k < 8; k++) {
          if (!(m & (1 << k))) continue; const n = c + OFF[k]; if (out[n] !== 65535) continue;
          out[n] = dc; q[tl++] = n;
        }
      }
    };
    return sim;
  }

  /* ------------------------------------------------------------------ the board game */
  function create(api) {
    const { A, PL, W, H, players, drawSprite } = api;
    const cfg = { ...CFG, ...(window.__liquid && window.__liquid.tune) };
    const lv = DATA.levels;
    const want = cfg.level || (api.opts && api.opts.level) || 'village';
    const level = want === 'random' ? lv[(Math.random() * lv.length) | 0] : (lv.find(l => l.id === want) || lv[0]);
    seedState = (Date.now() ^ (Math.random() * 4294967296)) >>> 0;
    const sim = makeSim(level, players.length, cfg);
    const TX = PL ? { go: 'CHLUP!', time: 'KONIEC CZASU', last: 'OSTATNI NA POLU', out: 'WYPADŁ', score: 'udział', won: 'zostali sami', timeout: 'czas', level: 'POZIOM', eliminated: 'wyeliminowany' }
      : { go: 'SPLASH!', time: 'TIME UP', last: 'LAST ONE STANDING', out: 'OUT', score: 'share', won: 'last one left', timeout: 'time', level: 'LEVEL', eliminated: 'eliminated' };
    const lname = (level.name && level.name[PL ? 'pl' : 'en']) || level.id;
    const teams = players.map((p, i) => {
      const sub = SUB[(api.subs && api.subs[i]) || p.sub] || SUBS[i];
      const t = { i, p, sub, name: PL ? sub.pl : sub.en, col: sub.col, hex: hex(sub.col), ptr: null, cpu: null };
      if (p.cpu) {
        const skill = Math.max(.3, Math.min(1, .35 + .65 * ((p.cpuScore || 25) / 50)));   // PRZECIĘTNIAK: strength follows the average past share
        t.cpu = { skill, every: Math.round(24 + (1 - skill) * 90), next: 6 + i * 7, field: new Uint16Array(N), has: false, target: -1 };
      }
      return t;
    });
    let time = 0, over = false, why = '', lastChlup = -1, started = false;
    const parts = [];   // splash particles (board px)
    const perfT = [], perfD = [];

    /* ---- colours */
    const pack = (r, g, b) => (255 << 24) | (b << 16) | (g << 8) | r;
    const clampc = v => Math.max(0, Math.min(255, v | 0));
    // fighter colour per health level (8 steps, dim = hurt); a fighter is one pixel of the GW x GH buffer, drawn 3x
    const PAL = teams.map(t => { const lv8 = new Uint32Array(8); for (let l = 0; l < 8; l++) { const sh = .45 + .55 * (l / 7), c = t.col; lv8[l] = pack(clampc(c[0] * sh * 1.12 + 8), clampc(c[1] * sh * 1.12 + 8), clampc(c[2] * sh * 1.12 + 8)); } return lv8; });
    const HPL = new Uint8Array(cfg.hp + 1); for (let h = 0; h <= cfg.hp; h++) HPL[h] = Math.min(7, Math.max(0, (h * 7 / cfg.hp + .5) | 0));
    const off = document.createElement('canvas'); off.width = GW; off.height = GH;
    const octx = off.getContext('2d'), img = octx.createImageData(GW, GH), u32 = new Uint32Array(img.data.buffer);
    const base = new Uint32Array(N);
    (() => {   // static layer: dark floor with a little grain, walls with lit tops and shaded feet
      const w = level.walk, hash = (x, y) => { let h = (x * 374761393 + y * 668265263) >>> 0; h = ((h ^ (h >>> 13)) * 1274126177) >>> 0; return (h ^ (h >>> 16)) & 255; };
      for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
        const c = y * GW + x, open = w[c] === 1, g = hash(x, y) / 255 - .5; let col;
        if (open) col = [30 + g * 7, 46 + g * 8, 38 + g * 7];
        else {
          const up = y > 0 && w[c - GW], dn = y < GH - 1 && w[c + GW], k = up ? 1.35 : dn ? .62 : .92 + g * .18;
          col = [92 * k, 104 * k, 128 * k];
        }
        base[c] = pack(clampc(col[0]), clampc(col[1]), clampc(col[2]));
      }
    })();

    /* ---- input */
    function update(dt, ev, phase) {
      if (phase === 'run') {
        time += dt;
        for (const t of teams) {
          if (sim.out[t.i]) continue;
          if (t.cpu) cpuDrive(t);
          else {
            let dx = (api.down(t.p, 'right') ? 1 : 0) - (api.down(t.p, 'left') ? 1 : 0), dy = (api.down(t.p, 'down') ? 1 : 0) - (api.down(t.p, 'up') ? 1 : 0);
            if (!dx && !dy && t.ptr && t.ptr.active) { const c = sim.cur[t.i]; dx = t.ptr.x - c.x; dy = t.ptr.y - c.y; if (Math.hypot(dx, dy) < .8) dx = dy = 0; }
            if (dx || dy) sim.moveCursor(t.i, dx, dy, cfg.cursorSpeed);
          }
        }
        const s0 = performance.now(); sim.step(); perfT.push(performance.now() - s0); if (perfT.length > 600) perfT.shift();
        splash();
        if (!over) {
          if (sim.alive() <= 1) { over = true; why = 'last'; } else if (time >= cfg.roundSec) { over = true; why = 'time'; }
          if (over) api.sfx('finish');
        }
      }
      let w = 0; for (const p of parts) { p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 150 * dt; p.t -= dt; if (p.t > 0) parts[w++] = p; } parts.length = w;
    }
    function splash() {
      const cv = sim.conv; let n = 0;
      for (let i = 0; i < cv.length && n < 6; i += 2, n++) {
        const c = cv[i], x = c % GW, y = (c / GW) | 0, col = teams[cv[i + 1]].col;
        if (parts.length < 320) parts.push({ x: x * CELL + 1, y: FY + y * CELL + 1, vx: (Math.random() - .5) * 70, vy: -30 - Math.random() * 60, t: .45 + Math.random() * .25, col });
      }
      sim.conv.length = 0;
      if (sim.convTick > 0 && time - lastChlup > .14) { lastChlup = time; api.sfx('chlup'); }
    }

    /* ---- computer cursors */
    function cpuDrive(t) {
      const k = t.cpu, c = sim.cur[t.i], me = t.i;
      if (sim.tick >= k.next) {
        k.next = sim.tick + k.every; let best = -1e9, bf = -1;
        const tries = 20 + ((60 * k.skill) | 0), cc = sim.cursorCell(me), cx = cc % GW, cy = (cc / GW) | 0;
        for (let q = 0; q < tries; q++) {
          const f = (rng() * sim.total) | 0; if (sim.fteam[f] === me) continue;
          const pos = sim.fpos[f], x = pos % GW, y = (pos / GW) | 0; if (x < 4 || y < 4 || x > GW - 5 || y > GH - 5) continue;
          let fr = 0, en = 0;
          for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) { const o = sim.occ[pos + dy * GW + dx]; if (o) { if (sim.fteam[o - 1] === me) fr++; else en++; } }
          const sc = (fr * 1.2 - en * .5) * .5 + (1 - sim.fhp[f] / cfg.hp) * 3 - Math.hypot(x - cx, y - cy) * .015 + (rng() - .5) * (1 - k.skill) * 8;
          if (sc > best) { best = sc; bf = f; }
        }
        if (bf >= 0) { k.target = sim.fpos[bf]; sim.bfs(k.target, k.field); k.has = true; }
      }
      if (!k.has) return;
      const cc = sim.cursorCell(me), cd = k.field[cc]; if (cd === 0) return;
      let bk = -1, bd = cd;
      for (let q = 0; q < 8; q++) { const n = cc + OFF[q]; if (!sim.walk[n]) continue; if (q & 1 && !(sim.walk[cc + SIDEX[q]] && sim.walk[cc + SIDEY[q]])) continue; if (k.field[n] < bd) { bd = k.field[n]; bk = q; } }
      if (bk < 0) return;
      const tx = (cc % GW) + DX[bk] + .5, ty = ((cc / GW) | 0) + DY[bk] + .5;
      sim.moveCursor(me, tx - c.x, ty - c.y, cfg.cursorSpeed * (.7 + .3 * k.skill));
    }

    /* ---- drawing */
    function head(c, t, x, y, r) {   // the slot's character as the cursor badge
      c.save(); c.beginPath(); c.arc(x, y, r, 0, 7); c.clip();
      c.fillStyle = hex(t.col); c.fillRect(x - r, y - r, r * 2, r * 2);
      const a = api.atlas(t.p.atlas), fr = a && a.meta && a.meta.frames && a.meta.frames.stand;
      if (a && a.img && fr) { const sh = fr.h * .4, s = (r * 2.1) / Math.max(fr.w * .8, sh); c.imageSmoothingEnabled = true; c.drawImage(a.img, fr.x + fr.w * .1, fr.y + fr.h * .04, fr.w * .8, sh, x - fr.w * .8 * s / 2, y - sh * s / 2, fr.w * .8 * s, sh * s); }
      c.restore();
    }
    function drawCursor(c, t) {
      if (sim.out[t.i]) return;
      const cu = sim.cur[t.i], x = FX + cu.x * CELL, y = FY + cu.y * CELL, r = 12, pulse = 1 + Math.sin(performance.now() / 160 + t.i) * .08;
      c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.ellipse(x, y + r * .9, r * .9, r * .35, 0, 0, 7); c.fill();
      head(c, t, x, y, r - 2);
      c.lineWidth = 3; c.strokeStyle = '#10141f'; c.beginPath(); c.arc(x, y, (r + 1) * pulse, 0, 7); c.stroke();
      c.lineWidth = 2; c.strokeStyle = hex(t.col); c.beginPath(); c.arc(x, y, (r + 1) * pulse, 0, 7); c.stroke();
      c.font = '10px PixelifySans'; c.textAlign = 'center'; c.fillStyle = '#10141f'; c.fillText(t.p.tag, x + 1, y - r - 5); c.fillStyle = '#fff'; c.fillText(t.p.tag, x, y - r - 6); c.textAlign = 'left';
    }
    function drawHud(c, phase, t) {
      const n = teams.length, gap = 6, pw = Math.min(232, (W - 20 - gap * (n - 1)) / n);
      c.fillStyle = '#080c18'; c.fillRect(0, 0, W, FY);
      teams.forEach((tm, i) => {
        const x = 10 + i * (pw + gap), y = 3, cnt = sim.counts[i], pct = cnt / sim.total * 100, dead = sim.out[i];
        c.globalAlpha = dead ? .45 : 1;
        c.fillStyle = '#162036'; c.fillRect(x, y, pw, 31); c.fillStyle = tm.hex; c.fillRect(x, y, 4, 31);
        c.font = '12px PixelifySans'; c.textAlign = 'left'; c.fillStyle = tm.hex; c.fillText(tm.name, x + 9, y + 12);
        c.textAlign = 'right'; c.fillStyle = '#c8cee0'; c.font = '10px PixelifySans'; c.fillText(tm.p.tag, x + pw - 6, y + 11);
        c.textAlign = 'left'; c.font = '11px PixelifySans'; c.fillStyle = '#f5f0e0';
        c.fillText(dead ? TX.eliminated : `${cnt}  ·  ${pct.toFixed(1)}%`, x + 9, y + 24);
        c.fillStyle = '#0a1120'; c.fillRect(x + 100, y + 18, pw - 108, 6); c.fillStyle = tm.hex; c.fillRect(x + 100, y + 18, (pw - 108) * pct / 100, 6);
        c.globalAlpha = 1;
      });
      const left = Math.max(0, cfg.roundSec - time);
      const mm = Math.floor(Math.ceil(left) / 60), ss = Math.ceil(left) % 60, tt = `${mm}:${String(ss).padStart(2, '0')}`;
      c.fillStyle = 'rgba(8,12,40,.78)'; c.fillRect(W / 2 - 38, FY + 4, 76, 22); c.font = '16px PixelifySans'; c.textAlign = 'center'; c.fillStyle = left < 10 && phase === 'run' ? '#ff6b5e' : '#fff'; c.fillText(tt, W / 2, FY + 21);
      c.font = '10px PixelifySans'; c.fillStyle = 'rgba(255,255,255,.75)'; c.fillText(lname, W / 2, FY + 38);
      if (phase === 'count') {
        const k = Math.max(1, Math.ceil(COUNT_LEN - t - .4));
        c.font = '64px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(t < COUNT_LEN - .4 ? String(Math.min(3, k)) : TX.go, W / 2 + 3, H * .5 + 3); c.fillStyle = '#ffd21f'; c.fillText(t < COUNT_LEN - .4 ? String(Math.min(3, k)) : TX.go, W / 2, H * .5);
        c.font = '12px PixelifySans'; c.fillStyle = '#fff';
        const hum = players.filter(p => !p.cpu).map(p => `${p.tag}: ${p.ctrl === 'touch' ? (PL ? 'przeciągnij' : 'drag') : api.keyLabel(p, 'left') + ' ' + api.keyLabel(p, 'right') + ' ' + api.keyLabel(p, 'up') + ' ' + api.keyLabel(p, 'down')}`).join('     ');
        c.fillText(hum, W / 2, H - 22);
      } else if (phase === 'run' && t < .7) { c.font = '64px PixelifySans'; c.fillStyle = `rgba(124,255,107,${1 - t / .7})`; c.fillText(TX.go, W / 2, H * .5); }
      if (over && phase !== 'count') { c.font = '34px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(why === 'last' ? TX.last : TX.time, W / 2 + 2, H * .5 + 2); c.fillStyle = '#ffd21f'; c.fillText(why === 'last' ? TX.last : TX.time, W / 2, H * .5); }
      c.textAlign = 'left';
    }
    function draw(c, phase, t) {
      const d0 = performance.now();
      u32.set(base);
      const fp = sim.fpos, ft = sim.fteam, fh = sim.fhp, total = sim.total;
      for (let i = 0; i < total; i++) u32[fp[i]] = PAL[ft[i]][HPL[fh[i]]];
      octx.putImageData(img, 0, 0);
      c.fillStyle = '#05070d'; c.fillRect(0, 0, W, H);
      c.imageSmoothingEnabled = false; c.drawImage(off, FX, FY, GW * CELL, GH * CELL);
      for (const p of parts) { c.globalAlpha = Math.max(0, Math.min(1, p.t * 2.2)); c.fillStyle = hex(p.col); c.fillRect(Math.round(p.x) - 1, Math.round(p.y) - 1, 3, 3); }
      c.globalAlpha = 1;
      for (const tm of teams) drawCursor(c, tm);
      drawHud(c, phase, t);
      perfD.push(performance.now() - d0); if (perfD.length > 600) perfD.shift();
    }

    /* ---- framework contract */
    function go() { time = 0; started = true; api.sfx('gun'); }
    const finished = () => over;
    function results() {
      return teams.map(t => ({ slot: t.p.slot, score: Math.round(sim.counts[t.i] / sim.total * 1000) / 10,
        note: `${t.name}${sim.out[t.i] ? ' · ' + TX.out : ''}`, col: t.hex, proof: { fighters: sim.counts[t.i], total: sim.total, level: level.id } }));
    }
    function pointer(kind, x, y, p) {
      const t = teams.find(q => q.p === p); if (!t) return;
      const gx = (x - FX) / CELL, gy = (y - FY) / CELL;
      if (kind === 'up') { if (t.ptr) t.ptr.active = false; } else t.ptr = { active: true, x: Math.max(1, Math.min(GW - 2, gx)), y: Math.max(1, Math.min(GH - 2, gy)) };
    }
    const q = a => { const s = Array.from(a).sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(s.length * .95))] : 0; };
    const avg = a => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0);
    function audit() {   // invariants for the tests
      let occN = 0, bad = 0; const seen = new Set();
      for (let c = 0; c < N; c++) if (sim.occ[c]) { occN++; const f = sim.occ[c] - 1; if (sim.fpos[f] !== c || !sim.walk[c] || seen.has(f)) bad++; seen.add(f); }
      const byTeam = new Array(sim.nTeams).fill(0); for (let i = 0; i < sim.total; i++) byTeam[sim.fteam[i]]++;
      return { total: sim.total, countsSum: sim.counts.reduce((s, v) => s + v, 0), occupied: occN, bad, byTeamMatches: byTeam.every((v, i) => v === sim.counts[i]), hpOk: Array.from(sim.fhp).every(h => h > 0 && h <= cfg.hp) };
    }
    function debug() {
      return { level: level.id, levelName: lname, grid: [GW, GH], cell: CELL, started, over, why, time, tick: sim.tick, total: sim.total, per: sim.per, conv: sim.convCount, open: sim.openN,
        teams: teams.map(t => ({ slot: t.p.slot, i: t.i, sub: t.sub.id, name: t.name, cpu: !!t.p.cpu, count: sim.counts[t.i], out: sim.out[t.i], outAt: sim.outAt[t.i], x: sim.cur[t.i].x, y: sim.cur[t.i].y, skill: t.cpu ? t.cpu.skill : null })),
        perf: { floodAvg: sim.floodSum / Math.max(1, sim.tick), tickAvg: avg(perfT), tickP95: q(perfT), tickMax: Math.max(0, ...perfT), drawAvg: avg(perfD), drawP95: q(perfD), drawMax: Math.max(0, ...perfD), n: perfT.length } };
    }
    window.__liquid.sim = sim; window.__liquid.audit = audit; window.__liquid.game = { teams, level };
    return { countLen: COUNT_LEN, update, go, finished, results, draw, debug, pointer };
  }

  /* ------------------------------------------------------------------ registration */
  const lobbyLevels = PL => [...LEVELS.map(l => [l.id, PL ? l.pl : l.en]), ['random', PL ? 'LOSOWY' : 'RANDOM']];
  // lobby thumbnail of the chosen level (board.js calls it after a level change): walls, open ground and the four start areas
  function preview(cv, opts) {
    const g = cv.getContext('2d'), w = cv.width, h = cv.height; g.clearRect(0, 0, w, h);
    const l = DATA && DATA.levels.find(x => x.id === (opts && opts.level));
    g.fillStyle = '#0b1220'; g.fillRect(0, 0, w, h);
    if (!l) {
      g.fillStyle = '#9aa0c0'; g.font = `${Math.round(h * .4)}px PixelifySans, monospace`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(opts && opts.level === 'random' ? '?' : '…', w / 2, h / 2); return false;
    }
    const im = g.createImageData(w, h), px = new Uint32Array(im.data.buffer), sx = GW / w, sy = GH / h;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) px[y * w + x] = l.walk[((y * sy) | 0) * GW + ((x * sx) | 0)] ? 0xff262e1e : 0xff80684c;
    g.putImageData(im, 0, 0);
    l.anchors.forEach(([ax, ay], i) => { g.fillStyle = hex(SUBS[i].col); g.beginPath(); g.arc(ax / sx, ay / sy, Math.max(3, h / 22), 0, 7); g.fill(); g.strokeStyle = '#000'; g.lineWidth = 1; g.stroke(); });
    return true;
  }
  window.__liquid = window.__liquid || { tune: {} };
  Object.assign(window.__liquid, { CFG, SUBS, LEVELS, VENUE, GW, GH, load, preview, venue: A => (VENUE_RESOLVERS[VENUE.kind] || (() => null))(A, VENUE) });
  Object.defineProperties(window.__liquid, { data: { get: () => DATA, configurable: true }, status: { get: () => status, configurable: true } });
  window.ARK_BOARD_REGISTER({
    id: 'liquid', host: null, global: false, records: false,   // records: false = no medals, best, top 10, history or global board (board.js)
    title: PL => (PL ? 'WOJNA PŁYNÓW' : 'LIQUID WAR'),
    sub: PL => (PL
      ? 'Minigra: ruszasz tylko kursorem. Cała twoja substancja płynie do niego, wokół ścian. Kto wpadnie na cudzą, zbija jej zdrowie i przejmuje ją. Nikt nie znika, wygrywa ostatni na polu albo ten, kto ma najwięcej po upływie czasu.'
      : 'Minigame: you only steer a cursor. All of your substance flows to it, around the walls. Whoever runs into a foreign one wears its health down and takes it over. Nobody vanishes: last one standing wins, or the biggest when time is up.'),
    logName: PL => (PL ? 'Wojna płynów' : 'Liquid war'),
    get flagLabel() { const A = window.ARK; return A && A.LANG === 'pl' ? 'WOJNA PŁYNÓW' : 'LIQUID WAR'; },
    flagColors: ['#2fb8c9', '#f4f0e4'],
    actions: ['left', 'right', 'up', 'down'],
    keys: {
      kb1: { left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', down: 'ArrowDown' },
      kb2: { left: 'KeyA', right: 'KeyD', up: 'KeyW', down: 'KeyS' },
      kb3: { left: 'KeyJ', right: 'KeyL', up: 'KeyI', down: 'KeyK' },
      kb4: { left: 'Numpad4', right: 'Numpad6', up: 'Numpad8', down: 'Numpad5' },
    },
    pointer: true,
    slotOption: { key: 'sub', label: PL => (PL ? 'substancja' : 'substance'), values: PL => SUBS.map(s => [s.id, PL ? s.pl : s.en]), defaults: ['slurry', 'melior', 'milk', 'orange'] },
    options: [{ key: 'level', label: PL => (PL ? 'poziom' : 'level'), values: lobbyLevels, default: 'village' }],
    cpuNote: PL => (PL ? 'KOMPUTER sam steruje swoim kursorem. Liczy się tylko ta runda.' : 'COMPUTER steers its own cursor. Only this round counts.'),
    preview,
    score: { unit: 'percent', lower: false, medals: [], cpuDefault: 25, traceLen: 0, format: v => `${v.toFixed(1)}%` },
    load, status: () => status,
    venue: A => window.__liquid.venue(A),
    create(api) { api.subs = api.players.map(p => p.sub); return create(api); },
  });
})();
