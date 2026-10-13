/* BIEG NA 100 METRÓW — the first board on docs/js/board.js (plan: plans/2026-10-12-sprint-board-minigame.md).
   Up to four runners on a straight 100 m along the village road. Each player has a LEFT and a
   RIGHT key: pressing them alternately is a stride, so speed ≈ stride length × cadence. The same
   key twice is a stumble (speed drops, short pause). False start (any key before START): the
   first one is a warning, the second adds 2 s to that runner's time.
   Every runner records a trace: the time at 10, 20, ... 100 m. The PRZECIĘTNIAK CPU replays the averaged
   trace of past runs (global from cloud/api, else this computer's), other CPUs the same trace a little
   faster or slower. Without any trace a CPU follows a smooth curve to its target time. CPUs never read input.
   The background is the BIJATYKA road stage, read from ARK.brawl.STAGES.road when available and
   only used as a wide scrolling backdrop (no house positions assumed), so a changed road art or
   size does not break the sprint. */
'use strict';
(() => {
  const DIST = 100;                 // metres
  const SPLITS = 10;                // trace checkpoints: every 10 m
  const MPX = 40;                   // board px per metre
  const X0 = 110;                   // start line x when the camera is at 0
  const STRIDE = 1.05;              // metres per stride at a steady cadence: v ≈ STRIDE × strides/s
  const DRAG = 1.6;                 // 1/s, exponential slowdown between strides
  const GAIN = STRIDE * DRAG;       // speed added per stride (m/s)
  const VMAX = 11;                  // m/s cap (~9.6 s best)
  const STUMBLE_T = .22, STUMBLE_K = .7, PENALTY = 2, DNF_T = 45;
  const SCALE = .8;
  let BG = { src: null, img: null, road: null };
  // Find the asphalt band in the road art: low-saturation grey rows in the lower half, measured on the first
  // ~2000 px. Returns [top, bottom] as fractions of the image height, or null to use the stage's ground line.
  function findRoad(img) {
    try {
      const w = Math.min(img.width, 2000), h = img.height, cv = document.createElement('canvas'); cv.width = 64; cv.height = h;
      const g = cv.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0, w, h, 0, 0, 64, h);
      const d = g.getImageData(0, 0, 64, h).data, grey = [];
      for (let y = 0; y < h; y++) { let n = 0; for (let x = 0; x < 64; x++) { const i = (y * 64 + x) * 4, r = d[i], gg = d[i + 1], b = d[i + 2], mx = Math.max(r, gg, b), mn = Math.min(r, gg, b); if (mx - mn < 28 && mx > 50 && mx < 200) n++; } grey.push(n / 64 > .6); }
      let best = null;
      for (let y = Math.floor(h * .4); y < h; y++) if (grey[y]) { let e = y; while (e + 1 < h && grey[e + 1]) e++; if (!best || e - y > best[1] - best[0]) best = [y, e]; y = e; }
      return best && best[1] - best[0] > h * .05 ? [best[0] / h, (best[1] + 1) / h] : null;
    } catch (e) { return null; }
  }

  function create(api) {
    const { A, PL, W, H, players, drawSprite, sfx } = api;
    const stage = (A.brawl && A.brawl.STAGES && A.brawl.STAGES.road) || {};
    const src = stage.img || 'img/brawl/stage_road.webp';
    if (BG.src !== src) { BG = { src, img: null, road: null }; A.load(src).then(i => { if (BG.src === src) { BG.img = i; BG.road = findRoad(i); } }).catch(() => {}); }
    // Runners use the road art itself: two on the asphalt, two on the grass in front of it (like BIJATYKA's depth).
    // The asphalt band is measured from the image, so a redrawn or resized road stage still lines up.
    const roadTop = () => H * (BG.road ? BG.road[0] : Math.max(.45, (Number.isFinite(stage.top) ? stage.top : .51) + .01));
    const roadBot = () => H * (BG.road ? BG.road[1] : Math.max(.45, (Number.isFinite(stage.top) ? stage.top : .51) + .01) + .15);
    const footY = lane => { const t = roadTop(), b = roadBot(); return [t + (b - t) * .45, t + (b - t) * .95, b + (H - b) * .4, b + (H - b) * .82][lane]; };
    const TX = PL ? {
      mark: 'NA MIEJSCA!', set: 'GOTOWI...', go: 'START!', warn: 'FALSTART! OSTRZEŻENIE', pen: 'FALSTART! +2 s', stumble: 'POTKNIĘCIE!',
      noteWarn: 'falstart: ostrzeżenie', notePen: '+2 s za falstart', done: 'META', m: 'm',
    } : {
      mark: 'ON YOUR MARKS!', set: 'GET SET...', go: 'GO!', warn: 'FALSE START! WARNING', pen: 'FALSE START! +2 s', stumble: 'STUMBLE!',
      noteWarn: 'false start: warning', notePen: '+2 s false start', done: 'FINISH', m: 'm',
    };
    const R = players.map(p => {
      const r = { p, d: 0, v: 0, last: null, strides: 0, stumble: 0, fs: 0, penalty: 0, finish: null, msg: null, msgT: 0, bob: 0, splits: [] };
      if (p.cpu && Array.isArray(p.cpuTrace) && p.cpuTrace.length === SPLITS && p.cpuTrace.every((v, i) => v > (i ? p.cpuTrace[i - 1] : 0))) {
        r.trace = p.cpuTrace.slice(); r.target = r.trace[SPLITS - 1];   // replay an (averaged) recorded run
      } else if (p.cpu) {   // smooth curve d(t) = vtop * (t - tau * (1 - e^(-t/tau))), finishing exactly at the target time
        r.react = .14 + Math.random() * .1; r.tau = .9;
        r.target = Math.max(8.8, Math.min(30, p.cpuScore));
        const tr = r.target - r.react; r.vtop = DIST / (tr - r.tau * (1 - Math.exp(-tr / r.tau)));
      }
      return r;
    });
    const by = slot => R.find(r => r.p.slot === slot);
    const countLen = 2 + .4 + Math.random();   // NA MIEJSCA 1 s, GOTOWI 1 s, then a random hold so nobody can time the gun
    let time = 0, cam = 0, tape = null, firstDone = false;
    const say = (r, msg) => { r.msg = msg; r.msgT = 1.6; };

    function cpuAt(r, t) {
      if (r.trace) {   // piecewise through the checkpoints; the first 10 m accelerate from standing
        const tr = r.trace, seg = DIST / SPLITS;
        if (t <= 0) return [0, 0];
        if (t < tr[0]) { const u = t / tr[0]; return [seg * Math.pow(u, 1.4), seg * 1.4 * Math.pow(u, .4) / tr[0]]; }
        for (let i = 1; i < SPLITS; i++) if (t < tr[i]) { const v = seg / (tr[i] - tr[i - 1]); return [seg * i + v * (t - tr[i - 1]), v]; }
        const v = seg / (tr[SPLITS - 1] - tr[SPLITS - 2]); return [DIST + v * (t - tr[SPLITS - 1]), v];
      }
      const u = t - r.react; if (u <= 0) return [0, 0];
      return [r.vtop * (u - r.tau * (1 - Math.exp(-u / r.tau))), r.vtop * (1 - Math.exp(-u / r.tau))];
    }
    function crossed(r, prevD, prevT, dt) {   // exact crossing times within the tick: 10 m checkpoints, then the line
      while (r.splits.length < SPLITS && r.d >= (r.splits.length + 1) * DIST / SPLITS) {
        const m = (r.splits.length + 1) * DIST / SPLITS;
        r.splits.push(prevT + dt * (m - prevD) / Math.max(1e-6, r.d - prevD));
      }
      if (r.finish !== null || r.d < DIST) return;
      r.finish = prevT + dt * (DIST - prevD) / Math.max(1e-6, r.d - prevD);
      if (!firstDone) { firstDone = true; tape = { t: 0 }; sfx('finish'); }
    }
    function update(dt, ev, phase) {
      for (const r of R) { r.msgT = Math.max(0, r.msgT - dt); }
      if (phase === 'count') {
        for (const e of ev) {
          const r = by(e.slot); if (!r || r.p.cpu) continue;
          r.fs++;
          if (r.fs === 1) { say(r, TX.warn); sfx('false'); }
          else if (r.fs === 2) { r.penalty = PENALTY; say(r, TX.pen); sfx('false'); }
        }
      } else if (phase === 'run') {
        const prevT = time; time += dt;
        for (const e of ev) {
          const r = by(e.slot); if (!r || r.p.cpu || r.finish !== null || r.dnf) continue;
          if (r.stumble > 0) continue;
          if (r.last === null || e.action !== r.last) { r.v = Math.min(VMAX, r.v + GAIN); r.strides++; r.last = e.action; sfx('step'); }
          else { r.v *= STUMBLE_K; r.stumble = STUMBLE_T; say(r, TX.stumble); sfx('stumble'); }
        }
        for (const r of R) {
          const prevD = r.d;
          if (r.p.cpu && r.finish === null) { [r.d, r.v] = cpuAt(r, time); r.strides = Math.floor(r.d / STRIDE); }
          else if (r.finish === null && !r.dnf) { r.v *= Math.exp(-DRAG * dt); r.d += r.v * dt; r.stumble = Math.max(0, r.stumble - dt); }
          else { r.v *= Math.exp(-2.2 * dt); r.d += r.v * dt; }   // run-out after the line
          crossed(r, prevD, prevT, dt);
          if (!r.p.cpu && r.finish === null && time >= DNF_T) r.dnf = true;
        }
      } else {
        for (const r of R) { r.v *= Math.exp(-2.2 * dt); r.d += r.v * dt; }
      }
      for (const r of R) r.bob += r.v * dt;
      if (tape) tape.t += dt;
      const lead = Math.min(DIST + 6, Math.max(...R.map(r => r.d)));
      const target = Math.max(0, Math.min(lead * MPX + X0 - W * .62, (DIST + 5) * MPX + X0 - W * .8));
      cam += (target - cam) * Math.min(1, dt * 6);
    }
    const humansDone = () => R.filter(r => !r.p.cpu).every(r => r.finish !== null || r.dnf);
    let humansDoneAt = null;
    function finished() {
      if (!humansDone()) return false;
      if (humansDoneAt === null) humansDoneAt = time;
      return R.every(r => r.finish !== null || r.dnf) || time - humansDoneAt >= 2.5;
    }
    function results() {
      return R.map(r => {
        // a CPU still running when everyone else is done gets its own deterministic finish time
        const fin = r.finish !== null ? r.finish : r.p.cpu ? r.target : null;
        return { slot: r.p.slot, score: fin === null ? null : fin + r.penalty, note: r.penalty ? TX.notePen : r.fs ? TX.noteWarn : '',
          trace: !r.p.cpu && r.splits.length === SPLITS ? r.splits.map(v => Math.round(v * 100) / 100) : null, proof: { strides: r.strides, falseStarts: r.fs } };
      });
    }

    /* ------------------------------------------------------------------ drawing */
    const sx = d => X0 + d * MPX - cam;
    function drawBackground(c) {
      const img = BG.img;
      if (img && img.width && img.height) {
        const k = img.height / H, vw = W * k, span = Math.max(1, img.width - vw);
        let x = (cam * k) % (2 * span); if (x > span) x = 2 * span - x;   // the ground moves with the runners; ping-pong if the road art is ever shorter than the run
        c.imageSmoothingEnabled = true; c.drawImage(img, x, 0, vw, img.height, 0, 0, W, H);
      } else {
        const g = c.createLinearGradient(0, 0, 0, roadTop()); g.addColorStop(0, '#6fb6e8'); g.addColorStop(1, '#cfe9f2');
        const t = roadTop(), b = roadBot();
        c.fillStyle = g; c.fillRect(0, 0, W, t); c.fillStyle = '#6d6b6e'; c.fillRect(0, t, W, b - t); c.fillStyle = '#6aa83a'; c.fillRect(0, b, W, H - b);
      }
    }
    function drawTrack(c) {   // no painted lanes: chalk start line, small distance posts, chequered finish with a tape
      const t = roadTop(), b = roadBot(), y0 = t + 2, y1 = H - 6;
      for (let m = 10; m < DIST; m += 10) {   // little white posts at the far edge of the road every 10 m
        const x = sx(m); if (x < -30 || x > W + 30) continue;
        c.fillStyle = 'rgba(10,20,10,.35)'; c.fillRect(Math.round(x) - 3, t, 8, 2);
        c.fillStyle = '#f5f0e0'; c.fillRect(Math.round(x) - 2, t - 16, 5, 16); c.fillStyle = '#d8262c'; c.fillRect(Math.round(x) - 2, t - 16, 5, 3);
        c.font = '10px PixelifySans'; c.textAlign = 'center'; c.fillStyle = '#10141f'; c.fillText(`${m}`, x + 1, t - 19); c.fillStyle = '#fff'; c.fillText(`${m}`, x, t - 20);
      }
      const s0 = sx(0);
      if (s0 > -10 && s0 < W + 10) { c.fillStyle = 'rgba(255,255,255,.85)'; c.fillRect(Math.round(s0) - 2, y0, 4, b - y0); c.fillStyle = 'rgba(255,255,255,.55)'; c.fillRect(Math.round(s0) - 2, b, 4, y1 - b); }
      const f = sx(DIST);
      if (f > -40 && f < W + 40) {
        for (let y = y0, k = 0; y < y1; y += 6, k++) for (let j = 0; j < 2; j++) { c.fillStyle = (k + j) % 2 ? 'rgba(17,17,17,.9)' : 'rgba(245,245,245,.9)'; c.fillRect(Math.round(f) - 6 + j * 6, y, 6, Math.min(6, y1 - y)); }
        // two posts with a META banner on the far one; the tape snaps when the first runner breaks it
        c.fillStyle = '#5a3a1e'; c.fillRect(Math.round(f) + 6, t - 46, 3, 46); c.fillRect(Math.round(f) + 6, y1 - 50, 3, 50);
        c.fillStyle = 'rgba(8,12,40,.85)'; c.fillRect(f - 22, t - 62, 56, 16);
        c.font = '12px PixelifySans'; c.textAlign = 'center'; c.fillStyle = '#ffd21f'; c.fillText(TX.done, f + 6, t - 50);
        c.strokeStyle = '#e8262c'; c.lineWidth = 2; const ta = t - 20, tb = y1 - 30;
        if (!tape) { c.beginPath(); c.moveTo(f + 8, ta); c.lineTo(f + 8, tb); c.stroke(); }
        else if (tape.t < 1.2) { const a = Math.min(1, tape.t * 3); c.globalAlpha = 1 - tape.t / 1.2; c.beginPath(); c.moveTo(f + 8, ta); c.lineTo(f + 8 + 30 * a, ta + 30 + 20 * a); c.moveTo(f + 8, tb); c.lineTo(f + 8 + 30 * a, tb - 30 - 20 * a); c.stroke(); c.globalAlpha = 1; }
      }
      c.textAlign = 'left';
    }
    function frameOf(r, phase) {
      if (phase === 'count' || (r.v < .3 && r.finish === null)) return ['stand'];
      if (r.stumble > 0) return ['hurt', 'stand'];
      if (r.finish !== null && r.v < 1.5) return r === winner() ? ['win', 'stand'] : ['stand'];
      const odd = r.strides % 2 === 1;
      return r.v > 4 ? [odd ? 'run1' : 'run2', 'run1', 'walk1'] : [odd ? 'walk1' : 'walk2', 'walk1', 'stand'];
    }
    function winner() { let w = null; for (const r of R) if (r.finish !== null && (!w || r.finish + r.penalty < w.finish + w.penalty)) w = r; return w; }
    function drawRunners(c, phase) {
      for (const r of [...R].sort((a, b) => a.p.lane - b.p.lane)) {
        const x = sx(r.d), y = footY(r.p.lane);
        if (x < -40 || x > W + 40) {   // off-screen: edge marker with the gap to the leader
          const left = x < 0, ex = left ? 6 : W - 6, lead = Math.max(...R.map(o => o.d));
          c.font = '11px PixelifySans'; c.textAlign = left ? 'left' : 'right'; c.fillStyle = 'rgba(8,12,40,.75)';
          const label = `${left ? '◀ ' : ''}${r.p.cpu ? 'CPU' : 'P' + (r.p.slot + 1)} ${left ? '-' + Math.round(lead - r.d) + ' ' + TX.m : ''}${left ? '' : ' ▶'}`;
          const tw = c.measureText(label).width + 8; c.fillRect(left ? ex - 2 : ex - tw + 2, y - 40, tw, 16);
          c.fillStyle = r.p.color; c.fillText(label, ex + (left ? 2 : -2), y - 28); c.textAlign = 'left';
          continue;
        }
        c.fillStyle = 'rgba(10,20,10,.35)'; c.beginPath(); c.ellipse(x, y, 20, 5, 0, 0, 7); c.fill();
        const hop = r.v > 1 && r.finish === null ? -Math.abs(Math.sin(r.bob * 1.5)) * 3 : 0;
        if (!drawSprite(c, r.p.atlas, frameOf(r, phase), x, y + hop, 1, SCALE)) { c.fillStyle = r.p.color; c.fillRect(x - 10, y - 70, 20, 70); }
        const tag = r.p.tag || (r.p.cpu ? 'CPU' : `P${r.p.slot + 1}`);
        c.font = '10px PixelifySans'; c.textAlign = 'center'; c.fillStyle = '#10141f'; c.fillText(tag, x + 1, y - 87); c.fillStyle = r.p.color; c.fillText(tag, x, y - 88);
        if (r.msgT > 0) { c.globalAlpha = Math.min(1, r.msgT * 2); c.font = '12px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(r.msg, x + 1, y - 101); c.fillStyle = '#ff9a5e'; c.fillText(r.msg, x, y - 102); c.globalAlpha = 1; }
        c.textAlign = 'left';
      }
    }
    const fmt = v => v.toFixed(2);
    function drawHud(c, phase, t) {
      const n = R.length, gap = 6, pw = Math.min(232, (W - 20 - gap * (n - 1)) / n);
      R.forEach((r, i) => {
        const x = 10 + i * (pw + gap), y = 6, p = r.p;
        c.fillStyle = 'rgba(8,12,40,.82)'; c.fillRect(x, y, pw, 52); c.fillStyle = p.color; c.fillRect(x, y, pw, 2);
        c.font = '11px PixelifySans'; c.textAlign = 'left'; c.fillStyle = '#f5f0e0'; c.fillText(p.name.slice(0, 14), x + 6, y + 15);
        c.textAlign = 'right'; c.fillStyle = p.color; c.fillText(p.tag || (p.cpu ? 'CPU' : `P${p.slot + 1}`), x + pw - 6, y + 15);
        if (!p.cpu) {   // which key comes next: the one you did not press last
          const kl = api.keyLabel(p, 'left'), kr = api.keyLabel(p, 'right'), next = r.last === 'left' ? 'right' : r.last === 'right' ? 'left' : null;
          c.textAlign = 'left'; c.font = '12px PixelifySans';
          c.fillStyle = next === 'right' ? 'rgba(255,255,255,.35)' : '#ffd21f'; c.fillText(kl, x + 6, y + 31);
          c.fillStyle = next === 'left' ? 'rgba(255,255,255,.35)' : '#ffd21f'; c.fillText(kr, x + 6 + c.measureText(kl + '  ').width, y + 31);
        }
        c.textAlign = 'right'; c.font = '11px PixelifySans'; c.fillStyle = '#c8cee0';
        const right = r.finish !== null ? `${fmt(r.finish + r.penalty)} s` : r.dnf ? '—' : `${Math.min(DIST, Math.floor(r.d))} ${TX.m}`;
        c.fillText(right, x + pw - 6, y + 31);
        c.fillStyle = '#0a1120'; c.fillRect(x + 6, y + 38, pw - 12, 7);
        c.fillStyle = r.stumble > 0 ? '#ff6b5e' : p.color; c.fillRect(x + 6, y + 38, (pw - 12) * Math.min(1, r.v / VMAX), 7);
        if (r.penalty || r.fs) { c.fillStyle = r.penalty ? '#ff6b5e' : '#ffd21f'; c.font = '10px PixelifySans'; c.textAlign = 'center'; c.fillText(r.penalty ? '+2 s' : '!', x + pw * .56, y + 31); }
      });
      c.textAlign = 'center';
      c.font = '26px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(fmt(time), W / 2 + 2, 92); c.fillStyle = '#fff'; c.fillText(fmt(time), W / 2, 90);
      if (phase === 'count') {
        const txt = t < 1 ? TX.mark : TX.set;
        c.font = '44px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(txt, W / 2 + 3, H * .38 + 3); c.fillStyle = '#ffd21f'; c.fillText(txt, W / 2, H * .38);
      } else if (phase === 'run' && t < .7) {
        c.font = '64px PixelifySans'; c.fillStyle = `rgba(124,255,107,${1 - t / .7})`; c.fillText(TX.go, W / 2, H * .4);
      }
      c.textAlign = 'left';
    }
    function draw(c, phase, t) { drawBackground(c); drawTrack(c); drawRunners(c, phase); drawHud(c, phase, t); }
    function go() { time = 0; sfx('gun'); }
    function debug() {
      return { countLen, time, cam, road: BG.road, feet: [0, 1, 2, 3].map(footY), runners: R.map(r => ({ slot: r.p.slot, cpu: r.p.cpu, name: r.p.name, d: r.d, v: r.v, strides: r.strides, last: r.last,
        stumble: r.stumble, falseStarts: r.fs, penalty: r.penalty, finish: r.finish, dnf: !!r.dnf, target: r.target || null, replay: !!r.trace, splits: r.splits.slice() })) };
    }
    return { countLen, update, go, finished, results, draw, debug };
  }

  window.ARK_BOARD_REGISTER({
    id: 'sprint', host: 'damian', global: true,
    title: PL => (PL ? 'BIEG NA 100 METRÓW' : '100 METRE SPRINT'),
    sub: PL => (PL
      ? 'Prosto drogą przez wieś. Naciskaj NA ZMIANĘ lewy i prawy klawisz: im szybciej, tym szybciej biegniesz. Dwa razy ten sam = potknięcie. Falstart: pierwszy raz ostrzeżenie, drugi +2 s.'
      : 'Straight down the village road. Press your LEFT and RIGHT keys alternately: the faster, the faster you run. The same key twice = stumble. False start: first a warning, then +2 s.'),
    logName: PL => (PL ? 'Bieg na 100 m' : '100 m sprint'),
    intro: PL => (PL
      ? ['Damian: „Bieg na sto metrów, prosto drogą przez wieś! Do czterech osób, ludzie albo komputer.”', 'Damian: „Klikaj NA ZMIANĘ lewy i prawy klawisz. Dwa razy ten sam to potknięcie, a za falstart jest kara.”']
      : ['Damian: "A hundred metres, straight down the village road! Up to four runners, people or computer."', 'Damian: "Press left and right ALTERNATELY. The same key twice trips you up, and a false start costs you."']),
    flagLabel: '100 M', flagColors: ['#1b1b1b', '#f5f0e0'],
    actions: ['left', 'right'],
    keys: { kb1: { left: 'KeyQ', right: 'KeyW' }, kb2: { left: 'KeyV', right: 'KeyB' }, kb3: { left: 'KeyO', right: 'KeyP' }, kb4: { left: 'ArrowLeft', right: 'ArrowRight' } },
    score: { unit: 'time', lower: true, medals: [16, 13, 11], cpuDefault: 15, traceLen: 10, format: v => `${v.toFixed(2)} s` },
    venue(A) {
      const M = A.MAP;
      if (M.sprint) return { x: M.sprint.x, y: M.sprint.y };
      if (M.track) return { x: M.track.cx - 30, y: M.track.cy + M.track.ry + M.track.w / 2 + 22 };   // pre-2026-10-12 map data
      return null;
    },
    create,
  });
})();
