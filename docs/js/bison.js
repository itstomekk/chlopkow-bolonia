/* Żubr (European bison): a rare, dignified wanderer of the forests.
   Standalone hook plugin (same pattern as sokol-watermark.js): no changes to world-life animals,
   their seeded counts or their saves.

   - Never before 5 minutes of play in the current session; after that a visit starts only by chance
     (checked every 2 minutes), so some sessions never see him.
   - Lives in the forest regions (terrainAt === 'forest'), grazes, and sometimes walks across the
     fields to another forest. Not on the minimap: you have to find him.
   - Keeps his distance: when Arek comes close he stops, looks, then slowly walks away. Cannot be touched.
   - Spotting him (close and on screen) once per visit shows a toast and counts Q.bisonSeen.
   Debug/tests: window.__bison; ?bison=1 starts a visit right away. */
'use strict';
(() => {
  const FIRST_AFTER = 300, CHECK_EVERY = 120, CHANCE = 0.4;     // seconds of play, chance per check
  const VISIT_MIN = 180, VISIT_MAX = 300;                       // a visit lasts 3-5 minutes
  const SPEED = 11, AWAY_SPEED = 20, SHY = 110, SPOT = 150;     // map px/s, map px
  const MIGRATE = 0.3;                                          // chance a new walk goes to another forest
  const GRID = 24, MIN_REGION = 40;                             // forest sampling step, cells per region
  const CELL_W = 96, CELL_H = 80, FOOT = 77, K = 21 / 44 * 1.3; // art -> map px; 1.3x the critter density so he stands as tall as Arek
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__bisonInstalled) return;
    A.__bisonInstalled = true;
    const { HOOKS, MAP, P, ctx } = A;
    const PL = A.LANG === 'pl';
    let img = null;
    A.load('img/bison.png').then(i => { img = i; }, () => {});

    /* forest regions: 4-connected components of forest cells on a GRID-px lattice */
    const gw = Math.ceil(MAP.w / GRID), gh = Math.ceil(MAP.h / GRID);
    const label = new Int32Array(gw * gh).fill(-1), regions = [];
    const isForest = (gx, gy) => A.terrainAt(gx * GRID + GRID / 2, gy * GRID + GRID / 2) === 'forest';
    for (let i = 0; i < gw * gh; i++) {
      if (label[i] !== -1) continue;
      const gx = i % gw, gy = (i / gw) | 0;
      if (!isForest(gx, gy)) { label[i] = -2; continue; }
      const cells = [], stack = [i]; label[i] = regions.length;
      while (stack.length) {
        const c = stack.pop(), cx = c % gw, cy = (c / gw) | 0; cells.push(c);
        for (const [nx, ny] of [[cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]]) {
          if (nx < 0 || ny < 0 || nx >= gw || ny >= gh) continue;
          const n = ny * gw + nx;
          if (label[n] !== -1) continue;
          if (isForest(nx, ny)) { label[n] = regions.length; stack.push(n); } else label[n] = -2;
        }
      }
      regions.push(cells);
    }
    const forests = regions.filter(r => r.length >= MIN_REGION);
    const cellPoint = c => ({ x: (c % gw) * GRID + Math.random() * GRID, y: ((c / gw) | 0) * GRID + Math.random() * GRID });
    const randomIn = (r, ok = () => true) => {
      for (let k = 0; k < 40; k++) { const p = cellPoint(r[(Math.random() * r.length) | 0]); if (!A.blocked(p.x, p.y) && ok(p)) return p; }
      return null;
    };
    const regionAt = (x, y) => {
      const gx = Math.floor(x / GRID), gy = Math.floor(y / GRID);
      const l = gx >= 0 && gy >= 0 && gx < gw && gy < gh ? label[gy * gw + gx] : -2;
      return l >= 0 ? forests.indexOf(regions[l]) : -1;
    };

    let played = 0, nextCheck = FIRST_AFTER, b = null;
    const dist = (x, y) => Math.hypot(P.x - x, P.y - y);

    function startVisit(force) {
      if (!forests.length) return false;
      const far = p => force || dist(p.x, p.y) > 600;
      for (let k = 0; k < 30; k++) {
        const r = forests[(Math.random() * forests.length) | 0], p = randomIn(r, far);
        if (!p) continue;
        b = { x: p.x, y: p.y, home: forests.indexOf(r), tx: p.x, ty: p.y, dir: 'right', step: 0, idle: 4, graze: 0,
              moving: false, left: VISIT_MIN + Math.random() * (VISIT_MAX - VISIT_MIN), leaving: false, alpha: 0, seen: false, stuck: 0, migrating: false };
        return true;
      }
      return false;
    }
    function pickTarget() {
      let r = b.home;
      b.migrating = forests.length > 1 && Math.random() < MIGRATE;
      if (b.migrating) { do r = (Math.random() * forests.length) | 0; while (r === b.home); }
      const p = randomIn(forests[r]);
      if (!p) { b.migrating = false; return; }
      b.tx = p.x; b.ty = p.y; b.target = r;
    }
    function step(dx, dy, speed, dt) {
      const d = Math.hypot(dx, dy) || 1;
      for (const turn of [0, .6, -.6, 1.2, -1.2]) {
        const c = Math.cos(turn), s = Math.sin(turn), ux = (dx * c - dy * s) / d, uy = (dx * s + dy * c) / d;
        const nx = b.x + ux * speed * dt, ny = b.y + uy * speed * dt;
        if (nx > 0 && ny > 0 && nx < MAP.w && ny < MAP.h && !A.blocked(nx, ny)) {
          b.x = nx; b.y = ny; if (Math.abs(ux) > .2) b.dir = ux > 0 ? 'right' : 'left';
          b.step += speed * dt / 14; b.moving = true; return true;
        }
      }
      return false;
    }

    HOOKS.update.push(dt => {
      if (A.room) return;
      played += dt;
      if (!b && played >= nextCheck) { nextCheck = played + CHECK_EVERY; if (Math.random() < CHANCE) startVisit(false); }
      if (!b) return;
      b.moving = false;
      b.left -= dt;
      b.alpha = Math.min(1, b.alpha + dt / 2);
      const d = dist(b.x, b.y);
      if (!b.leaving && b.left <= 0) { b.leaving = true; const p = randomIn(forests[b.home], q => dist(q.x, q.y) > 700); if (p) { b.tx = p.x; b.ty = p.y; } }
      if (b.leaving && (d > 900 || b.left < -60)) { b.alpha -= dt; if (b.alpha <= 0) { b = null; return; } }
      if (!b.seen && d < SPOT && b.alpha > .5 && A.scene === 'play') {
        b.seen = true;
        const Q = A.Q; Q.bisonSeen = (Q.bisonSeen | 0) + 1; A.save();
        A.popToast(PL ? `ŻUBR! Król puszczy przechodzi obok (${Q.bisonSeen}×)` : `A BISON! The king of the forest walks by (${Q.bisonSeen}×)`);
      }
      if (d < SHY) {                                    // dignified retreat, never a run
        if (b.shyT === undefined) b.shyT = 1.2;         // first: stop and look
        b.shyT -= dt;
        if (b.shyT > 0) { b.dir = P.x > b.x ? 'right' : 'left'; return; }
        step(b.x - P.x, b.y - P.y, AWAY_SPEED, dt);
        b.tx = b.x; b.ty = b.y; b.idle = 2;
        return;
      }
      b.shyT = undefined;
      if (b.idle > 0) { b.idle -= dt; b.graze += dt; return; }
      const dx = b.tx - b.x, dy = b.ty - b.y;
      if (Math.hypot(dx, dy) < 8) {
        if (b.migrating) b.home = b.target;
        b.migrating = false; b.idle = 4 + Math.random() * 8; b.graze = 0;
        if (!b.leaving) pickTarget();
        return;
      }
      if (step(dx, dy, SPEED, dt)) b.stuck = 0;
      else if ((b.stuck += dt) > 2) { b.stuck = 0; b.migrating = false; const p = randomIn(forests[b.home]); if (p) { b.tx = p.x; b.ty = p.y; } }
    });

    HOOKS.world.push((push, S, inView) => {
      if (!b || !img || !inView(b.x, b.y)) return;
      push(b.y, () => {
        const z = A.zoom, [sx, sy] = S(b.x, b.y);
        const f = b.moving ? Math.floor(b.step) % 2 : (Math.floor(b.graze / 3) % 2 ? 3 : 2);
        const w = CELL_W * K * z, h = CELL_H * K * z;
        ctx.save();
        ctx.globalAlpha = Math.max(0, Math.min(1, b.alpha));
        A.shadow(sx, sy, z * 2.2, 10);
        ctx.imageSmoothingEnabled = false;
        ctx.translate(sx, sy);
        if (b.dir === 'left') ctx.scale(-1, 1);
        ctx.drawImage(img, f * CELL_W, 0, CELL_W, CELL_H, -w / 2, -FOOT * K * z, w, h);
        ctx.restore();
      });
    });

    window.__bison = {
      get state() { return b ? { x: b.x, y: b.y, moving: b.moving, migrating: b.migrating, home: b.home, leaving: b.leaving, seen: b.seen, region: regionAt(b.x, b.y) } : null; },
      get played() { return played; }, get nextCheck() { return nextCheck; },
      forests: forests.map(r => r.length), regionAt, start: () => startVisit(true), stop: () => { b = null; },
      constants: { FIRST_AFTER, CHECK_EVERY, CHANCE, SHY, SPOT },
    };
    if (/[?&]bison=1\b/.test(location.search)) startVisit(true);
  };
  window.addEventListener('ark-ready', READY);
  if (window.ARK) READY();
})();
