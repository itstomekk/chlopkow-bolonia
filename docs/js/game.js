/* AREK W CHŁOPKOWIE — top-down adventure on a map generated from real OpenStreetMap data.
   World units = art pixels of map_ground.png (2 px per metre). Pure JS, no libraries.
   Quests: Kasia (10 apples), Damian (lost cap), Marcin (orangeade from the shop) -> Grandpa's tractor keys. */
'use strict';
(() => {
  const cvs = document.getElementById('game');
  const ctx = cvs.getContext('2d');
  // Silkscreen has no 'Ć'. Measure it as 'C' and draw 'C' plus a tiny acute accent.
  const _fill = ctx.fillText.bind(ctx), _measure = ctx.measureText.bind(ctx);
  ctx.measureText = t => _measure(String(t).replace(/Ć/g, 'C'));
  ctx.fillText = (t, x, y, mw) => {
    t = String(t);
    if (!t.includes('Ć')) return _fill(t, x, y, mw);
    const plain = t.replace(/Ć/g, 'C'), w = _measure(plain).width, al = ctx.textAlign;
    let cx = al === 'center' ? x - w / 2 : al === 'right' || al === 'end' ? x - w : x;
    const fs = parseFloat((ctx.font.match(/([\d.]+)px/) || [0, 16])[1]);
    ctx.textAlign = 'left';
    for (const part of t.split(/(Ć)/)) {
      if (!part) continue;
      const seg = part === 'Ć' ? 'C' : part; _fill(seg, cx, y);
      if (part === 'Ć') { const cw = _measure('C').width, u = fs / 8; ctx.fillRect(cx + cw * .45, y - fs * .78, u * 1.4, u); ctx.fillRect(cx + cw * .45 + u, y - fs * .78 - u, u * 1.4, u); }
      cx += _measure(seg).width;
    }
    ctx.textAlign = al;
  };
  const params = new URLSearchParams(location.search);
  const LANG = params.get('lang') === 'en' ? 'en' : 'pl';
  const DEBUG = params.get('debug') === '1';
  const SAVE_KEY = 'arek-chlopkow-save-v1';
  const APPLES_NEEDED = 10;

  /* ---------- text ---------- */
  const T = {
    pl: {
      title: 'AREK W CHŁOPKOWIE', start: 'NACIŚNIJ ENTER / DOTKNIJ', cont: 'KONTYNUUJ: ENTER · NOWA GRA: N',
      help: 'STRZAŁKI / WASD — CHODZENIE · SHIFT — BIEG · SPACJA — ROZMOWA / SKOK · M — MAPA',
      names: { arek: 'AREK', kasia: 'KASIA', marcin: 'MARCIN', damian: 'DAMIAN', grandpa: 'DZIADEK ZBYSZEK', halina: 'PANI HALINA' },
      church: ['Kościół pw. Narodzenia NMP. Dzwony biją w południe. Arek, jak zwykle, spóźniony.'],
      rectory: ['Plebania. Ksiądz macha z okna. Arek udaje, że poprawia okulary.'],
      cemetery: ['Cmentarz parafialny. Arek zdejmuje okulary. Na chwilę.'],
      windmill: ['Wiatrak „Koźlak”. Stoi tu dłużej niż ktokolwiek pamięta. Skrzypi, jakby coś mówił.'],
      shop: ['Sklep spożywczo-przemysłowy. Oranżada, drożdżówka i najnowsze plotki ze wsi.'],
      shopBuy: ['Pani ze sklepu: „Oranżada? Ostatnia butelka, dla Marcina.”', 'Arek dostaje oranżadę!'],
      bus: ['Przystanek. Autobus był... albo będzie. W Chłopkowie to jedno i to samo.'],
      river: ['Rzeka Białka. Woda zimna, żaby głośne, a lato jeszcze długie.'],
      kasia0: ['Arek! Piekę szarlotkę na dożynki, a nie mam jabłek.', 'Przynieś mi 10 jabłek. Rosną w sadzie na południu i przy domach.'],
      kasia1: n => [`Masz dopiero ${n}/10 jabłek. Szarlotka sama się nie upiecze!`],
      kasia2: ['10 jabłek! Jesteś niezastąpiony. No, prawie.', 'Szarlotka będzie gotowa wieczorem. Zostawię ci kawałek.'],
      kasia3: ['Szarlotka w piekarniku. Pachnie całą wsią!'],
      damian0: ['Stary, zgubiłem czapkę! Biegałem przez pszenicę na wschód od drogi...', 'Znajdziesz ją? Bez czapki nie gram.'],
      damian1: ['Nadal nic? Szukaj w żółtym zbożu za drogą do kościoła.'],
      damian2: ['MOJA CZAPKA! Arek, jesteś legendą.', 'Stawiam ci kanapkę. No, pół kanapki.'],
      damian3: ['Z czapką gram jak Lewandowski. Prawie.'],
      marcin0: ['Czekam na autobus od godziny. Umieram z pragnienia.', 'Skoczysz do sklepu po oranżadę? Ja pilnuję przystanku.'],
      marcin1: ['Oranżada. Sklep. Szybko. Proszę.'],
      marcin2: ['Oranżada! Ratujesz mi życie.', 'Autobus i tak nie przyjechał. Ale kto by się przejmował.'],
      marcin3: ['Jeszcze tylko jeden łyk... i idę po traktor. Żartuję. Chyba.'],
      grandpa0: ['Czego tu szukasz, młody? Wiatrak nie jest na sprzedaż.', 'Chcesz czegoś więcej niż spacer? Pomóż najpierw Kasi, Damianowi i Marcinowi.'],
      grandpa1: n => [`Pomogłeś ${n} z 3 przyjaciół. Wracaj, jak skończysz.`],
      grandpa2: ['Pomogłeś całej ekipie. Dobra robota, Arek.', 'Masz tu kluczyki do mojego Ursusa. Tylko w niedzielę i tylko do wzgórza.', 'I nie mów babci.'],
      apple: 'JABŁKO', cap: 'CZAPKA DAMIANA', gotCap: ['Czapka Damiana! Trochę zakurzona, ale cała.'],
      quests: ['10 jabłek dla Kasi', 'Czapka Damiana', 'Oranżada dla Marcina', 'Pogadaj z dziadkiem Zbyszkiem'],
      end1: 'MASZ KLUCZYKI DO URSUSA', end2: 'CIĄG DALSZY: GRAND THEFT TRACTOR', end3: 'CZAS', endKey: 'ENTER — GRAJ DALEJ',
    },
    en: {
      title: 'AREK IN CHŁOPKÓW', start: 'PRESS ENTER / TAP', cont: 'CONTINUE: ENTER · NEW GAME: N',
      help: 'ARROWS / WASD — WALK · SHIFT — RUN · SPACE — TALK / JUMP · M — MAP',
      names: { arek: 'AREK', kasia: 'KASIA', marcin: 'MARCIN', damian: 'DAMIAN', grandpa: 'GRANDPA ZBYSZEK', halina: 'MRS HALINA' },
      church: ['Church of the Nativity of the Virgin Mary. Bells at noon. Arek is late, as usual.'],
      rectory: ['The rectory. The priest waves from a window. Arek pretends to fix his sunglasses.'],
      cemetery: ['The parish cemetery. Arek takes his sunglasses off. For a moment.'],
      windmill: ['The "Koźlak" windmill. Older than anyone remembers. It creaks like it wants to talk.'],
      shop: ['The village shop. Orangeade, sweet buns and the freshest gossip in Chłopków.'],
      shopBuy: ['Shop lady: "Orangeade? Last bottle. For Marcin."', 'Arek got an ORANGEADE!'],
      bus: ['Bus stop. The bus has been... or will be. In Chłopków that is the same thing.'],
      river: ['The Białka river. Cold water, loud frogs, and summer is still long.'],
      kasia0: ["Arek! I'm baking apple pie for the harvest festival and I have no apples.", 'Bring me 10 apples. They grow in the orchard down south and by the houses.'],
      kasia1: n => [`Only ${n}/10 apples. The pie won't bake itself!`],
      kasia2: ['10 apples! You are irreplaceable. Well, almost.', "The pie will be ready tonight. I'll save you a slice."],
      kasia3: ['Pie is in the oven. The whole village smells of it!'],
      damian0: ['Dude, I lost my cap! I was running through the wheat east of the road...', "Can you find it? I don't play without it."],
      damian1: ['Still nothing? Look in the yellow wheat past the church road.'],
      damian2: ['MY CAP! Arek, you legend.', "I owe you a sandwich. Well, half a sandwich."],
      damian3: ['With the cap on I play like Lewandowski. Almost.'],
      marcin0: ["I've been waiting for the bus for an hour. I'm dying of thirst.", "Could you run to the shop for an orangeade? I'll guard the bus stop."],
      marcin1: ['Orangeade. Shop. Quick. Please.'],
      marcin2: ["Orangeade! You're a lifesaver.", "The bus never came anyway. Who cares."],
      marcin3: ["One more sip... then I'm going for the tractor. Kidding. Probably."],
      grandpa0: ["What are you after, young man? The windmill isn't for sale.", 'Want to prove yourself? Help Kasia, Damian and Marcin first.'],
      grandpa1: n => [`You've helped ${n} of 3 friends. Come back when you're done.`],
      grandpa2: ['You helped the whole crew. Good job, Arek.', 'Here are the keys to my Ursus. Sundays only, and only to the hill.', "And don't tell Grandma."],
      apple: 'APPLE', cap: "DAMIAN'S CAP", gotCap: ["Damian's cap! A bit dusty, but in one piece."],
      quests: ['10 apples for Kasia', "Damian's cap", 'Orangeade for Marcin', 'Talk to Grandpa Zbyszek'],
      end1: 'YOU GOT THE URSUS KEYS', end2: 'TO BE CONTINUED: GRAND THEFT TRACTOR', end3: 'TIME', endKey: 'ENTER — KEEP PLAYING',
    },
  }[LANG];
  const SPOT_R = { church: 90, rectory: 60, cemetery: 90, windmill: 60, shop: 60, bus: 40, river: 70 };
  const NPC_IDX = { kasia: 0, marcin: 1, damian: 2, grandpa: 3, halina: 4 };
  /* Extension hooks used by features.js (quiz, minigames). Each list holds callbacks:
     near(P) -> [{x,y,r,label,onInteract}]   extra things Arek can interact with
     npcTalk(id) -> true if handled           dialogue for NPCs defined outside this file
     update(dt)                               per-frame logic (runs while scene === 'play')
     world(push, S, inView)                   add y-sorted drawables: push(baseY, drawFn)
     hud(U, W, H)                             draw on top of the HUD
     key(e) / pointer(px, py) -> true if consumed (modal UIs)
     questLog(lines)                          push [text, done] rows into the quest log
     minimap(dot)                             draw markers: dot(x, y, colour)
     blocksPlayer() -> true to freeze normal movement (e.g. countdowns) */
  const HOOKS = { near: [], npcTalk: [], update: [], world: [], hud: [], key: [], pointer: [], questLog: [], minimap: [], blocksPlayer: [] };

  /* ---------- assets ---------- */
  const load = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error(src)); i.src = src; });
  let MAP, GROUND, OBJ, SOLID, SPR, MINI, NPCIMG, ITEMS;

  /* ---------- state ---------- */
  const P = { x: 0, y: 0, dir: 'down', moving: false, step: 0, z: 0, air: false, jt: 0, jx: 0, jy: 0, ox: 0, oy: 0, land: 1 };
  const JUMP_T = .48, JUMP_H = 15, DIRV = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
  const CHAR_H = 40, SPEED = 110, HIT = { w: 14, h: 6 };
  let scene = 'title', talkClosedAt = -9, talk = null, talkT = 0, time = 0, dust = [], showMap = false, fx = [], toast = null;
  // Q.kasia/damian/marcin: 0 not met, 1 active, 2 done. Q.grandpa: 0/1 met, 2 got keys.
  let Q = { kasia: 0, damian: 0, marcin: 0, grandpa: 0, halina: 0, quiz: {}, mg: {}, apples: [], cap: false, orange: false, playTime: 0 };
  let hasSave = false;
  const keys = new Set();
  const joy = { active: false, id: null, cx: 0, cy: 0, x: 0, y: 0 };

  function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify({ Q, x: P.x, y: P.y })); } catch (e) { } }
  function loadSave() {
    try { const s = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null'); if (s && s.Q) { Q = Object.assign(Q, s.Q); P.x = s.x; P.y = s.y; return true; } } catch (e) { }
    return false;
  }
  const appleCount = () => Q.apples.length;
  const questsDone = () => (Q.kasia === 2) + (Q.damian === 2) + (Q.marcin === 2);

  /* ---------- input ---------- */
  function startGame(fresh) {
    if (fresh) { try { localStorage.removeItem(SAVE_KEY); } catch (e) { } Q = { kasia: 0, damian: 0, marcin: 0, grandpa: 0, halina: 0, quiz: {}, mg: {}, apples: [], cap: false, orange: false, playTime: 0 }; P.x = MAP.spawn.x; P.y = MAP.spawn.y; unstick(); camX = P.x; camY = P.y; }
    scene = 'play';
  }
  addEventListener('keydown', e => {
    keys.add(e.code);
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) e.preventDefault();
    if (scene === 'title') { if (e.code === 'KeyN') startGame(true); else if (e.code === 'Enter' || e.code === 'Space') startGame(false); return; }
    if (scene === 'end') { if (e.code === 'Enter' || e.code === 'Space') scene = 'play'; return; }
    if (!talk && HOOKS.key.some(f => f(e))) return;
    if (e.code === 'KeyX' || e.code === 'KeyJ') jump();
    else if (e.code === 'Space') { if (talk || nearThing()) interact(); else jump(); }
    else if (e.code === 'KeyE' || e.code === 'Enter') interact();
    if (e.code === 'KeyM') showMap = !showMap;
  });
  addEventListener('keyup', e => keys.delete(e.code));
  const toCanvas = e => { const r = cvs.getBoundingClientRect(); return [(e.clientX - r.left) / r.width * cvs.width, (e.clientY - r.top) / r.height * cvs.height]; };
  cvs.addEventListener('pointerdown', e => {
    cvs.setPointerCapture(e.pointerId);
    if (scene === 'title') { startGame(false); return; }
    if (scene === 'end') { scene = 'play'; return; }
    const [px, py] = toCanvas(e);
    if (!talk && HOOKS.pointer.some(f => f(px, py))) return;
    if (px > cvs.width * .78 && py > cvs.height * .6) { if (talk || nearThing()) interact(); else jump(); return; }
    if (px > cvs.width * .78 && py < cvs.height * .3) { showMap = !showMap; return; }
    if (talk) { interact(); return; }
    Object.assign(joy, { active: true, id: e.pointerId, cx: px, cy: py, x: 0, y: 0 });
  });
  cvs.addEventListener('pointermove', e => {
    if (!joy.active || e.pointerId !== joy.id) return;
    const [px, py] = toCanvas(e);
    let dx = px - joy.cx, dy = py - joy.cy; const d = Math.hypot(dx, dy), max = 70;
    if (d > max) { dx *= max / d; dy *= max / d; }
    joy.x = dx / max; joy.y = dy / max;
  });
  const endJoy = e => { if (e.pointerId === joy.id) Object.assign(joy, { active: false, x: 0, y: 0 }); };
  cvs.addEventListener('pointerup', endJoy); cvs.addEventListener('pointercancel', endJoy);

  /* ---------- dialogue & quests ---------- */
  function say(who, lines, after) { talk = { who, lines, i: 0, after }; talkT = 0; }
  function nearThing() {
    let best = null, bd = 1e9;
    for (const n of ITEMS.npcs) { const d = Math.hypot(P.x - n.x, P.y - n.y); if (d < 42 && d < bd) { bd = d; best = { npc: n.id, x: n.x, y: n.y }; } }
    if (best) return best;
    for (const f of HOOKS.near) for (const c of f(P)) { const d = Math.hypot(P.x - c.x, P.y - c.y); if (d < (c.r || 30) && d < bd) { bd = d; best = { feat: c, x: c.x, y: c.y }; } }
    if (best) return best;
    for (const s of MAP.pois) { const r = SPOT_R[s.key] || 50, d = Math.hypot(P.x - s.x, P.y - s.y); if (d < r && d < bd) { bd = d; best = { poi: s.key, x: s.x, y: s.y }; } }
    return best;
  }
  function talkNpc(id) {
    if (id === 'kasia') {
      if (Q.kasia === 0) { Q.kasia = 1; say(id, T.kasia0); }
      else if (Q.kasia === 1) { if (appleCount() >= APPLES_NEEDED) { Q.kasia = 2; say(id, T.kasia2, () => celebrate()); } else say(id, T.kasia1(appleCount())); }
      else say(id, T.kasia3);
    } else if (id === 'damian') {
      if (Q.damian === 0) { Q.damian = 1; say(id, Q.cap ? T.damian2 : T.damian0); if (Q.cap) { Q.damian = 2; celebrate(); } }
      else if (Q.damian === 1) { if (Q.cap) { Q.damian = 2; say(id, T.damian2, () => celebrate()); } else say(id, T.damian1); }
      else say(id, T.damian3);
    } else if (id === 'marcin') {
      if (Q.marcin === 0) { Q.marcin = 1; say(id, T.marcin0); }
      else if (Q.marcin === 1) { if (Q.orange) { Q.marcin = 2; say(id, T.marcin2, () => celebrate()); } else say(id, T.marcin1); }
      else say(id, T.marcin3);
    } else if (id === 'grandpa') {
      const n = questsDone();
      if (Q.grandpa === 2) say(id, [T.grandpa2[2]]);
      else if (n >= 3) { say(id, T.grandpa2, () => { Q.grandpa = 2; save(); celebrate(); scene = 'end'; }); }
      else if (Q.grandpa === 0) { Q.grandpa = 1; say(id, T.grandpa0); }
      else say(id, T.grandpa1(n));
    } else HOOKS.npcTalk.some(f => f(id));
    save();
  }
  function interact() {
    if (talk) {
      const line = talk.lines[talk.i];
      if (talkT * 45 < line.length) { talkT = 1e3; return; }
      if (talk.i < talk.lines.length - 1) { talk.i++; talkT = 0; return; }
      const after = talk.after; talk = null; talkClosedAt = time; if (after) after(); return;
    }
    if (P.air) return;
    const s = nearThing(); if (!s) return;
    if (s.npc) { turnTo(s); talkNpc(s.npc); return; }
    if (s.feat) { turnTo(s); s.feat.onInteract(); return; }
    if (s.poi === 'shop' && Q.marcin === 1 && !Q.orange) { Q.orange = true; save(); say('arek', T.shopBuy, () => popToast('+ ORANŻADA'.replace('ORANŻADA', LANG === 'pl' ? 'ORANŻADA' : 'ORANGEADE'))); return; }
    say('arek', T[s.poi]);
  }
  function turnTo(s) { const dx = s.x - P.x, dy = s.y - P.y; P.dir = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down'); }
  function popToast(text) { toast = { text, t: 0 }; }
  function jump() {
    if (scene !== 'play' || talk || P.air || time - talkClosedAt < .3) return;   // don't jump when mashing Space through dialogue
    let ix = 0, iy = 0;
    if (keys.has('ArrowLeft') || keys.has('KeyA')) ix -= 1;
    if (keys.has('ArrowRight') || keys.has('KeyD')) ix += 1;
    if (keys.has('ArrowUp') || keys.has('KeyW')) iy -= 1;
    if (keys.has('ArrowDown') || keys.has('KeyS')) iy += 1;
    if (joy.active && Math.hypot(joy.x, joy.y) > .2) { ix = joy.x; iy = joy.y; }
    const m = Math.hypot(ix, iy), moving = m > .01;
    if (!moving) [ix, iy] = DIRV[P.dir]; else { ix /= m; iy /= m; }
    const run = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 1.5 : 1;
    const sp = (moving ? 1.35 : .8) * SPEED * run;   // standing jump still hops forward a little
    Object.assign(P, { air: true, jt: 0, jx: ix * sp, jy: iy * sp, ox: P.x, oy: P.y });
  }
  function updateJump(dt) {
    P.jt += dt;
    const nx = P.x + P.jx * dt, ny = P.y + P.jy * dt;
    if (!blocked(nx, P.y, true)) P.x = nx;
    if (!blocked(P.x, ny, true)) P.y = ny;
    const k = P.jt / JUMP_T;
    if (k < 1) { P.z = Math.sin(Math.PI * k) * JUMP_H; return; }
    // coming down on top of a fence / into the stream: glide a little further, else hop back
    if (blocked(P.x, P.y, false)) {
      P.z = 2;
      if (P.jt > JUMP_T + .35) { P.x = P.ox; P.y = P.oy; land(); }
      return;
    }
    land();
  }
  function land() {
    P.air = false; P.z = 0; P.land = 0;
    for (let k = 0; k < 6; k++) dust.push({ x: P.x + (k - 2.5) * 3, y: P.y + (k % 2), t: k * .03 });
  }
  function celebrate() { for (let i = 0; i < 40; i++) fx.push({ x: P.x, y: P.y - 25, vx: (Math.random() - .5) * 160, vy: -Math.random() * 180 - 40, t: 0, c: ['#ffd21f', '#ff4fa3', '#7cff6b', '#6fd0ff'][i % 4] }); }

  /* ---------- physics ---------- */
  function solidAt(x, y, air) {
    x |= 0; y |= 0;
    if (x < 4 || y < 40 || x >= MAP.w - 4 || y >= MAP.h - 2) return true;
    const v = SOLID[y * MAP.w + x];
    return air ? v === 2 : v !== 0;   // 2 = tall (walls, trees, ponds), 1 = low (fences, streams, hay) — clearable mid-air
  }
  function blocked(x, y, air = false) {
    const l = x - HIT.w / 2, r = x + HIT.w / 2, t = y - HIT.h;
    if (solidAt(l, y, air) || solidAt(r, y, air) || solidAt(l, t, air) || solidAt(r, t, air) || solidAt(x, y, air) || solidAt(x, t, air)) return true;
    if (ITEMS) for (const n of ITEMS.npcs) if (Math.abs(x - n.x) < 12 && Math.abs(y - n.y) < 6) return true;
    return false;
  }
  function unstick() {
    if (!blocked(P.x, P.y)) return;
    const ox = P.x, oy = P.y;
    for (let r = 4; r < 300; r += 4) for (let a = 0; a < 6.28; a += .4) { const x = ox + Math.cos(a) * r, y = oy + Math.sin(a) * r; if (!blocked(x, y)) { P.x = x; P.y = y; return; } }
  }
  function update(dt) {
    time += dt;
    dust = dust.filter(d => (d.t += dt) < .5);
    fx = fx.filter(f => { f.t += dt; f.x += f.vx * dt; f.y += f.vy * dt; f.vy += 320 * dt; return f.t < 1.2; });
    if (toast && (toast.t += dt) > 1.6) toast = null;
    if (scene !== 'play') return;
    Q.playTime += dt;
    if (talk) { talkT += dt; P.moving = false; return; }
    HOOKS.update.forEach(f => f(dt));
    if (HOOKS.blocksPlayer.some(f => f())) { P.moving = false; return; }
    P.land = Math.min(1, P.land + dt * 6);
    if (P.air) { updateJump(dt); P.moving = true; P.step += dt * 3; } else {
    let ix = 0, iy = 0;
    if (keys.has('ArrowLeft') || keys.has('KeyA')) ix -= 1;
    if (keys.has('ArrowRight') || keys.has('KeyD')) ix += 1;
    if (keys.has('ArrowUp') || keys.has('KeyW')) iy -= 1;
    if (keys.has('ArrowDown') || keys.has('KeyS')) iy += 1;
    if (joy.active && Math.hypot(joy.x, joy.y) > .2) { ix = joy.x; iy = joy.y; }
    const m = Math.hypot(ix, iy);
    P.moving = m > .01;
    if (P.moving) {
      ix /= Math.max(1, m); iy /= Math.max(1, m);
      P.dir = Math.abs(ix) > Math.abs(iy) * .9 ? (ix < 0 ? 'left' : 'right') : (iy < 0 ? 'up' : 'down');
      const run = keys.has('ShiftLeft') || keys.has('ShiftRight') || (joy.active && m > .95) ? 1.8 : 1;
      const nx = P.x + ix * SPEED * run * dt, ny = P.y + iy * SPEED * run * dt;
      let moved = false;
      if (!blocked(nx, P.y)) { P.x = nx; moved = true; }
      if (!blocked(P.x, ny)) { P.y = ny; moved = true; }
      if (moved) {
        const prev = Math.floor(P.step);
        P.step += dt * 7 * run;
        if (Math.floor(P.step) !== prev && Math.floor(P.step) % 2 === 0) dust.push({ x: P.x, y: P.y, t: 0 });
      }
    }
    }
    // pickups
    ITEMS.apples.forEach((a, i) => {
      if (Q.apples.includes(i) || Math.hypot(P.x - a.x, P.y - a.y) > 14) return;
      Q.apples.push(i); save();
      popToast(`+1 ${T.apple}  ${appleCount()}/${APPLES_NEEDED}`);
      for (let k = 0; k < 14; k++) fx.push({ x: a.x, y: a.y - 6, vx: (Math.random() - .5) * 90, vy: -Math.random() * 120, t: 0, c: k % 2 ? '#ffd21f' : '#ff5a4e' });
    });
    if (!Q.cap && Math.hypot(P.x - ITEMS.cap.x, P.y - ITEMS.cap.y) < 16) {
      Q.cap = true; save(); popToast('+ ' + T.cap); say('arek', T.gotCap);
      for (let k = 0; k < 20; k++) fx.push({ x: ITEMS.cap.x, y: ITEMS.cap.y - 6, vx: (Math.random() - .5) * 110, vy: -Math.random() * 140, t: 0, c: '#ffd21f' });
    }
  }

  /* ---------- render helpers ---------- */
  let zoom = 3, camX = 0, camY = 0;
  function resize() {
    const dpr = Math.min(2, devicePixelRatio || 1);
    cvs.width = Math.round(innerWidth * dpr); cvs.height = Math.round(innerHeight * dpr);
    zoom = Math.max(cvs.height / 330, cvs.width / 640);
  }
  addEventListener('resize', resize);

  function shadow(sx, sy, s, w = 8.5) { ctx.fillStyle = 'rgba(20,34,12,0.38)'; ctx.beginPath(); ctx.ellipse(sx, sy, w * s, 3 * s, 0, 0, Math.PI * 2); ctx.fill(); }
  function drawArek(sx, sy, s) {
    const h = CHAR_H * s, zk = 1 - P.z / JUMP_H * .45;
    ctx.globalAlpha = zk; shadow(sx, sy, s * zk); ctx.globalAlpha = 1;
    sy -= P.z * s;
    const { meta, sheet } = SPR;
    const anim = meta.anims[(P.moving || P.air ? 'walk_' : 'idle_') + P.dir];
    const f = anim.frames[P.air ? 2 % anim.frames.length : P.moving ? Math.floor(P.step) % anim.frames.length : 0];
    const scale = h / (f.h - meta.foot - 14), w = f.w * scale, hh = f.h * scale;
    ctx.save(); ctx.translate(sx, sy + meta.foot * scale);
    if (anim.flip) ctx.scale(-1, 1);
    const sq = P.land < 1 ? 1 - Math.sin(P.land * Math.PI) * .14 : 1;   // landing squash
    ctx.scale(2 - sq, sq);
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(sheet, f.x, f.y, f.w, f.h, -w / 2, -hh, w, hh);
    ctx.restore(); ctx.imageSmoothingEnabled = false;
  }
  function drawNpc(n, sx, sy, s) {
    shadow(sx, sy, s, 8);
    const i = NPC_IDX[n.id], h = CHAR_H * s * (n.id === 'grandpa' ? 1.05 : 1);
    const scale = h / (170 - 6 - 14), w = 130 * scale, hh = 170 * scale;
    const bob = Math.sin(time * 2.4 + i) * .6 * s;
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(NPCIMG, i * 130, 0, 130, 170, sx - w / 2, sy + 6 * scale - hh + bob, w, hh);
    ctx.imageSmoothingEnabled = false;
    // quest marker
    const state = n.id === 'grandpa' ? (Q.grandpa === 2 ? 2 : questsDone() >= 3 ? 'ready' : Q.grandpa) : Q[n.id];
    const ready = (n.id === 'kasia' && Q.kasia === 1 && appleCount() >= APPLES_NEEDED) || (n.id === 'damian' && Q.damian === 1 && Q.cap) || (n.id === 'marcin' && Q.marcin === 1 && Q.orange) || state === 'ready';
    const mark = state === 0 ? '!' : ready ? '?' : null;
    if (mark && !n.rival) {
      const my = sy - h - 12 * s + Math.sin(time * 5 + i) * 1.5 * s;
      ctx.fillStyle = '#10163a'; ctx.fillRect(sx - 5 * s, my - 6 * s, 10 * s, 11 * s);
      ctx.fillStyle = mark === '!' ? '#ffd21f' : '#7cff6b'; ctx.font = `${9 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(mark, sx, my);
    }
  }
  function drawApple(sx, sy, s) {
    const b = Math.sin(time * 3 + sx) * s * .8;
    ctx.fillStyle = 'rgba(20,34,12,.35)'; ctx.fillRect(sx - 3 * s, sy + 1 * s, 6 * s, 1.5 * s);
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s - b, w * s, h * s); };
    px(-3, -6, 6, 5, '#d8262c'); px(-2, -7, 4, 7, '#d8262c'); px(-2, -6, 2, 2, '#ff8a80'); px(2, -3, 1, 2, '#9a1a1f'); px(-1, -2, 3, 1, '#9a1a1f');
    px(0, -9, 1, 2, '#6b3b1a'); px(1, -9, 2, 1, '#4fa34a');
  }
  function drawCap(sx, sy, s) {
    const b = Math.sin(time * 3) * s;
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s - b, w * s, h * s); };
    px(-4, -5, 7, 4, '#1f5fd1'); px(-3, -6, 5, 1, '#1f5fd1'); px(2, -2, 4, 1.5, '#163f8c'); px(-2, -5, 2, 1, '#6fa3ff');
    if (Math.floor(time * 4) % 2) { ctx.fillStyle = '#fff'; ctx.fillRect(sx + 5 * s, sy - 9 * s, s, s); }
  }
  function box(x, y, w, h, u) {
    ctx.fillStyle = 'rgba(8,12,40,0.94)'; ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = '#f5f0e0'; ctx.lineWidth = Math.max(2, u * .35); ctx.strokeRect(x + u * .8, y + u * .8, w - u * 1.6, h - u * 1.6);
  }
  function wrapText(text, maxW) {
    const words = text.split(' '), out = []; let cur = '';
    for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }
    if (cur) out.push(cur); return out;
  }
  const fmtTime = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  /* ---------- render ---------- */
  function render() {
    const W = cvs.width, H = cvs.height;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = '#5f9c3b'; ctx.fillRect(0, 0, W, H);
    camX += (P.x - camX) * .12; camY += (P.y - 16 - camY) * .12;
    const vw = W / zoom, vh = H / zoom;
    const cx = Math.max(vw / 2, Math.min(MAP.w - vw / 2, camX)), cy = Math.max(vh / 2, Math.min(MAP.h - vh / 2, camY));
    const ox = Math.round(W / 2 - cx * zoom), oy = Math.round(H / 2 - cy * zoom);
    const sx0 = Math.max(0, Math.floor(-ox / zoom)), sy0 = Math.max(0, Math.floor(-oy / zoom));
    const sw = Math.min(MAP.w - sx0, Math.ceil(W / zoom) + 2), sh = Math.min(MAP.h - sy0, Math.ceil(H / zoom) + 2);
    ctx.drawImage(GROUND, sx0, sy0, sw, sh, ox + sx0 * zoom, oy + sy0 * zoom, sw * zoom, sh * zoom);
    const S = (x, y) => [ox + x * zoom, oy + y * zoom];
    for (const d of dust) { const k = d.t / .5; ctx.fillStyle = `rgba(235,220,180,${.55 * (1 - k)})`; const s = (2 + k * 3) * zoom; ctx.fillRect(ox + (d.x - 2 - k * 4) * zoom, oy + (d.y - 2 - k * 3) * zoom, s, s); }

    // everything that stands on the ground, sorted by baseline
    const inView = (x, y) => x > sx0 - 60 && x < sx0 + sw + 60 && y > sy0 - 60 && y < sy0 + sh + 80;
    const draw = [];
    for (const o of MAP.objects) if (o.x < sx0 + sw && o.x + o.w > sx0 && o.y < sy0 + sh && o.y + o.h > sy0) draw.push({ base: o.base, fn: () => ctx.drawImage(OBJ, o.x, o.y, o.w, o.h, ox + o.x * zoom, oy + o.y * zoom, o.w * zoom, o.h * zoom) });
    ITEMS.apples.forEach((a, i) => { if (!Q.apples.includes(i) && inView(a.x, a.y)) draw.push({ base: a.y, fn: () => drawApple(...S(a.x, a.y), zoom) }); });
    if (!Q.cap && inView(ITEMS.cap.x, ITEMS.cap.y)) draw.push({ base: ITEMS.cap.y, fn: () => drawCap(...S(ITEMS.cap.x, ITEMS.cap.y), zoom) });
    for (const n of ITEMS.npcs) if (inView(n.x, n.y)) draw.push({ base: n.y, fn: () => drawNpc(n, ...S(n.x, n.y), zoom) });
    draw.push({ base: P.y, fn: () => drawArek(...S(P.x, P.y), zoom) });
    HOOKS.world.forEach(f => f((base, fn) => draw.push({ base, fn }), S, inView));
    draw.sort((a, b) => a.base - b.base).forEach(d => d.fn());

    for (const f of fx) { ctx.globalAlpha = 1 - f.t / 1.2; ctx.fillStyle = f.c; const s = zoom * 2; ctx.fillRect(ox + f.x * zoom - s / 2, oy + f.y * zoom - s / 2, s, s); }
    ctx.globalAlpha = 1;
    if (DEBUG) { ctx.strokeStyle = 'cyan'; for (const s of MAP.pois) { ctx.beginPath(); ctx.arc(ox + s.x * zoom, oy + s.y * zoom, (SPOT_R[s.key] || 50) * zoom, 0, 7); ctx.stroke(); } }

    const U = Math.min(W, H * 1.6) / 100;
    ctx.textBaseline = 'middle';
    const near = scene === 'play' && !talk ? nearThing() : null;
    if (near && !near.npc) {
      const [bx, by0] = S(P.x, P.y - CHAR_H - 8), by = by0 + Math.sin(time * 6) * U * .4;
      ctx.textAlign = 'center'; ctx.fillStyle = '#10163a'; ctx.fillRect(bx - U * 2.2, by - U * 2.2, U * 4.4, U * 4.4);
      ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 3}px Silkscreen`; ctx.fillText('…', bx, by);
    }
    // HUD: apples + quest log
    if (scene === 'play' || scene === 'end') {
      const qx = U * 2, qy = U * 2, qw = U * 34, lines = [];
      if (Q.kasia) lines.push([`${T.quests[0]} (${Math.min(appleCount(), APPLES_NEEDED)}/${APPLES_NEEDED})`, Q.kasia === 2]);
      if (Q.damian) lines.push([T.quests[1], Q.damian === 2]);
      if (Q.marcin) lines.push([T.quests[2], Q.marcin === 2]);
      if (Q.grandpa || questsDone() >= 3) lines.push([T.quests[3], Q.grandpa === 2]);
      HOOKS.questLog.forEach(f => f(lines));
      const qh = U * (5.2 + lines.length * 2.6);
      ctx.fillStyle = 'rgba(8,12,40,0.78)'; ctx.fillRect(qx, qy, qw, qh);
      // apple icon + count
      const ax = qx + U * 2.4, ay = qy + U * 2.8;
      ctx.save(); ctx.translate(ax, ay + U * .8); const us = U * .32; ctx.fillStyle = '#d8262c'; ctx.fillRect(-3 * us, -6 * us, 6 * us, 6 * us); ctx.fillStyle = '#4fa34a'; ctx.fillRect(0, -9 * us, 2 * us, 2 * us); ctx.restore();
      ctx.font = `${U * 2}px Silkscreen`; ctx.fillStyle = '#f5f0e0'; ctx.textAlign = 'left';
      ctx.fillText(`× ${appleCount()}`, ax + U * 2, ay);
      ctx.fillStyle = '#ffd21f'; ctx.fillText(fmtTime(Q.playTime), qx + qw - U * 7, ay);
      ctx.font = `${U * 1.45}px Silkscreen`;
      lines.forEach(([txt, done], i) => {
        const ly = qy + U * (6 + i * 2.6);
        ctx.strokeStyle = done ? '#7cff6b' : '#f5f0e0'; ctx.lineWidth = Math.max(1, U * .2); ctx.strokeRect(qx + U * 1.6, ly - U * .7, U * 1.4, U * 1.4);
        if (done) { ctx.fillStyle = '#7cff6b'; ctx.fillRect(qx + U * 1.9, ly - U * .4, U * .8, U * .8); }
        ctx.fillStyle = done ? '#8aa08a' : '#f5f0e0'; ctx.fillText(txt.toUpperCase(), qx + U * 3.8, ly);
      });
    }
    if (toast) {
      const a = Math.min(1, (1.6 - toast.t) * 3), y = H * .22 - toast.t * U * 3;
      ctx.globalAlpha = a; ctx.font = `${U * 2.6}px Silkscreen`; ctx.textAlign = 'center';
      const tw = ctx.measureText(toast.text).width + U * 3; ctx.fillStyle = 'rgba(8,12,40,.85)'; ctx.fillRect(W / 2 - tw / 2, y - U * 2.2, tw, U * 4.4);
      ctx.fillStyle = '#ffd21f'; ctx.fillText(toast.text, W / 2, y); ctx.globalAlpha = 1;
    }
    if (talk) {
      const bw = Math.min(W - U * 6, U * 92), bh = U * 17, bx = (W - bw) / 2, by = H - bh - U * 3;
      box(bx, by, bw, bh, U);
      ctx.font = `${U * 2.4}px Silkscreen`; ctx.fillStyle = talk.who === 'arek' ? '#ffd21f' : '#7cd0ff'; ctx.textAlign = 'left';
      ctx.fillText(T.names[talk.who], bx + U * 3, by + U * 3.6);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.25}px Silkscreen`;
      const full = talk.lines[talk.i].toUpperCase(), shown = full.slice(0, Math.floor(talkT * 45));
      wrapText(shown, bw - U * 6).slice(0, 3).forEach((l, i) => ctx.fillText(l, bx + U * 3, by + U * (7.6 + i * 3.1)));
      if (shown.length >= full.length && Math.floor(time * 3) % 2) { ctx.fillStyle = '#ffd21f'; ctx.fillText('▼', bx + bw - U * 4, by + bh - U * 2.8); }
    }
    // minimap
    if (scene === 'play') {
      const big = showMap, mw = big ? Math.min(W * .8, H * .8 * MAP.w / MAP.h) : U * 16, mh = mw * MAP.h / MAP.w;
      const mx = big ? (W - mw) / 2 : W - mw - U * 2, my = big ? (H - mh) / 2 : U * 2;
      ctx.globalAlpha = big ? 1 : .9; ctx.fillStyle = '#10163a'; ctx.fillRect(mx - U * .5, my - U * .5, mw + U, mh + U);
      ctx.imageSmoothingEnabled = true; ctx.drawImage(MINI, mx, my, mw, mh); ctx.imageSmoothingEnabled = false; ctx.globalAlpha = 1;
      const dot = (x, y, c, r = .5) => { ctx.fillStyle = c; ctx.fillRect(mx + x / MAP.w * mw - U * r, my + y / MAP.h * mh - U * r, U * r * 2, U * r * 2); };
      for (const n of ITEMS.npcs) { const st = n.id === 'grandpa' ? Q.grandpa : Q[n.id]; if (st !== 2) dot(n.x, n.y, '#7cd0ff', big ? .6 : .4); }
      HOOKS.minimap.forEach(f => f((x, y, c) => dot(x, y, c, big ? .45 : .3)));
      dot(P.x, P.y, Math.floor(time * 4) % 2 ? '#ff3b30' : '#fff', big ? .7 : .5);
      if (big) {
        ctx.font = `${U * 1.6}px Silkscreen`; ctx.textAlign = 'center';
        const label = { church: LANG === 'pl' ? 'KOŚCIÓŁ' : 'CHURCH', windmill: LANG === 'pl' ? 'WIATRAK' : 'WINDMILL', shop: LANG === 'pl' ? 'SKLEP' : 'SHOP', cemetery: LANG === 'pl' ? 'CMENTARZ' : 'CEMETERY', river: 'BIAŁKA' };
        const tag = (x, y, txt, col) => { const qx = mx + x / MAP.w * mw, qy = my + y / MAP.h * mh; const tw = ctx.measureText(txt).width + U; ctx.fillStyle = 'rgba(16,22,58,.85)'; ctx.fillRect(qx - tw / 2, qy - U * 2.4, tw, U * 1.9); ctx.fillStyle = col; ctx.fillText(txt, qx, qy - U * 1.4); };
        for (const q of MAP.pois) if (label[q.key]) tag(q.x, q.y, label[q.key], '#ffd21f');
        for (const n of ITEMS.npcs) tag(n.x, n.y + 60, T.names[n.id].split(' ')[0], '#7cd0ff');
      }
      ctx.font = `${U * 1.1}px Silkscreen`; ctx.textAlign = 'right'; ctx.fillStyle = 'rgba(255,255,255,.75)';
      ctx.fillText('© OPENSTREETMAP CONTRIBUTORS', W - U * 1.5, H - U * 1.2);
    }
    if (scene === 'play') HOOKS.hud.forEach(f => f(U, W, H));
    if (scene === 'play' && matchMedia('(pointer:coarse)').matches) {
      ctx.globalAlpha = .3; ctx.fillStyle = '#fff';
      if (joy.active) { ctx.beginPath(); ctx.arc(joy.cx, joy.cy, 70, 0, 7); ctx.fill(); ctx.globalAlpha = .6; ctx.beginPath(); ctx.arc(joy.cx + joy.x * 70, joy.cy + joy.y * 70, 30, 0, 7); ctx.fill(); }
      ctx.globalAlpha = .5; ctx.beginPath(); ctx.arc(W * .89, H * .8, U * 5, 0, 7); ctx.fill();
      ctx.globalAlpha = 1; ctx.fillStyle = '#10163a'; ctx.font = `${U * 2.6}px Silkscreen`; ctx.textAlign = 'center'; ctx.fillText('A', W * .89, H * .8);
    }
    if (scene === 'title') {
      ctx.fillStyle = 'rgba(5,8,25,0.72)'; ctx.fillRect(0, 0, W, H);
      ctx.textAlign = 'center'; ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 6}px Silkscreen`;
      ctx.fillText(T.title, W / 2, H * .36);
      if (Math.floor(time * 2) % 2) { ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.6}px Silkscreen`; ctx.fillText(hasSave ? T.cont : T.start, W / 2, H * .54); }
      ctx.fillStyle = '#9aa0c0'; ctx.font = `${U * 1.6}px Silkscreen`; ctx.fillText(T.help, W / 2, H * .66);
    }
    if (scene === 'end') {
      ctx.fillStyle = 'rgba(5,8,25,0.8)'; ctx.fillRect(0, 0, W, H);
      ctx.textAlign = 'center'; ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 4.6}px Silkscreen`; ctx.fillText(T.end1, W / 2, H * .36);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.6}px Silkscreen`; ctx.fillText(T.end2, W / 2, H * .48);
      ctx.fillStyle = '#9aa0c0'; ctx.font = `${U * 2}px Silkscreen`; ctx.fillText(`${T.end3} ${fmtTime(Q.playTime)} · ${appleCount()}/${ITEMS.apples.length}`, W / 2, H * .58);
      if (Math.floor(time * 2) % 2) ctx.fillText(T.endKey, W / 2, H * .7);
    }
  }

  let last = 0;
  function loop(ts) {
    const dt = Math.min(.05, (ts - last) / 1000 || 0); last = ts;
    update(dt); render();
    requestAnimationFrame(loop);
  }

  async function init() {
    [MAP, ITEMS] = await Promise.all([fetch('map.json').then(r => r.json()), fetch('items.json').then(r => r.json())]);
    const [g, o, c, sheet, meta, npcs] = await Promise.all([
      load('img/map_ground.png'), load('img/map_objects.png'), load('img/map_collide.png'),
      load('img/arek_sheet.png'), fetch('img/arek_sheet.json').then(r => r.json()), load('img/npcs.png'),
      document.fonts.load('20px Silkscreen', 'ŁŚĆŻ')]);
    GROUND = g; OBJ = o; SPR = { sheet, meta }; NPCIMG = npcs;
    const tc = document.createElement('canvas'); tc.width = MAP.w; tc.height = MAP.h;
    const tx = tc.getContext('2d', { willReadFrequently: true }); tx.drawImage(c, 0, 0);
    const d = tx.getImageData(0, 0, MAP.w, MAP.h).data; SOLID = new Uint8Array(MAP.w * MAP.h);
    for (let i = 0; i < SOLID.length; i++) { const v = d[i * 4]; SOLID[i] = v > 200 ? 2 : v > 64 ? 1 : 0; }
    MINI = document.createElement('canvas'); MINI.width = 400; MINI.height = Math.round(400 * MAP.h / MAP.w);
    const mx = MINI.getContext('2d'); mx.drawImage(g, 0, 0, MINI.width, MINI.height); mx.drawImage(o, 0, 0, MINI.width, MINI.height);
    P.x = MAP.spawn.x; P.y = MAP.spawn.y;
    hasSave = loadSave();
    unstick(); camX = P.x; camY = P.y;
    resize(); requestAnimationFrame(loop);
    // API for features.js
    window.ARK = {
      HOOKS, P, MAP, ITEMS, LANG, ctx, keys, joy, T, CHAR_H, SPEED,
      get Q() { return Q; }, get time() { return time; }, get zoom() { return zoom; }, get talk() { return talk; }, get scene() { return scene; },
      save, say, popToast, celebrate, blocked, unstick, drawNpc, shadow, box, wrapText, fmtTime,
      teleport(x, y) { P.x = x; P.y = y; P.air = false; P.z = 0; unstick(); },
      burst(x, y, colors, n = 16) { for (let k = 0; k < n; k++) fx.push({ x, y, vx: (Math.random() - .5) * 120, vy: -Math.random() * 150, t: 0, c: colors[k % colors.length] }); },
      load,
    };
    window.dispatchEvent(new Event('ark-ready'));
    window.__game = { P, MAP, ITEMS, blocked, get Q() { return Q; }, get scene() { return scene; }, set scene(v) { scene = v; }, get talk() { return talk; } };
  }
  init().catch(e => { document.body.insertAdjacentHTML('beforeend', `<pre style="color:#f66">${e.message}</pre>`); });
})();
