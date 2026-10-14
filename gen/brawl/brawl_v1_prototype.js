/* BIJATYKA: a Little-Fighter-2-style local brawler (prototype).
   Several people on one machine (keyboard schemes + gamepads, rebindable) plus computer
   fighters. Started from a purple flag in the south-west of the map.

   Controls per player: 4 directions, ATTACK, JUMP, DEFEND.
     double-tap left/right  run            run + ATTACK  dash punch (knock-down)
     ATTACK x3              combo, 3rd hit knocks down     JUMP + ATTACK   flying kick
     DEFEND                 block frontal hits (90% less damage)
     DEFEND, forward, ATTACK  special 1 (projectile, costs MP)
     DEFEND, up, ATTACK       special 2 (rising attack, costs MP)
   Fighters are data: add an entry to FIGHTERS with a sheet that has walk_left/walk_right.
   Art is a placeholder built from the overworld walking sheets; dedicated fight frames come later.
   Settings and results live in localStorage (ark_brawl_*), never in the main save. */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK;
  if (A.__brawlInstalled) return; A.__brawlInstalled = true;
  const PL = A.LANG === 'pl';

  /* ------------------------------------------------------------------ data */
  const FIGHTERS = {
    arek: {
      name: 'AREK', sheet: 'arek_sheet', skin: '#f0b07c', sleeve: '#3a3f4c', shoe: '#f4f4f4', color: '#e34c4c',
      hp: 500, speed: 1, power: 1,
      special1: { name: PL ? 'JABŁKO' : 'APPLE', kind: 'ball', mp: 75, dmg: 45, color: '#d8262c', leaf: '#4caf50', speed: 520 },
      special2: { name: PL ? 'WIATRAK' : 'WINDMILL', kind: 'rise', mp: 110, dmg: 70 },
    },
    edytka: {
      name: 'EDYTKA', sheet: 'edytka_sheet', skin: '#e9a777', sleeve: '#b5523b', shoe: '#6b3f22', color: '#4aa8e8',
      hp: 480, speed: 1.08, power: .95,
      special1: { name: PL ? 'GRZYB' : 'MUSHROOM', kind: 'ball', mp: 75, dmg: 45, color: '#8a5a2c', leaf: '#f3e3c0', speed: 470 },
      special2: { name: PL ? 'KOPNIAK Z OBROTU' : 'SPIN KICK', kind: 'rise', mp: 110, dmg: 70 },
    },
  };
  const ACTIONS = ['up', 'down', 'left', 'right', 'attack', 'jump', 'defend'];
  const ACTION_LABEL = PL
    ? { up: 'GÓRA', down: 'DÓŁ', left: 'LEWO', right: 'PRAWO', attack: 'ATAK', jump: 'SKOK', defend: 'OBRONA' }
    : { up: 'UP', down: 'DOWN', left: 'LEFT', right: 'RIGHT', attack: 'ATTACK', jump: 'JUMP', defend: 'DEFEND' };
  const DEFAULT_KEYS = {
    kb1: { up: 'KeyW', down: 'KeyS', left: 'KeyA', right: 'KeyD', attack: 'KeyF', jump: 'KeyG', defend: 'KeyH' },
    kb2: { up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight', attack: 'Period', jump: 'Slash', defend: 'ShiftRight' },
    kb3: { up: 'KeyI', down: 'KeyK', left: 'KeyJ', right: 'KeyL', attack: 'KeyO', jump: 'KeyP', defend: 'BracketLeft' },
  };
  const SCHEMES = ['kb1', 'kb2', 'kb3', 'pad1', 'pad2', 'pad3', 'pad4'];
  const schemeLabel = s => s.startsWith('kb') ? (PL ? `KLAWIATURA ${s[2]}` : `KEYBOARD ${s[2]}`) : (PL ? `PAD ${s[3]}` : `GAMEPAD ${s[3]}`);
  const SLOT_COLORS = ['#e34c4c', '#4aa8e8', '#7cff6b', '#ffd21f'];
  const LS_KEYS = 'ark_brawl_keys_v1', LS_SLOTS = 'ark_brawl_slots_v1', LS_STATS = 'ark_brawl_stats_v1';
  const readLS = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v && typeof v === 'object' ? v : d; } catch (e) { return d; } };
  const writeLS = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } };
  const clone = o => JSON.parse(JSON.stringify(o));
  function loadKeys() {
    const saved = readLS(LS_KEYS, {}), out = clone(DEFAULT_KEYS);
    for (const s of Object.keys(out)) for (const a of ACTIONS) if (saved[s] && typeof saved[s][a] === 'string') out[s][a] = saved[s][a];
    return out;
  }
  const DEFAULT_SLOTS = [
    { type: 'human', fighter: 'arek', ctrl: 'kb1', team: '' },
    { type: 'human', fighter: 'edytka', ctrl: 'kb2', team: '' },
    { type: 'cpu', fighter: 'edytka', ctrl: 'kb3', team: '' },
    { type: 'off', fighter: 'arek', ctrl: 'pad1', team: '' },
  ];
  function loadSlots() {
    const saved = readLS(LS_SLOTS, null);
    if (!Array.isArray(saved) || saved.length !== 4) return clone(DEFAULT_SLOTS);
    return saved.map((s, i) => ({
      type: ['human', 'cpu', 'off'].includes(s.type) ? s.type : DEFAULT_SLOTS[i].type,
      fighter: FIGHTERS[s.fighter] ? s.fighter : DEFAULT_SLOTS[i].fighter,
      ctrl: SCHEMES.includes(s.ctrl) ? s.ctrl : DEFAULT_SLOTS[i].ctrl,
      team: ['', 'A', 'B'].includes(s.team) ? s.team : '',
    }));
  }
  let KEYS = loadKeys(), SLOTS = loadSlots();
  const keyName = code => !code ? '—' : code.replace(/^Key/, '').replace(/^Digit/, '').replace(/^Arrow(.*)/, (m, d) => ({ Up: '↑', Down: '↓', Left: '←', Right: '→' }[d]))
    .replace('ShiftRight', 'R-SHIFT').replace('ShiftLeft', 'L-SHIFT').replace('ControlRight', 'R-CTRL').replace('ControlLeft', 'L-CTRL')
    .replace('Period', '.').replace('Comma', ',').replace('Slash', '/').replace('Semicolon', ';').replace('Quote', "'").replace('BracketLeft', '[').replace('BracketRight', ']')
    .replace(/^Numpad/, 'NUM ').toUpperCase();

  /* ------------------------------------------------------------------ sprites */
  const SPRITES = {};
  function loadFighterArt(id) {
    if (SPRITES[id]) return SPRITES[id].ready;
    const f = FIGHTERS[id], spr = SPRITES[id] = { img: null, json: null, bbox: null };
    spr.ready = Promise.all([A.load(`img/${f.sheet}.png`), fetch(`img/${f.sheet}.json`).then(r => r.json())]).then(([img, json]) => {
      spr.img = img; spr.json = json;
      const fr = json.anims.walk_right.frames[0];
      try {   // measure the figure once: shoulder/hip heights for the placeholder limbs
        const c = document.createElement('canvas'); c.width = fr.w; c.height = fr.h;
        const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, fr.x, fr.y, fr.w, fr.h, 0, 0, fr.w, fr.h);
        const d = x.getImageData(0, 0, fr.w, fr.h).data; let top = fr.h, bot = 0, l = fr.w, r = 0;
        for (let yy = 0; yy < fr.h; yy++) for (let xx = 0; xx < fr.w; xx++) if (d[(yy * fr.w + xx) * 4 + 3] > 40) { top = Math.min(top, yy); bot = Math.max(bot, yy); l = Math.min(l, xx); r = Math.max(r, xx); }
        spr.bbox = bot > top ? { top, bot, l, r } : null;
      } catch (e) { spr.bbox = null; }
      return spr;
    });
    return spr.ready;
  }

  /* ------------------------------------------------------------------ arena geometry (logical pixels) */
  const W = 960, H = 540, Z0 = 318, Z1 = 520, X0 = 34, X1 = W - 34, GRAV = 1900, SCALE = .62;
  const groundY = z => Z0 + z;

  /* ------------------------------------------------------------------ venue in the south-west */
  let venue = null;
  function findVenue() {
    const MAP = A.MAP, g = window.__game;
    const ok = (x, y) => x > 40 && y > 40 && x < MAP.w - 40 && y < MAP.h - 40 && !A.blocked(x, y)
      && (!g || !g.isSpawnReachable || g.isSpawnReachable(x, y));
    const sx = MAP.w * .16, sy = MAP.h * .84;
    for (let r = 0; r < 900; r += 14) for (let a = 0; a < Math.PI * 2; a += .35) {
      const x = sx + Math.cos(a) * r, y = sy + Math.sin(a) * r;
      if (ok(x, y)) return { x: Math.round(x), y: Math.round(y) };
    }
    return null;
  }
  queueMicrotask(() => { venue = findVenue(); });

  function drawFlag(sx, sy, s) {
    const c = A.ctx, px = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 5);
    px(-1, -30, 2, 30, '#5a3a1e');
    for (let i = 0; i < 12; i++) px(1 + i, -29 + i * .35 + Math.sin(A.time * 5 + i * .5) * .8, 1, 8 - i * .6, i % 4 < 2 ? '#9b3fe0' : '#ffd21f');
    const st = readLS(LS_STATS, {}), label = (PL ? 'BIJATYKA' : 'BRAWL') + (st.fights ? ` ${st.fights}` : '');
    c.font = `${6 * s}px Silkscreen`; c.textAlign = 'center'; c.textBaseline = 'middle';
    const tw = c.measureText(label).width + 3 * s;
    c.fillStyle = 'rgba(8,12,40,.8)'; c.fillRect(sx - tw / 2, sy - 40 * s, tw, 8 * s);
    c.fillStyle = '#e8c8ff'; c.fillText(label, sx, sy - 36 * s); c.textAlign = 'left';
  }

  /* ------------------------------------------------------------------ input */
  const held = new Set();             // keyboard codes currently down
  const edges = [];                   // keyboard edges since the last tick: [code, down]
  const typing = t => !!(t && t.closest && t.closest('input, textarea, select, [contenteditable="true"], .chat, #player-name-input'));
  let ui = null, fight = null, rebinding = null;

  function onKeyDown(e) {
    if (!ui) return;
    if (rebinding) {
      e.preventDefault(); e.stopImmediatePropagation();
      if (e.code === 'Escape') { rebinding = null; renderLobby(); return; }
      setKey(rebinding.scheme, rebinding.action, e.code); rebinding = null; renderLobby(); return;
    }
    if (e.code !== 'Escape' && (typing(e.target) || typing(document.activeElement))) { if (!fight) e.stopImmediatePropagation(); return; }
    if (e.code === 'Escape') {
      e.preventDefault(); e.stopImmediatePropagation();
      if (fight) endFight(); else closeBrawl();
      return;
    }
    if (fight && fight.phase === 'over' && fight.overT > .8 && (e.code === 'Enter' || e.code === 'KeyR')) { e.preventDefault(); e.stopImmediatePropagation(); startFight(); return; }
    if (!fight) { e.stopImmediatePropagation(); return; }   // lobby: native button/select behaviour only, never the village
    e.preventDefault(); e.stopImmediatePropagation();
    if (e.repeat) return;
    held.add(e.code); edges.push([e.code, true]);
  }
  function onKeyUp(e) {
    if (!ui) return;
    if (held.has(e.code)) { held.delete(e.code); edges.push([e.code, false]); }
    e.stopImmediatePropagation(); if (fight) e.preventDefault();
  }
  window.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('keyup', onKeyUp, true);
  window.addEventListener('blur', () => { held.clear(); });

  function setKey(scheme, action, code) {
    for (const s of Object.keys(KEYS)) for (const a of ACTIONS) if (KEYS[s][a] === code && !(s === scheme && a === action)) KEYS[s][a] = KEYS[scheme][action];   // swap duplicates
    KEYS[scheme][action] = code; writeLS(LS_KEYS, KEYS);
  }

  // Gamepad: d-pad or left stick move; X/Square = attack, A/Cross = jump, B/Circle or RB = defend.
  const padPrev = {};
  function readPad(n) {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const p = pads && pads[n]; if (!p) return null;
    const b = i => !!(p.buttons[i] && p.buttons[i].pressed), ax = p.axes[0] || 0, ay = p.axes[1] || 0;
    return { up: b(12) || ay < -.5, down: b(13) || ay > .5, left: b(14) || ax < -.5, right: b(15) || ax > .5, attack: b(2), jump: b(0), defend: b(1) || b(5) };
  }

  // One controller object per fighter: {held:{action:bool}, pressed:[action...]} rebuilt every tick.
  function gatherInputs(dt) {
    const byScheme = {};
    for (const s of Object.keys(KEYS)) {
      const h = {}, pressed = [];
      for (const a of ACTIONS) h[a] = held.has(KEYS[s][a]);
      for (const [code, down] of edges) if (down) for (const a of ACTIONS) if (KEYS[s][a] === code) pressed.push(a);
      byScheme[s] = { held: h, pressed };
    }
    for (let n = 0; n < 4; n++) {
      const st = readPad(n), prev = padPrev[n] || {}, pressed = [];
      const h = st || Object.fromEntries(ACTIONS.map(a => [a, false]));
      for (const a of ACTIONS) if (h[a] && !prev[a]) pressed.push(a);
      padPrev[n] = { ...h }; byScheme[`pad${n + 1}`] = { held: h, pressed };
    }
    edges.length = 0;
    for (const f of fight.fighters) f.input = f.cpu ? cpuThink(f, dt) : (byScheme[f.ctrl] || { held: {}, pressed: [] });
  }

  /* ------------------------------------------------------------------ fighters */
  function makeFighter(slot, i, n) {
    const d = FIGHTERS[slot.fighter];
    const x = X0 + 120 + (X1 - X0 - 240) * (n > 1 ? i / (n - 1) : .5);
    return {
      id: `p${i + 1}`, slot: i, def: d, key: slot.fighter, cpu: slot.type === 'cpu', ctrl: slot.ctrl,
      team: slot.team || `solo${i}`, color: SLOT_COLORS[i],
      label: slot.type === 'cpu' ? `${d.name} (CPU)` : `${d.name} P${i + 1}`,
      x, z: 90 + (i % 2) * 70, y: 0, vx: 0, vz: 0, vy: 0, face: x < W / 2 ? 1 : -1,
      hp: d.hp, hpMax: d.hp, hpShown: d.hp, mp: 250, mpMax: 500,
      st: 'idle', t: 0, combo: 0, comboT: 0, hitSet: null, fall: 0, inv: 0, flash: 0, hitstop: 0,
      running: false, tap: { left: -1, right: -1 }, hist: [], walkT: 0, ai: { think: 0, plan: null, wait: 0 },
      input: { held: {}, pressed: [] }, kos: 0, dealt: 0,
    };
  }
  const alive = f => f.st !== 'dead';
  const canAct = f => ['idle', 'walk', 'run'].includes(f.st);
  const enemies = f => fight.fighters.filter(o => o !== f && o.team !== f.team && alive(o));

  // Attack table: active window [t0,t1] s, reach/height of the hitbox, damage, fall added, knock velocity.
  const MOVES = {
    punch1: { dur: .30, t0: .08, t1: .16, reach: 62, hy: .62, dmg: 22, fall: 25, kx: 60 },
    punch2: { dur: .30, t0: .08, t1: .16, reach: 62, hy: .62, dmg: 24, fall: 25, kx: 70 },
    kick3: { dur: .46, t0: .12, t1: .24, reach: 72, hy: .38, dmg: 38, fall: 100, kx: 300, ky: 360 },
    dash: { dur: .50, t0: .06, t1: .32, reach: 70, hy: .55, dmg: 42, fall: 100, kx: 360, ky: 330 },
    jkick: { dur: .60, t0: .05, t1: .45, reach: 66, hy: .35, dmg: 38, fall: 100, kx: 300, ky: 300 },
    rise: { dur: .62, t0: .10, t1: .42, reach: 66, hy: .7, dmg: 70, fall: 100, kx: 140, ky: 720 },
  };

  function startState(f, st) { f.st = st; f.t = 0; f.hitSet = new Set(); }
  function special(f, which) {
    const sp = f.def[which];
    if (!sp || f.mp < sp.mp) return false;
    f.mp -= sp.mp;
    if (sp.kind === 'ball') {
      startState(f, 'cast');
      fight.shots.push({ owner: f, team: f.team, x: f.x + f.face * 40, z: f.z, y: 58, vx: f.face * sp.speed, dmg: Math.round(sp.dmg * f.def.power), sp, life: 1.8, spin: 0 });
    } else { startState(f, 'rise'); f.vy = 520; f.y = .1; }
    fight.banners.push({ text: sp.name, x: f.x, y: groundY(f.z) - 140, t: 0, color: f.color });
    return true;
  }
  function recordPress(f, a, now) { f.hist.push([a, now]); while (f.hist.length > 8) f.hist.shift(); }
  // DEFEND, then a direction, then ATTACK, all inside 0.7 s.
  function specialInput(f, now) {
    const h = f.hist.filter(p => now - p[1] < .7), n = h.length;
    if (n < 3 || h[n - 1][0] !== 'attack') return null;
    const dir = h[n - 2][0], d = h[n - 3][0];
    if (d !== 'defend') return null;
    if (dir === 'left' || dir === 'right') return { which: 'special1', face: dir === 'left' ? -1 : 1 };
    if (dir === 'up') return { which: 'special2' };
    return null;
  }

  function updateFighter(f, dt, now) {
    const inp = f.input, hd = inp.held || {};
    f.inv = Math.max(0, f.inv - dt); f.flash = Math.max(0, f.flash - dt); f.fall = Math.max(0, f.fall - dt * 30);
    f.comboT = Math.max(0, f.comboT - dt); if (!f.comboT) f.combo = 0;
    if (alive(f)) f.mp = Math.min(f.mpMax, f.mp + dt * (f.hp < f.hpMax * .35 ? 34 : 22));
    f.hpShown += (f.hp - f.hpShown) * Math.min(1, dt * 4);
    if (f.hitstop > 0) { f.hitstop -= dt; return; }
    for (const a of inp.pressed || []) recordPress(f, a, now);
    f.t += dt;
    const spd = 150 * f.def.speed;

    // ---- grounded control
    if (canAct(f)) {
      for (const a of inp.pressed || []) if (a === 'left' || a === 'right') {
        if (now - f.tap[a] < .26) f.running = a === 'left' ? -1 : 1;
        else if (f.running && (a === 'left' ? -1 : 1) !== f.running) f.running = 0;
        f.tap[a] = now;
      }
      const mx = (hd.right ? 1 : 0) - (hd.left ? 1 : 0), mz = (hd.down ? 1 : 0) - (hd.up ? 1 : 0);
      const sp = specialInput(f, now);
      if (sp && (inp.pressed || []).includes('attack')) {
        if (sp.face) f.face = sp.face;
        f.hist.length = 0;
        if (special(f, sp.which)) return;
      }
      if ((inp.pressed || []).includes('jump')) {
        startState(f, 'jump'); f.vy = 610; f.y = .1;
        f.vx = f.running ? f.running * spd * 2.2 : mx * spd * 1.05; f.vz = mz * spd * .55; f.running = 0; return;
      }
      if ((inp.pressed || []).includes('attack')) {
        if (f.running) { startState(f, 'dash'); f.vx = f.running * spd * 2.3; f.running = 0; return; }
        f.combo = f.comboT > 0 ? f.combo + 1 : 1; f.comboT = .55;
        startState(f, f.combo >= 3 ? 'kick3' : f.combo === 2 ? 'punch2' : 'punch1');
        if (f.combo >= 3) f.combo = 0;
        return;
      }
      if (hd.defend && !f.running) { startState(f, 'defend'); return; }
      if (f.running) {
        f.face = f.running; f.x += f.running * spd * 2.1 * dt; f.z += mz * spd * .45 * dt;
        if (f.st !== 'run') { f.st = 'run'; }
      } else if (mx || mz) {
        if (mx) f.face = mx;
        f.x += mx * spd * dt; f.z += mz * spd * .62 * dt;
        if (f.st !== 'walk') f.st = 'walk';
      } else if (f.st !== 'idle') f.st = 'idle';
      f.walkT += dt * (f.st === 'run' ? 2 : 1) * (f.st === 'idle' ? 0 : 1);
    } else if (f.st === 'defend') {
      if (!hd.defend && f.t > .12) startState(f, 'idle');
      const sp = specialInput(f, now);
      if (sp && (inp.pressed || []).includes('attack')) { if (sp.face) f.face = sp.face; f.hist.length = 0; special(f, sp.which); }
    } else if (MOVES[f.st] && f.st !== 'jkick' && f.st !== 'rise') {
      const m = MOVES[f.st];
      if (f.st === 'dash') { f.x += f.vx * dt; f.vx *= Math.pow(.06, dt); }
      else if (f.t < m.t1) f.x += f.face * 40 * dt;
      // chain the next combo hit early
      if ((inp.pressed || []).includes('attack') && f.t > m.t1 && f.st !== 'kick3' && f.st !== 'dash') {
        f.combo += 1; f.comboT = .55; startState(f, f.combo >= 3 ? 'kick3' : 'punch2'); if (f.combo >= 3) f.combo = 0;
      } else if (f.t >= m.dur) startState(f, 'idle');
    } else if (f.st === 'cast') {
      if (f.t >= .42) startState(f, 'idle');
    } else if (f.st === 'jump' || f.st === 'jkick' || f.st === 'rise') {
      if (f.st === 'jump' && (inp.pressed || []).includes('attack')) startState(f, 'jkick');
      if (f.st === 'rise') f.x += f.face * 60 * dt;
      f.x += f.vx * dt; f.z += f.vz * dt; f.vy -= GRAV * dt; f.y += f.vy * dt;
      if (f.y <= 0) { f.y = 0; f.vy = 0; f.vx = 0; f.vz = 0; startState(f, 'land'); }
    } else if (f.st === 'land') {
      if (f.t > .1) startState(f, 'idle');
    } else if (f.st === 'hurt') {
      f.x += f.vx * dt; f.vx *= Math.pow(.02, dt);
      if (f.t > .32) startState(f, 'idle');
    } else if (f.st === 'fly') {
      f.x += f.vx * dt; f.z += f.vz * dt; f.vy -= GRAV * dt; f.y += f.vy * dt;
      if (f.y <= 0) {
        f.y = 0;
        if (f.vy < -420) { f.vy = -f.vy * .32; f.vx *= .5; fight.shake = Math.max(fight.shake, .12); }
        else { f.vy = 0; f.vx = 0; f.vz = 0; startState(f, f.hp <= 0 ? 'dead' : 'down'); if (f.hp <= 0) onKo(f); }
      }
    } else if (f.st === 'down') {
      if (f.t > .9) { startState(f, 'idle'); f.inv = .7; f.fall = 0; }
    }
    f.x = Math.max(X0, Math.min(X1, f.x)); f.z = Math.max(0, Math.min(Z1 - Z0, f.z));
  }

  function hurtable(o) { return alive(o) && !['down', 'dead'].includes(o.st) && !(o.st === 'fly' && o.y > 0) && o.inv <= 0; }
  function blocking(o, fromX) { return o.st === 'defend' && Math.sign(fromX - o.x) === o.face; }
  function hit(att, o, dmg, fall, kx, ky, srcX) {
    const blocked = blocking(o, srcX);
    const dir = Math.sign(o.x - srcX) || att.face;
    if (blocked) {
      dmg = Math.round(dmg * .1); o.x += dir * 10; o.mp = Math.max(0, o.mp - 8);
      sparks(o.x - dir * 20, groundY(o.z) - 70, '#9fd0f0', 6);
    } else {
      o.fall += fall; o.flash = .12; o.combo = 0; o.running = 0;
      sparks(o.x - dir * 14, groundY(o.z) - o.y - 70, '#fff3b0', 10);
      fight.shake = Math.max(fight.shake, fall >= 100 ? .18 : .07);
      if (o.fall >= 70 || o.hp - dmg <= 0 || ky || o.y > 0) { startState(o, 'fly'); o.vx = dir * (kx || 240); o.vy = ky || 380; o.y = Math.max(o.y, .1); o.fall = 0; }
      else { startState(o, 'hurt'); o.vx = dir * (kx || 60); }
    }
    o.hp = Math.max(0, o.hp - dmg); att.dealt += dmg;
    att.hitstop = o.hitstop = blocked ? .03 : .06;
    if (o.hp <= 0 && o.st !== 'fly') { startState(o, 'fly'); o.vx = dir * 220; o.vy = 420; o.y = .1; }
    if (o.hp <= 0) o.lastHitBy = att;
    fight.pops.push({ text: blocked ? (PL ? 'BLOK' : 'BLOCK') : String(dmg), x: o.x, y: groundY(o.z) - o.y - 120, t: 0, color: blocked ? '#9fd0f0' : '#fff' });
  }
  function resolveMelee(f) {
    const m = MOVES[f.st]; if (!m || f.t < m.t0 || f.t > m.t1) return;
    const figH = 95;
    for (const o of fight.fighters) {
      if (o === f || o.team === f.team || f.hitSet.has(o) || !hurtable(o)) continue;
      const dx = (o.x - f.x) * f.face, dz = Math.abs(o.z - f.z), hy = f.y + figH * m.hy;
      if (dx < -8 || dx > m.reach || dz > 22) continue;
      if (hy < o.y - 10 || hy > o.y + figH + 20) continue;
      f.hitSet.add(o);
      const sp = f.st === 'rise' ? f.def.special2 : null;
      hit(f, o, Math.round((sp ? sp.dmg : m.dmg) * f.def.power), m.fall, m.kx, m.ky, f.x);
    }
  }
  function onKo(f) {
    const by = f.lastHitBy; if (by) by.kos++;
    fight.banners.push({ text: 'K.O.', x: f.x, y: groundY(f.z) - 110, t: 0, color: '#ff6b5e' });
  }

  function updateShots(dt) {
    for (const s of fight.shots) {
      s.x += s.vx * dt; s.life -= dt; s.spin += dt * 14;
      if (s.x < X0 - 40 || s.x > X1 + 40) s.life = 0;
      for (const o of fight.fighters) {
        if (s.life <= 0 || o.team === s.team || !hurtable(o)) continue;
        if (Math.abs(o.x - s.x) < 26 && Math.abs(o.z - s.z) < 20 && o.y < 90) { hit(s.owner, o, s.dmg, 75, 260, 0, s.x - Math.sign(s.vx) * 30); s.life = 0; }
      }
      for (const t of fight.shots) if (t !== s && t.team !== s.team && t.life > 0 && s.life > 0 && Math.abs(t.x - s.x) < 24 && Math.abs(t.z - s.z) < 20) {
        t.life = s.life = 0; sparks(s.x, groundY(s.z) - s.y, '#ffd21f', 14);
      }
    }
    fight.shots = fight.shots.filter(s => s.life > 0);
  }
  function sparks(x, y, color, n) {
    for (let k = 0; k < n; k++) fight.fx.push({ x, y, vx: (Math.random() - .5) * 420, vy: -Math.random() * 300, t: 0, life: .3 + Math.random() * .25, color });
  }

  /* ------------------------------------------------------------------ computer fighter */
  function cpuThink(f, dt) {
    const out = { held: {}, pressed: [] }, ai = f.ai;
    if (!alive(f) || fight.phase !== 'fight') return out;
    const foes = enemies(f); if (!foes.length) return out;
    const tgt = foes.reduce((b, o) => (Math.hypot(o.x - f.x, (o.z - f.z) * 2) < Math.hypot(b.x - f.x, (b.z - f.z) * 2) ? o : b));
    const dx = tgt.x - f.x, dz = tgt.z - f.z, adx = Math.abs(dx);
    ai.wait -= dt; ai.think -= dt;
    // react to an incoming attack: sometimes block, sometimes jump away
    const threat = foes.find(o => MOVES[o.st] && Math.abs(o.x - f.x) < 90 && Math.abs(o.z - f.z) < 26 && o.t < (MOVES[o.st].t0 + .02));
    if (threat && canAct(f) && ai.think <= 0) {
      ai.think = .45;
      const r = Math.random();
      if (r < .32) { f.face = Math.sign(threat.x - f.x) || f.face; ai.plan = { block: .35 }; }
      else if (r < .42) out.pressed.push('jump');
    }
    if (ai.plan && ai.plan.block > 0) { ai.plan.block -= dt; out.held.defend = true; return out; }
    const shotNear = fight.shots.find(s => s.team !== f.team && Math.abs(s.z - f.z) < 22 && Math.sign(f.x - s.x) === Math.sign(s.vx) && Math.abs(f.x - s.x) < 160);
    if (shotNear && canAct(f) && ai.think <= 0) { ai.think = .5; if (Math.random() < .5) out.pressed.push('jump'); else { out.held[dz > 0 ? 'up' : 'down'] = true; } }
    if (ai.wait > 0) return out;
    if (Math.abs(dz) > 10) out.held[dz > 0 ? 'down' : 'up'] = true;
    const special1 = f.def.special1;
    if (canAct(f) && f.mp >= special1.mp && adx > 170 && adx < 520 && Math.abs(dz) < 14 && Math.random() < dt * 1.1) {
      f.face = Math.sign(dx);
      f.hist.push(['defend', fight.time - .2], [dx > 0 ? 'right' : 'left', fight.time - .1]);
      out.pressed.push('attack'); ai.wait = .5; return out;
    }
    if (adx > 62) { out.held[dx > 0 ? 'right' : 'left'] = true; if (adx > 330 && canAct(f) && f.st !== 'run' && Math.random() < dt * 1.5) { f.running = Math.sign(dx); } }
    else if (adx < 30) out.held[dx > 0 ? 'left' : 'right'] = true;
    else f.face = Math.sign(dx) || f.face;
    if (adx < 75 && Math.abs(dz) < 16 && canAct(f) && Math.random() < dt * 4.2) {
      f.face = Math.sign(dx) || f.face;
      if (f.mp >= f.def.special2.mp && Math.random() < .12) { f.hist.push(['defend', fight.time - .2], ['up', fight.time - .1]); }
      out.pressed.push('attack'); ai.wait = .18 + Math.random() * .25;
    } else if ((MOVES[f.st] && f.st.startsWith('punch')) && Math.random() < dt * 8) out.pressed.push('attack');
    return out;
  }

  /* ------------------------------------------------------------------ fight lifecycle */
  function teamsAlive() { return [...new Set(fight.fighters.filter(alive).map(f => f.team))]; }
  function startFight() {
    const active = SLOTS.map((s, i) => [s, i]).filter(([s]) => s.type !== 'off');
    const err = validate(); if (err) { setLobbyError(err); return false; }
    held.clear(); edges.length = 0; rebinding = null;
    fight = { phase: 'intro', t: 0, time: 0, overT: 0, fighters: [], shots: [], fx: [], pops: [], banners: [], shake: 0, winner: null };
    fight.fighters = active.map(([s, i], k) => makeFighter(s, i, active.length));
    showFightCanvas(true);
    Promise.all(Object.keys(FIGHTERS).map(loadFighterArt)).catch(() => {});
    return true;
  }
  function endFight() { fight = null; held.clear(); edges.length = 0; showFightCanvas(false); renderLobby(); }
  function finish() {
    const teams = teamsAlive();
    fight.phase = 'over'; fight.overT = 0;
    const winners = fight.fighters.filter(f => f.team === teams[0] && alive(f));
    fight.winner = teams.length === 1 ? winners : [];
    const st = readLS(LS_STATS, {}); st.fights = (st.fights || 0) + 1; st.wins = st.wins || {};
    for (const f of fight.winner) st.wins[f.key] = (st.wins[f.key] || 0) + 1;
    writeLS(LS_STATS, st);
  }
  function tick(dt) {
    if (!fight) return;
    fight.t += dt; fight.shake = Math.max(0, fight.shake - dt);
    gatherInputs(dt);
    if (fight.phase === 'intro') { if (fight.t > 1.6) { fight.phase = 'fight'; fight.t = 0; } }
    else {
      fight.time += dt;
      if (fight.phase === 'over') fight.overT += dt;
      for (const f of fight.fighters) {
        if (fight.phase === 'over' && f.input) f.input = { held: {}, pressed: [] };
        updateFighter(f, dt, fight.time);
      }
      for (const f of fight.fighters) resolveMelee(f);
      updateShots(dt);
      if (fight.phase === 'fight' && teamsAlive().length <= 1 && fight.fighters.every(f => f.st !== 'fly')) finish();
    }
    for (const p of fight.fx) { p.t += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 900 * dt; }
    fight.fx = fight.fx.filter(p => p.t < p.life);
    for (const p of fight.pops) { p.t += dt; p.y -= 40 * dt; }
    fight.pops = fight.pops.filter(p => p.t < .8);
    for (const b of fight.banners) b.t += dt;
    fight.banners = fight.banners.filter(b => b.t < 1.1);
  }

  /* ------------------------------------------------------------------ rendering */
  let cvs = null, cx = null, bg = null, raf = 0, last = 0, acc = 0;
  function buildBackground() {
    const b = document.createElement('canvas'); b.width = W / 4; b.height = H / 4;
    const g = b.getContext('2d'), w = b.width, h = b.height, gz = Z0 / 4;
    const sky = g.createLinearGradient(0, 0, 0, gz); sky.addColorStop(0, '#6fb6e8'); sky.addColorStop(1, '#cfe9f2');
    g.fillStyle = sky; g.fillRect(0, 0, w, gz);
    g.fillStyle = '#f4f8fb'; for (const [x, y, r] of [[30, 14, 6], [38, 12, 8], [46, 15, 5], [160, 20, 6], [170, 17, 8], [180, 20, 5]]) { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); }
    g.fillStyle = '#3f6e3a'; for (let x = 0; x < w; x += 6) { const th = 14 + ((x * 37) % 11); g.fillRect(x, gz - 18 - th, 7, th + 6); }
    g.fillStyle = '#2f5a2c'; for (let x = 3; x < w; x += 9) g.fillRect(x, gz - 20 - ((x * 13) % 7), 3, 8);
    // barn
    g.fillStyle = '#8f2f25'; g.fillRect(148, gz - 46, 54, 34); g.fillStyle = '#6d231c'; g.beginPath(); g.moveTo(144, gz - 46); g.lineTo(175, gz - 62); g.lineTo(206, gz - 46); g.fill();
    g.fillStyle = '#e9dcc0'; g.fillRect(166, gz - 34, 18, 22); g.fillStyle = '#8f2f25'; g.fillRect(174, gz - 34, 2, 22);
    g.strokeStyle = '#8f2f25'; g.lineWidth = 1; g.beginPath(); g.moveTo(166, gz - 34); g.lineTo(184, gz - 12); g.moveTo(184, gz - 34); g.lineTo(166, gz - 12); g.stroke();
    // fence
    g.fillStyle = '#7a5530'; g.fillRect(0, gz - 10, w, 2); g.fillRect(0, gz - 6, w, 2); for (let x = 2; x < w; x += 12) g.fillRect(x, gz - 13, 2, 13);
    // ground
    const gr = g.createLinearGradient(0, gz, 0, h); gr.addColorStop(0, '#6b9d45'); gr.addColorStop(1, '#4f7e33');
    g.fillStyle = gr; g.fillRect(0, gz, w, h - gz);
    for (let i = 0; i < 260; i++) { const x = (i * 97) % w, y = gz + ((i * 53) % (h - gz)); g.fillStyle = i % 3 ? '#5f9140' : '#79ad52'; g.fillRect(x, y, 1, 2); }
    g.fillStyle = 'rgba(160,120,70,.35)'; g.fillRect(0, gz + 22, w, 6);
    // hay bales at the edges
    for (const [x, y] of [[4, gz + 6], [222, gz + 10]]) { g.fillStyle = '#d6b45a'; g.fillRect(x, y, 14, 9); g.fillStyle = '#b8953f'; g.fillRect(x, y + 3, 14, 1); g.fillRect(x, y + 6, 14, 1); }
    return b;
  }
  function frameFor(f, spr) {
    const dir = f.face < 0 ? 'left' : 'right', anims = spr.json.anims;
    const walk = (anims[`walk_${dir}`] || anims.walk_right).frames;
    let i = 0;
    if (f.st === 'walk' || f.st === 'run') i = Math.floor(f.walkT * (f.st === 'run' ? 7 : 8)) % walk.length;
    else if (['jump', 'jkick', 'rise', 'fly'].includes(f.st)) i = 1;
    else if (['punch1', 'punch2', 'dash', 'kick3', 'cast'].includes(f.st)) i = 2;
    return walk[i];
  }
  function drawFighter(f) {
    const spr = SPRITES[f.key];
    const gx = f.x, gy = groundY(f.z), c = cx;
    // shadow
    c.fillStyle = 'rgba(10,30,10,.35)'; c.beginPath(); c.ellipse(gx, gy, 30 - Math.min(18, f.y / 12), 8 - Math.min(4, f.y / 40), 0, 0, 7); c.fill();
    if (f.st === 'dead' && fight.phase === 'over' && fight.overT > 1.2) c.globalAlpha = .6;
    if (f.inv > 0 && Math.floor(f.inv * 20) % 2) c.globalAlpha = .45;
    const ready = spr && spr.img && spr.json;
    const fr = ready ? frameFor(f, spr) : null;
    const s = SCALE, fw = fr ? fr.w * s : 70, fh = fr ? fr.h * s : 100, foot = ready ? (spr.json.foot || 6) * s : 0;
    const bb = ready && spr.bbox ? spr.bbox : { top: 10, bot: 164 };
    const figH = (bb.bot - bb.top) * s;
    c.save();
    c.translate(gx, gy - f.y);
    let rot = 0;
    if (f.st === 'down' || f.st === 'dead') rot = -f.face * Math.PI / 2;
    else if (f.st === 'fly') rot = -f.face * Math.min(Math.PI / 2, f.t * 5);
    else if (f.st === 'run' || f.st === 'dash') rot = f.face * .16;
    else if (['punch1', 'punch2', 'kick3'].includes(f.st)) rot = f.face * .08;
    else if (f.st === 'hurt') rot = -f.face * .14;
    else if (f.st === 'defend') rot = -f.face * .06;
    else if (f.st === 'rise') rot = f.face * f.t * 18;
    if (rot) { const pivot = (f.st === 'rise') ? -figH / 2 : 0; c.translate(0, pivot); c.rotate(rot); c.translate(0, -pivot); }
    if (f.st === 'down' || f.st === 'dead') c.translate(0, figH * .18);
    if (f.st === 'hurt') c.translate((Math.random() - .5) * 4, 0);
    if (fr) {
      c.imageSmoothingEnabled = false;
      if (f.flash > 0) c.filter = 'brightness(2.4)';
      c.drawImage(spr.img, fr.x, fr.y, fr.w, fr.h, -fw / 2, -fh + foot, fw, fh);
      c.filter = 'none';
    } else { c.fillStyle = f.def.color; c.fillRect(-14, -90, 28, 90); }
    // placeholder limbs for attack poses
    const shoulderY = -figH * .64, hipY = -figH * .3, d = f.def;
    const limb = (fromY, toX, toY, col, end, endCol, w) => {
      c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'round';
      c.beginPath(); c.moveTo(0, fromY); c.lineTo(toX, toY); c.stroke();
      c.fillStyle = '#1b1b22'; c.fillRect(toX - end / 2 - 1, toY - end / 2 - 1, end + 2, end + 2);
      c.fillStyle = endCol; c.fillRect(toX - end / 2, toY - end / 2, end, end);
    };
    const m = MOVES[f.st], active = m && f.t >= m.t0 && f.t <= m.t1;
    if (f.st === 'punch1' || f.st === 'punch2' || f.st === 'dash') {
      const ext = m && f.t < m.t1 ? Math.min(1, f.t / Math.max(.01, m.t0)) : Math.max(0, 1 - (f.t - m.t1) / .1);
      limb(shoulderY + (f.st === 'punch2' ? 4 : 0), f.face * (14 + 34 * ext), shoulderY + 2, d.sleeve, 9, d.skin, 7);
    } else if (f.st === 'kick3' || f.st === 'jkick') {
      const ext = f.st === 'jkick' ? 1 : Math.min(1, f.t / .12);
      limb(hipY, f.face * (10 + 42 * ext), hipY + (f.st === 'jkick' ? 8 : -6), d.skin, 11, d.shoe, 8);
    } else if (f.st === 'rise') {
      limb(shoulderY, f.face * 30, shoulderY - 30, d.sleeve, 10, d.skin, 7);
    } else if (f.st === 'cast') {
      limb(shoulderY, f.face * 40, shoulderY - 4, d.sleeve, 9, d.skin, 7);
    } else if (f.st === 'defend') {
      limb(shoulderY + 6, f.face * 18, shoulderY - 8, d.sleeve, 8, d.skin, 7);
      c.strokeStyle = 'rgba(159,208,240,.75)'; c.lineWidth = 3;
      c.beginPath(); c.arc(f.face * 10, -figH * .5, figH * .45, f.face > 0 ? -1 : Math.PI - 1, f.face > 0 ? 1 : Math.PI + 1); c.stroke();
    }
    if (active && f.st !== 'defend') {   // swoosh
      c.strokeStyle = 'rgba(255,255,255,.7)'; c.lineWidth = 3;
      const yy = (m.hy > .5 ? shoulderY : hipY);
      c.beginPath(); c.arc(f.face * 30, yy, 26, f.face > 0 ? -.9 : Math.PI - .9, f.face > 0 ? .9 : Math.PI + .9); c.stroke();
    }
    c.restore(); c.globalAlpha = 1;
    // name tag
    c.font = '12px Silkscreen'; c.textAlign = 'center'; c.fillStyle = f.color;
    if (f.st !== 'dead') c.fillText(f.cpu ? 'CPU' : `P${f.slot + 1}`, gx, gy - f.y - figH - 12);
  }
  function drawShot(s) {
    const c = cx, x = s.x, y = groundY(s.z) - s.y;
    c.fillStyle = 'rgba(10,30,10,.3)'; c.beginPath(); c.ellipse(x, groundY(s.z), 12, 4, 0, 0, 7); c.fill();
    c.save(); c.translate(x, y); c.rotate(s.spin);
    c.fillStyle = '#1b1b22'; c.beginPath(); c.arc(0, 0, 13, 0, 7); c.fill();
    c.fillStyle = s.sp.color; c.beginPath(); c.arc(0, 0, 11, 0, 7); c.fill();
    c.fillStyle = 'rgba(255,255,255,.45)'; c.fillRect(-6, -7, 4, 4);
    c.fillStyle = s.sp.leaf; c.fillRect(-2, -15, 4, 6);
    c.restore();
    c.fillStyle = 'rgba(255,255,255,.35)'; for (let k = 1; k < 4; k++) c.fillRect(x - Math.sign(s.vx) * k * 12, y - 2, 6, 4);
  }
  function bar(x, y, w, h, v, max, col, ghost) {
    const c = cx; c.fillStyle = '#0a1120'; c.fillRect(x - 1, y - 1, w + 2, h + 2);
    if (ghost !== undefined) { c.fillStyle = '#fff3b0'; c.fillRect(x, y, w * Math.max(0, ghost) / max, h); }
    c.fillStyle = col; c.fillRect(x, y, w * Math.max(0, v) / max, h);
  }
  function drawHud() {
    const c = cx, n = fight.fighters.length, pw = Math.min(228, (W - 20) / n - 8);
    fight.fighters.forEach((f, i) => {
      const x = 10 + i * (pw + 8), y = 8;
      c.fillStyle = 'rgba(8,12,40,.78)'; c.fillRect(x, y, pw, 46);
      c.fillStyle = f.color; c.fillRect(x, y, 4, 46);
      c.font = '12px Silkscreen'; c.textAlign = 'left'; c.fillStyle = f.st === 'dead' ? '#777' : '#f5f0e0';
      c.fillText(f.label, x + 10, y + 15);
      c.textAlign = 'right'; c.fillStyle = '#9aa0c0'; c.fillText(f.cpu ? 'CPU' : schemeLabel(f.ctrl), x + pw - 6, y + 15);
      bar(x + 10, y + 22, pw - 18, 8, f.hp, f.hpMax, f.hp < f.hpMax * .3 ? '#ff6b5e' : '#e34c4c', f.hpShown);
      bar(x + 10, y + 34, pw - 18, 5, f.mp, f.mpMax, '#4aa8e8');
    });
    c.textAlign = 'center';
    if (fight.phase === 'intro') {
      const k = Math.min(3, Math.floor(fight.t / .5));
      c.font = '64px Silkscreen'; c.fillStyle = '#ffd21f';
      c.fillText(k < 3 ? String(3 - k) : (PL ? 'WALKA!' : 'FIGHT!'), W / 2, H * .42);
    } else if (fight.phase === 'fight' && fight.t < .6) {
      c.font = '64px Silkscreen'; c.fillStyle = `rgba(124,255,107,${1 - fight.t / .6})`; c.fillText(PL ? 'WALKA!' : 'FIGHT!', W / 2, H * .42);
    } else if (fight.phase === 'over') {
      c.fillStyle = 'rgba(8,12,40,.82)'; c.fillRect(W / 2 - 300, H * .26, 600, 170);
      c.font = '34px Silkscreen'; c.fillStyle = fight.winner.length ? '#7cff6b' : '#ffd21f';
      const names = fight.winner.map(f => f.def.name + (f.cpu ? ' (CPU)' : ` P${f.slot + 1}`));
      c.fillText(fight.winner.length ? (PL ? 'WYGRYWA' : 'WINNER') : (PL ? 'REMIS' : 'DRAW'), W / 2, H * .26 + 50);
      c.font = '20px Silkscreen'; c.fillStyle = '#f5f0e0'; c.fillText(names.join(' + '), W / 2, H * .26 + 88);
      c.font = '14px Silkscreen'; c.fillStyle = '#9aa0c0';
      c.fillText(fight.fighters.map(f => `${f.cpu ? 'CPU' : 'P' + (f.slot + 1)}: ${f.dealt} dmg, ${f.kos} KO`).join('   '), W / 2, H * .26 + 116);
      if (fight.overT > .8) { c.fillStyle = Math.floor(fight.overT * 3) % 2 ? '#ffd21f' : '#fff3b0'; c.fillText(PL ? 'ENTER / R — JESZCZE RAZ     ESC — MENU' : 'ENTER / R — AGAIN     ESC — MENU', W / 2, H * .26 + 150); }
    }
    if (fight.phase !== 'over') { c.font = '11px Silkscreen'; c.fillStyle = 'rgba(255,255,255,.7)'; c.fillText(PL ? 'ESC — MENU' : 'ESC — MENU', W / 2, H - 10); }
    c.textAlign = 'left';
  }
  function render() {
    if (!fight || !cx) return;
    const c = cx;
    c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, cvs.width, cvs.height);
    const k = Math.min(cvs.width / W, cvs.height / H), ox = (cvs.width - W * k) / 2, oy = (cvs.height - H * k) / 2;
    const sh = fight.shake > 0 ? (Math.random() - .5) * 10 : 0;
    c.setTransform(k, 0, 0, k, ox + sh * k, oy + sh * k * .5);
    if (!bg) bg = buildBackground();
    c.imageSmoothingEnabled = false; c.drawImage(bg, 0, 0, W, H);
    const items = [...fight.fighters.map(f => [f.z, () => drawFighter(f)]), ...fight.shots.map(s => [s.z + .5, () => drawShot(s)])];
    items.sort((a, b) => a[0] - b[0]).forEach(it => it[1]());
    for (const p of fight.fx) { c.fillStyle = p.color; c.globalAlpha = 1 - p.t / p.life; c.fillRect(p.x - 2, p.y - 2, 4, 4); }
    c.globalAlpha = 1; c.textAlign = 'center';
    for (const p of fight.pops) { c.font = '16px Silkscreen'; c.fillStyle = '#1b1b22'; c.fillText(p.text, p.x + 1, p.y + 1); c.fillStyle = p.color; c.fillText(p.text, p.x, p.y); }
    for (const b of fight.banners) { c.font = '18px Silkscreen'; c.globalAlpha = 1 - b.t / 1.1; const by = b.y - b.t * 20; c.fillStyle = '#1b1b22'; c.fillText(b.text, b.x + 2, by + 2); c.fillStyle = b.color; c.fillText(b.text, b.x, by); }
    c.globalAlpha = 1;
    drawHud();
  }
  function loop(ts) {
    raf = 0; if (!fight) return;
    const dt = Math.min(.1, (ts - (last || ts)) / 1000); last = ts; acc += dt;
    while (acc >= 1 / 60) { tick(1 / 60); acc -= 1 / 60; if (!fight) return; }
    render();
    raf = requestAnimationFrame(loop);
  }
  function showFightCanvas(on) {
    if (!ui) return;
    ui.lobby.hidden = on; cvs.hidden = !on;
    if (on) { resize(); last = 0; acc = 0; if (!raf) raf = requestAnimationFrame(loop); cvs.focus(); }
    else if (raf) { cancelAnimationFrame(raf); raf = 0; }
  }
  function resize() { if (!cvs) return; const d = Math.min(2, window.devicePixelRatio || 1); cvs.width = Math.round(innerWidth * d); cvs.height = Math.round(innerHeight * d); }
  window.addEventListener('resize', resize);

  /* ------------------------------------------------------------------ lobby UI */
  const T = PL ? {
    title: 'BIJATYKA', sub: 'Kilka osób przy jednej klawiaturze lub padach + komputer. Ostatnia drużyna na nogach wygrywa.',
    slot: 'GRACZ', type: { human: 'CZŁOWIEK', cpu: 'KOMPUTER', off: '—' }, team: { '': 'BEZ DRUŻYNY', A: 'DRUŻYNA A', B: 'DRUŻYNA B' },
    start: 'WALKA!', close: 'WYJDŹ', controls: 'STEROWANIE', reset: 'DOMYŚLNE KLAWISZE', press: 'naciśnij klawisz…',
    moves: 'Biegnij: 2× w bok · Combo: ATAK ×3 · Kopniak w locie: SKOK+ATAK · Specjalne: OBRONA, kierunek, ATAK',
    pads: 'Pad: krzyżak/gałka, X/□ atak, A/✕ skok, B/○ lub RB obrona',
    errFew: 'Potrzeba co najmniej 2 zawodników.', errSame: 'Dwóch graczy ma to samo sterowanie: ', errTeam: 'Wszyscy są w jednej drużynie.', errHuman: 'Dodaj co najmniej jednego człowieka.',
  } : {
    title: 'BRAWL', sub: 'Several people on one keyboard or gamepads, plus computer fighters. Last team standing wins.',
    slot: 'PLAYER', type: { human: 'HUMAN', cpu: 'COMPUTER', off: '—' }, team: { '': 'NO TEAM', A: 'TEAM A', B: 'TEAM B' },
    start: 'FIGHT!', close: 'LEAVE', controls: 'CONTROLS', reset: 'DEFAULT KEYS', press: 'press a key…',
    moves: 'Run: double-tap sideways · Combo: ATTACK ×3 · Flying kick: JUMP+ATTACK · Specials: DEFEND, direction, ATTACK',
    pads: 'Gamepad: d-pad/stick, X/□ attack, A/✕ jump, B/○ or RB defend',
    errFew: 'At least 2 fighters are needed.', errSame: 'Two players share the same controls: ', errTeam: 'Everyone is on one team.', errHuman: 'Add at least one human player.',
  };
  function validate() {
    const act = SLOTS.filter(s => s.type !== 'off');
    if (act.length < 2) return T.errFew;
    if (!act.some(s => s.type === 'human')) return T.errHuman;
    const used = {};
    for (const s of act) if (s.type === 'human') { if (used[s.ctrl]) return T.errSame + schemeLabel(s.ctrl); used[s.ctrl] = 1; }
    const teams = new Set(act.map((s, i) => s.team || `solo${i}`));
    if (teams.size < 2) return T.errTeam;
    return null;
  }
  function setLobbyError(msg) { const e = ui && ui.lobby.querySelector('#brawl-error'); if (e) e.textContent = msg || ''; }
  const css = {
    btn: 'min-height:40px;padding:6px 14px;border:2px solid #ffd21f;border-radius:6px;background:#263a61;color:#fff;font:bold 14px monospace;cursor:pointer',
    sel: 'min-height:34px;padding:4px;border:1px solid #9ba9c4;border-radius:4px;background:#0f1a33;color:#f8f3df;font:13px monospace',
    key: 'min-width:64px;min-height:30px;padding:2px 6px;border:1px solid #9ba9c4;border-radius:4px;background:#0f1a33;color:#ffd21f;font:bold 12px monospace;cursor:pointer',
  };
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const opt = (v, label, cur) => `<option value="${esc(v)}"${v === cur ? ' selected' : ''}>${esc(label)}</option>`;
  function renderLobby() {
    if (!ui) return;
    const slots = SLOTS.map((s, i) => `
      <div class="brawl-slot" data-slot="${i}" style="display:grid;grid-template-columns:auto 1fr 1fr 1fr 1fr;gap:6px;align-items:center;padding:6px;border-left:4px solid ${SLOT_COLORS[i]};background:#1c2b4d;border-radius:4px">
        <strong style="color:${SLOT_COLORS[i]};min-width:62px">P${i + 1}</strong>
        <select data-k="type" aria-label="${T.slot} ${i + 1}" style="${css.sel}">${['human', 'cpu', 'off'].map(v => opt(v, T.type[v], s.type)).join('')}</select>
        <select data-k="fighter" aria-label="fighter ${i + 1}" style="${css.sel}"${s.type === 'off' ? ' disabled' : ''}>${Object.keys(FIGHTERS).map(v => opt(v, FIGHTERS[v].name, s.fighter)).join('')}</select>
        <select data-k="ctrl" aria-label="controls ${i + 1}" style="${css.sel}"${s.type !== 'human' ? ' disabled' : ''}>${SCHEMES.map(v => opt(v, schemeLabel(v), s.ctrl)).join('')}</select>
        <select data-k="team" aria-label="team ${i + 1}" style="${css.sel}"${s.type === 'off' ? ' disabled' : ''}>${['', 'A', 'B'].map(v => opt(v, T.team[v], s.team)).join('')}</select>
      </div>`).join('');
    const rows = ACTIONS.map(a => `<tr><th style="text-align:left;padding:2px 8px;color:#c8cee0">${ACTION_LABEL[a]}</th>${Object.keys(KEYS).map(s => {
      const on = rebinding && rebinding.scheme === s && rebinding.action === a;
      return `<td style="padding:2px"><button type="button" data-rebind="${s}:${a}" style="${css.key}${on ? ';background:#ffd21f;color:#172442' : ''}">${on ? T.press : esc(keyName(KEYS[s][a]))}</button></td>`;
    }).join('')}</tr>`).join('');
    ui.lobby.innerHTML = `<section style="box-sizing:border-box;width:min(96vw,820px);max-height:94vh;overflow:auto;padding:clamp(12px,3vw,24px);border:3px solid #9b3fe0;border-radius:10px;background:#172442;box-shadow:0 12px 45px #0009">
      <h2 style="margin:0 0 6px;font-size:clamp(20px,5vw,32px);color:#e8c8ff;text-align:center;letter-spacing:2px">${T.title}</h2>
      <p style="margin:0 0 14px;text-align:center;line-height:1.4;color:#c8cee0">${T.sub}</p>
      <div style="display:grid;gap:6px">${slots}</div>
      <p id="brawl-error" role="alert" style="min-height:1.3em;margin:10px 0;color:#ff6b5e;text-align:center"></p>
      <div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:14px">
        <button id="brawl-start" type="button" style="${css.btn};border-color:#7cff6b;font-size:17px">${T.start}</button>
        <button id="brawl-close" type="button" style="${css.btn}">${T.close}</button>
      </div>
      <details id="brawl-controls"${ui.controlsOpen ? ' open' : ''} style="border-top:1px solid #34476e;padding-top:10px">
        <summary style="cursor:pointer;color:#ffd21f;font-weight:bold">${T.controls}</summary>
        <div style="overflow-x:auto"><table style="margin:10px auto;border-collapse:collapse">
          <tr><th></th>${Object.keys(KEYS).map(s => `<th style="padding:2px 6px;color:#e8c8ff;font-size:12px">${schemeLabel(s)}</th>`).join('')}</tr>${rows}</table></div>
        <p style="margin:4px 0;text-align:center;font-size:12px;color:#9aa0c0">${T.pads}</p>
        <div style="text-align:center;margin-top:8px"><button id="brawl-reset-keys" type="button" style="${css.btn};min-height:32px;font-size:12px">${T.reset}</button></div>
      </details>
      <p style="margin:12px 0 0;text-align:center;font-size:12px;line-height:1.5;color:#9aa0c0">${T.moves}</p>
    </section>`;
    ui.lobby.querySelectorAll('.brawl-slot select').forEach(sel => sel.addEventListener('change', () => {
      const i = +sel.closest('.brawl-slot').dataset.slot; SLOTS[i][sel.dataset.k] = sel.value; writeLS(LS_SLOTS, SLOTS); renderLobby();
    }));
    ui.lobby.querySelectorAll('[data-rebind]').forEach(b => b.addEventListener('click', () => {
      const [scheme, action] = b.dataset.rebind.split(':'); rebinding = { scheme, action }; renderLobby();
    }));
    ui.lobby.querySelector('#brawl-controls').addEventListener('toggle', e => { ui.controlsOpen = e.target.open; });
    ui.lobby.querySelector('#brawl-start').addEventListener('click', () => startFight());
    ui.lobby.querySelector('#brawl-close').addEventListener('click', closeBrawl);
    ui.lobby.querySelector('#brawl-reset-keys').addEventListener('click', () => { KEYS = clone(DEFAULT_KEYS); writeLS(LS_KEYS, KEYS); rebinding = null; renderLobby(); });
    setLobbyError(validate() && SLOTS.some(s => s.type !== 'off') ? validate() : '');
  }
  function openBrawl() {
    if (ui) return;
    const root = document.createElement('div');
    root.id = 'brawl-overlay'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-label', T.title);
    root.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(8,12,24,.9);font:15px monospace;color:#f8f3df';
    const lobby = document.createElement('div'); lobby.id = 'brawl-lobby';
    lobby.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:8px';
    cvs = document.createElement('canvas'); cvs.id = 'brawl-canvas'; cvs.tabIndex = 0; cvs.hidden = true;
    cvs.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;background:#0b1020;outline:none';
    cx = cvs.getContext('2d');
    root.append(lobby, cvs); document.body.appendChild(root);
    ui = { root, lobby, controlsOpen: false };
    held.clear(); edges.length = 0; if (A.keys && A.keys.clear) A.keys.clear();
    Object.keys(FIGHTERS).forEach(id => loadFighterArt(id).catch(() => {}));
    renderLobby();
    const st = lobby.querySelector('#brawl-start'); if (st) st.focus();
  }
  function closeBrawl() {
    fight = null; rebinding = null; if (raf) cancelAnimationFrame(raf); raf = 0;
    if (ui) ui.root.remove(); ui = null; cvs = null; cx = null; held.clear(); edges.length = 0;
  }

  /* ------------------------------------------------------------------ hooks into the village */
  A.HOOKS.near.push(() => (!venue || ui || A.HOOKS.busy.some(f => f()) ? [] : [{ x: venue.x, y: venue.y, r: 30, _brawl: true, onInteract: openBrawl }]));
  A.HOOKS.busy.push(() => !!ui);
  A.HOOKS.world.push((push, S, inView) => {
    if (!venue || !inView(venue.x, venue.y)) return;
    push(venue.y, () => { const [sx, sy] = S(venue.x, venue.y); drawFlag(sx, sy, A.zoom); });
  });
  A.HOOKS.minimap.push(dot => { if (venue) dot(venue.x, venue.y, '#9b3fe0'); });

  // API for tests and future tweaks
  A.brawl = {
    FIGHTERS, MOVES, open: openBrawl, close: closeBrawl, start: startFight, end: endFight, validate,
    get venue() { return venue ? { ...venue } : null; }, get fight() { return fight; }, get ui() { return ui; },
    get keys() { return clone(KEYS); }, get slots() { return clone(SLOTS); },
    setSlots(s) { SLOTS = s.map(x => ({ ...x })); writeLS(LS_SLOTS, SLOTS); renderLobby(); },
    setKey(scheme, action, code) { setKey(scheme, action, code); renderLobby(); },
    step(n = 1) { for (let i = 0; i < n && fight; i++) tick(1 / 60); render(); },
    loaded: () => Promise.all(Object.keys(FIGHTERS).map(loadFighterArt)),
  };
});
