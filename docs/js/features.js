/* Quiz o Chłopkowie for "Arek w Chłopkowie": Babcia Irenka, the question markers (village, wayside shrines, jazz barn) and the ABCD quiz modal.
   Plugs into game.js through window.ARK.HOOKS (see the comment at HOOKS in game.js). Minigames live in minigames.js.
   State in the save object: Q.halina (0 not met / 1 met / 2 quiz finished), Q.quiz {id: 1 correct | 0 wrong}. */
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
    names: { halina: 'BABCIA IRENKA' },
    halina0: ['Dzień dobry, młody człowieku! Jestem Irenka, prowadzę kronikę Chłopkowa.', 'Rozstawiłam po okolicy zagadki — szukaj znaków zapytania!', 'Sprawdźmy najpierw, czy uważałeś na lekcjach historii...'],
    halinaProgress: (n, c, all) => [`Rozwiązane zagadki: ${n} z ${all}. Poprawnie: ${c}.`, 'Znaki zapytania unoszą się przy kościele, plebanii, cmentarzu, wiatraku, sklepie, przystankach, rzece, boisku, sadzie, lesie i drodze na wschód.', 'Zajrzyj też do każdej przydrożnej kapliczki i krzyża, a wieczorem do stodoły, gdzie grają jazz.'],
    halinaEnd: (c, all, title) => [`Wszystkie wymagane zagadki rozwiązane! Wynik: ${c} na ${all}.`, `Mianuję cię tytułem: ${title}!`, 'Wpiszę cię do kroniki. Ołówkiem, na razie.'],
    halinaAfter: (c, all, title) => [`${title} — ${c}/${all}. Kronika pamięta!`],
    titles: [[1, 'HONOROWY KRONIKARZ CHŁOPKOWA'], [.75, 'ZNAWCA CHŁOPKOWA'], [.45, 'TURYSTA Z AMBICJAMI'], [0, 'PRZYJEZDNY Z MIASTA']],
    boardDone: ok => [ok ? 'Tę zagadkę już rozwiązałeś — poprawnie!' : 'Tę zagadkę już rozwiązałeś... niestety źle.'],
    quizTitle: 'ZAGADKA', correct: 'DOBRZE!', wrong: 'NIESTETY...', answerWas: 'Poprawna odpowiedź', cont: 'SPACJA — DALEJ', pick: 'STRZAŁKI / 1-4 — WYBÓR · SPACJA — ODPOWIEDZ',
    quizLog: (c, n, all) => `Quiz o Chłopkowie ★${c} (${n}/${all})`,
  } : {
    names: { halina: 'GRANNY IRENKA' },
    halina0: ["Good day, young man! I'm Irenka, I keep the chronicle of Chłopków.", 'I left riddles all around the village — look for the floating question marks!', "First, let's see if you paid attention in history class..."],
    halinaProgress: (n, c, all) => [`Riddles solved: ${n} of ${all}. Correct: ${c}.`, 'Question marks float by the church, rectory, cemetery, windmill, shop, bus stops, river, pitch, orchard, woods and the road east.', 'Check every wayside shrine and cross too, and the barn where they play jazz.'],
    halinaEnd: (c, all, title) => [`All required riddles solved! Score: ${c} of ${all}.`, `I hereby name you: ${title}!`, "I'll write you into the chronicle. In pencil, for now."],
    halinaAfter: (c, all, title) => [`${title} — ${c}/${all}. The chronicle remembers!`],
    titles: [[1, 'HONORARY CHRONICLER OF CHŁOPKÓW'], [.75, 'CHŁOPKÓW EXPERT'], [.45, 'AMBITIOUS TOURIST'], [0, 'VISITOR FROM THE CITY']],
    boardDone: ok => [ok ? 'You already solved this one — correctly!' : 'You already answered this one... wrongly.'],
    quizTitle: 'RIDDLE', correct: 'CORRECT!', wrong: 'NOT QUITE...', answerWas: 'The answer', cont: 'SPACE — CONTINUE', pick: 'ARROWS / 1-4 — CHOOSE · SPACE — ANSWER',
    quizLog: (c, n, all) => `Chłopków quiz ★${c} (${n}/${all})`,
  };
  // only questions that can actually be reached count: Irenka's own + those whose signboard exists in items.json
  const ACTIVE = window.QUIZ.filter(q => q.spot === 'halina' || (ITEMS.boards || []).some(b => b.spot === q.spot));
  const QZ_ALL = ACTIVE.length;
  const REQUIRED = ACTIVE.filter(q => !q.optional);
  const QZ_REQUIRED = REQUIRED.length;
  const qById = id => window.QUIZ.find(q => q.id === id);
  const answered = () => ACTIVE.filter(q => Q().quiz[q.id] !== undefined).length;
  const correctN = () => ACTIVE.filter(q => Q().quiz[q.id] === 1).length;
  const requiredAnswered = () => REQUIRED.filter(q => Q().quiz[q.id] !== undefined).length;
  const requiredCorrect = () => REQUIRED.filter(q => Q().quiz[q.id] === 1).length;
  const titleFor = c => L.titles.find(([min]) => c >= Math.ceil(min * QZ_REQUIRED))[1];

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
    if (requiredAnswered() === QZ_REQUIRED && Q().halina === 1) A.popToast(PL ? 'WRÓĆ DO BABCI IRENKI' : 'GO BACK TO GRANNY IRENKA');
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
    // Keep the quiz in the same hard-edged pixel language as the dialogue box.
    ctx.fillStyle = '#050819'; ctx.fillRect(bx + U * 2, by + U * 2, bw, bh);
    ctx.fillStyle = '#10163a'; ctx.fillRect(bx, by, bw, bh);
    ctx.strokeStyle = '#f5f0e0'; ctx.lineWidth = Math.max(1, U * .35); ctx.strokeRect(bx, by, bw, bh);
    ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
    ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 2.3}px Silkscreen`;
    ctx.fillText(`${L.quizTitle} ${answered() + (QZ.phase === 'ask' ? 1 : 0)}/${QZ_ALL}`, bx + U * 3, by + U * 3.4);
    ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.1}px Silkscreen`;
    qLines.forEach((l, i) => ctx.fillText(l, bx + U * 3, by + U * (7 + i * 3)));
    const ay = by + U * 6 + qLines.length * U * 3 + gap;
    const aw = (bw - U * 6 - gap) / 2;
    QZ.rects = [];
    for (let slot = 0; slot < 4; slot++) {
      const ox = bx + U * 3 + (slot & 1) * (aw + gap), oy = ay + (slot >> 1) * (ansH + gap);
      QZ.rects.push([ox, oy, aw, ansH]);
      const orig = QZ.order[slot], isOk = orig === QZ.q.ok, picked = QZ.phase === 'done' && orig === QZ.pick;
      let bg = '#17204a', fg = '#f5f0e0';
      if (QZ.phase === 'ask' && slot === QZ.sel) { bg = '#355fbc'; fg = '#ffd21f'; }
      if (QZ.phase === 'done' && isOk) { bg = '#245c38'; fg = '#b8ffae'; }
      if (picked && !isOk) { bg = '#73353b'; fg = '#ffb3ab'; }
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

  /* =================================================================== Babcia Irenka + question markers */
  HOOKS.npcTalk.push(id => {
    if (id !== 'halina') return false;
    const q = Q();
    if (requiredAnswered() >= QZ_REQUIRED) { q.halina = 2; A.save(); A.say('halina', L.halinaEnd(requiredCorrect(), QZ_REQUIRED, titleFor(requiredCorrect())), () => A.celebrate()); }
    else if (q.halina === 0) {
      q.halina = 1; A.save();
      if (q.quiz.king === undefined) A.say('halina', L.halina0, () => openQuiz('king'));
      else A.say('halina', L.halinaProgress(answered(), correctN(), QZ_ALL));
    }
    else if (q.halina === 1 && q.quiz.king === undefined) openQuiz('king');
    else if (q.halina === 1) A.say('halina', L.halinaProgress(answered(), correctN(), QZ_ALL));
    else A.say('halina', L.halinaAfter(correctN(), QZ_ALL, titleFor(requiredCorrect())));
    return true;
  });
  const spotQuestion = spot => window.QUIZ.find(q => q.spot === spot);
  HOOKS.near.push(() => (HOOKS.busy.some(f => f()) ? [] : ITEMS.boards.map(b => ({
    x: b.x, y: b.y, r: 30,
    onInteract() {
      const q = spotQuestion(b.spot); if (!q) return;
      if (Q().quiz[q.id] !== undefined) {
        const t = q[PL ? 'pl' : 'en'];
        A.say('arek', [...L.boardDone(Q().quiz[q.id] === 1), `${L.answerWas}: ${t.a[q.ok]}.`]);
      } else openQuiz(q.id);
    },
  }))));
  function drawQuestionMarker(b, sx, sy, s) {
    const q = spotQuestion(b.spot), st = q ? Q().quiz[q.id] : undefined;
    if (st !== undefined) return;
    const bob = Math.sin(A.time * 5 + b.x) * 1.5 * s, my = sy - 20 * s + bob;
    ctx.fillStyle = '#10163a'; ctx.fillRect(sx - 5 * s, my - 6 * s, 10 * s, 11 * s);
    ctx.fillStyle = '#ffd21f'; ctx.font = `${8 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('?', sx, my);
  }
  HOOKS.world.push((push, S, inView) => {
    for (const b of ITEMS.boards) {
      const marker = b.marker || b;
      if (inView(marker.x, marker.y)) push(marker.base || (b.marker ? marker.y + 40 : b.y - 20), () => drawQuestionMarker(b, ...S(marker.x, marker.y), A.zoom));
    }
  });
  HOOKS.minimap.push(dot => { if (Q().halina) for (const b of ITEMS.boards) { const q = spotQuestion(b.spot), marker = b.marker || b; if (q && Q().quiz[q.id] === undefined) dot(marker.x, marker.y, '#ffd21f'); } });
  HOOKS.questLog.push(lines => {
    if (Q().halina) lines.unshift([L.quizLog(correctN(), answered(), QZ_ALL), Q().halina === 2]);
  });

  HOOKS.hud.push((U, W, H) => drawQuiz(U, W, H));

  // test hook (minigames.js adds startMG / MG to the same object)
  window.__features = Object.assign(window.__features || {}, { openQuiz, answer });
  Object.defineProperty(window.__features, 'QZ', { get: () => QZ, configurable: true });
});
