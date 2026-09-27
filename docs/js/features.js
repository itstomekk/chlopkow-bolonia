/* Quiz o Chłopkowie + minigames (race, pig, dogs) for "Arek w Chłopkowie".
   Plugs into game.js through window.ARK.HOOKS (see the comment at HOOKS in game.js).
   State lives in the save object: Q.halina (0 not met / 1 met / 2 quiz finished), Q.quiz {id: 1 correct | 0 wrong},
   Q.mg {race|pig|dogs: {tries, best, won}}. */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK, { HOOKS, P, MAP, ITEMS, ctx } = A;
  const PL = A.LANG === 'pl';
  const Q = () => A.Q;
  if (Q().halina === undefined) Q().halina = 0;
  if (!Q().quiz) Q().quiz = {};
  if (!Q().mg) Q().mg = {};

  /* =================================================================== texts */
  const L = PL ? {
    names: { halina: 'PANI HALINA' },
    halina0: ['Dzień dobry, młody człowieku! Jestem Halina, prowadzę kronikę Chłopkowa.', 'Nasza wieś ma ponad 570 lat historii. Rozstawiłam po okolicy tabliczki z zagadkami — szukaj znaków zapytania!', 'Sprawdźmy najpierw, czy uważałeś na lekcjach historii...'],
    halinaProgress: (n, c, all) => [`Rozwiązane zagadki: ${n} z ${all}. Poprawnie: ${c}.`, 'Tabliczki stoją przy kościele, plebanii, cmentarzu, wiatraku, sklepie, przystankach, rzece, boisku, sadzie, lesie i drodze na wschód.'],
    halinaEnd: (c, all, title) => [`Wszystkie zagadki rozwiązane! Wynik: ${c} na ${all}.`, `Mianuję cię tytułem: ${title}!`, 'Wpiszę cię do kroniki. Ołówkiem, na razie.'],
    halinaAfter: (c, all, title) => [`${title} — ${c}/${all}. Kronika pamięta!`],
    titles: [[13, 'HONOROWY KRONIKARZ CHŁOPKOWA'], [10, 'ZNAWCA CHŁOPKOWA'], [6, 'TURYSTA Z AMBICJAMI'], [0, 'PRZYJEZDNY Z MIASTA']],
    boardLocked: ['Tabliczka z zagadką. Najpierw porozmawiaj z panią Haliną, kronikarką — stoi niedaleko sklepu.'],
    boardDone: ok => [ok ? 'Tę zagadkę już rozwiązałeś — poprawnie!' : 'Tę zagadkę już rozwiązałeś... niestety źle.'],
    quizTitle: 'ZAGADKA', correct: 'DOBRZE!', wrong: 'NIESTETY...', answerWas: 'Poprawna odpowiedź', cont: 'SPACJA — DALEJ', pick: 'STRZAŁKI / 1-4 — WYBÓR · SPACJA — ODPOWIEDZ',
    quizLog: (c, n, all) => `Quiz o Chłopkowie ★${c} (${n}/${all})`,
    // minigames
    flagRace: 'TOR', flagPig: 'ŚWINKA', flagDogs: 'PSY',
    raceIntro: ['Damian: „Wyścig! Dwa okrążenia, kto pierwszy na mecie. Bele siana przeskakujesz — SPACJA albo X!”', 'Damian: „Trzymaj się toru, skróty przez trawę się nie liczą. Gotowy?”'],
    pigIntro: ['Dziadek Zbyszek: „Świnka Pepa znowu wyszła z chlewika! Złap ją w 30 sekund, zanim wlezie babci w ogródek.”'],
    dogsIntro: ['Marcin: „Na pastwisku kury pana Stefana zniosły 6 jajek, ale pilnują ich psy.”', 'Marcin: „Zbierz wszystkie jajka i nie daj się złapać. Psy da się przeskoczyć!”'],
    go: 'START!', lap: 'OKRĄŻENIE', time: 'CZAS', best: 'REKORD', eggs: 'JAJKA', left: 'ZOSTAŁO',
    hit: 'TRAFIONO',
    raceWin: 'WYGRAŁEŚ Z DAMIANEM!', raceLose: 'DAMIAN BYŁ SZYBSZY...', pigWin: 'MASZ PEPĘ!', pigLose: 'PEPA UCIEKŁA...',
    dogsWin: 'WSZYSTKIE JAJKA ZEBRANE!', dogsLose: 'PIES CIĘ DOPADŁ!', dogsOut: 'UCIEKŁEŚ Z PASTWISKA...',
    skeetIntro: ['Marcin: „Na strzelnicy lecą kurki wodne. Przeładowujesz dwulufę — SPACJA. Celuj myszką/dotykiem, strzelaj SPACJĄ.”', 'Marcin: „Traf 10 z 15. Muszka bywa zdradliwa, ale masz dwie lufy.”'],
    skeetWin: 'STRZELNY MISTRZ!', skeetLose: 'MUSZKA WYGRALA...',
    flagSkeet: 'STRZELNICA',
    again: 'SPACJA — ZAMKNIJ', esc: 'ESC — PRZERWIJ',
    mgLog: { race: 'Wyścig z Damianem', pig: 'Złap świnkę Pepę', dogs: 'Jajka i psy' },
  } : {
    names: { halina: 'MRS HALINA' },
    halina0: ["Good day, young man! I'm Halina, I keep the chronicle of Chłopków.", 'Our village has over 570 years of history. I put riddle signboards all around — look for the question marks!', "First, let's see if you paid attention in history class..."],
    halinaProgress: (n, c, all) => [`Riddles solved: ${n} of ${all}. Correct: ${c}.`, 'The signboards stand by the church, rectory, cemetery, windmill, shop, bus stops, river, pitch, orchard, woods and the road east.'],
    halinaEnd: (c, all, title) => [`All riddles solved! Score: ${c} of ${all}.`, `I hereby name you: ${title}!`, "I'll write you into the chronicle. In pencil, for now."],
    halinaAfter: (c, all, title) => [`${title} — ${c}/${all}. The chronicle remembers!`],
    titles: [[13, 'HONORARY CHRONICLER OF CHŁOPKÓW'], [10, 'CHŁOPKÓW EXPERT'], [6, 'AMBITIOUS TOURIST'], [0, 'VISITOR FROM THE CITY']],
    boardLocked: ['A riddle signboard. Talk to Mrs Halina, the village chronicler, first — she stands near the shop.'],
    boardDone: ok => [ok ? 'You already solved this one — correctly!' : 'You already answered this one... wrongly.'],
    quizTitle: 'RIDDLE', correct: 'CORRECT!', wrong: 'NOT QUITE...', answerWas: 'The answer', cont: 'SPACE — CONTINUE', pick: 'ARROWS / 1-4 — CHOOSE · SPACE — ANSWER',
    quizLog: (c, n, all) => `Chłopków quiz ★${c} (${n}/${all})`,
    flagRace: 'TRACK', flagPig: 'PIGGY', flagDogs: 'DOGS',
    raceIntro: ['Damian: "Race! Two laps, first to the finish wins. Jump the hay bales — SPACE or X!"', 'Damian: "Stay on the track, shortcuts across the grass don\'t count. Ready?"'],
    pigIntro: ['Grandpa Zbyszek: "Pepa the piglet escaped again! Catch her in 30 seconds before she gets into Grandma\'s garden."'],
    dogsIntro: ['Marcin: "Mr Stefan\'s hens laid 6 eggs on the meadow, but his dogs guard them."', 'Marcin: "Collect every egg and don\'t get caught. You can jump over the dogs!"'],
    go: 'GO!', lap: 'LAP', time: 'TIME', best: 'BEST', eggs: 'EGGS', left: 'LEFT',
    hit: 'HIT',
    raceWin: 'YOU BEAT DAMIAN!', raceLose: 'DAMIAN WAS FASTER...', pigWin: 'GOT PEPA!', pigLose: 'PEPA GOT AWAY...',
    dogsWin: 'ALL EGGS COLLECTED!', dogsLose: 'A DOG GOT YOU!', dogsOut: 'YOU LEFT THE MEADOW...',
    skeetIntro: ['Marcin: "Clay pigeons are flying at the range. Load the double barrel — SPACE. Aim with mouse/touch, shoot with SPACE."', 'Marcin: "Hit 10 out of 15. The clay can be tricky, but you have two barrels."'],
    skeetWin: 'SHARPSHOOTER!', skeetLose: 'THE CLAY WON...',
    flagSkeet: 'RANGE',
    again: 'SPACE — CLOSE', esc: 'ESC — QUIT',
    mgLog: { race: 'Race against Damian', pig: 'Catch Pepa the piglet', dogs: 'Eggs and dogs' },
  };
  const QZ_ALL = window.QUIZ.length;
  const qById = id => window.QUIZ.find(q => q.id === id);
  const answered = () => Object.keys(Q().quiz).length;
  const correctN = () => Object.values(Q().quiz).filter(v => v === 1).length;
  const titleFor = c => L.titles.find(([min]) => c >= min)[1];

  /* =================================================================== quiz modal */
  let QZ = null; // {q, order:[origIdx...], sel, phase:'ask'|'done', pick, rects:[], t}
  function openQuiz(id) {
    const q = qById(id), order = [0, 1, 2, 3].sort(() => Math.random() - .5);
    QZ = { q, order, sel: 0, phase: 'ask', pick: -1, rects: [], t: 0 };
  }
  function answer(slot) {
    if (!QZ || QZ.phase !== 'ask') return;
    QZ.sel = slot; QZ.pick = QZ.order[slot]; QZ.phase = 'done'; QZ.t = 0;
    const ok = QZ.pick === QZ.q.ok;
    Q().quiz[QZ.q.id] = ok ? 1 : 0; A.save();
    if (ok) { A.celebrate(); A.popToast('+★'); } else A.popToast(PL ? 'PUDŁO' : 'MISS');
  }
  function closeQuiz() {
    QZ = null;
    if (answered() === QZ_ALL && Q().halina === 1) A.popToast(PL ? 'WRÓĆ DO PANI HALINY' : 'GO BACK TO MRS HALINA');
  }
  HOOKS.key.push(e => {
    if (!QZ) return false;
    if (QZ.phase === 'ask') {
      const m = { Digit1: 0, Digit2: 1, Digit3: 2, Digit4: 3, Numpad1: 0, Numpad2: 1, Numpad3: 2, Numpad4: 3 };
      if (e.code in m) answer(m[e.code]);
      else if (e.code === 'ArrowLeft' || e.code === 'ArrowRight' || e.code === 'KeyA' || e.code === 'KeyD') QZ.sel ^= 1;
      else if (e.code === 'ArrowUp' || e.code === 'ArrowDown' || e.code === 'KeyW' || e.code === 'KeyS') QZ.sel ^= 2;
      else if (e.code === 'Space' || e.code === 'Enter') answer(QZ.sel);
    } else if ((e.code === 'Space' || e.code === 'Enter' || e.code === 'Escape') && QZ.t > .25) closeQuiz();
    return true;
  });
  HOOKS.pointer.push((px, py) => {
    if (!QZ) return false;
    if (QZ.phase === 'ask') { const i = QZ.rects.findIndex(r => px > r[0] && px < r[0] + r[2] && py > r[1] && py < r[1] + r[3]); if (i >= 0) answer(i); }
    else if (QZ.t > .25) closeQuiz();
    return true;
  });
  HOOKS.blocksPlayer.push(() => !!QZ);
  if (HOOKS.busy) HOOKS.busy.push(() => !!QZ);
  HOOKS.update.push(dt => { if (QZ) QZ.t += dt; });

  function drawQuiz(U, W, H) {
    if (!QZ) return;
    const t = QZ.q[PL ? 'pl' : 'en'];
    ctx.fillStyle = 'rgba(4,6,20,0.62)'; ctx.fillRect(0, 0, W, H);
    const bw = Math.min(W - U * 4, U * 96), bx = (W - bw) / 2;
    ctx.font = `${U * 2.1}px Silkscreen`;
    const qLines = A.wrapText(t.q.toUpperCase(), bw - U * 6);
    const factLines = QZ.phase === 'done' ? A.wrapText(t.fact.toUpperCase(), bw - U * 6) : [];
    const ansH = U * 7.2, gap = U * 1.2;
    const bh = U * 6 + qLines.length * U * 3 + ansH * 2 + gap * 3 + (QZ.phase === 'done' ? U * 5 + factLines.length * U * 2.8 : U * 3);
    const by = Math.max(U, (H - bh) / 2);
    A.box(bx, by, bw, bh, U);
    ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
    ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 2.3}px Silkscreen`;
    ctx.fillText(`${L.quizTitle} ${Object.keys(Q().quiz).length + (QZ.phase === 'ask' ? 1 : 0)}/${QZ_ALL}`, bx + U * 3, by + U * 3.4);
    ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.1}px Silkscreen`;
    qLines.forEach((l, i) => ctx.fillText(l, bx + U * 3, by + U * (7 + i * 3)));
    const ay = by + U * 6 + qLines.length * U * 3 + gap;
    const aw = (bw - U * 6 - gap) / 2;
    QZ.rects = [];
    for (let slot = 0; slot < 4; slot++) {
      const ox = bx + U * 3 + (slot & 1) * (aw + gap), oy = ay + (slot >> 1) * (ansH + gap);
      QZ.rects.push([ox, oy, aw, ansH]);
      const orig = QZ.order[slot], isOk = orig === QZ.q.ok, picked = QZ.phase === 'done' && orig === QZ.pick;
      let bg = 'rgba(255,255,255,0.07)', fg = '#f5f0e0';
      if (QZ.phase === 'ask' && slot === QZ.sel) { bg = 'rgba(255,210,31,0.22)'; fg = '#ffd21f'; }
      if (QZ.phase === 'done' && isOk) { bg = 'rgba(124,255,107,0.25)'; fg = '#b8ffae'; }
      if (picked && !isOk) { bg = 'rgba(255,75,62,0.3)'; fg = '#ffb3ab'; }
      ctx.fillStyle = bg; ctx.fillRect(ox, oy, aw, ansH);
      ctx.strokeStyle = fg; ctx.lineWidth = Math.max(1, U * .2); ctx.strokeRect(ox, oy, aw, ansH);
      ctx.fillStyle = fg; ctx.font = `${U * 2}px Silkscreen`;
      ctx.fillText('ABCD'[slot] + ')', ox + U * 1.2, oy + ansH / 2);
      ctx.font = `${U * 1.75}px Silkscreen`;
      const al = A.wrapText(t.a[orig].toUpperCase(), aw - U * 6).slice(0, 2);
      al.forEach((l, i) => ctx.fillText(l, ox + U * 4.4, oy + ansH / 2 + (i - (al.length - 1) / 2) * U * 2.3));
    }
    const fy = ay + ansH * 2 + gap * 2;
    if (QZ.phase === 'ask') {
      ctx.fillStyle = '#9aa0c0'; ctx.font = `${U * 1.4}px Silkscreen`; ctx.textAlign = 'center';
      ctx.fillText(matchMedia('(pointer:coarse)').matches ? '' : L.pick, W / 2, fy + U * 1.4);
    } else {
      const ok = QZ.pick === QZ.q.ok;
      ctx.fillStyle = ok ? '#7cff6b' : '#ff6b5e'; ctx.font = `${U * 2.4}px Silkscreen`;
      ctx.fillText(ok ? L.correct : L.wrong, bx + U * 3, fy + U * 1.8);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 1.9}px Silkscreen`;
      factLines.forEach((l, i) => ctx.fillText(l, bx + U * 3, fy + U * (4.8 + i * 2.8)));
      if (Math.floor(A.time * 3) % 2) { ctx.fillStyle = '#ffd21f'; ctx.textAlign = 'right'; ctx.font = `${U * 1.5}px Silkscreen`; ctx.fillText(L.cont, bx + bw - U * 3, by + bh - U * 2.2); }
    }
    ctx.textAlign = 'left';
  }

  /* =================================================================== Pani Halina + signboards */
  HOOKS.npcTalk.push(id => {
    if (id !== 'halina') return false;
    const q = Q();
    if (q.halina === 0) { q.halina = 1; A.save(); A.say('halina', L.halina0, () => openQuiz('king')); }
    else if (q.halina === 1 && q.quiz.king === undefined) openQuiz('king');
    else if (q.halina === 1 && answered() >= QZ_ALL) { q.halina = 2; A.save(); A.say('halina', L.halinaEnd(correctN(), QZ_ALL, titleFor(correctN())), () => A.celebrate()); }
    else if (q.halina === 1) A.say('halina', L.halinaProgress(answered(), correctN(), QZ_ALL));
    else A.say('halina', L.halinaAfter(correctN(), QZ_ALL, titleFor(correctN())));
    return true;
  });
  const spotQuestion = spot => window.QUIZ.find(q => q.spot === spot);
  HOOKS.near.push(() => (MG ? [] : ITEMS.boards.map(b => ({
    x: b.x, y: b.y, r: 30,
    onInteract() {
      const q = spotQuestion(b.spot); if (!q) return;
      if (Q().halina === 0) A.say('arek', L.boardLocked);
      else if (Q().quiz[q.id] !== undefined) {
        const t = q[PL ? 'pl' : 'en'];
        A.say('arek', [...L.boardDone(Q().quiz[q.id] === 1), `${L.answerWas}: ${t.a[q.ok]}.`]);
      } else openQuiz(q.id);
    },
  }))));
  function drawBoard(b, sx, sy, s) {
    const q = spotQuestion(b.spot), st = q ? Q().quiz[q.id] : undefined;
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 6);
    px(-1, -16, 2, 16, '#6b4526');                         // post
    px(-8, -24, 16, 11, '#3f2814'); px(-7, -23, 14, 9, '#c89a5c'); // board
    px(-7, -23, 14, 1, '#e0b878');
    const bob = Math.floor(A.time * 2) % 2;
    if (st === undefined) {                                // pixel "?"
      const c = Q().halina ? '#d8262c' : '#8a5a2c';
      px(-2, -22 + bob * 0, 4, 1, c); px(1, -21, 1, 2, c); px(-1, -19, 2, 1, c); px(-1, -18, 1, 1, c); px(-1, -16, 1, 1, c);
    } else if (st === 1) {                                 // tick
      px(-3, -18, 1, 1, '#2a8a2a'); px(-2, -17, 1, 1, '#2a8a2a'); px(-1, -18, 1, 1, '#2a8a2a'); px(0, -19, 1, 1, '#2a8a2a'); px(1, -20, 1, 1, '#2a8a2a'); px(2, -21, 1, 1, '#2a8a2a');
    } else {                                               // cross
      for (let k = -2; k <= 2; k++) { px(k, -18 + k, 1, 1, '#b8261e'); px(k, -18 - k, 1, 1, '#b8261e'); }
    }
  }
  HOOKS.world.push((push, S, inView) => {
    for (const b of ITEMS.boards) if (inView(b.x, b.y)) push(b.y, () => drawBoard(b, ...S(b.x, b.y), A.zoom));
  });
  HOOKS.minimap.push(dot => { if (Q().halina) for (const b of ITEMS.boards) { const q = spotQuestion(b.spot); if (q && Q().quiz[q.id] === undefined) dot(b.x, b.y, '#ffd21f'); } });
  HOOKS.questLog.push(lines => {
    if (Q().halina) lines.push([L.quizLog(correctN(), answered(), QZ_ALL), Q().halina === 2]);
    for (const k of ['race', 'pig', 'dogs']) if (Q().mg[k]) lines.push([L.mgLog[k] + (Q().mg[k].best ? ` ${fmt(Q().mg[k].best)}` : ''), !!Q().mg[k].won]);
  });

  /* =================================================================== minigames */
  let ANIM = null; A.load('img/animals.png').then(i => { ANIM = i; });
  const fmt = s => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`;
  const TR = MAP.track, CO = MAP.corral, ME = MAP.meadow;
  const trackPt = th => [TR.cx + Math.cos(th) * TR.rx, TR.cy + Math.sin(th) * TR.ry];
  const onTrack = (x, y) => { const r = Math.hypot((x - TR.cx) / TR.rx, (y - TR.cy) / TR.ry); return Math.abs(r - 1) < (TR.w / 2 + 10) / ((TR.rx + TR.ry) / 2); };
  const angOf = (x, y) => { let a = Math.atan2((y - TR.cy) / TR.ry, (x - TR.cx) / TR.rx); if (a < 0) a += Math.PI * 2; return a; };
  const FLAGS = [
    { type: 'race', x: TR.cx - 30, y: TR.cy + TR.ry + TR.w / 2 + 22, color: '#d8262c', label: () => L.flagRace },
    { type: 'pig', x: CO.cx - CO.r - 26, y: CO.cy + 6, color: '#ff8fb8', label: () => L.flagPig },
    { type: 'dogs', x: ME.x0 - 18, y: (ME.y0 + ME.y1) / 2, color: '#2f6fe0', label: () => L.flagDogs },
    { type: 'skeet', x: 900, y: 1050, color: '#d8a03a', label: () => L.flagSkeet },
  ];
  let MG = null;

  function startMG(type) {
    const q = Q(); q.mg[type] = q.mg[type] || { tries: 0, best: 0, won: false }; q.mg[type].tries++; A.save();
    MG = { type, phase: 'count', t: 0, run: 0 };
    if (type === 'race') {
      A.teleport(TR.cx + 20, TR.cy + TR.ry); P.dir = 'left';
      // checkpoints every 22.5°, racing clockwise on screen starting at the bottom (90°)
      Object.assign(MG, { cp: 0, lap: 1, laps: 2, rival: { th: Math.PI / 2 + .02, z: 0, done: false }, cps: 16 });
    } else if (type === 'pig') {
      A.teleport(CO.cx - CO.r - 10, CO.cy); P.dir = 'right';
      MG.pig = { x: CO.cx + 20, y: CO.cy, vx: 0, vy: 0, dir: 'left', step: 0, wander: 0 }; MG.limit = 30;
    } else {
      A.teleport(ME.x0 + 20, (ME.y0 + ME.y1) / 2); P.dir = 'right';
      const eggs = [];
      while (eggs.length < 6) {
        const x = ME.x0 + 60 + Math.random() * (ME.x1 - ME.x0 - 100), y = ME.y0 + 30 + Math.random() * (ME.y1 - ME.y0 - 50);
        if (!A.blocked(x, y) && eggs.every(e => Math.hypot(e.x - x, e.y - y) > 60)) eggs.push({ x, y, got: false });
      }
      const dogs = [0, 1, 2].map(i => ({ x: ME.x1 - 30, y: ME.y0 + 50 + i * (ME.y1 - ME.y0 - 100) / 2, dir: 'left', step: 0, sp: 118 + i * 8, t: Math.random() * 9 }));
      Object.assign(MG, { eggs, dogs });
    }
  }
  function endMG(win, msg) {
    MG.phase = win ? 'win' : 'lose'; MG.msg = msg; MG.t = 0;
    const rec = Q().mg[MG.type];
    if (win) { rec.won = true; if (!rec.best || MG.run < rec.best) { rec.best = MG.run; MG.record = true; } A.celebrate(); }
    A.save();
  }
  HOOKS.near.push(() => (MG ? [] : FLAGS.map(f => ({
    x: f.x, y: f.y, r: 30,
    onInteract() {
      const intro = { race: L.raceIntro, pig: L.pigIntro, dogs: L.dogsIntro }[f.type];
      A.say({ race: 'damian', pig: 'grandpa', dogs: 'marcin' }[f.type], intro, () => startMG(f.type));
    },
  }))));
  HOOKS.blocksPlayer.push(() => !!MG && MG.phase !== 'run');
  if (HOOKS.busy) HOOKS.busy.push(() => !!MG);
  HOOKS.key.push(e => {
    if (!MG) return false;
    if (e.code === 'Escape') { MG = null; return true; }
    if ((MG.phase === 'win' || MG.phase === 'lose') && (e.code === 'Space' || e.code === 'Enter')) { if (MG.t > .6) MG = null; return true; }
    if (MG.type === 'skeet' && MG.phase === 'run' && e.code === 'Space') {
      const sk = MG.skeet;
      if (sk.reload > 0) return true;
      // find nearest pigeon to crosshair
      const cx = A.keys.has('PointerX') ? A.keys.PointerX : W / 2;
      const cy = A.keys.has('PointerY') ? A.keys.PointerY : H * .5;
      let best = null, bd = 1e9;
      for (const p of sk.pigeons) if (p.alive) {
        const [sx, sy] = S(p.x, p.y);
        const d = Math.hypot(sx - cx, sy - cy);
        if (d < bd && d < 60) { bd = d; best = p; }
      }
      if (best) { best.alive = false; sk.hit++; A.burst(best.x, best.y, ['#ffd21f', '#fff', '#c8c4b8']); A.celebrate(); }
      sk.barrel = 1 - sk.barrel;
      if (sk.barrel === 0) sk.reload = 1.2;
      return true;
    }
    return false;                        // let Space/X reach the jump handler during the run
  });
  HOOKS.pointer.push(() => { if (MG && (MG.phase === 'win' || MG.phase === 'lose') && MG.t > .6) { MG = null; return true; } return false; });

  function steer(o, tx, ty, sp, dt, air = false) {  // move an animal toward (tx,ty) with simple obstacle sliding
    let dx = tx - o.x, dy = ty - o.y; const d = Math.hypot(dx, dy) || 1; dx /= d; dy /= d;
    for (const rot of [0, .6, -.6, 1.2, -1.2, 1.8, -1.8]) {
      const c = Math.cos(rot), s = Math.sin(rot), ux = dx * c - dy * s, uy = dx * s + dy * c;
      const nx = o.x + ux * sp * dt, ny = o.y + uy * sp * dt;
      if (!A.blocked(nx, ny, air)) { o.x = nx; o.y = ny; o.dir = Math.abs(ux) > Math.abs(uy) ? (ux < 0 ? 'left' : 'right') : (uy < 0 ? 'up' : 'down'); o.step += dt * 9; return true; }
    }
    return false;
  }
  HOOKS.update.push(dt => {
    if (!MG) return;
    MG.t += dt;
    if (MG.phase === 'count') { if (MG.t >= 3) { MG.phase = 'run'; MG.t = 0; } return; }
    if (MG.phase !== 'run') return;
    MG.run += dt;
    if (MG.type === 'race') {
      // player progress through checkpoints
      const step = Math.PI * 2 / MG.cps, next = (Math.PI / 2 + (MG.cp + 1) * step) % (Math.PI * 2);
      const a = angOf(P.x, P.y); let diff = Math.abs(a - next); diff = Math.min(diff, Math.PI * 2 - diff);
      if (diff < step * .5 && onTrack(P.x, P.y)) {
        MG.cp++;
        if (MG.cp === MG.cps) { MG.cp = 0; if (MG.lap === MG.laps) { endMG(true, L.raceWin); return; } MG.lap++; A.popToast(`${L.lap} ${MG.lap}/${MG.laps}`); }
      }
      // Damian: steady pace with a little wobble, hops over the bale walls at 200° and 330°
      const R = MG.rival, total = Math.PI * 2 * MG.laps, lapT = 8.1;
      R.th += (Math.PI * 2 / lapT) * (1 + Math.sin(MG.run * 1.3) * .08) * dt;
      const deg = ((R.th * 180 / Math.PI) % 360 + 360) % 360;
      R.z = [200, 330].some(b => Math.abs(deg - b) < 9) ? Math.sin((1 - Math.abs(deg - [200, 330].find(b => Math.abs(deg - b) < 9)) / 9) * Math.PI / 2) * 14 : 0;
      if (R.th - Math.PI / 2 >= total) endMG(false, L.raceLose);
    } else if (MG.type === 'pig') {
      const pig = MG.pig, d = Math.hypot(P.x - pig.x, P.y - pig.y);
      if (d < 16 && !P.air) { endMG(true, L.pigWin); return; }
      if (d < 120) {   // flee: away from Arek, with a sideways juke; drift back toward the corral centre
        const fx = pig.x - P.x, fy = pig.y - P.y, side = Math.sin(MG.run * 2.2) * .7;
        const cx = (CO.cx - pig.x) * .004, cy = (CO.cy - pig.y) * .004;
        steer(pig, pig.x + fx / d - fy / d * side + cx * 60, pig.y + fy / d + fx / d * side + cy * 60, 158, dt);
      } else {
        pig.wander -= dt; if (pig.wander <= 0) { pig.wander = 1 + Math.random(); pig.tx = CO.cx + (Math.random() - .5) * CO.r; pig.ty = CO.cy + (Math.random() - .5) * CO.r * .7; }
        steer(pig, pig.tx, pig.ty, 45, dt);
      }
      if (MG.run >= MG.limit) endMG(false, L.pigLose);
    } else {
      for (const e of MG.eggs) if (!e.got && Math.hypot(P.x - e.x, P.y - e.y) < 14) { e.got = true; A.burst(e.x, e.y - 6, ['#fff', '#ffd21f']); }
      const left = MG.eggs.filter(e => !e.got).length;
      if (!left) { endMG(true, L.dogsWin); return; }
      if (P.x < ME.x0 - 40 || P.x > ME.x1 + 40 || P.y < ME.y0 - 40 || P.y > ME.y1 + 40) { endMG(false, L.dogsOut); return; }
      for (const dg of MG.dogs) {
        dg.t += dt;
        const d = Math.hypot(P.x - dg.x, P.y - dg.y);
        if (d < 190) steer(dg, P.x, P.y, dg.sp * (dg.t % 4 < .6 ? .3 : 1), dt);   // short pauses to sniff: gives you a chance
        else steer(dg, ME.x1 - 40 - Math.sin(dg.t * .5) * 120, dg.y + Math.cos(dg.t) * 30, 50, dt);
        if (d < 13 && P.z < 6) { endMG(false, L.dogsLose); return; }
      }
    }
  });

  function drawAnimal(row, o, sx, sy, s, z = 0) {
    if (!ANIM) return;
    A.shadow(sx, sy, s, 7);
    const f = o.dir === 'down' ? 2 : o.dir === 'up' ? 3 : Math.floor(o.step) % 2;
    const h = 24 * s, w = 110 / 90 * h;
    ctx.save(); ctx.translate(sx, sy - z * s + Math.abs(Math.sin(o.step * 2)) * -1.2 * s);
    if (o.dir === 'left') ctx.scale(-1, 1);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(ANIM, f * 110, row * 90, 110, 90, -w / 2, -h + 4 / 90 * h, w, h);
    ctx.restore(); ctx.imageSmoothingEnabled = false;
  }
  function drawFlag(f, sx, sy, s) {
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 5);
    px(-1, -30, 2, 30, '#5a3a1e');
    const wave = Math.sin(A.time * 5) * 1.5;
    for (let i = 0; i < 12; i++) px(1 + i, -29 + i * .35 + Math.sin(A.time * 5 + i * .5) * .8, 1, 8 - i * .6, f.color);
    ctx.font = `${6 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    const tw = ctx.measureText(f.label()).width + 3 * s;
    ctx.fillStyle = 'rgba(8,12,40,.8)'; ctx.fillRect(sx - tw / 2, sy - (40 + wave * 0) * s, tw, 8 * s);
    ctx.fillStyle = '#fff'; ctx.fillText(f.label(), sx, sy - 36 * s);
  }
  HOOKS.world.push((push, S, inView) => {
    for (const f of FLAGS) if (inView(f.x, f.y)) push(f.y, () => drawFlag(f, ...S(f.x, f.y), A.zoom));
    if (!MG) return;
    if (MG.type === 'race') {
      const R = MG.rival, [x, y] = trackPt(R.th + .02 * 0);
      if (inView(x, y)) push(y, () => { const [sx, sy] = S(x, y + 6); A.drawNpc({ id: 'damian', x, y, rival: true }, sx, sy - R.z * A.zoom, A.zoom); });
    } else if (MG.type === 'pig') {
      const p = MG.pig; push(p.y, () => drawAnimal(0, p, ...S(p.x, p.y), A.zoom));
    } else {
      for (const e of MG.eggs) if (!e.got) push(e.y, () => { const [sx, sy] = S(e.x, e.y), s = A.zoom; ctx.fillStyle = 'rgba(20,34,12,.3)'; ctx.fillRect(sx - 3 * s, sy, 6 * s, 1.5 * s); ctx.fillStyle = '#fbf6e8'; ctx.beginPath(); ctx.ellipse(sx, sy - 4 * s, 3 * s, 4 * s, 0, 0, 7); ctx.fill(); ctx.fillStyle = '#fff'; ctx.fillRect(sx - 1.5 * s, sy - 7 * s, s, s * 1.5); });
      for (const d of MG.dogs) push(d.y, () => drawAnimal(1, d, ...S(d.x, d.y), A.zoom));
    }
  });
  HOOKS.minimap.push(dot => { for (const f of FLAGS) dot(f.x, f.y, f.color); });

  function drawMG(U, W, H) {
    if (!MG) return;
    ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
    // top bar
    const info = MG.type === 'race' ? `${L.lap} ${MG.lap}/${MG.laps}` : MG.type === 'pig' ? `${L.left} ${Math.max(0, MG.limit - MG.run).toFixed(1)}` : MG.type === 'skeet' ? `${L.hit || 'TRAFIONO'} ${MG.skeet.hit}/${MG.skeet.total} ${L.left || 'ZOSTAŁO'} ${MG.skeet.total - MG.skeet.spawned + MG.skeet.pigeons.length}` : `${L.eggs} ${MG.eggs.filter(e => e.got).length}/6`;
    const rec = Q().mg[MG.type];
    const bw = Math.min(W * .5, U * 60), bx = (W - bw) / 2;
    ctx.fillStyle = 'rgba(8,12,40,.85)'; ctx.fillRect(bx, U * 1.5, bw, U * 6);
    ctx.font = `${U * 2.3}px Silkscreen`; ctx.fillStyle = '#ffd21f'; ctx.textAlign = 'left'; ctx.fillText(`${L.time} ${fmt(MG.run)}`, bx + U * 2, U * 3.6);
    ctx.fillStyle = '#f5f0e0'; ctx.textAlign = 'right'; ctx.fillText(info, bx + bw - U * 2, U * 3.6); ctx.textAlign = 'center';
    ctx.font = `${U * 1.3}px Silkscreen`; ctx.fillStyle = '#9aa0c0';
    ctx.fillText(`${rec && rec.best ? L.best + ' ' + fmt(rec.best) + ' · ' : ''}${L.esc}`, W / 2, U * 6.2);
    if (MG.phase === 'count') {
      const n = 3 - Math.floor(MG.t), k = MG.t % 1;
      ctx.font = `${U * (14 - k * 5)}px Silkscreen`; ctx.fillStyle = `rgba(255,210,31,${1 - k * .6})`; ctx.fillText(String(n), W / 2, H * .42);
    } else if (MG.phase === 'run' && MG.run < .8) {
      ctx.font = `${U * 9}px Silkscreen`; ctx.fillStyle = `rgba(124,255,107,${1 - MG.run / .8})`; ctx.fillText(L.go, W / 2, H * .42);
    } else if (MG.phase === 'run' && MG.type === 'skeet') {
      // crosshair
      const cx = A.keys.has('PointerX') ? A.keys.PointerX : W / 2;
      const cy = A.keys.has('PointerY') ? A.keys.PointerY : H * .5;
      ctx.strokeStyle = '#ffd21f'; ctx.lineWidth = Math.max(2, U * .3);
      const rs = U * 8; ctx.beginPath(); ctx.moveTo(cx - rs, cy); ctx.lineTo(cx + rs, cy); ctx.moveTo(cx, cy - rs); ctx.lineTo(cx, cy + rs); ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, rs * 1.3, 0, 7); ctx.stroke();
      // barrel indicator
      const sk = MG.skeet;
      ctx.font = `${U * 1.6}px Silkscreen`; ctx.fillStyle = sk.barrel === 0 ? '#ffd21f' : '#f5f0e0';
      ctx.fillText(sk.reload > 0 ? `PRZEŁADOWUJESZ...` : `LUFA ${sk.barrel + 1}/2`, W / 2, H * .15);
    } else if (MG.phase === 'win' || MG.phase === 'lose') {
      const pw = Math.min(W - U * 6, U * 60), ph = U * 18, px = (W - pw) / 2, py = H * .32;
      A.box(px, py, pw, ph, U);
      ctx.font = `${U * 3.4}px Silkscreen`; ctx.fillStyle = MG.phase === 'win' ? '#7cff6b' : '#ff6b5e'; ctx.fillText(MG.msg, W / 2, py + U * 5);
      ctx.font = `${U * 2.2}px Silkscreen`; ctx.fillStyle = '#f5f0e0';
      ctx.fillText(`${L.time} ${fmt(MG.run)}${MG.record ? '  ★ ' + (PL ? 'NOWY REKORD' : 'NEW RECORD') : ''}`, W / 2, py + U * 10);
      if (MG.t > .6 && Math.floor(A.time * 3) % 2) { ctx.font = `${U * 1.6}px Silkscreen`; ctx.fillStyle = '#ffd21f'; ctx.fillText(L.again, W / 2, py + ph - U * 3); }
    }
    ctx.textAlign = 'left';
  }
  HOOKS.hud.push((U, W, H) => { drawMG(U, W, H); drawQuiz(U, W, H); });

  // test hook
  window.__features = { get MG() { return MG; }, get QZ() { return QZ; }, startMG, openQuiz, answer };
});
