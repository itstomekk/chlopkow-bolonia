/* World life for "Arek w Chłopkowie".
   Standalone hook plugin: harmless pecking chickens, scruffy wandering dogs and
   two procedurally drawn red vintage hatchbacks. Loaded before game.js. */
'use strict';
(() => {
  const COST = 10, RIDE_SECONDS = 15, RIDE_SPEED = 2.35;
  const CHICKENS = 5, DOGS = 3, SITE_STEP = 36, MIN_PLAYER_GAP = 30;
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__worldLifeInstalled) return;
    A.__worldLifeInstalled = true;

    const { HOOKS, P, MAP, ITEMS, ctx } = A;
    const Q = () => A.Q;
    const PL = A.LANG === 'pl';
    const state = { q: null, cars: [], animals: [], ride: 0, car: -1, sites: null, saveT: 0, carImage: null };
    A.load('img/car_red.png').then(image => { state.carImage = image; }, () => {});
    const text = PL ? {
      car: 'SAMOCHÓD: 10 JABŁEK = 15 SEK. SZYBKIEJ JAZDY',
      noApples: 'Potrzebujesz 10 jabłek w bilansie.',
      riding: 'SZYBKA JAZDA',
      balance: 'BILANS JABŁEK',
    } : {
      car: 'CAR: 10 APPLES = 15 SEC. FAST RIDE',
      noApples: 'You need 10 apples in your balance.',
      riding: 'FAST RIDE',
      balance: 'APPLE BALANCE',
    };

    const finite = n => Number.isFinite(n) && n >= 0;
    const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const appleBalance = () => {
      const w = Q().worldLife || {};
      return Math.max(0, Q().apples.length - Math.max(0, w.spentApples || 0));
    };
    const tooCloseToStatic = (x, y, extra = []) => {
      const p = { x, y };
      if (Math.hypot(P.x - x, P.y - y) < 100) return true;
      if (ITEMS && ITEMS.npcs && ITEMS.npcs.some(n => distance(p, n) < 70)) return true;
      if (ITEMS && ITEMS.apples && ITEMS.apples.some(a => distance(p, a) < 32)) return true;
      if (ITEMS && ITEMS.cap && distance(p, ITEMS.cap) < 32) return true;
      if (MAP.pois && MAP.pois.some(s => distance(p, s) < Math.max(70, s.r || 0))) return true;
      return extra.some(o => distance(p, o) < (o.kind === 'car' ? 100 : 42));
    };
    const standable = (x, y, extra = [], ignorePlayer = false) => {
      if (!finite(x) || !finite(y) || x < 18 || y < (MAP.top || 40) + 18 || x > MAP.w - 18 || y > MAP.h - 18) return false;
      if (!ignorePlayer && Math.hypot(P.x - x, P.y - y) < MIN_PLAYER_GAP) return false;
      if (A.blocked(x, y)) return false;
      return !extra.some(o => distance({ x, y }, o) < (o.kind === 'car' ? 36 : 24));
    };

    function startCell() {
      const sx = Math.floor(P.x / SITE_STEP), sy = Math.floor(P.y / SITE_STEP);
      for (let r = 0; r < 12; r++) for (let dy = -r; dy <= r; dy++) for (const dx of [-r, r]) {
        const x = (sx + dx) * SITE_STEP + SITE_STEP / 2, y = (sy + dy) * SITE_STEP + SITE_STEP / 2;
        if (standable(x, y, [], true)) return [sx + dx, sy + dy];
      }
      return [sx, sy];
    }

    /* Coarse flood fill makes every selected cell reachable through the same
       standable grid. Exact placement is checked again before use. */
    function reachableSites() {
      if (state.sites) return state.sites;
      const [sx, sy] = startCell(), maxX = Math.ceil(MAP.w / SITE_STEP), maxY = Math.ceil(MAP.h / SITE_STEP);
      const q = [[sx, sy]], seen = new Set([`${sx},${sy}`]), out = [];
      for (let head = 0; head < q.length && head < 12000; head++) {
        const [gx, gy] = q[head], x = gx * SITE_STEP + SITE_STEP / 2, y = gy * SITE_STEP + SITE_STEP / 2;
        if (standable(x, y, [], true)) out.push({ x, y });
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = gx + dx, ny = gy + dy, key = `${nx},${ny}`;
          if (nx < 1 || ny < 1 || nx >= maxX - 1 || ny >= maxY - 1 || seen.has(key)) continue;
          seen.add(key);
          const px = nx * SITE_STEP + SITE_STEP / 2, py = ny * SITE_STEP + SITE_STEP / 2;
          if (standable(px, py, [], true)) q.push([nx, ny]);
        }
      }
      /* A short random walk is a graceful fallback on maps whose narrow paths
         are missed by the coarse grid. Every fallback point follows a valid
         unblocked point, so it remains in the spawn-connected area. */
      let x = P.x, y = P.y;
      for (let i = 0; i < 1000 && out.length < 180; i++) {
        const a = Math.random() * Math.PI * 2, d = 24 + Math.random() * 90;
        const nx = x + Math.cos(a) * d, ny = y + Math.sin(a) * d;
        if (standable(nx, ny, [], true)) { x = nx; y = ny; out.push({ x, y }); }
      }
      state.sites = out;
      return out;
    }

    function randomSite(extra, minFromPlayer = 100) {
      const pool = reachableSites().slice();
      for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
      for (const s of pool) {
        if (Math.hypot(P.x - s.x, P.y - s.y) < minFromPlayer) continue;
        if (tooCloseToStatic(s.x, s.y, extra)) continue;
        if (standable(s.x, s.y, extra)) return { x: s.x, y: s.y };
      }
      for (let r = 120; r < 900; r += 36) {
        for (let a = 0; a < Math.PI * 2; a += .35) {
          const x = P.x + Math.cos(a) * r, y = P.y + Math.sin(a) * r;
          if (standable(x, y, extra) && !tooCloseToStatic(x, y, extra)) return { x, y };
        }
      }
      return { x: Math.max(24, Math.min(MAP.w - 24, P.x + 120)), y: Math.max((MAP.top || 40) + 24, Math.min(MAP.h - 24, P.y)) };
    }

    function validSavedCars(cars) {
      return Array.isArray(cars) && cars.length === 2 && cars.every(c => standable(c.x, c.y, [], true));
    }
    function chooseCars() {
      const cars = [];
      const first = randomSite(cars, 140); first.kind = 'car'; cars.push(first);
      let second = null;
      for (let n = 0; n < 80 && !second; n++) {
        const candidate = randomSite(cars, 140);
        if (Math.hypot(candidate.x - first.x, candidate.y - first.y) > 280) second = candidate;
      }
      if (!second) second = randomSite(cars, 140);
      second.kind = 'car'; cars.push(second);
      return cars;
    }

    function newAnimal(kind, extra) {
      const p = randomSite(extra, 150); p.kind = kind;
      return { kind, x: p.x, y: p.y, homeX: p.x, homeY: p.y, tx: p.x, ty: p.y, dir: Math.random() < .5 ? 'left' : 'right', step: Math.random() * 4, peck: Math.random() * 2, wait: Math.random() * 2 };
    }
    function makeAnimals() {
      const extra = state.cars.slice();
      const animals = [];
      for (let i = 0; i < CHICKENS; i++) { const a = newAnimal('chicken', extra.concat(animals)); animals.push(a); }
      for (let i = 0; i < DOGS; i++) { const a = newAnimal('dog', extra.concat(animals)); animals.push(a); }
      return animals;
    }

    function syncState() {
      const q = Q();
      if (state.q === q) return;
      state.q = q;
      state.sites = null;
      if (!q.worldLife || typeof q.worldLife !== 'object') q.worldLife = {};
      const w = q.worldLife;
      if (!finite(w.spentApples)) w.spentApples = 0;
      if (validSavedCars(w.cars)) state.cars = w.cars.map(c => ({ x: c.x, y: c.y, kind: 'car' }));
      else {
        state.cars = chooseCars();
        w.cars = state.cars.map(c => ({ x: c.x, y: c.y }));
      }
      state.animals = makeAnimals();
      state.ride = Math.max(0, Math.min(RIDE_SECONDS, Number(w.rideRemaining) || 0));
      state.car = Number.isInteger(w.rideCar) ? w.rideCar : -1;
      state.saveT = 0;
    }

    function saveRideState() {
      const w = Q().worldLife;
      w.rideRemaining = Math.max(0, state.ride);
      w.rideCar = state.ride > 0 ? state.car : -1;
      A.save();
    }
    function buyRide(index) {
      syncState();
      if (state.ride > 0) { A.popToast(text.riding); return; }
      if (appleBalance() < COST) { A.say('arek', [text.noApples]); return; }
      const w = Q().worldLife;
      w.spentApples = Math.max(0, w.spentApples || 0) + COST;
      state.ride = RIDE_SECONDS; state.car = index;
      saveRideState();
      A.popToast(text.car);
    }

    function chooseTarget(o) {
      o.wait = 1.5 + Math.random() * 3.5;
      const radius = o.kind === 'chicken' ? 90 : 150;
      for (let i = 0; i < 18; i++) {
        const a = Math.random() * Math.PI * 2, d = Math.random() * radius;
        const x = o.homeX + Math.cos(a) * d, y = o.homeY + Math.sin(a) * d;
        if (standable(x, y, state.cars.concat(state.animals.filter(a2 => a2 !== o)))) { o.tx = x; o.ty = y; return; }
      }
      o.tx = o.homeX; o.ty = o.homeY;
    }
    function tryMove(o, ux, uy, speed, dt) {
      const turns = [0, .55, -.55, 1.1, -1.1, 1.7, -1.7];
      for (const turn of turns) {
        const c = Math.cos(turn), s = Math.sin(turn), vx = ux * c - uy * s, vy = ux * s + uy * c;
        const nx = o.x + vx * speed * dt, ny = o.y + vy * speed * dt;
        if (!standable(nx, ny, state.cars.concat(state.animals.filter(a => a !== o))) || Math.hypot(P.x - nx, P.y - ny) < MIN_PLAYER_GAP) continue;
        o.x = nx; o.y = ny; o.dir = Math.abs(vx) > Math.abs(vy) ? (vx < 0 ? 'left' : 'right') : (vy < 0 ? 'up' : 'down'); o.step += dt * (o.kind === 'dog' ? 7 : 5); return true;
      }
      return false;
    }
    function updateAnimal(o, dt) {
      o.peck += dt;
      const pdx = o.x - P.x, pdy = o.y - P.y, pd = Math.hypot(pdx, pdy);
      if (pd < 78) {
        const d = pd || 1;
        if (tryMove(o, pdx / d, pdy / d, o.kind === 'dog' ? 30 : 22, dt)) return;
      }
      if ((o.wait -= dt) <= 0 || Math.hypot(o.tx - o.x, o.ty - o.y) < 8) chooseTarget(o);
      const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy);
      if (d > 3) tryMove(o, dx / d, dy / d, o.kind === 'dog' ? 18 : 12, dt);
    }

    function px(sx, sy, s, x, y, w, h, c) { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); }
    function drawChicken(o, sx, sy, s) {
      A.shadow(sx, sy, s * .8, 6);
      const peck = Math.sin(o.peck * 5) > .55 ? 2 : 0, bob = Math.sin(o.step * 2) * .35;
      px(sx, sy, s, -6, -10 + bob, 11, 8, '#f2ead4'); px(sx, sy, s, -3, -12 + bob - peck, 7, 5, '#fff8e8');
      px(sx, sy, s, 3, -11 + bob - peck, 3, 2, '#d8262c'); px(sx, sy, s, 5, -9 + bob - peck, 3, 2, '#e09b22');
      px(sx, sy, s, -1, -11 + bob - peck, 1, 1, '#202235'); px(sx, sy, s, -4, -2, 1, 4, '#d89d29'); px(sx, sy, s, 2, -2, 1, 4, '#d89d29');
      px(sx, sy, s, -7, -8, 3, 3, '#d6c6a2');
    }
    function drawDog(o, sx, sy, s) {
      A.shadow(sx, sy, s * .9, 8);
      ctx.save(); ctx.translate(sx, sy); if (o.dir === 'left') ctx.scale(-1, 1);
      const bob = Math.sin(o.step * 2) * .6;
      px(0, 0, s, -10, -12 + bob, 18, 9, '#665444'); px(0, 0, s, 7, -15 + bob, 8, 8, '#806b58');
      px(0, 0, s, 10, -11 + bob, 5, 4, '#4a392f'); px(0, 0, s, 13, -10 + bob, 3, 2, '#d7ad75');
      px(0, 0, s, 8, -17 + bob, 3, 4, '#3d3029'); px(0, 0, s, -7, -3, 3, 7, '#4a392f'); px(0, 0, s, 4, -3, 3, 7, '#4a392f');
      px(0, 0, s, -8, -10 + bob, 4, 3, '#9b8064'); px(0, 0, s, 9, -14 + bob, 1, 1, '#f5f0e0');
      px(0, 0, s, -13, -12 + bob, 4, 2, '#806b58'); px(0, 0, s, -14, -15 + bob, 2, 5, '#665444');
      ctx.restore();
    }
    function drawCar(car, sx, sy, s) {
      A.shadow(sx, sy, s, 14);
      if (state.carImage) {
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(state.carImage, sx - 28 * s, sy - 29 * s, 56 * s, 38 * s);
        return;
      }
      px(sx, sy, s, -21, -16, 42, 14, '#a91f27'); px(sx, sy, s, -16, -22, 25, 8, '#c72a2e');
      px(sx, sy, s, -12, -20, 9, 5, '#24354a'); px(sx, sy, s, 0, -20, 9, 5, '#24354a');
      px(sx, sy, s, -20, -11, 40, 7, '#c72a2e'); px(sx, sy, s, -22, -7, 4, 3, '#f1c35b'); px(sx, sy, s, 18, -8, 4, 3, '#7d141e');
      px(sx, sy, s, -15, -4, 8, 6, '#24232b'); px(sx, sy, s, 9, -4, 8, 6, '#24232b');
      px(sx, sy, s, -19, -12, 5, 2, '#ee5050'); px(sx, sy, s, -8, -24, 10, 2, '#8a181e');
      px(sx, sy, s, 13, -15, 3, 2, '#6e171c'); px(sx, sy, s, -15, -8, 2, 2, '#e2664c');
    }

    HOOKS.near.push(() => state.cars.map((car, i) => ({ x: car.x, y: car.y, r: 34, onInteract: () => buyRide(i) })));
    HOOKS.speed.push(() => state.ride > 0 ? RIDE_SPEED : 1);
    HOOKS.update.push(dt => {
      syncState();
      if (state.ride > 0) {
        state.ride = Math.max(0, state.ride - dt); state.saveT += dt;
        if (state.saveT >= 1 || state.ride === 0) { state.saveT = 0; saveRideState(); }
      }
      if (A.scene !== 'play') return;
      for (const o of state.animals) updateAnimal(o, dt);
    });
    HOOKS.world.push((push, S, inView) => {
      syncState();
      for (const car of state.cars) if (inView(car.x, car.y)) push(car.y, () => drawCar(car, ...S(car.x, car.y), A.zoom));
      for (const o of state.animals) if (inView(o.x, o.y)) push(o.y, () => (o.kind === 'chicken' ? drawChicken : drawDog)(o, ...S(o.x, o.y), A.zoom));
    });
    HOOKS.minimap.push(dot => { for (const car of state.cars) dot(car.x, car.y, '#d8262c'); });
    HOOKS.questLog.push(lines => {
      const w = Q().worldLife || {}, spent = Math.max(0, w.spentApples || 0);
      if (spent) lines.push([`${text.balance}: ${appleBalance()}`, false]);
    });
    HOOKS.hud.push((U, W, H) => {
      if (!state.ride && !(Q().worldLife && Q().worldLife.spentApples)) return;
      const lines = [`${text.balance}: ${appleBalance()}`];
      if (state.ride > 0) lines.push(`${text.riding}: ${Math.ceil(state.ride)}s`);
      const width = U * 28, x = W - width - U * 2, y = H - U * (lines.length * 2.8 + 3);
      ctx.fillStyle = 'rgba(8,12,40,.78)'; ctx.fillRect(x, y, width, U * (lines.length * 2.8 + 2));
      ctx.font = `${U * 1.45}px Silkscreen`; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      lines.forEach((line, i) => { ctx.fillStyle = i === 1 ? '#ffd21f' : '#f5f0e0'; ctx.fillText(line, x + width - U * 1.4, y + U * (1.3 + i * 2.8)); });
      ctx.textAlign = 'left';
    });

    /* Small public surface for deterministic browser tests and debugging. */
    window.__worldLife = {
      get cars() { return state.cars; },
      get animals() { return state.animals; },
      get rideSeconds() { return state.ride; },
      balance: appleBalance,
      buyRide,
      resetCars() {
        const q = Q();
        if (!q.worldLife) q.worldLife = {};
        q.worldLife.cars = null;
        state.q = null;
        syncState();
      },
    };
    syncState();
  };
  window.addEventListener('ark-ready', READY);
})();
