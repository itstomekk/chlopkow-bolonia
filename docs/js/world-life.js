/* World life for "Arek w Chłopkowie".
   Standalone hook plugin: harmless pecking chickens, scruffy wandering dogs and
   two procedurally drawn red vintage hatchbacks. Loaded before game.js. */
'use strict';
(() => {
  const COST = 10, RIDE_SECONDS = 15, RIDE_SPEED = 2.35;
  // Keep domestic birds out of the forest; wild animals are selected by terrain.
  const CHICKENS = 12, DOGS = 7, BOARS = 4, MICE = 10, HARES = 6, PIGS = 5, BUTTERFLIES = 8, BIRD_FLOCKS = 6, STORKS = 3, FOXES = 2, SITE_STEP = 36, MIN_PLAYER_GAP = 30;
  // docs/img/critters.png rows (64px cells, drawn facing right): hen, stray, bird, stork, fox.
  // `px` = tallest sprite in that row in sheet pixels (critters.json h), `h` = its on-screen height in map px.
  const CRIT = { chicken: { row: 0, px: 30, h: 12 }, dog: { row: 1, px: 40, h: 19 }, bird: { row: 2, px: 22, h: 7 }, stork: { row: 3, px: 56, h: 30 }, fox: { row: 4, px: 40, h: 17 }, boar: { row: 5, px: 44, h: 21 }, mouse: { row: 6, px: 18, h: 9 }, hare: { row: 7, px: 28, h: 15 }, pig: { row: 8, px: 42, h: 18 } };
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__worldLifeInstalled) return;
    A.__worldLifeInstalled = true;

    const { HOOKS, P, MAP, ITEMS, ctx } = A;
    const Q = () => A.Q;
    const PL = A.LANG === 'pl';
    const state = { q: null, cars: [], animals: [], ride: 0, car: -1, sites: null, saveT: 0, carImage: null, critters: null };
    A.load('img/car_red.png').then(image => { state.carImage = image; }, () => {});
    A.load('img/critters.png').then(image => { state.critters = image; }, () => {});
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

    function randomSite(extra, minFromPlayer = 100, allowed = () => true) {
      const pool = reachableSites().slice();
      for (let i = pool.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [pool[i], pool[j]] = [pool[j], pool[i]]; }
      for (const s of pool) {
        if (Math.hypot(P.x - s.x, P.y - s.y) < minFromPlayer) continue;
        if (!allowed(s)) continue;
        if (tooCloseToStatic(s.x, s.y, extra)) continue;
        if (standable(s.x, s.y, extra)) return { x: s.x, y: s.y };
      }
      for (let r = 120; r < 900; r += 36) {
        for (let a = 0; a < Math.PI * 2; a += .35) {
          const x = P.x + Math.cos(a) * r, y = P.y + Math.sin(a) * r;
          if (allowed({ x, y }) && standable(x, y, extra) && !tooCloseToStatic(x, y, extra)) return { x, y };
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

    function newAnimal(kind, extra, site) {
      const p = site || randomSite(extra, 150, s => wildlifeAllowed(kind, s)); p.kind = kind;
      return { kind, x: p.x, y: p.y, homeX: p.x, homeY: p.y, tx: p.x, ty: p.y, dir: Math.random() < .5 ? 'left' : 'right', step: Math.random() * 4, peck: Math.random() * 2, wait: Math.random() * 2, z: 0, fly: 0 };
    }
    // How "empty" a site is: few map objects / POIs / landmarks nearby. Used to send extra wildlife to the quiet fields.
    function emptiness(s) {
      let n = 0;
      for (const o of MAP.objects || []) if (Math.abs(o.x + o.w / 2 - s.x) < 260 && Math.abs(o.base - s.y) < 260) n++;
      return n;
    }
    function emptySite(extra, pred) {
      const pool = reachableSites();
      if (!pool.length) return null;
      let best = null;
      for (let i = 0, tries = 0; i < 24 && tries < 400; tries++) {
        const s = pool[(Math.random() * pool.length) | 0];
        if ((pred && !pred(s)) || tooCloseToStatic(s.x, s.y, extra) || !standable(s.x, s.y, extra)) continue;
        i++; const e = emptiness(s) + Math.random() * 2; if (!best || e < best.e) best = { x: s.x, y: s.y, e };
      }
      return best;
    }
    const inMeadow = s => {
      const m = MAP.meadow;
      return !!m && s.x >= m.x0 && s.x <= m.x1 && s.y >= m.y0 && s.y <= m.y1;
    };
    const wildlifeAllowed = (kind, s) => {
      const terrain = A.terrainAt(s.x, s.y);
      if (kind === 'boar') return terrain === 'forest';
      if (kind === 'mouse') return terrain === 'forest' || terrain === 'field';
      if (kind === 'hare') return terrain === 'field' || inMeadow(s) || terrain === 'grass';
      if (kind === 'butterfly') return terrain === 'field' || terrain === 'grass' || inMeadow(s);
      return terrain !== 'forest';
    };
    function animalSite(kind, extra, preferred = () => true) {
      const allowed = s => wildlifeAllowed(kind, s) && preferred(s);
      const found = emptySite(extra, allowed);
      if (found) return found;
      if (kind === 'stork') {
        // Never use randomSite's generic last-resort point for storks: that
        // fallback is deliberately global and would violate the river rule.
        for (const s of reachableSites()) if (allowed(s) && standable(s, [], true)) return { x: s.x, y: s.y };
      }
      return randomSite(extra, 150, s => wildlifeAllowed(kind, s));
    }
    // building spots for the foxes: map objects that are buildings (wide sprites), reduced to a standable point in front
    function buildingSpots() {
      if (state.buildings) return state.buildings;
      const out = [];
      for (const o of MAP.objects || []) if (o.w >= 40 && o.h >= 30 && o.w <= 200) {
        const x = o.x + o.w / 2, y = o.base + 14;
        if (standable(x, y, [], true)) out.push({ x, y });
      }
      return (state.buildings = out);
    }
    function pigHomeSite(home, extra) {
      // Keep the animal visibly tied to the building, while leaving the door and
      // the player a little room. The first valid offset is deterministic.
      for (const [dx, dy] of [[28, 0], [-28, 0], [0, 28], [0, -28], [40, 22], [-40, 22]]) {
        const x = home.x + dx, y = home.y + dy;
        if (standable(x, y, extra) && Math.hypot(x - home.x, y - home.y) < 90) return { x, y };
      }
      return standable(home.x, home.y, extra, true) ? { x: home.x, y: home.y } : null;
    }
    // The bridge POI is the stable, exported reference for the river. Never use
    // emptiness as a fallback here: that used to put storks in arbitrary fields.
    const nearRiver = s => (MAP.pois || []).some(p => p.key === 'river' && Math.hypot(p.x - s.x, p.y - s.y) < 720);
    function makeAnimals() {
      const extra = state.cars.slice();
      const animals = [];
      const add = (kind, site) => { const a = newAnimal(kind, extra.concat(animals), site || undefined); animals.push(a); return a; };
      for (let i = 0; i < CHICKENS; i++) add('chicken', animalSite('chicken', extra.concat(animals)));
      for (let i = 0; i < DOGS; i++) add('dog', animalSite('dog', extra.concat(animals)));
      for (let i = 0; i < BOARS; i++) add('boar', animalSite('boar', extra.concat(animals)));
      for (let i = 0; i < MICE; i++) add('mouse', animalSite('mouse', extra.concat(animals)));
      for (let i = 0; i < HARES; i++) add('hare', animalSite('hare', extra.concat(animals)));
      // Pigs stay by a subset of accessible building fronts rather than becoming
      // generic roaming wildlife. This gives the village a few lived-in farmyards.
      const pigHomes = buildingSpots().filter((s, i, all) => all.slice(0, i).every(v => Math.hypot(v.x - s.x, v.y - s.y) > 260));
      for (let i = 0; i < PIGS; i++) {
        const home = pigHomes[i % Math.max(1, pigHomes.length)];
        const site = home ? (pigHomeSite(home, extra.concat(animals)) || animalSite('pig', extra.concat(animals), s => Math.hypot(s.x - home.x, s.y - home.y) < 130)) : animalSite('pig', extra.concat(animals));
        add('pig', site);
      }
      for (let i = 0; i < BUTTERFLIES; i++) {
        const b = animalSite('butterfly', extra.concat(animals), s => wildlifeAllowed('butterfly', s));
        if (b) { const a = add('butterfly', b); a.mood = Math.random() < .5 ? -1 : 1; a.color = ['#ff5a8a', '#ffd21f', '#6fd0ff', '#a67cff'][i % 4]; }
      }
      for (let i = 0; i < STORKS; i++) add('stork', animalSite('stork', extra.concat(animals), nearRiver));
      for (let i = 0; i < FOXES; i++) { const b = buildingSpots(); add('fox', animalSite('fox', extra.concat(animals), s => b.length && b.some(v => Math.hypot(v.x - s.x, v.y - s.y) < 90))); }
      for (let f = 0; f < BIRD_FLOCKS; f++) {   // small flocks of sparrows, half of them in the empty north
        const c = f % 2 ? animalSite('bird', extra.concat(animals), s => s.y < MAP.h * .4) : animalSite('bird', extra.concat(animals));
        if (!c) continue;
        for (let k = 0; k < 3 + (f % 3); k++) {
          const b = newAnimal('bird', [], { x: c.x + (Math.random() - .5) * 40, y: c.y + (Math.random() - .5) * 30 });
          if (!standable(b.x, b.y, [], true)) { b.x = c.x; b.y = c.y; }
          b.homeX = c.x; b.homeY = c.y; animals.push(b);
        }
      }
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
      if (o.kind === 'fox') {   // trots from one building to another
        const b = buildingSpots().filter(s => { const d = Math.hypot(s.x - o.x, s.y - o.y); return d > 120 && d < 700; });
        if (b.length) { const s = b[(Math.random() * b.length) | 0]; o.tx = s.x; o.ty = s.y; o.wait = 14; return; }
      }
      const radius = { chicken: 90, dog: 150, boar: 140, mouse: 70, hare: 120, pig: 80, butterfly: 110, stork: 90, bird: 40, fox: 200 }[o.kind] || 120;
      for (let i = 0; i < 18; i++) {
        const a = Math.random() * Math.PI * 2, d = Math.random() * radius;
        const x = o.homeX + Math.cos(a) * d, y = o.homeY + Math.sin(a) * d;
        if (standable(x, y, o.kind === 'bird' ? [] : state.cars.concat(state.animals.filter(a2 => a2 !== o && a2.kind !== 'bird')))) { o.tx = x; o.ty = y; return; }
      }
      o.tx = o.homeX; o.ty = o.homeY;
    }
    function tryMove(o, ux, uy, speed, dt) {
      const turns = [0, .55, -.55, 1.1, -1.1, 1.7, -1.7];
      const others = o.kind === 'bird' ? [] : state.cars.concat(state.animals.filter(a => a !== o && a.kind !== 'bird' && Math.abs(a.x - o.x) < 40 && Math.abs(a.y - o.y) < 40));
      for (const turn of turns) {
        const c = Math.cos(turn), s = Math.sin(turn), vx = ux * c - uy * s, vy = ux * s + uy * c;
        const nx = o.x + vx * speed * dt, ny = o.y + vy * speed * dt;
        if (o.kind === 'stork' && !nearRiver({ x: nx, y: ny })) continue;
        if (!standable(nx, ny, others) || Math.hypot(P.x - nx, P.y - ny) < MIN_PLAYER_GAP) continue;
        o.x = nx; o.y = ny; o.dir = Math.abs(vx) > Math.abs(vy) ? (vx < 0 ? 'left' : 'right') : (vy < 0 ? 'up' : 'down');
        if (Math.abs(vx) > .2) o.face = vx < 0 ? 'left' : 'right';
        o.step += dt * ({ dog: 7, fox: 10, stork: 3, bird: 8 }[o.kind] || 5); o.moving = .15; return true;
      }
      return false;
    }
    // birds: take off when Arek comes close, fly in an arc to a new spot and land (flying ignores walls)
    function updateBird(o, dt) {
      if (o.fly > 0) {
        const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy), st = Math.min(d, 120 * dt);
        o.x += dx / (d || 1) * st; o.y += dy / (d || 1) * st; o.step += dt * 12;
        if (Math.abs(dx) > 1) o.face = dx < 0 ? 'left' : 'right';
        o.z = Math.min(26, Math.sin(Math.min(1, 1 - d / Math.max(1, o.flyLen)) * Math.PI) * 30 + 4);
        if (d < 2) { o.fly = 0; o.z = 0; o.homeX = o.x; o.homeY = o.y; o.wait = 1 + Math.random() * 2; }
        return;
      }
      const pd = Math.hypot(o.x - P.x, o.y - P.y);
      if (pd < 70) {   // scatter away from Arek
        const away = Math.atan2(o.y - P.y, o.x - P.x);
        for (let i = 0; i < 16; i++) {
          const a = away + (Math.random() - .5) * 1.6, r = 160 + Math.random() * 180, x = o.x + Math.cos(a) * r, y = o.y + Math.sin(a) * r;
          if (standable(x, y, [], true)) { o.tx = x; o.ty = y; o.fly = 1; o.flyLen = Math.hypot(x - o.x, y - o.y); window.__worldLife.takeoffs = (window.__worldLife.takeoffs || 0) + 1; return; }
        }
      }
      o.peck += dt;
      if ((o.wait -= dt) <= 0) { chooseTarget(o); o.wait = .6 + Math.random() * 1.8; o.hop = .25; }
      if (o.hop > 0) {   // short hop to the next seed
        o.hop -= dt; const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy);
        if (d > 1) { o.x += dx / d * Math.min(d, 60 * dt); o.y += dy / d * Math.min(d, 60 * dt); if (Math.abs(dx) > 1) o.face = dx < 0 ? 'left' : 'right'; }
        o.z = Math.sin(Math.max(0, o.hop) / .25 * Math.PI) * 3;
      } else o.z = 0;
    }
    function updateAnimal(o, dt) {
      if (o.kind === 'bird') return updateBird(o, dt);
      if (o.kind === 'butterfly') return updateButterfly(o, dt);
      o.peck += dt; o.moving = Math.max(0, (o.moving || 0) - dt);
      const pdx = o.x - P.x, pdy = o.y - P.y, pd = Math.hypot(pdx, pdy);
      const shy = o.kind === 'fox' ? 150 : o.kind === 'stork' ? 110 : 78;
      if (pd < shy) {
        const d = pd || 1;
        if (tryMove(o, pdx / d, pdy / d, { dog: 30, boar: 44, mouse: 24, hare: 38, pig: 25, fox: 85, stork: 26 }[o.kind] || 22, dt)) return;
      }
      if (o.kind === 'fox' && Math.hypot(o.tx - o.x, o.ty - o.y) < 8) {   // sniff around the building for a moment
        if (!o.rest) o.rest = 2 + Math.random() * 4;
        if ((o.rest -= dt) > 0) return;
        o.rest = 0; chooseTarget(o);
      }
      if ((o.wait -= dt) <= 0 || Math.hypot(o.tx - o.x, o.ty - o.y) < 8) chooseTarget(o);
      const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy);
      if (d > 3) tryMove(o, dx / d, dy / d, { dog: 18, boar: 28, mouse: 16, hare: 24, pig: 16, fox: 48, stork: 9 }[o.kind] || 12, dt);
    }
    function updateButterfly(o, dt) {
      const pdx = P.x - o.x, pdy = P.y - o.y, pd = Math.hypot(pdx, pdy);
      let ux = Math.cos(A.time * 1.7 + o.homeX) * .7, uy = Math.sin(A.time * 1.4 + o.homeY) * .7;
      if (pd < 150) { const sign = o.mood > 0 ? 1 : -1, d = pd || 1; ux += sign * pdx / d * 1.8; uy += sign * pdy / d * 1.8; }
      const d = Math.hypot(ux, uy) || 1;
      tryMove(o, ux / d, uy / d, 22, dt);
      o.z = 5 + Math.sin(A.time * 8 + o.homeX) * 3; o.step += dt * 8; o.moving = .2;
    }

    // sprite frames per kind (see CRIT / critters.json): walk cycle while moving, an idle pose otherwise
    function critterFrame(o) {
      const walk2 = Math.floor(o.step) % 2;
      switch (o.kind) {
        case 'chicken': return o.moving ? walk2 : Math.sin(o.peck * 3) > .4 ? 2 : 3;
        case 'dog': return o.moving ? walk2 : (Math.floor(o.peck / 4) % 2 ? 2 : 3);
        case 'bird': return o.fly > 0 ? 2 + (Math.floor(o.step) % 2) : o.z > .5 ? 1 : 0;
        case 'stork': return o.moving ? walk2 : (Math.floor(o.peck / 3) % 3 === 1 ? 3 : 2);
        case 'fox': return o.moving ? Math.floor(o.step) % 3 : 3;
        case 'boar': return o.moving ? walk2 : 2 + (Math.floor(o.peck / 3) % 2);
        case 'mouse': return o.moving ? walk2 : 2 + (Math.floor(o.peck / 3) % 2);
        case 'hare': return o.moving ? walk2 : 2 + (Math.floor(o.peck / 3) % 2);
        case 'pig': return o.moving ? walk2 : 2 + (Math.floor(o.peck / 3) % 2);
      }
      return 0;
    }
    function drawCritter(o, sx, sy, s) {
      if (o.kind === 'butterfly') return drawButterfly(o, sx, sy, s);
      const c = CRIT[o.kind], img = state.critters;
      if (!img || !c) return (o.kind === 'dog' ? drawDog : o.kind === 'chicken' ? drawChicken : drawSmallWildlife)(o, sx, sy, s);
      const size = 64 * c.h * s / c.px, f = critterFrame(o), z = (o.z || 0) * s;
      A.shadow(sx, sy, s * (o.kind === 'stork' ? 1 : o.kind === 'bird' ? .4 : .8) * (z ? .7 : 1), o.kind === 'bird' ? 3 : 7);
      ctx.save(); ctx.imageSmoothingEnabled = false; ctx.translate(sx, sy - z);
      if ((o.face || o.dir) === 'left') ctx.scale(-1, 1);
      ctx.drawImage(img, f * 64, c.row * 64, 64, 64, -size / 2, -size + 2 * size / 64, size, size);
      ctx.restore();
    }
    function drawButterfly(o, sx, sy, s) {
      const flap = Math.sin(A.time * 9 + o.homeX) > 0 ? 1 : .55, c = o.color || '#ff5a8a';
      A.shadow(sx, sy, s * .3, 3);
      ctx.save(); ctx.translate(sx, sy - (o.z || 0) * s); ctx.imageSmoothingEnabled = false;
      ctx.fillStyle = c; ctx.fillRect(-7 * s * flap, -7 * s, 5 * s * flap, 6 * s); ctx.fillRect(2 * s, -7 * s, 5 * s * flap, 6 * s);
      ctx.fillStyle = '#402b4f'; ctx.fillRect(-1 * s, -7 * s, 2 * s, 8 * s); ctx.fillRect(-2 * s, 0, 4 * s, 2 * s);
      ctx.restore();
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
    function drawSmallWildlife(o, sx, sy, s) {
      A.shadow(sx, sy, s * .7, o.kind === 'boar' || o.kind === 'pig' ? 8 : 4);
      ctx.save(); ctx.translate(sx, sy); if ((o.face || o.dir) === 'left') ctx.scale(-1, 1);
      const bob = Math.sin(o.step * 2) * .4;
      if (o.kind === 'boar') {
        px(0, 0, s, -12, -13 + bob, 22, 11, '#4d3b32'); px(0, 0, s, 6, -16 + bob, 9, 9, '#60483c');
        px(0, 0, s, 13, -13 + bob, 5, 4, '#2d2423'); px(0, 0, s, 15, -12 + bob, 2, 2, '#e7c1a1');
        px(0, 0, s, -8, -4, 3, 6, '#332827'); px(0, 0, s, 7, -4, 3, 6, '#332827');
      } else if (o.kind === 'pig') {
        px(0, 0, s, -12, -13 + bob, 21, 12, '#d48691'); px(0, 0, s, 5, -17 + bob, 10, 10, '#e19aa2');
        px(0, 0, s, 13, -14 + bob, 5, 4, '#b86270'); px(0, 0, s, 15, -13 + bob, 2, 2, '#5e3841');
        px(0, 0, s, -7, -3, 3, 6, '#a95f6c'); px(0, 0, s, 5, -3, 3, 6, '#a95f6c');
        px(0, 0, s, -15, -10 + bob, 4, 2, '#e19aa2');
      } else if (o.kind === 'mouse') {
        px(0, 0, s, -6, -7 + bob, 11, 6, '#8b776d'); px(0, 0, s, 3, -10 + bob, 6, 6, '#a38b80');
        px(0, 0, s, 6, -9 + bob, 3, 2, '#d8a4a2'); px(0, 0, s, 8, -8 + bob, 2, 2, '#27222a'); px(0, 0, s, -10, -3, 6, 2, '#a38b80');
      } else {
        px(0, 0, s, -7, -10 + bob, 13, 8, '#9b6b49'); px(0, 0, s, 3, -15 + bob, 7, 8, '#b27b52');
        px(0, 0, s, 7, -13 + bob, 3, 2, '#28232a'); px(0, 0, s, -7, -3, 3, 6, '#6e4b39'); px(0, 0, s, 3, -3, 3, 6, '#6e4b39');
      }
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
      for (const o of state.animals) if (inView(o.x, o.y)) push(o.y, () => drawCritter(o, ...S(o.x, o.y), A.zoom));
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
