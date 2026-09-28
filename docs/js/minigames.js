/* Minigames for "Arek w Chłopkowie" — each started from a coloured flag on the map.
     race   (Damian, north track)      2 laps vs Damian; jump the bale walls; off-track = slow; ghost of your best run
     pig    (Grandpa, corral)          catch Pepa in 30 s; she is fast at first and tires over time
     dogs   (Marcin, south meadow)     collect 6 eggs; dogs growl ("!") before they lunge — jump over them
     skeet  (Michał, PPM range)         shoot a pixel-art target at the range; aim & shoot, 2 barrels
     ducks  (south-east wetland)        ducks fly across the southern-east fields; aim & shoot, 2 barrels
     mowing (football pitch)            mow every strip of the pitch before time runs out
   Shared: 3-2-1 lights, bronze/silver/gold medals, records and retry. Venues come from map.json (osm/render_map.py).
   Save: Q.mg[type] = { tries, won, best, medal, ghost? }  — best = time (s) or hits (skeet). */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK, { HOOKS, P, MAP, ctx } = A;
  const PL = A.LANG === 'pl';
  const Q = () => A.Q;
  if (!Q().mg) Q().mg = {};
  const TR = MAP.track, CO = MAP.corral, ME = MAP.meadow, RG = MAP.range;
  const coarse = () => matchMedia('(pointer:coarse)').matches;

  /* ------------------------------------------------------------------ texts */
  const L = PL ? {
    flag: { race: 'TOR', pig: 'ŚWINKA', dogs: 'PSY', skeet: 'TARCZA', ducks: 'KACZKI', mowing: 'KOSZENIE' },
    intro: {
      race: ['Damian: „Wyścig! Dwa okrążenia. Bele siana przeskakujesz — SPACJA albo X.”', 'Damian: „Po trawie biegnie się wolno, a skróty się nie liczą. Pobij mnie, a potem swój rekord!”'],
      pig: ['Dziadek Zdzisiek: „Świnka Pepa znowu uciekła z chlewika! Złap ją w 30 sekund.”', 'Dziadek: „Na początku jest szybka jak zając, ale szybko się męczy. Zapędź ją pod płot.”'],
      dogs: ['Marcin: „Kury pana Stefana zniosły na pastwisku 6 jajek, ale pilnują ich psy.”', 'Marcin: „Kiedy pies warknie „!”, zaraz skoczy. Wtedy przeskocz go albo uciekaj w bok!”'],
      skeet: ['Michał: „Tu jest tarcza, nie gra w kurki. Sprawdź oko na PPM Strzelectwie.”', !coarse() ? 'Michał: „Celuj myszką albo strzałkami, strzelaj SPACJĄ lub kliknięciem. Dwie lufy, potem przeładowanie. Traf 10 z 15!”' : 'Michał: „Dotknij tarczy, żeby strzelić. Dwie lufy, potem przeładowanie. Traf 10 z 15!”'],
      ducks: ['Michał: „Grę w kaczki przeniosłem na południowy wschód, nad mokradła.”', 'Michał: „Kaczki lecą łukiem nad polami. Traf 10 z 15, ale nie strzelaj w nic poza tarczą.”'],
      mowing: ['Damian: „Boisko zarosło po deszczu. Pomożesz je skosić?”', 'Damian: „Przejdź po każdym pasie murawy. Spacja uruchamia kosiarkę, ale liczy się dokładność.”'],
    },
    win: { race: 'WYGRAŁEŚ Z DAMIANEM!', pig: 'MASZ PEPĘ!', dogs: 'WSZYSTKIE JAJKA!', skeet: 'CELNA TARCZA!', ducks: 'KACZKI TRAFIONE!', mowing: 'BOISKO SKOSZONE!' },
    lose: { race: 'DAMIAN BYŁ SZYBSZY...', pig: 'PEPA UCIEKŁA...', dogs: 'PIES CIĘ DOPADŁ!', dogsOut: 'UCIEKŁEŚ Z PASTWISKA...', skeet: 'ZA MAŁO TRAFIEŃ...', ducks: 'KACZKI ODLECIAŁY...', mowing: 'BOISKO NADAL ZAROSŁE...' },
    log: { race: 'Wyścig z Damianem', pig: 'Złap świnkę Pepę', dogs: 'Jajka i psy', skeet: 'Tarcza u Michała', ducks: 'Gra w kaczki', mowing: 'Koszenie boiska' },
    medal: ['', 'BRĄZ', 'SREBRO', 'ZŁOTO'], next: m => `NASTĘPNY: ${m}`,
    go: 'START!', lap: 'OKRĄŻENIE', time: 'CZAS', best: 'REKORD', eggs: 'JAJKA', left: 'ZOSTAŁO', hits: 'TRAFIENIA', reload: 'PRZEŁADOWANIE...',
    retry: 'SPACJA / R — JESZCZE RAZ', quit: 'ESC — WYJDŹ', esc: 'ESC — PRZERWIJ', record: 'NOWY REKORD!', ghost: 'DUCH REKORDU', offTrack: 'TRAWA — WOLNIEJ!',
    tired: 'PEPA SIĘ MĘCZY!',
  } : {
    flag: { race: 'TRACK', pig: 'PIGGY', dogs: 'DOGS', skeet: 'TARGET', ducks: 'DUCKS', mowing: 'MOWING' },
    intro: {
      race: ['Damian: "Race! Two laps. Jump the hay bales — SPACE or X."', 'Damian: "Grass is slow and shortcuts don\'t count. Beat me, then beat your own record!"'],
      pig: ['Grandpa Zdzisiek: "Pepa the piglet escaped again! Catch her in 30 seconds."', 'Grandpa: "She\'s quick as a hare at first but tires fast. Corner her against the fence."'],
      dogs: ['Marcin: "Mr Stefan\'s hens laid 6 eggs on the meadow, but his dogs guard them."', 'Marcin: "When a dog growls "!", it is about to lunge. Jump over it or dodge sideways!"'],
      skeet: ['Michał: "This is a target, not a moorhen game. Test your aim at the PPM range."', !coarse() ? 'Michał: "Aim with the mouse or arrows, shoot with SPACE or a click. Two barrels, then reload. Hit 10 of 15!"' : 'Michał: "Tap the target to shoot. Two barrels, then reload. Hit 10 of 15!"'],
      ducks: ['Michał: "The duck game moved south-east, out by the wetlands."', 'Michał: "Ducks fly in arcs over the fields. Hit 10 of 15, and keep your aim on the targets."'],
      mowing: ['Damian: "The pitch has grown wild after the rain. Can you mow it?"', 'Damian: "Walk every strip of grass. SPACE starts the mower, but accuracy matters."'],
    },
    win: { race: 'YOU BEAT DAMIAN!', pig: 'GOT PEPA!', dogs: 'ALL THE EGGS!', skeet: 'TARGET MASTER!', ducks: 'DUCKS HIT!', mowing: 'PITCH MOWN!' },
    lose: { race: 'DAMIAN WAS FASTER...', pig: 'PEPA GOT AWAY...', dogs: 'A DOG GOT YOU!', dogsOut: 'YOU LEFT THE MEADOW...', skeet: 'NOT ENOUGH HITS...', ducks: 'THE DUCKS FLEW OFF...', mowing: 'THE PITCH IS STILL WILD...' },
    log: { race: 'Race against Damian', pig: 'Catch Pepa the piglet', dogs: 'Eggs and dogs', skeet: 'Target at Michał\'s range', ducks: 'Duck game', mowing: 'Mow the football pitch' },
    medal: ['', 'BRONZE', 'SILVER', 'GOLD'], next: m => `NEXT: ${m}`,
    go: 'GO!', lap: 'LAP', time: 'TIME', best: 'BEST', eggs: 'EGGS', left: 'LEFT', hits: 'HITS', reload: 'RELOADING...',
    retry: 'SPACE / R — AGAIN', quit: 'ESC — LEAVE', esc: 'ESC — QUIT', record: 'NEW RECORD!', ghost: 'RECORD GHOST', offTrack: 'GRASS — SLOWER!',
    tired: 'PEPA IS TIRING!',
  };

  /* ------------------------------------------------------------------ medals: [bronze, silver, gold] thresholds */
  const MEDAL = {   // time games: lower is better; shooting: hits, higher is better
    race: { lower: true, t: [Infinity, 18.5, 16.5] },   // bronze = simply beating Damian (~18.4 s)
    pig: { lower: true, t: [30, 15, 8] },
    dogs: { lower: true, t: [Infinity, 28, 18] },
    skeet: { lower: false, t: [10, 12, 14] }, ducks: { lower: false, t: [10, 12, 14] }, mowing: { lower: true, t: [Infinity, 35, 22] },
  };
  const medalFor = (type, score) => { const m = MEDAL[type]; let r = 0; m.t.forEach((th, i) => { if (m.lower ? score <= th : score >= th) r = i + 1; }); return r; };
  const MEDAL_COL = ['#666', '#cd7f32', '#d8d8e0', '#ffd21f'];
  const fmt = s => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`;
  const scoreText = (type, v) => ['skeet', 'ducks'].includes(type) ? `${v}/15` : fmt(v);

  /* ------------------------------------------------------------------ geometry helpers */
  const trackPt = th => [TR.cx + Math.cos(th) * TR.rx, TR.cy + Math.sin(th) * TR.ry];
  const onTrack = (x, y) => { const r = Math.hypot((x - TR.cx) / TR.rx, (y - TR.cy) / TR.ry); return Math.abs(r - 1) < (TR.w / 2 + 6) / ((TR.rx + TR.ry) / 2); };
  const angOf = (x, y) => { let a = Math.atan2((y - TR.cy) / TR.ry, (x - TR.cx) / TR.rx); if (a < 0) a += Math.PI * 2; return a; };
  const DIRS = ['down', 'up', 'left', 'right'];

  function freeVenue(x, y) {
    for (let r = 0; r < 500; r += 18) for (let a = 0; a < Math.PI * 2; a += .45) {
      const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
      if (px > 30 && py > 30 && px < MAP.w - 30 && py < MAP.h - 30 && !A.blocked(px, py)) return { x: px, y: py };
    }
    return { x, y };
  }
  const DUCKS_SITE = freeVenue(MAP.w * .78, MAP.h * .78);
  const FLAGS = [
    { type: 'race', host: 'damian', x: TR.cx - 30, y: TR.cy + TR.ry + TR.w / 2 + 22, color: '#d8262c' },
    { type: 'pig', host: 'grandpa', x: CO.cx - CO.r - 26, y: CO.cy + 6, color: '#ff8fb8' },
    { type: 'dogs', host: 'marcin', x: ME.x0 - 18, y: (ME.y0 + ME.y1) / 2, color: '#2f6fe0' },
    { type: 'skeet', host: 'michal', x: RG.x + 40, y: RG.y + 22, color: '#d8a03a' },
    { type: 'ducks', host: 'michal', x: DUCKS_SITE.x, y: DUCKS_SITE.y, color: '#5fb7d4' },
    { type: 'mowing', host: 'damian', x: MAP.football_pitch.cx, y: MAP.football_pitch.cy + MAP.football_pitch.h / 2 + 30, color: '#68bd52' },
  ];
  let MG = null, ANIM = null;
  A.minigame = () => MG && MG.type;   // read by music.js
  A.load('img/animals.png').then(i => { ANIM = i; });

  /* ------------------------------------------------------------------ lifecycle */
  function startMG(type) {
    const q = Q(); q.mg[type] = q.mg[type] || { tries: 0, best: 0, won: false, medal: 0 }; q.mg[type].tries++; A.save();
    MG = { type, phase: 'count', t: 0, run: 0 };
    if (type === 'race') {
      A.teleport(TR.cx + 20, TR.cy + TR.ry); P.dir = 'left';
      // checkpoints every 22.5°, clockwise on screen from the bottom (90°); a ghost replays the record run
      Object.assign(MG, { cp: 0, lap: 1, laps: 2, cps: 16, laps_t: [], rival: { th: Math.PI / 2 + .02, z: 0 }, path: [], ghost: q.mg.race.ghost || null });
    } else if (type === 'pig') {
      A.teleport(CO.cx - CO.r - 10, CO.cy); P.dir = 'right';
      MG.pig = { x: CO.cx + 20, y: CO.cy, dir: 'left', step: 0, wander: 0, juke: 1.5, jx: 0, jy: 0 }; MG.limit = 30;
    } else if (type === 'dogs') {
      A.teleport(ME.x0 + 20, (ME.y0 + ME.y1) / 2); P.dir = 'right';
      const eggs = [];
      for (let n = 0; eggs.length < 6 && n < 500; n++) {
        const x = ME.x0 + 70 + Math.random() * (ME.x1 - ME.x0 - 110), y = ME.y0 + 30 + Math.random() * (ME.y1 - ME.y0 - 50);
        if (!A.blocked(x, y) && eggs.every(e => Math.hypot(e.x - x, e.y - y) > 60)) eggs.push({ x, y, got: false });
      }
      const dogs = [0, 1, 2].map(i => ({ x: ME.x1 - 30, y: ME.y0 + 50 + i * (ME.y1 - ME.y0 - 100) / 2, dir: 'left', step: 0, st: 'patrol', st_t: Math.random(), home: ME.y0 + 50 + i * (ME.y1 - ME.y0 - 100) / 2 }));
      Object.assign(MG, { eggs, dogs });
    } else if (type === 'mowing') {
      A.teleport(MAP.football_pitch.cx, MAP.football_pitch.cy); P.dir = 'up';
      Object.assign(MG, { cut: new Set(), cellsX: 7, cellsY: 10, target: 70, mower: false, limit: 45 });
    } else {
      A.teleport(RG.x, RG.y); P.dir = 'up';
      if (type === 'ducks') { A.teleport(DUCKS_SITE.x, DUCKS_SITE.y); P.dir = 'up'; }
      setupShooting(type, type === 'ducks' ? DUCKS_SITE : RG);
    }
  }
  function endMG(win, msg) {
    const rec = Q().mg[MG.type], score = MG.type === 'skeet' ? MG.hits : MG.run;
    MG.phase = win ? 'win' : 'lose'; MG.msg = msg; MG.t = 0; MG.score = score;
    MG.medal = win ? medalFor(MG.type, score) : 0;
    if (win) {
      const better = MG.type === 'skeet' ? score > (rec.best || 0) : (!rec.best || score < rec.best);
      rec.won = true; rec.medal = Math.max(rec.medal || 0, MG.medal);
      if (better) { rec.best = score; MG.record = true; if (MG.type === 'race') rec.ghost = MG.path; }
      A.celebrate();
    }
    A.save();
  }
  const leave = () => { MG = null; };
  const retry = () => { const t = MG.type; MG = null; startMG(t); };

  function setupShooting(type, site) {
    const plan = []; let t = 1.2;
    for (let i = 0; i < 12; i++) { const dbl = i === 4 || i === 8 || i === 11; plan.push({ t, from: i % 2 }); if (dbl) plan.push({ t: t + .15, from: 1 - (i % 2) }); t += dbl ? 2.4 : 1.7; }
    Object.assign(MG, { site, plan, targets: [], hits: 0, shots: 0, barrel: 2, reload: 0, aim: null, flash: 0, results: [] });
  }

  /* ------------------------------------------------------------------ hooks: interaction, input, movement */
  HOOKS.near.push(() => (HOOKS.busy.some(f => f()) ? [] : FLAGS.map(f => ({
    x: f.x, y: f.y, r: 30,
    onInteract() { A.say(f.host, L.intro[f.type], () => startMG(f.type)); },
  }))));
  HOOKS.busy.push(() => !!MG);
  HOOKS.blocksPlayer.push(() => !!MG && (MG.phase !== 'run' || MG.type === 'skeet'));
  HOOKS.speed.push((x, y) => (MG && MG.type === 'race' && MG.phase === 'run' && !onTrack(x, y) ? .55 : 1));
  HOOKS.key.push(e => {
    if (!MG) return false;
    if (e.code === 'Escape') { leave(); return true; }
    if (MG.phase === 'win' || MG.phase === 'lose') { if (MG.t > .5 && (e.code === 'Space' || e.code === 'Enter' || e.code === 'KeyR')) retry(); return true; }
    if (['skeet', 'ducks'].includes(MG.type) && MG.phase === 'run' && (e.code === 'Space' || e.code === 'Enter' || e.code === 'KeyX')) { shoot(); return true; }
    return false;   // let Space/X reach the jump handler in the other games
  });
  HOOKS.pointer.push((px, py) => {
    if (!MG) return false;
    if (MG.phase === 'win' || MG.phase === 'lose') { if (MG.t > .5) { if (MG.btn && px > MG.btn.mid) leave(); else retry(); } return true; }
    if (['skeet', 'ducks'].includes(MG.type) && MG.phase === 'run') { MG.aim = [px, py]; shoot(); return true; }
    return false;
  });

  /* ------------------------------------------------------------------ AI helpers */
  function steer(o, tx, ty, sp, dt) {   // move toward (tx, ty), sliding around obstacles
    let dx = tx - o.x, dy = ty - o.y; const d = Math.hypot(dx, dy) || 1; dx /= d; dy /= d;
    for (const rot of [0, .6, -.6, 1.2, -1.2, 1.8, -1.8]) {
      const c = Math.cos(rot), s = Math.sin(rot), ux = dx * c - dy * s, uy = dx * s + dy * c;
      const nx = o.x + ux * sp * dt, ny = o.y + uy * sp * dt;
      if (!A.blocked(nx, ny)) { o.x = nx; o.y = ny; o.dir = Math.abs(ux) > Math.abs(uy) ? (ux < 0 ? 'left' : 'right') : (uy < 0 ? 'up' : 'down'); o.step += dt * 9; return true; }
    }
    return false;
  }

  /* ------------------------------------------------------------------ skeet */
  const BOOTH = (side, site) => [site.x + (side ? 130 : -130), site.y - 18];   // arcs stay close to the selected venue
  function shoot() {
    if (MG.reload > 0 || MG.barrel <= 0) return;
    MG.barrel--; MG.shots++; MG.flash = .12;
    if (MG.barrel === 0) MG.reload = .9;
    const cam = A.camera; if (!cam) return;
    const [ax, ay] = MG.aim || [cam.S(RG.x, RG.y - 80)[0], cam.S(RG.x, RG.y - 80)[1]];
    let best = null, bd = 1e9;
    for (const t of MG.targets) if (t.alive) {
      const [sx, sy] = cam.S(t.x, t.y - t.z), d = Math.hypot(sx - ax, sy - ay);
      if (d < 12 * cam.zoom && d < bd) { bd = d; best = t; }
    }
    MG.shotAt = [ax, ay, .25];
    if (best) {
      best.alive = false; best.hit = true; MG.hits++; MG.results.push(1);
      A.burst(best.x, best.y - best.z, ['#1b1b1b', '#d8262c', '#f5f0e0', '#ffd21f'], 22);
      A.popToast(`${L.hits} ${MG.hits}`);
    }
  }
  function updateSkeet(dt) {
    MG.flash = Math.max(0, MG.flash - dt);
    if (MG.shotAt) MG.shotAt[2] -= dt;
    if (MG.reload > 0 && (MG.reload -= dt) <= 0) { MG.reload = 0; MG.barrel = 2; }
    // aim: mouse on desktop, arrows move the crosshair, touch aims where you tap
    const cam = A.camera; if (!cam) return;
    if (!MG.aim) MG.aim = cam.S(RG.x, RG.y - 90);
    if (A.pointer.seen && !coarse()) MG.aim = [A.pointer.x, A.pointer.y];
    const k = (A.keys.has('ArrowLeft') || A.keys.has('KeyA') ? -1 : 0) + (A.keys.has('ArrowRight') || A.keys.has('KeyD') ? 1 : 0);
    const j = (A.keys.has('ArrowUp') || A.keys.has('KeyW') ? -1 : 0) + (A.keys.has('ArrowDown') || A.keys.has('KeyS') ? 1 : 0);
    if (k || j) { A.pointer.seen = false; MG.aim = [MG.aim[0] + k * cam.zoom * 150 * dt, MG.aim[1] + j * cam.zoom * 150 * dt]; }
    // launch
    for (const p of MG.plan) if (!p.done && MG.run >= p.t) {
      p.done = true;
      const [x0, y0] = BOOTH(p.from, MG.site), [x1, y1] = BOOTH(1 - p.from, MG.site);
      MG.targets.push({ x0, y0, x1: x1 + (Math.random() - .5) * 50, y1: y1 - 10 - Math.random() * 40, T: 1.6 + Math.random() * .5, h: 45 + Math.random() * 45, t: 0, alive: true, x: x0, y: y0, z: 0, spin: Math.random() * 6 });
    }
    for (const t of MG.targets) if (t.alive) {
      t.t += dt; const u = t.t / t.T;
      t.x = t.x0 + (t.x1 - t.x0) * u; t.y = t.y0 + (t.y1 - t.y0) * u; t.z = Math.sin(Math.PI * Math.min(1, u)) * t.h; t.spin += dt * 9;
      if (u >= 1) { t.alive = false; MG.results.push(0); }
    }
    if (MG.plan.every(p => p.done) && MG.targets.every(t => !t.alive)) endMG(MG.hits >= 10, MG.hits >= 10 ? L.win[MG.type] : L.lose[MG.type]);
  }

  /* ------------------------------------------------------------------ per-frame update */
  HOOKS.update.push(dt => {
    if (!MG) return;
    MG.t += dt;
    if (MG.phase === 'count') { if (MG.t >= 3) { MG.phase = 'run'; MG.t = 0; } return; }
    if (MG.phase !== 'run') return;
    MG.run += dt;
    if (MG.type === 'race') {
      // record the path (10 Hz) for the ghost
      if (MG.path.length < MG.run * 10) MG.path.push([Math.round(P.x), Math.round(P.y), DIRS.indexOf(P.dir)]);
      const step = Math.PI * 2 / MG.cps, next = (Math.PI / 2 + (MG.cp + 1) * step) % (Math.PI * 2);
      const a = angOf(P.x, P.y); let diff = Math.abs(a - next); diff = Math.min(diff, Math.PI * 2 - diff);
      if (diff < step * .5 && onTrack(P.x, P.y)) {
        MG.cp++;
        if (MG.cp === MG.cps) {
          MG.cp = 0; MG.laps_t.push(MG.run);
          if (MG.lap === MG.laps) { endMG(true, L.win.race); return; }
          MG.lap++; A.popToast(`${L.lap} ${MG.lap}/${MG.laps} · ${fmt(MG.run)}`);
        }
      }
      MG.offTrack = !onTrack(P.x, P.y);
      // Damian: steady pace with a little wobble (0.7x of his old 9.2 s lap); hops over the bale walls at 200° and 330°
      const R = MG.rival, lapT = 9.2 / .7;
      R.th += (Math.PI * 2 / lapT) * (1 + Math.sin(MG.run * 1.3) * .08) * dt;
      const deg = ((R.th * 180 / Math.PI) % 360 + 360) % 360, wall = [200, 330].find(b => Math.abs(deg - b) < 9);
      R.z = wall ? Math.cos((deg - wall) / 9 * Math.PI / 2) * 14 : 0;
      if (R.th - Math.PI / 2 >= Math.PI * 2 * MG.laps) endMG(false, L.lose.race);
    } else if (MG.type === 'pig') {
      const pig = MG.pig, d = Math.hypot(P.x - pig.x, P.y - pig.y);
      if (d < 16 && !P.air) { endMG(true, L.win.pig); return; }
      const stamina = Math.max(0, 1 - MG.run / 26);                // 1 -> 0 over ~26 s
      MG.tired = stamina < .45;
      const sp = 105 + 70 * stamina;
      pig.juke -= dt;
      if (d < 120) {   // flee from Arek; every ~1.5 s a sudden sideways juke; drift back toward the corral centre
        let fx = (pig.x - P.x) / d, fy = (pig.y - P.y) / d;
        if (pig.juke <= 0) { pig.juke = 1.2 + Math.random() * .8; const s = Math.random() < .5 ? -1 : 1; pig.jx = -fy * s; pig.jy = fx * s; pig.jt = .35; }
        if (pig.jt > 0) { pig.jt -= dt; fx = fx * .3 + pig.jx; fy = fy * .3 + pig.jy; }
        const cx = (CO.cx - pig.x) / CO.r * .5, cy = (CO.cy - pig.y) / CO.r * .5;
        steer(pig, pig.x + (fx + cx) * 50, pig.y + (fy + cy) * 50, sp * (pig.jt > 0 ? 1.25 : 1), dt);
      } else {
        pig.wander -= dt; if (pig.wander <= 0) { pig.wander = 1 + Math.random(); pig.tx = CO.cx + (Math.random() - .5) * CO.r; pig.ty = CO.cy + (Math.random() - .5) * CO.r * .7; }
        steer(pig, pig.tx, pig.ty, 45, dt);
      }
      if (MG.tired && Math.random() < dt * 4) A.burst(pig.x + (Math.random() - .5) * 8, pig.y - 22, ['#9fd0f0'], 1);
      if (MG.run >= MG.limit) endMG(false, L.lose.pig);
    } else if (MG.type === 'dogs') {
      for (const e of MG.eggs) if (!e.got && Math.hypot(P.x - e.x, P.y - e.y) < 14) { e.got = true; A.burst(e.x, e.y - 6, ['#fff', '#ffd21f']); }
      const got = MG.eggs.filter(e => e.got).length;
      if (got === MG.eggs.length) { endMG(true, L.win.dogs); return; }
      if (P.x < ME.x0 - 40 || P.x > ME.x1 + 40 || P.y < ME.y0 - 40 || P.y > ME.y1 + 40) { endMG(false, L.lose.dogsOut); return; }
      const chaseSpeed = 68 + got * 3;                                  // speeds up with eggs, but stays below Arek's 110 px/s walk speed
      for (const dg of MG.dogs) {
        dg.st_t -= dt;
        const d = Math.hypot(P.x - dg.x, P.y - dg.y);
        if (dg.st === 'windup') { if (dg.st_t <= 0) { dg.st = 'lunge'; dg.st_t = .5; const k = 1 / (d || 1); dg.lx = (P.x - dg.x) * k; dg.ly = (P.y - dg.y) * k; } }
        else if (dg.st === 'lunge') { steer(dg, dg.x + dg.lx * 40, dg.y + dg.ly * 40, 145 + got * 4, dt); if (dg.st_t <= 0) { dg.st = 'rest'; dg.st_t = .9; } }
        else if (dg.st === 'rest') { if (dg.st_t <= 0) dg.st = 'chase'; }
        else if (dg.st === 'alert') { if (d > 250) dg.st = 'patrol'; else if (dg.st_t <= 0) dg.st = 'chase'; }
        else if (dg.st === 'chase') { if (d > 250) dg.st = 'patrol'; else { steer(dg, P.x, P.y, chaseSpeed, dt); if (d < 95 && dg.st_t <= 0) { dg.st = 'windup'; dg.st_t = .75; } } }
        else if (d < 210) { dg.st = 'alert'; dg.st_t = .8; }
        else { dg.st = 'patrol'; steer(dg, ME.x1 - 50 - Math.sin(MG.run * .5 + dg.home) * 110, dg.home, 45, dt); }
        if (dg.st === 'rest' && dg.st_t < 0) dg.st_t = 0;
        if (d < 13 && P.z < 6) { endMG(false, L.lose.dogs); return; }
      }
    } else if (MG.type === 'mowing') {
      const fp = MAP.football_pitch, x0 = fp.cx - fp.w / 2, y0 = fp.cy - fp.h / 2;
      const inside = P.x >= x0 && P.x <= x0 + fp.w && P.y >= y0 && P.y <= y0 + fp.h;
      if (inside && (P.moving || A.keys.has('Space'))) {
        const cx = Math.max(0, Math.min(MG.cellsX - 1, Math.floor((P.x - x0) / fp.w * MG.cellsX)));
        const cy = Math.max(0, Math.min(MG.cellsY - 1, Math.floor((P.y - y0) / fp.h * MG.cellsY)));
        MG.cut.add(`${cx},${cy}`);
        // The mower cuts a small cross around the player's strip, so walking
        // naturally covers the pitch instead of requiring pixel-perfect paths.
        if (A.keys.has('Space')) for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const nx = cx + dx, ny = cy + dy; if (nx >= 0 && nx < MG.cellsX && ny >= 0 && ny < MG.cellsY) MG.cut.add(`${nx},${ny}`);
        }
        MG.mower = true;
      } else MG.mower = false;
      if (MG.cut.size >= MG.target) endMG(true, L.win.mowing);
      else if (MG.run >= MG.limit) endMG(false, L.lose.mowing);
    } else updateSkeet(dt);
  });

  /* ------------------------------------------------------------------ drawing: world */
  function drawAnimal(row, o, sx, sy, s) {
    if (!ANIM) return;
    A.shadow(sx, sy, s, 7);
    const f = o.dir === 'down' ? 2 : o.dir === 'up' ? 3 : Math.floor(o.step) % 2;
    const h = 24 * s, w = 110 / 90 * h;
    ctx.save(); ctx.translate(sx, sy + Math.abs(Math.sin(o.step * 2)) * -1.2 * s);
    if (o.dir === 'left') ctx.scale(-1, 1);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(ANIM, f * 110, row * 90, 110, 90, -w / 2, -h + 4 / 90 * h, w, h);
    ctx.restore(); ctx.imageSmoothingEnabled = false;
  }
  function bubble(sx, sy, s, txt, col) {
    ctx.fillStyle = '#10163a'; ctx.fillRect(sx - 4 * s, sy - 5 * s, 8 * s, 9 * s);
    ctx.fillStyle = col; ctx.font = `${8 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(txt, sx, sy);
  }
  function drawFlag(f, sx, sy, s) {
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 5);
    px(-1, -30, 2, 30, '#5a3a1e');
    for (let i = 0; i < 12; i++) px(1 + i, -29 + i * .35 + Math.sin(A.time * 5 + i * .5) * .8, 1, 8 - i * .6, f.color);
    const rec = Q().mg[f.type], label = L.flag[f.type] + (rec && rec.medal ? ' ★' : '');
    ctx.font = `${6 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    const tw = ctx.measureText(label).width + 3 * s;
    ctx.fillStyle = 'rgba(8,12,40,.8)'; ctx.fillRect(sx - tw / 2, sy - 40 * s, tw, 8 * s);
    ctx.fillStyle = rec && rec.medal ? MEDAL_COL[rec.medal] : '#fff'; ctx.fillText(label, sx, sy - 36 * s);
  }
  function drawBooth(side, sx, sy, s) {   // little striped fairground booth that throws the moorhens
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 9);
    px(-9, -14, 18, 14, '#6b4526'); px(-8, -13, 16, 12, '#8a5a2c');
    for (let i = 0; i < 5; i++) px(-10 + i * 4, -19, 4, 5, i % 2 ? '#f5f0e0' : '#d8262c');
    px(-4, -9, 8, 5, '#1b1b1b');
  }
  function drawMoorhen(t, sx, sy, s) {   // tin fairground "kurka wodna" target, flipping as it flies
    const flip = Math.cos(t.spin), w = Math.max(.25, Math.abs(flip));
    ctx.save(); ctx.translate(sx, sy); ctx.scale(w * (flip < 0 ? -1 : 1), 1);
    const px = (x, y, ww, h, c) => { ctx.fillStyle = c; ctx.fillRect(x * s, y * s, ww * s, h * s); };
    px(-5, -2, 9, 5, '#1d2230'); px(-6, -1, 2, 3, '#1d2230'); px(3, -5, 3, 4, '#1d2230');   // body, tail, head
    px(5, -4, 2, 1.5, '#d8262c'); px(4, -6, 1.5, 1.5, '#d8262c');                         // red beak + shield
    px(-6, -1, 1.5, 1.5, '#f5f0e0'); px(-3, 0, 5, 1, '#3a4256'); px(4, -4, 1, 1, '#f5f0e0'); // white under-tail, wing line, eye
    ctx.restore();
  }
  function drawTarget(t, sx, sy, s) {
    const w = 18 * s, h = 24 * s;
    ctx.fillStyle = '#6a4229'; ctx.fillRect(sx - 2 * s, sy - 4 * s, 4 * s, h);
    ctx.fillStyle = '#e7dfcb'; ctx.fillRect(sx - w / 2, sy - h, w, h * .78);
    ctx.fillStyle = '#d8262c'; ctx.beginPath(); ctx.arc(sx, sy - h * .61, 7 * s, 0, 7); ctx.fill();
    ctx.fillStyle = '#f5f0e0'; ctx.beginPath(); ctx.arc(sx, sy - h * .61, 4.5 * s, 0, 7); ctx.fill();
    ctx.fillStyle = '#d8262c'; ctx.beginPath(); ctx.arc(sx, sy - h * .61, 2 * s, 0, 7); ctx.fill();
  }
  function drawMower(sx, sy, s) {
    ctx.fillStyle = '#68bd52'; ctx.fillRect(sx - 8 * s, sy - 10 * s, 16 * s, 9 * s);
    ctx.fillStyle = '#2b542d'; ctx.fillRect(sx - 5 * s, sy - 13 * s, 10 * s, 3 * s);
    ctx.fillStyle = '#24232b'; ctx.fillRect(sx - 7 * s, sy - 1 * s, 4 * s, 3 * s); ctx.fillRect(sx + 3 * s, sy - 1 * s, 4 * s, 3 * s);
  }
  HOOKS.world.push((push, S, inView) => {
    for (const f of FLAGS) if (inView(f.x, f.y) && !(MG && MG.type === f.type)) push(f.y, () => drawFlag(f, ...S(f.x, f.y), A.zoom));
    const host = FLAGS[3];
    if (inView(host.x + 28, host.y - 25)) push(host.y - 25, () => {
      const [sx, sy] = S(host.x + 28, host.y - 25);
      A.drawNpc({ id: host.host, x: host.x + 28, y: host.y - 25 }, sx, sy, A.zoom);
    });
    for (const side of [0, 1]) { const [bx, by] = BOOTH(side, DUCKS_SITE); if (inView(bx, by)) push(by, () => drawBooth(side, ...S(bx, by), A.zoom)); }
    if (inView(RG.x, RG.y)) push(RG.y, () => drawTarget(null, ...S(RG.x, RG.y), A.zoom));
    if (!MG) return;
    const s = A.zoom;
    if (MG.type === 'race') {
      const R = MG.rival, [x, y] = trackPt(R.th);
      if (inView(x, y)) push(y, () => { const [sx, sy] = S(x, y + 6); A.drawNpc({ id: 'damian', x, y, rival: true }, sx, sy - R.z * s, s); });
      if (MG.ghost && MG.phase !== 'count') {
        const i = Math.min(MG.ghost.length - 1, Math.floor(MG.run * 10)), g = MG.ghost[i];
        if (g && inView(g[0], g[1])) push(g[1] - .5, () => A.drawArekPose(...S(g[0], g[1]), s, DIRS[g[2]] || 'down', MG.run * 7, .35));
      }
    } else if (MG.type === 'pig') {
      const p = MG.pig; push(p.y, () => drawAnimal(0, p, ...S(p.x, p.y), s));
    } else if (MG.type === 'dogs') {
      for (const e of MG.eggs) if (!e.got) push(e.y, () => { const [sx, sy] = S(e.x, e.y); ctx.fillStyle = 'rgba(20,34,12,.3)'; ctx.fillRect(sx - 3 * s, sy, 6 * s, 1.5 * s); ctx.fillStyle = '#fbf6e8'; ctx.beginPath(); ctx.ellipse(sx, sy - 4 * s, 3 * s, 4 * s, 0, 0, 7); ctx.fill(); ctx.fillStyle = '#fff'; ctx.fillRect(sx - 1.5 * s, sy - 7 * s, s, s * 1.5); });
      for (const d of MG.dogs) push(d.y, () => {
        const [sx, sy] = S(d.x, d.y); drawAnimal(1, d, sx, sy, s);
        if (d.st === 'windup') bubble(sx, sy - 30 * s, s, '!', '#ff4b3e');
      });
    } else if (MG.type === 'mowing') {
      const fp = MAP.football_pitch, s0 = A.zoom, x0 = fp.cx - fp.w / 2, y0 = fp.cy - fp.h / 2;
      for (const key of MG.cut) { const [cx, cy] = key.split(',').map(Number); const [sx, sy] = S(x0 + (cx + .5) * fp.w / MG.cellsX, y0 + (cy + .5) * fp.h / MG.cellsY); ctx.fillStyle = '#68bd52'; ctx.fillRect(sx - fp.w / MG.cellsX * s0 / 2, sy - fp.h / MG.cellsY * s0 / 2, fp.w / MG.cellsX * s0, fp.h / MG.cellsY * s0); }
      if (MG.mower) { const [sx, sy] = S(P.x, P.y); push(P.y, () => drawMower(sx, sy, s0)); }
    } else {
      for (const t of MG.targets) if (t.alive) push(t.y + 400, () => {
        const [sx, sy] = S(t.x, t.y), [hx, hy] = S(t.x, t.y - t.z);
        ctx.fillStyle = 'rgba(20,34,12,.25)'; ctx.beginPath(); ctx.ellipse(sx, sy, 4 * s, 1.5 * s, 0, 0, 7); ctx.fill();
        if (MG.type === 'skeet') drawTarget(t, hx, hy, s * 1.5); else drawMoorhen(t, hx, hy, s * 1.6);
      });
    }
  });
  HOOKS.minimap.push(dot => { for (const f of FLAGS) dot(f.x, f.y, f.color); });
  HOOKS.questLog.push(lines => {
    for (const f of FLAGS) {
      const r = Q().mg[f.type]; if (!r) continue;
      lines.push([L.log[f.type] + (r.best ? ` ${scoreText(f.type, r.best)}` : '') + (r.medal ? ` ★${L.medal[r.medal]}` : ''), r.medal >= 3]);
    }
  });

  /* ------------------------------------------------------------------ drawing: HUD */
  function drawMedal(cx, cy, r, m) {
    ctx.fillStyle = '#2f6fe0'; ctx.beginPath(); ctx.moveTo(cx - r * .7, cy - r * 2.1); ctx.lineTo(cx - r * .1, cy - r * .6); ctx.lineTo(cx - r * .7, cy - r * .6); ctx.fill();
    ctx.fillStyle = '#d8262c'; ctx.beginPath(); ctx.moveTo(cx + r * .7, cy - r * 2.1); ctx.lineTo(cx + r * .1, cy - r * .6); ctx.lineTo(cx + r * .7, cy - r * .6); ctx.fill();
    ctx.fillStyle = MEDAL_COL[m]; ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,.35)'; ctx.lineWidth = r * .15; ctx.beginPath(); ctx.arc(cx, cy, r * .72, 0, 7); ctx.stroke();
    ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.fillRect(cx - r * .45, cy - r * .5, r * .25, r * .25);
  }
  function drawMG(U, W, H) {
    if (!MG) return;
    ctx.textBaseline = 'middle';
    const rec = Q().mg[MG.type];
    const info = MG.type === 'race' ? `${L.lap} ${MG.lap}/${MG.laps}` : MG.type === 'pig' ? `${L.left} ${Math.max(0, MG.limit - MG.run).toFixed(1)}`
      : MG.type === 'dogs' ? `${L.eggs} ${MG.eggs.filter(e => e.got).length}/6` : MG.type === 'mowing' ? `${MG.cut.size}/${MG.target}` : `${L.hits} ${MG.hits}/15`;
    const bw = Math.min(W * .56, U * 64), bx = (W - bw) / 2;
    ctx.fillStyle = 'rgba(8,12,40,.85)'; ctx.fillRect(bx, U * 1.5, bw, U * 6);
    ctx.font = `${U * 2.3}px Silkscreen`; ctx.textAlign = 'left'; ctx.fillStyle = '#ffd21f'; ctx.fillText(`${L.time} ${fmt(MG.run)}`, bx + U * 2, U * 3.6);
    ctx.textAlign = 'right'; ctx.fillStyle = '#f5f0e0'; ctx.fillText(info, bx + bw - U * 2, U * 3.6);
    ctx.textAlign = 'center'; ctx.font = `${U * 1.3}px Silkscreen`; ctx.fillStyle = '#9aa0c0';
    const nextMedal = [3, 2, 1].find(m => !rec || (rec.medal || 0) < m);
    ctx.fillText([rec && rec.best ? `${L.best} ${scoreText(MG.type, rec.best)}` : '', nextMedal && rec && rec.medal < 3 && rec.medal ? L.next(L.medal[rec.medal + 1]) : '', L.esc].filter(Boolean).join(' · '), W / 2, U * 6.2);
    // status line under the bar
    let status = null;
    if (MG.type === 'race' && MG.phase === 'run' && MG.offTrack) status = [L.offTrack, '#ff6b5e'];
    if (MG.type === 'race' && MG.ghost && MG.phase === 'run' && !status) status = [L.ghost, '#9fd0f0'];
    if (MG.type === 'pig' && MG.tired) status = [L.tired, '#7cff6b'];
    if (['skeet', 'ducks'].includes(MG.type) && MG.reload > 0) status = [L.reload, '#ffd21f'];
    if (MG.type === 'mowing' && MG.phase === 'run') status = [`${MG.cut.size}/${MG.target}`, '#7cff6b'];
    if (status) { ctx.font = `${U * 1.7}px Silkscreen`; ctx.fillStyle = status[1]; ctx.fillText(status[0], W / 2, U * 9.2); }

    if (['skeet', 'ducks'].includes(MG.type) && MG.phase === 'run') drawSkeetHUD(U, W, H);
    if (MG.phase === 'count') {   // three lamps: red, red, yellow... then green GO
      const n = Math.floor(MG.t), k = MG.t % 1, r = U * 3.2, cy = H * .38;
      ctx.fillStyle = 'rgba(8,12,40,.85)'; ctx.fillRect(W / 2 - r * 5, cy - r * 1.6, r * 10, r * 3.2);
      for (let i = 0; i < 3; i++) { ctx.fillStyle = i <= n ? (i < 2 ? '#ff4b3e' : '#ffd21f') : '#2a2f45'; ctx.beginPath(); ctx.arc(W / 2 + (i - 1) * r * 3, cy, r, 0, 7); ctx.fill(); }
      ctx.font = `${U * (6 - k * 2)}px Silkscreen`; ctx.fillStyle = `rgba(255,255,255,${1 - k * .5})`; ctx.fillText(String(3 - n), W / 2, cy + r * 2.8);
    } else if (MG.phase === 'run' && MG.run < .8) {
      ctx.font = `${U * 9}px Silkscreen`; ctx.fillStyle = `rgba(124,255,107,${1 - MG.run / .8})`; ctx.fillText(L.go, W / 2, H * .42);
    } else if (MG.phase === 'win' || MG.phase === 'lose') {
      const pw = Math.min(W - U * 6, U * 64), ph = U * 25, px = (W - pw) / 2, py = H * .26;
      A.box(px, py, pw, ph, U);
      ctx.font = `${U * 3.2}px Silkscreen`; ctx.fillStyle = MG.phase === 'win' ? '#7cff6b' : '#ff6b5e'; ctx.fillText(MG.msg, W / 2, py + U * 4.6);
      if (MG.medal) { drawMedal(W / 2 - pw * .32, py + U * 12.5, U * 3, MG.medal); ctx.font = `${U * 1.8}px Silkscreen`; ctx.fillStyle = MEDAL_COL[MG.medal]; ctx.fillText(L.medal[MG.medal], W / 2 - pw * .32, py + U * 17.4); }
      ctx.font = `${U * 2.2}px Silkscreen`; ctx.fillStyle = '#f5f0e0';
      const main = ['skeet', 'ducks'].includes(MG.type) ? `${L.hits} ${MG.hits}/15` : `${L.time} ${fmt(MG.run)}`;
      ctx.fillText(main, W / 2 + (MG.medal ? pw * .1 : 0), py + U * 9.5);
      ctx.font = `${U * 1.6}px Silkscreen`; ctx.fillStyle = '#c8cee0';
      if (MG.type === 'race' && MG.laps_t.length) ctx.fillText(MG.laps_t.map((t, i) => `${L.lap} ${i + 1}: ${fmt(i ? t - MG.laps_t[i - 1] : t)}`).join('  '), W / 2 + (MG.medal ? pw * .1 : 0), py + U * 12.6);
      if (rec && rec.best) ctx.fillText(`${L.best} ${scoreText(MG.type, rec.best)}${MG.record ? '  ★ ' + L.record : ''}`, W / 2 + (MG.medal ? pw * .1 : 0), py + U * 15.4);
      MG.btn = { mid: W / 2 };
      if (MG.t > .5) {
        ctx.font = `${U * 1.7}px Silkscreen`;
        ctx.fillStyle = Math.floor(A.time * 3) % 2 ? '#ffd21f' : '#fff3b0'; ctx.fillText(L.retry, W / 2 - pw * .24, py + ph - U * 3);
        ctx.fillStyle = '#c8cee0'; ctx.fillText(L.quit, W / 2 + pw * .26, py + ph - U * 3);
      }
    }
    ctx.textAlign = 'left';
  }
  function drawSkeetHUD(U, W, H) {
    const aim = MG.aim; if (!aim) return;
    const [cx, cy] = aim, r = U * 3.2;
    ctx.strokeStyle = MG.reload > 0 ? 'rgba(255,255,255,.4)' : '#ffd21f'; ctx.lineWidth = Math.max(2, U * .3);
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx - r * 1.6, cy); ctx.lineTo(cx - r * .5, cy); ctx.moveTo(cx + r * .5, cy); ctx.lineTo(cx + r * 1.6, cy);
    ctx.moveTo(cx, cy - r * 1.6); ctx.lineTo(cx, cy - r * .5); ctx.moveTo(cx, cy + r * .5); ctx.lineTo(cx, cy + r * 1.6); ctx.stroke();
    if (MG.shotAt && MG.shotAt[2] > 0) { ctx.strokeStyle = `rgba(255,255,255,${MG.shotAt[2] * 4})`; ctx.beginPath(); ctx.arc(MG.shotAt[0], MG.shotAt[1], r * (1.8 - MG.shotAt[2] * 3), 0, 7); ctx.stroke(); }
    if (MG.flash > 0) { ctx.fillStyle = `rgba(255,240,180,${MG.flash * 3})`; ctx.fillRect(0, 0, W, H); }
    // shells: two barrels
    for (let i = 0; i < 2; i++) { ctx.fillStyle = i < MG.barrel ? '#d8262c' : 'rgba(255,255,255,.2)'; ctx.fillRect(W / 2 - U * 3 + i * U * 3.4, H - U * 6, U * 2.2, U * 4); ctx.fillStyle = i < MG.barrel ? '#ffd21f' : 'rgba(255,255,255,.1)'; ctx.fillRect(W / 2 - U * 3 + i * U * 3.4, H - U * 2.8, U * 2.2, U * .9); }
    // 15 result pips
    for (let i = 0; i < 15; i++) { const v = MG.results[i]; ctx.fillStyle = v === 1 ? '#7cff6b' : v === 0 ? '#ff4b3e' : 'rgba(255,255,255,.25)'; ctx.fillRect(W / 2 - U * 15 + i * U * 2, U * 8, U * 1.4, U * 1.4); }
  }
  HOOKS.hud.push(drawMG);

  // test hook
  window.__features = window.__features || {};
  Object.assign(window.__features, { startMG, medalFor });
  Object.defineProperty(window.__features, 'MG', { get: () => MG, configurable: true });
});
