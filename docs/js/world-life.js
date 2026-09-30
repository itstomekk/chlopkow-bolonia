/* World life for "Arek w Chłopkowie".
   Standalone hook plugin: harmless pecking chickens, scruffy wandering dogs and
   two procedurally drawn red vintage hatchbacks. Loaded before game.js. */
'use strict';
(() => {
  const COST = 10, RIDE_SECONDS = 15, RIDE_SPEED = 2.35, SITE_STEP = 36, MIN_PLAYER_GAP = 30, TRACTORS = 2;
  /* P02: dogs rest a moment after each wander leg (they used to retarget mid-walk
     and change position almost continuously). P03: occasionally a dog chases a
     nearby chicken - short, bounded, ends on its own, cooldown-gated like the
     B04 greet; never a catch, never a kill, and the hen keeps its own timers. */
  const DOG_REST_MIN = 1.0, DOG_REST_MAX = 3.5;
  const DOG_HUNT_RANGE = 170, DOG_HUNT_SECONDS = 2.6, DOG_HUNT_COOLDOWN = 15, DOG_HUNT_CHANCE = 0.6, DOG_HUNT_SPEED = 34;

  /* B01: single extensible registry for every animal kind (previously split
     across the CHICKENS..FOXES consts, the CRIT atlas table, wildlifeAllowed
     and several inline radius/speed maps). habitat: 'notForest' or a list of
     allowed terrain tokens, where 'meadow' means inside MAP.meadow. spawn:
     'any' | 'river' (stork, near water) | 'buildings' (fox, by building
     fronts) | 'farmyard' (pig, tied to farm homes) | 'flock' (bird, in small
     flocks - flocks x 3..5 birds). flies marks the airborne kinds (own update
     path, elevated z). Counts and ANIMAL_ORDER must stay baseline
     (12/7/4/10/6/5/8/3/2/24) - the seeded tests pin spawn positions and
     per-kind indices. */
  const ANIMAL_TYPES = {
    /* B03: noShadow marks art that must never receive A.shadow, in the atlas
       path (drawCritter) or the procedural fallbacks (drawChicken,
       drawSmallWildlife). Chicken/mouse/bird are excluded; dogs, boars and all
       other species keep their shadows. Mouse atlas px 18 -> 72 quarters the
       drawn cell (64*9/72 = 8 units vs the 32-unit baseline) in BOTH width and
       height; physics (radius/step/speeds) stay untouched. */
    chicken: { category: 'domestic', atlas: { row: 0, px: 30, h: 12 }, count: 12, habitat: 'notForest', radius: 90, step: 5, shy: 78, approachSpeed: 22, speed: 12, spawn: 'any', flies: false, noShadow: true, shadowScale: .8, shadowBlur: 7 },
    dog: { category: 'domestic', atlas: { row: 1, px: 40, h: 19 }, count: 7, habitat: 'notForest', radius: 150, step: 7, shy: 78, approachSpeed: 30, speed: 18, spawn: 'any', flies: false, shadowScale: .8, shadowBlur: 7 },
    bird: { category: 'wild', atlas: { row: 2, px: 22, h: 7 }, count: 24, flocks: 6, habitat: 'notForest', radius: 40, step: 8, shy: 78, approachSpeed: 22, speed: 12, spawn: 'flock', flies: true, noShadow: true, shadowScale: .4, shadowBlur: 3 },
    stork: { category: 'wild', atlas: { row: 3, px: 56, h: 30 }, count: 3, habitat: 'notForest', radius: 90, step: 3, shy: 110, approachSpeed: 26, speed: 9, spawn: 'river', flies: false, shadowScale: 1, shadowBlur: 7 },
    fox: { category: 'wild', atlas: { row: 4, px: 40, h: 17 }, count: 2, habitat: 'notForest', radius: 200, step: 10, shy: 150, approachSpeed: 85, speed: 48, spawn: 'buildings', flies: false, shadowScale: .8, shadowBlur: 7 },
    boar: { category: 'wild', atlas: { row: 5, px: 44, h: 21 }, count: 4, habitat: ['forest'], radius: 140, step: 5, shy: 78, approachSpeed: 44, speed: 28, spawn: 'any', flies: false, shadowScale: .8, shadowBlur: 7 },
    mouse: { category: 'wild', atlas: { row: 6, px: 72, h: 9 }, count: 10, habitat: ['forest', 'field'], radius: 70, step: 5, shy: 78, approachSpeed: 24, speed: 16, spawn: 'any', flies: false, noShadow: true, shadowScale: .8, shadowBlur: 7 },
    hare: { category: 'wild', atlas: { row: 7, px: 28, h: 15 }, count: 6, habitat: ['field', 'grass', 'meadow'], radius: 120, step: 5, shy: 78, approachSpeed: 38, speed: 24, spawn: 'any', flies: false, shadowScale: .8, shadowBlur: 7 },
    pig: { category: 'domestic', atlas: { row: 8, px: 42, h: 18 }, count: 5, habitat: 'notForest', radius: 80, step: 5, shy: 78, approachSpeed: 25, speed: 16, spawn: 'farmyard', flies: false, shadowScale: .8, shadowBlur: 7 },
    butterfly: { category: 'wild', atlas: { row: 9, px: 21, h: 5 }, count: 8, habitat: ['field', 'grass', 'meadow'], radius: 110, step: 5, shy: 78, approachSpeed: 22, speed: 12, spawn: 'any', flies: true, shadowScale: .8, shadowBlur: 3 },
  };
  // Spawn order drives the per-kind index of every id (e.g. chicken:0..11).
  const ANIMAL_ORDER = ['chicken', 'dog', 'boar', 'mouse', 'hare', 'pig', 'butterfly', 'stork', 'fox', 'bird'];
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__worldLifeInstalled) return;
    A.__worldLifeInstalled = true;

    const { HOOKS, P, MAP, ITEMS, ctx } = A;
    const Q = () => A.Q;
    const PL = A.LANG === 'pl';
    const state = { q: null, cars: [], tractors: [], animals: [], ride: 0, car: -1, sites: null, saveT: 0, carImage: null, vehicleImage: null, critters: null, waterPoints: [], lastRestoredIds: [] };
    const lastInteraction = Object.create(null), interactionCooldown = Object.create(null);
    /* B02b: animal identity snapshot. Only stable ids, kind and bounded positions
       are persisted into the existing Q.worldLife (same save key, no per-frame
       localStorage writes): on a bounded interval during play, when leaving for the
       title screen, and in a final pagehide/visibilitychange snapshot. Restored
       against the freshly built baseline by kind:index id after per-entry validation. */
    let animalSaveInterval = 10, animalSaveT = 0, lastSceneForSave = 'title';
    A.load('img/car_red.png').then(image => { state.carImage = image; }, () => {});
    A.load('img/vehicles.png').then(image => { state.vehicleImage = image; }, () => {});
    A.load('img/critters.png').then(image => { state.critters = image; }, () => {});
    A.load('img/map_collide.png').then(image => {
      if (Array.isArray(MAP.water) && MAP.water.length) state.waterPoints = MAP.water;
      else {
        const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
        const cx = canvas.getContext('2d', { willReadFrequently: true }); cx.drawImage(image, 0, 0);
        const data = cx.getImageData(0, 0, image.width, image.height).data, sx = MAP.w / image.width, sy = MAP.h / image.height;
        const stride = Math.max(2, Math.floor(Math.sqrt(image.width * image.height / 120000)));
        for (let y = 0; y < image.height && state.waterPoints.length < 5000; y += stride) for (let x = 0; x < image.width && state.waterPoints.length < 5000; x += stride) {
          const v = data[(y * image.width + x) * 4];
          if (v >= 112 && v <= 144 && ((x + y) % (stride * 5) < stride)) state.waterPoints.push({ x: x * sx, y: y * sy });
        }
      }
      if (state.q) { state.q = null; syncState(); }
    }, () => {});
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

    function makeTractors() {
      const pool = reachableSites().filter(s => A.terrainAt(s.x, s.y) === 'field' && standable(s.x, s.y, [], true));
      const out = [];
      for (const s of pool.sort(() => Math.random() - .5)) {
        if (out.some(t => distance(t, s) < 280) || Math.hypot(P.x - s.x, P.y - s.y) < 180) continue;
        out.push({ kind: 'tractor', x: s.x, y: s.y, homeX: s.x, homeY: s.y, tx: s.x, ty: s.y, dir: 'right', step: Math.random() * 4, wait: 0 });
        if (out.length >= TRACTORS) break;
      }
      return out;
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
      const def = ANIMAL_TYPES[kind], h = def && def.habitat, terrain = A.terrainAt(s.x, s.y);
      if (h === 'notForest') return terrain !== 'forest';
      if (Array.isArray(h)) return h.includes(terrain) || (h.includes('meadow') && inMeadow(s));
      return terrain !== 'forest';
    };
    function animalSite(kind, extra, preferred = () => true) {
      const allowed = s => wildlifeAllowed(kind, s) && preferred(s);
      const found = emptySite(extra, allowed);
      if (found) return found;
      if (kind === 'stork') {
        for (const s of reachableSites()) if (allowed(s) && standable(s.x, s.y, extra, true)) return { x: s.x, y: s.y };
        const waters = waterSources(), radii = [24, 42, 60, 78, 96];
        for (const water of waters) for (const radius of radii) for (let angle = 0; angle < Math.PI * 2; angle += .55) {
          const s = { x: water.x + Math.cos(angle) * radius, y: water.y + Math.sin(angle) * radius };
          if (allowed(s) && standable(s.x, s.y, extra, true)) return s;
        }
        return null;
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
    const waterSources = () => Array.isArray(MAP.water) && MAP.water.length ? MAP.water : state.waterPoints;
    const nearRiver = s => {
      const points = waterSources();
      if (points.length) {
        for (const p of points) if (Math.hypot(p.x - s.x, p.y - s.y) <= 100) return true;
        return false;
      }
      return (MAP.pois || []).some(p => p.key === 'river' && Math.hypot(p.x - s.x, p.y - s.y) <= 100);
    };
    function makeAnimals() {
      const extra = state.cars.slice();
      const animals = [];
      const counters = Object.create(null);
      const add = (kind, site) => {
        if (kind === 'stork' && !site) return null;
        const a = newAnimal(kind, extra.concat(animals), site || undefined);
        // Stable per-session identity in spawn order, e.g. 'chicken:0'. Not saved yet (B02b).
        const n = counters[kind] || 0; a.id = `${kind}:${n}`; counters[kind] = n + 1;
        animals.push(a); return a;
      };
      // Roaming wildlife first; ANIMAL_ORDER keeps every per-kind index stable.
      for (const kind of ['chicken', 'dog', 'boar', 'mouse', 'hare']) {
        for (let i = 0; i < ANIMAL_TYPES[kind].count; i++) add(kind, animalSite(kind, extra.concat(animals)));
      }
      // Pigs stay by a subset of accessible building fronts rather than becoming
      // generic roaming wildlife. This gives the village a few lived-in farmyards.
      const pigHomes = buildingSpots().filter((s, i, all) => all.slice(0, i).every(v => Math.hypot(v.x - s.x, v.y - s.y) > 260));
      for (let i = 0; i < ANIMAL_TYPES.pig.count; i++) {
        const home = pigHomes[i % Math.max(1, pigHomes.length)];
        const site = home ? (pigHomeSite(home, extra.concat(animals)) || animalSite('pig', extra.concat(animals), s => Math.hypot(s.x - home.x, s.y - home.y) < 130)) : animalSite('pig', extra.concat(animals));
        add('pig', site);
      }
      for (let i = 0; i < ANIMAL_TYPES.butterfly.count; i++) {
        const b = animalSite('butterfly', extra.concat(animals), s => wildlifeAllowed('butterfly', s));
        if (b) { const a = add('butterfly', b); a.mood = Math.random() < .5 ? -1 : 1; a.color = ['#ff5a8a', '#ffd21f', '#6fd0ff', '#a67cff'][i % 4]; }
      }
      for (let i = 0; i < ANIMAL_TYPES.stork.count; i++) {
        const site = animalSite('stork', extra.concat(animals), nearRiver);
        if (site) add('stork', site);
      }
      for (let i = 0; i < ANIMAL_TYPES.fox.count; i++) { const b = buildingSpots(); add('fox', animalSite('fox', extra.concat(animals), s => b.length && b.some(v => Math.hypot(v.x - s.x, v.y - s.y) < 90))); }
      for (let f = 0; f < ANIMAL_TYPES.bird.flocks; f++) {   // small flocks of sparrows, half of them in the empty north
        const c = f % 2 ? animalSite('bird', extra.concat(animals), s => s.y < MAP.h * .4) : animalSite('bird', extra.concat(animals));
        if (!c) continue;
        for (let k = 0; k < 3 + (f % 3); k++) {
          const b = add('bird', { x: c.x + (Math.random() - .5) * 40, y: c.y + (Math.random() - .5) * 30 });
          if (!standable(b.x, b.y, [], true)) { b.x = c.x; b.y = c.y; }
          b.homeX = c.x; b.homeY = c.y;
        }
      }
      return animals;
    }

    /* ---- B02b: animal identity/location persistence (not a simulation save) ---- */
    const animalSpotValid = (x, y, allowBlocked) => {
      if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
      if (x < 18 || y < (MAP.top || 40) + 18 || x > MAP.w - 18 || y > MAP.h - 18) return false;
      return allowBlocked || !A.blocked(x, y);
    };
    const ANIMAL_ID_RE = /^([a-z]+):(\d+)$/;
    function animalSnapshot() {
      // Floor (not round): A.blocked() floors, so a floored saved position always
      // stays in the pixel the animal actually occupied - rounding could shift a
      // walkable float onto the first blocked pixel of an adjacent wall/water edge.
      return state.animals.map(a => ({
        id: a.id, kind: a.kind,
        x: Math.floor(a.x), y: Math.floor(a.y),
        homeX: Math.floor(a.homeX), homeY: Math.floor(a.homeY),
        tx: Math.floor(a.tx), ty: Math.floor(a.ty),
      }));
    }
    function flushAnimalSave() {
      const q = Q();
      // A session that never named a hero has nothing meaningful to persist
      // (game.loadSave() ignores it anyway) - skip the write entirely.
      if (!q.playerName) return;
      // Never create a save out of thin air during unload: pagehide/title leaks can
      // otherwise resurrect a save the player (or the test suite) just cleared.
      // Only refresh a save that already exists on disk (game.js SAVE_KEY layout).
      if (!localStorage.getItem('arek-chlopkow-save-v1')) return;
      if (!q.worldLife || typeof q.worldLife !== 'object') q.worldLife = {};
      q.worldLife.animals = animalSnapshot();
      A.save();
    }
    /* Restore each validated saved entry onto the freshly built baseline animal
       with the same kind:index id. Malformed/unknown ids, NaN or out-of-bounds
       coords, solid-map spots (grounded kinds only - flying birds/butterflies can
       legitimately sit above water/walls), duplicate ids and id/kind mismatches are
       skipped, leaving that baseline animal at its own fresh position. */
    function applyAnimalSnapshot(list) {
      state.lastRestoredIds = [];
      if (!Array.isArray(list) || !list.length) return;
      const byId = new Map(state.animals.map(a => [a.id, a]));
      const seen = new Set();
      for (const e of list) {
        if (!e || typeof e !== 'object' || typeof e.id !== 'string' || seen.has(e.id)) continue;
        const kind = e.kind, def = ANIMAL_TYPES[kind], m = ANIMAL_ID_RE.exec(e.id);
        if (!def || !m || m[1] !== kind) continue;
        const idx = Number(m[2]);
        if (!Number.isInteger(idx) || idx < 0 || idx >= def.count) continue;
        const a = byId.get(e.id);
        if (!a) continue;
        const flies = !!def.flies;
        if (!animalSpotValid(e.x, e.y, flies)) continue;
        a.x = e.x; a.y = e.y;
        if (animalSpotValid(e.homeX, e.homeY, flies)) { a.homeX = e.homeX; a.homeY = e.homeY; }
        if (Number.isFinite(e.tx) && Number.isFinite(e.ty) &&
            e.tx >= 18 && e.tx <= MAP.w - 18 && e.ty >= (MAP.top || 40) + 18 && e.ty <= MAP.h - 18) { a.tx = e.tx; a.ty = e.ty; }
        seen.add(e.id);
        state.lastRestoredIds.push(e.id);
      }
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
      state.tractors = makeTractors();
      state.animals = makeAnimals();
      // Legacy saves have no snapshot; a malformed one is ignored entry-by-entry.
      applyAnimalSnapshot(w.animals);
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
      const radius = (ANIMAL_TYPES[o.kind] || {}).radius || 120;
      for (let i = 0; i < 18; i++) {
        const a = Math.random() * Math.PI * 2, d = Math.random() * radius;
        const x = o.homeX + Math.cos(a) * d, y = o.homeY + Math.sin(a) * d;
        if (!wildlifeAllowed(o.kind, { x, y })) continue;
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
        o.step += dt * ((ANIMAL_TYPES[o.kind] || {}).step || 5); o.moving = .15; return true;
      }
      return false;
    }
    function rememberInteraction(o, label) {
      lastInteraction[o.kind] = label;
      o.say = label; o.sayT = 1.5;
    }
    const frodoDistance = o => Math.hypot(o.x - A.FRODO.x, o.y - A.FRODO.y);
    let chaseAfter = 0, chaseTarget = null;
    function syncFrodoChase(dt) {
      const f = A.FRODO;
      if (chaseTarget) {
        chaseTarget.chaseT -= dt;
        if (chaseTarget.chaseT <= 0 || Math.hypot(f.x - P.x, f.y - P.y) > 260) {
          f.chase = null; chaseTarget = null;
        } else f.chase = { x: chaseTarget.x, y: chaseTarget.y, t: chaseTarget.chaseT };
      }
    }
    function startFrodoChase(o, seconds = 2.8) {
      if (chaseTarget || A.time < chaseAfter || Math.hypot(A.FRODO.x - P.x, A.FRODO.y - P.y) > 260) return false;
      chaseTarget = o; o.chaseT = seconds; chaseAfter = A.time + 20;
      rememberInteraction(o, 'hau!'); return true;
    }
    function flee(o, fromX, fromY, distance, speed, dt, zig = false) {
      let angle = Math.atan2(o.y - fromY, o.x - fromX);
      if (zig) angle += Math.sin(A.time * 11 + o.homeX) * .75;
      const ux = Math.cos(angle), uy = Math.sin(angle);
      if (tryMove(o, ux, uy, speed, dt)) { o.tx = o.x + ux * distance; o.ty = o.y + uy * distance; return true; }
      return false;
    }
    function updateInteraction(o, dt) {
      o.sayT = Math.max(0, (o.sayT || 0) - dt);
      const fd = frodoDistance(o), pd = distance(o, P);
      if (o.kind === 'mouse') {
        if (fd < 120 && !chaseTarget && A.time >= chaseAfter) startFrodoChase(o, 2.4);
        if (fd < 110 || pd < 68) {
          if (!o.fleeT) { o.fleeT = 1.6; rememberInteraction(o, 'squeak!'); }
          o.fleeT = Math.max(0, o.fleeT - dt);
          flee(o, fd < 110 ? A.FRODO.x : P.x, fd < 110 ? A.FRODO.y : P.y, 160, 62, dt);
          if (o.fleeT === 0) { o.tx = o.homeX; o.ty = o.homeY; }
        } else if (o.fleeT > 0) {
          // B02: threat left mid-flee. End the flight at once so the mouse
          // returns home with normal movement - never frozen, never invisible.
          o.fleeT = 0; o.tx = o.homeX; o.ty = o.homeY;
        }
      } else if (o.kind === 'hare') {
        if (fd < 120 || pd < 115) {
          if (!o.fleeT) { o.fleeT = 1.8; rememberInteraction(o, 'hop!'); }
          o.fleeT = Math.max(0, o.fleeT - dt);
          if (fd < 105 && o.chaseTry !== Math.floor(A.time / 20)) { o.chaseTry = Math.floor(A.time / 20); if (Math.random() < .28) startFrodoChase(o, 1.8); }
          flee(o, fd < 120 ? A.FRODO.x : P.x, fd < 120 ? A.FRODO.y : P.y, 130, 66, dt, true);
        } else if (o.fleeT > 0) {
          // B02: same class as mouse - never freeze mid-flee after the threat leaves.
          o.fleeT = 0;
        }
      } else if (o.kind === 'chicken') {
        if (fd < 75 || pd < 65) {
          if (!o.scatterT) { o.scatterT = .9; o.z = 5; rememberInteraction(o, 'bok!'); }
          o.scatterT = Math.max(0, o.scatterT - dt); o.z = Math.max(0, o.z - dt * 7);
          flee(o, fd < 75 ? A.FRODO.x : P.x, fd < 75 ? A.FRODO.y : P.y, 80, 78, dt);
        } else if (o.scatterT > 0) {
          // B02: same class as mouse - chicken can never be stranded mid-scatter.
          o.scatterT = 0; o.z = 0;
        }
      } else if (o.kind === 'dog') {
        /* B04: friendly greet. Once per cooldown the dog sidles up to Frodo
           (sniff -> play hop -> head home). The cooldown is in-memory only:
           the B02b snapshot whitelist never persists these fields, so nothing
           ephemeral leaks into Q. While the cooldown is active the dog ignores
           Frodo entirely - no re-greet, no tailing, no endless chase. */
        if (!(o.sniffT > 0) && !(o.playT > 0) && !(o.leaveT > 0)) {
          o.greetCdT = Math.max(0, (o.greetCdT || 0) - dt);
          if (fd < 95 && o.greetCdT === 0) { o.sniffT = 1.2; o.greetCdT = 12; rememberInteraction(o, 'hau!'); }
        }
        if (o.sniffT > 0) {
          o.sniffT = Math.max(0, o.sniffT - dt);
          const orbit = A.time * 2.5, tx = A.FRODO.x + Math.cos(orbit) * 24, ty = A.FRODO.y + Math.sin(orbit) * 18;
          const d = Math.hypot(tx - o.x, ty - o.y); if (d > 4) tryMove(o, (tx - o.x) / d, (ty - o.y) / d, 26, dt);
          if (!o.sniffT) { o.playT = 1.4; o.say = 'au!'; o.sayT = 1.4; }
          return;
        }
        if (o.playT > 0) {
          o.playT = Math.max(0, o.playT - dt);
          const orbit = A.time * 3.2, tx = A.FRODO.x + Math.cos(orbit) * 30, ty = A.FRODO.y + Math.sin(orbit) * 22;
          const d = Math.hypot(tx - o.x, ty - o.y); if (d > 6) tryMove(o, (tx - o.x) / d, (ty - o.y) / d, 32, dt);
          o.z = Math.floor(o.playT * 10) % 2 ? 5 : 0;   // playful hop
          if (!o.playT) { o.z = 0; o.leaveT = 3; o.tx = o.homeX; o.ty = o.homeY; }
          return;
        }
        if (o.leaveT > 0) {
          o.leaveT = Math.max(0, o.leaveT - dt);
          const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy);
          if (d > 4) tryMove(o, dx / d, dy / d, 24, dt);
          if (!o.leaveT) { o.tx = o.homeX; o.ty = o.homeY; }
          return;
        }
        /* P03: occasionally chase a nearby chicken. Short and bounded, ends on
           its own (dog heads home), gated by an in-memory cooldown like the
           B04 greet; never while greeting; no kill - the hen is never removed
           and keeps its own flight timers. Uses the same tryMove gate. */
        if (!(o.sniffT > 0) && !(o.playT > 0) && !(o.leaveT > 0) && !(o.huntT > 0)) {
          o.huntCdT = Math.max(0, (o.huntCdT || 0) - dt);
          if (o.huntCdT === 0) {
            let hen = null, best = DOG_HUNT_RANGE;
            for (const a of state.animals) {
              if (a === o || a.kind !== 'chicken') continue;
              const d = Math.hypot(a.x - o.x, a.y - o.y);
              if (d < best) { best = d; hen = a; }
            }
            if (hen && Math.random() < DOG_HUNT_CHANCE * dt) {
              o.huntT = DOG_HUNT_SECONDS; o.huntTarget = hen; o.huntCdT = DOG_HUNT_COOLDOWN;
              rememberInteraction(o, 'hau!');
            }
          }
        }
        if (o.huntT > 0) {
          o.huntT = Math.max(0, o.huntT - dt);
          const hen = o.huntTarget;
          if (hen && hen.kind === 'chicken') {
            const dx = hen.x - o.x, dy = hen.y - o.y, d = Math.hypot(dx, dy);
            if (d > 6) tryMove(o, dx / d, dy / d, DOG_HUNT_SPEED, dt);
          }
          if (!o.huntT) { o.tx = o.homeX; o.ty = o.homeY; o.huntTarget = null; }
          return;
        }
        if (o.greetCdT === 0 && fd < 180) { const d = fd || 1; tryMove(o, (A.FRODO.x - o.x) / d, (A.FRODO.y - o.y) / d, 18, dt); }
      } else if (o.kind === 'pig') {
        if (pd < 120 && !o.curiosityT) { o.curiosityT = 3.2; rememberInteraction(o, 'chrum!'); }
        if (o.curiosityT > 0) {
          o.curiosityT = Math.max(0, o.curiosityT - dt);
          const d = pd || 1; if (d > 34) tryMove(o, (P.x-o.x)/d, (P.y-o.y)/d, 18, dt);
          if (!o.curiosityT) { o.tx = o.homeX; o.ty = o.homeY; }
        }
      } else if (o.kind === 'boar') {
        if (pd < 90 && !o.chargeT && o.phase !== 'retreat') {
          o.chargeT = 1.2; o.phase = 'charge'; rememberInteraction(o, 'PRR!');
          const d = pd || 1, stop = 48; o.tx = P.x + (o.x-P.x) / d * stop; o.ty = P.y + (o.y-P.y) / d * stop;
        }
        if (o.chargeT > 0) {
          o.chargeT = Math.max(0, o.chargeT - dt);
          const dx=o.tx-o.x,dy=o.ty-o.y,d=Math.hypot(dx,dy); if (d>4) tryMove(o,dx/d,dy/d,72,dt);
          if (!o.chargeT) { o.phase='retreat'; o.homeX=o.x; o.homeY=o.y; chooseTarget(o); }
        }
      } else if (o.kind === 'fox') {
        if (fd < 150) {
          if (!o.fleeT) { o.fleeT = 1.4; rememberInteraction(o, 'yip!'); }
          o.fleeT = Math.max(0, o.fleeT - dt); flee(o, A.FRODO.x, A.FRODO.y, 170, 88, dt);
          if (fd < 110 && !chaseTarget && A.time >= chaseAfter) startFrodoChase(o, 1.8);
        } else if (o.fleeT > 0) {
          // B02: same class as mouse - the fox must never be stranded mid-flee.
          o.fleeT = 0;
        }
      } else if (o.kind === 'stork') {
        if (pd < 105 && !o.clatterT) { o.clatterT=2.4; rememberInteraction(o,'kle-kle'); }
        if (o.clatterT > 0) { o.clatterT=Math.max(0,o.clatterT-dt); flee(o,P.x,P.y,90,34,dt); }
      } else if (o.kind === 'bird') {
        if (fd < 85 && o.fly <= 0) rememberInteraction(o,'flutter');
      } else if (o.kind === 'butterfly') {
        if (pd < 145) {
          if (!o.following) { o.following=true; rememberInteraction(o,'flutter'); }
          if (pd < 32 && !o.landed && Math.random() < .018) { o.landed=true; o.landT=1.8; }
        }
        if (o.landed) { o.landT-=dt; o.x=P.x; o.y=P.y-22; o.z=0; if(o.landT<=0)o.landed=false; }
      }
    }
    // birds: take off when Arek or Frodo comes close, fly in an arc (walls are ignored)
    function updateBird(o, dt) {
      if (o.fly > 0) {
        const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy), st = Math.min(d, 120 * dt);
        o.x += dx / (d || 1) * st; o.y += dy / (d || 1) * st; o.step += dt * 12;
        if (Math.abs(dx) > 1) o.face = dx < 0 ? 'left' : 'right';
        o.z = Math.min(26, Math.sin(Math.min(1, 1 - d / Math.max(1, o.flyLen)) * Math.PI) * 30 + 4);
        if (d < 2) { o.fly = 0; o.z = 0; o.homeX = o.x; o.homeY = o.y; o.wait = 1 + Math.random() * 2; }
        return;
      }
      const pd = Math.hypot(o.x - P.x, o.y - P.y), fd = frodoDistance(o);
      if (Math.min(pd, fd) < 78) {   // scatter away from Arek or Frodo
        const source = pd <= fd ? P : A.FRODO;
        const away = Math.atan2(o.y - source.y, o.x - source.x);
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
      updateInteraction(o, dt);
      if (o.kind === 'bird') return updateBird(o, dt);
      if (o.kind === 'butterfly') return updateButterfly(o, dt);
      o.peck += dt; o.moving = Math.max(0, (o.moving || 0) - dt);
      if (o.kind === 'boar' && o.chargeT > 0) return;
      if (o.kind === 'mouse' && o.fleeT > 0 || o.kind === 'hare' && o.fleeT > 0 || o.kind === 'chicken' && o.scatterT > 0 || o.kind === 'fox' && o.fleeT > 0 || o.kind === 'stork' && o.clatterT > 0 || o.kind === 'pig' && o.curiosityT > 0 || o.kind === 'dog' && (o.sniffT > 0 || o.playT > 0 || o.leaveT > 0 || o.huntT > 0)) return;
      const pdx = o.x - P.x, pdy = o.y - P.y, pd = Math.hypot(pdx, pdy);
      const shy = (ANIMAL_TYPES[o.kind] || {}).shy || 78;
      if (pd < shy) {
        const d = pd || 1;
        if (tryMove(o, pdx / d, pdy / d, (ANIMAL_TYPES[o.kind] || {}).approachSpeed || 22, dt)) return;
      }
      if (o.kind === 'fox' && Math.hypot(o.tx - o.x, o.ty - o.y) < 8) {
        if (!o.rest) o.rest = 2 + Math.random() * 4;
        if ((o.rest -= dt) > 0) return;
        o.rest = 0; chooseTarget(o);
      }
      const wx = o.tx - o.x, wy = o.ty - o.y, wd = Math.hypot(wx, wy);
      if (o.kind === 'dog') {
        // P02: dogs change position less often - they only pick a new wander
        // target once they actually reached the current one, then rest a moment
        // before moving again (no mid-walk retargeting, no instant re-wander).
        if (wd < 8) {
          if (!o.restT) o.restT = DOG_REST_MIN + Math.random() * (DOG_REST_MAX - DOG_REST_MIN);
          if ((o.restT -= dt) > 0) return;
          o.restT = 0;
          chooseTarget(o);
        }
      } else if ((o.wait -= dt) <= 0 || wd < 8) {
        chooseTarget(o);
      }
      const dx = o.tx - o.x, dy = o.ty - o.y, d = Math.hypot(dx, dy);
      if (d > 3) tryMove(o, dx / d, dy / d, (ANIMAL_TYPES[o.kind] || {}).speed || 12, dt);
    }
    function updateButterfly(o, dt) {
      if (o.landed) { o.x=P.x; o.y=P.y-22; o.z=0; o.step+=dt*8; return; }
      const pdx = P.x - o.x, pdy = P.y - o.y, pd = Math.hypot(pdx, pdy);
      let ux = Math.cos(A.time * 1.7 + o.homeX) * .7, uy = Math.sin(A.time * 1.4 + o.homeY) * .7;
      if (pd < 150) { const sign = o.mood > 0 ? 1 : -1, d = pd || 1; ux += sign * pdx / d * 1.8; uy += sign * pdy / d * 1.8; }
      const d = Math.hypot(ux, uy) || 1;
      tryMove(o, ux / d, uy / d, 13, dt);
      o.z = 5 + Math.sin(A.time * 8 + o.homeX) * 3; o.step += dt * 8; o.moving = .2;
    }

    function chooseTractorTarget(t) {
      for (let i = 0; i < 24; i++) {
        const a = Math.random() * Math.PI * 2, d = 100 + Math.random() * 260;
        const x = t.homeX + Math.cos(a) * d, y = t.homeY + Math.sin(a) * d;
        if (A.terrainAt(x, y) === 'field' && standable(x, y, state.cars.concat(state.tractors.filter(v => v !== t)), true)) { t.tx = x; t.ty = y; return; }
      }
      t.tx = t.homeX; t.ty = t.homeY;
    }

    function updateTractor(t, dt) {
      t.moving = false;
      if (t.puffT > 0) t.puffT = Math.max(0, t.puffT - dt);
      if (Math.hypot(P.x - t.x, P.y - t.y) < 150) {
        const away = Math.atan2(t.y - P.y, t.x - P.x);
        t.tx = t.homeX + Math.cos(away) * 180; t.ty = t.homeY + Math.sin(away) * 180;
      } else if (Math.hypot(t.tx - t.x, t.ty - t.y) < 12 || (t.wait -= dt) <= 0) {
        chooseTractorTarget(t); t.wait = 2 + Math.random() * 4;
      }
      const dx = t.tx - t.x, dy = t.ty - t.y, d = Math.hypot(dx, dy);
      if (d < 2) return;
      const speed = 22, nx = t.x + dx / d * speed * dt, ny = t.y + dy / d * speed * dt;
      if (A.terrainAt(nx, ny) !== 'field' || !standable(nx, ny, state.cars.concat(state.tractors.filter(v => v !== t)))) { chooseTractorTarget(t); return; }
      t.x = nx; t.y = ny; t.dir = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down'); t.step += dt * 5; t.moving = true;
      if (!t.puffT) t.puffT = .7;
    }

    // sprite frames per kind (see ANIMAL_TYPES / critters.json): walk cycle while moving, an idle pose otherwise
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
        case 'butterfly': return Math.floor(A.time * 8 + o.homeX) % 4;
      }
      return 0;
    }
    function drawCritter(o, sx, sy, s) {
      const c = ANIMAL_TYPES[o.kind], img = state.critters;
      if (!img || !c) return (o.kind === 'dog' ? drawDog : o.kind === 'chicken' ? drawChicken : drawSmallWildlife)(o, sx, sy, s);
      const size = 64 * c.atlas.h * s / c.atlas.px, f = critterFrame(o), z = (o.z || 0) * s;
      // B03: noShadow kinds (chicken/mouse/bird) never get a ground shadow.
      if (!c.noShadow) A.shadow(sx, sy, s * c.shadowScale * (z ? .7 : 1), c.shadowBlur);
      ctx.save(); ctx.imageSmoothingEnabled = false; ctx.translate(sx, sy - z);
      if ((o.face || o.dir) === 'left') ctx.scale(-1, 1);
      ctx.drawImage(img, f * 64, c.atlas.row * 64, 64, 64, -size / 2, -size + 2 * size / 64, size, size);
      ctx.restore();
      if (o.sayT > 0 && o.say) {
        const w = Math.max(26 * s, o.say.length * 6 * s + 8 * s), h = 13 * s, y = sy - size - z - h;
        ctx.fillStyle = '#fff4d6'; ctx.fillRect(sx - w / 2, y, w, h);
        ctx.strokeStyle = '#282433'; ctx.lineWidth = Math.max(1, s); ctx.strokeRect(sx - w / 2, y, w, h);
        ctx.fillStyle = '#282433'; ctx.font = `bold ${Math.max(6, 7 * s)}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(o.say, sx, y + h / 2);
        ctx.textAlign = 'left';
      }
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
      // B03: chicken declares noShadow, so the fallback must not add a shadow either.
      if (!(ANIMAL_TYPES[o.kind] || {}).noShadow) A.shadow(sx, sy, s * .8, 6);
      const peck = Math.sin(o.peck * 5) > .55 ? 2 : 0, bob = Math.sin(o.step * 2) * .35;
      px(sx, sy, s, -6, -10 + bob, 11, 8, '#f2ead4'); px(sx, sy, s, -3, -12 + bob - peck, 7, 5, '#fff8e8');
      px(sx, sy, s, 3, -11 + bob - peck, 3, 2, '#d8262c'); px(sx, sy, s, 5, -9 + bob - peck, 3, 2, '#e09b22');
      px(sx, sy, s, -1, -11 + bob - peck, 1, 1, '#202235'); px(sx, sy, s, -4, -2, 1, 4, '#d89d29'); px(sx, sy, s, 2, -2, 1, 4, '#d89d29');
      px(sx, sy, s, -7, -8, 3, 3, '#d6c6a2');
    }
    function drawDog(o, sx, sy, s) {
      // B03: dogs keep their shadow (no noShadow flag in the registry).
      if (!(ANIMAL_TYPES[o.kind] || {}).noShadow) A.shadow(sx, sy, s * .9, 8);
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
      // B03: the same noShadow gate covers mouse and bird here; boars, pigs and
      // the generic species (hare/stork/fox/butterfly) keep their shadows.
      if (!(ANIMAL_TYPES[o.kind] || {}).noShadow) A.shadow(sx, sy, s * .7, o.kind === 'boar' || o.kind === 'pig' ? 8 : 4);
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
      ctx.imageSmoothingEnabled = false;
      if (state.vehicleImage) ctx.drawImage(state.vehicleImage, 0, 3 * 64, 64, 64, sx - 30 * s, sy - 32 * s, 60 * s, 38 * s);
      else if (state.carImage) ctx.drawImage(state.carImage, sx - 28 * s, sy - 29 * s, 56 * s, 38 * s);
      else {
        px(sx, sy, s, -21, -16, 42, 14, '#a91f27'); px(sx, sy, s, -16, -22, 25, 8, '#c72a2e');
        px(sx, sy, s, -12, -20, 9, 5, '#24354a'); px(sx, sy, s, 0, -20, 9, 5, '#24354a');
        px(sx, sy, s, -20, -11, 40, 7, '#c72a2e'); px(sx, sy, s, -22, -7, 4, 3, '#f1c35b'); px(sx, sy, s, 18, -8, 4, 3, '#7d141e');
        px(sx, sy, s, -15, -4, 8, 6, '#24232b'); px(sx, sy, s, 9, -4, 8, 6, '#24232b');
      }
    }
    function drawTractor(t, sx, sy, s) {
      A.shadow(sx, sy, s * 1.2, 15);
      ctx.imageSmoothingEnabled = false;
      const row = t.dir === 'up' ? 2 : t.dir === 'down' ? 1 : 0;
      const frame = t.moving ? Math.floor(t.step) % 4 : 0;
      if (state.vehicleImage) {
        ctx.save(); ctx.translate(sx, sy);
        if (row === 0 && t.dir === 'left') ctx.scale(-1, 1);
        ctx.drawImage(state.vehicleImage, frame * 64, row * 64, 64, 64, -30 * s, -38 * s, 60 * s, 42 * s);
        ctx.restore();
      } else {
        ctx.save(); ctx.translate(sx, sy); if (t.dir === 'left') ctx.scale(-1, 1);
        const bob = Math.sin(t.step * 2) * .5;
        px(0, 0, s, -22, -9 + bob, 30, 12, '#2e6ea7'); px(0, 0, s, -2, -22 + bob, 15, 14, '#3b82bd');
        px(0, 0, s, 1, -20 + bob, 10, 8, '#9ed2e8'); px(0, 0, s, -18, -1, 9, 8, '#171923'); px(0, 0, s, 12, -2, 7, 7, '#171923');
        px(0, 0, s, -25, -16 + bob, 5, 3, '#f0a62f'); px(0, 0, s, -5, -28 + bob, 3, 8, '#1f2937');
        ctx.restore();
      }
      if (t.moving && Math.floor(A.time * 3) % 2 === 0) {
        const dx = t.dir === 'left' ? -8 : t.dir === 'right' ? 8 : 0;
        ctx.fillStyle = 'rgba(215,220,214,.8)'; ctx.fillRect(sx + (dx - 8) * s, sy - 49 * s, 3 * s, 3 * s);
        ctx.fillStyle = 'rgba(180,190,190,.7)'; ctx.fillRect(sx + (dx - 11) * s, sy - 54 * s, 2 * s, 2 * s);
      }
    }

    /* A02: read-only world hover hit shapes (map px, unzoomed) for the game.js
       picker - no second animal/car registry there. The boxes mirror the real
       draw extents: cars/tractors use their 60 px sprite boxes, critters use
       the ANIMAL_TYPES atlas height, and flying birds/butterflies keep their current z. */
    function hitShapes() {
      const out = [];
      for (const c of state.cars) out.push({ kind: 'car', x: c.x, y: c.y, base: c.y, halfW: 30, top: 32, bottom: 6 });
      for (const t of state.tractors) out.push({ kind: 'tractor', x: t.x, y: t.y, base: t.y, halfW: 30, top: 38, bottom: 4 });
      for (const o of state.animals) {
        const c = ANIMAL_TYPES[o.kind], z = o.z || 0;
        if (o.kind === 'butterfly') { out.push({ kind: 'butterfly', x: o.x, y: o.y, base: o.y, halfW: 8, top: 8 + z, bottom: 1 + z }); continue; }
        out.push({ kind: o.kind, x: o.x, y: o.y, base: o.y, halfW: c ? 32 * c.atlas.h / c.atlas.px : 10, top: (c ? c.atlas.h : 12) + z, bottom: 1 + z });
      }
      return out;
    }

    HOOKS.near.push(() => state.cars.map((car, i) => ({ x: car.x, y: car.y, r: 34, onInteract: () => buyRide(i) })));
    HOOKS.speed.push(() => state.ride > 0 ? RIDE_SPEED : 1);
    function animalNeedsUpdate(o) {
      const camera = A.camera;
      if (!camera) return true;
      const margin = 120, left = -camera.ox / camera.zoom - margin, top = -camera.oy / camera.zoom - margin;
      const right = (ctx.canvas.width - camera.ox) / camera.zoom + margin;
      const bottom = (ctx.canvas.height - camera.oy) / camera.zoom + margin;
      if (o.x >= left && o.x <= right && o.y >= top && o.y <= bottom) return true;
      // Off-screen wildlife resumes as soon as it enters the camera or either character's interaction range.
      return Math.abs(o.x - P.x) < 260 && Math.abs(o.y - P.y) < 260 ||
        Math.abs(o.x - A.FRODO.x) < 260 && Math.abs(o.y - A.FRODO.y) < 260;
    }
    HOOKS.update.push(dt => {
      syncState();
      if (state.ride > 0) {
        state.ride = Math.max(0, state.ride - dt); state.saveT += dt;
        if (state.saveT >= 1 || state.ride === 0) { state.saveT = 0; saveRideState(); }
      }
      // B02b: bounded snapshots only - when leaving play for the title screen (the
      // game saves there too) and on a slow interval; never on every frame.
      if (lastSceneForSave !== A.scene) {
        if (A.scene === 'title' && lastSceneForSave === 'play') flushAnimalSave();
        lastSceneForSave = A.scene;
      }
      if (A.scene === 'play') {
        animalSaveT += dt;
        if (animalSaveT >= animalSaveInterval) { animalSaveT = 0; flushAnimalSave(); }
      }
      if (A.scene !== 'play') return;
      for (const t of state.tractors) updateTractor(t, dt);
      for (const o of state.animals) if (animalNeedsUpdate(o)) updateAnimal(o, dt);
      syncFrodoChase(dt);
    });
    /* B02b: final pagehide / tab-hidden snapshot so a reload or tab close keeps the
       last valid animal positions (the sandboxed save already round-trips them). */
    window.addEventListener('pagehide', () => { try { flushAnimalSave(); } catch (e) { } });
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') { try { flushAnimalSave(); } catch (e) { } } });
    HOOKS.world.push((push, S, inView) => {
      syncState();
      for (const car of state.cars) if (inView(car.x, car.y)) push(car.y, () => drawCar(car, ...S(car.x, car.y), A.zoom));
      for (const t of state.tractors) if (inView(t.x, t.y)) push(t.y, () => drawTractor(t, ...S(t.x, t.y), A.zoom));
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
      get tractors() { return state.tractors; },
      get animals() { return state.animals; },
      get waterPoints() { return waterSources(); },
      get lastInteraction() { return { ...lastInteraction }; },
      get vehicleSpritesLoaded() { return !!state.vehicleImage; },
      get crittersLoaded() { return !!state.critters; },
      get animalTypes() { return ANIMAL_TYPES; },
      get speciesOrder() { return ANIMAL_ORDER.slice(); },
      get rideSeconds() { return state.ride; },
      stepInteractions(dt = .05) { for (const o of state.animals) updateAnimal(o, dt); syncFrodoChase(dt); },
      resetInteractionCooldown(kind) {
        delete lastInteraction[kind]; interactionCooldown[kind] = 0; chaseAfter = 0;
        if (chaseTarget && chaseTarget.kind === kind) { A.FRODO.chase = null; chaseTarget = null; }
        /* B04: clear the ephemeral per-dog greet fields too, so a test/session
           restart starts from a clean cooldown (they never reach Q/save). */
        /* P02/P03: and the wander rest / chicken-chase fields (same ephemeral rule). */
        for (const a of state.animals) if (a.kind === kind) { a.sniffT = 0; a.playT = 0; a.leaveT = 0; a.greetCdT = 0; a.restT = 0; a.huntT = 0; a.huntCdT = 0; a.huntTarget = null; a.z = 0; }
      },
      balance: appleBalance,
            buyRide,
            hitShapes,
            /* B02b debug/test surface: read the last validated restore set, control
               the bounded save interval, force a snapshot, or rebuild animals from
               the current Q.worldLife snapshot (keeps cars/tractors untouched). */
            get lastRestored() { return state.lastRestoredIds.slice(); },
            get saveIntervalSec() { return animalSaveInterval; },
            set saveIntervalSec(v) { const n = Number(v); if (Number.isFinite(n) && n > 0) animalSaveInterval = n; },
            flushSave() { flushAnimalSave(); },
            reloadAnimals() { state.q = null; syncState(); },
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
