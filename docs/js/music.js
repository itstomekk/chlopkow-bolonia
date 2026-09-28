/* MUZYKA — procedural 8-bit Polish folk chiptune for Arek w Chłopkowie. No audio files: everything is synthesised
   live with WebAudio (NES-style pulse leads, triangle bass, noise drums, a bagpipe drone).
   Tracks (all original tunes written in folk-dance idioms):
     krakowiak — 2/4, syncopated 16th-8th-16th "hop" rhythm, G major with a Góral raised-4th (C#) in part B  (village)
     mazurka   — 3/4, dotted first beat, accents on 2 and 3, C major                                         (title, village alt.)
     oberek    — fast 3/4 whirling eighths, um-pa-PA accompaniment, D major                                   (minigames)
     pastoralka— slow 3/4 lullaby, soft organ-like pads, F major                                              (church, memories)
   Every pass is re-arranged: section order, a second fiddle in thirds, octave jumps, grace notes and drum fills
   are chosen at random, so the loop never repeats exactly.
   K toggles the music ("kapela"); the choice is remembered. ?music=0 disables it for a session.
   Browsers only allow audio after a user gesture, so the engine starts on the first key press or tap. */
'use strict';
(() => {
  const OFF_PARAM = new URLSearchParams(location.search).get('music') === '0';
  const MUTE_KEY = 'arek-music-muted';
  let muted = OFF_PARAM; try { if (localStorage.getItem(MUTE_KEY) === '1') muted = true; } catch (e) { }

  /* ------------------------------------------------------------------ notes & songs
     Melody tokens are "NOTE:len" with len in 16th-note steps; "-" is a rest. Chords are one symbol per bar. */
  const SEMI = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const midi = n => { const m = /^([A-G])([#b]?)(-?\d)$/.exec(n); return 12 * (+m[3] + 1) + SEMI[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0); };
  const freq = m => 440 * Math.pow(2, (m - 69) / 12);
  const parse = s => s.trim().split(/\s+/).map(t => { const [n, l] = t.split(':'); return { m: n === '-' ? null : midi(n), len: +(l || 2) }; });
  const CHORD = { // root (octave 3) + intervals
    C: [48, [0, 4, 7]], D: [50, [0, 4, 7]], E: [52, [0, 4, 7]], F: [53, [0, 4, 7]], G: [43, [0, 4, 7]], A: [45, [0, 4, 7]], Bb: [46, [0, 4, 7]],
    Em: [52, [0, 3, 7]], Bm: [47, [0, 3, 7]], Dm: [50, [0, 3, 7]], A7: [45, [0, 4, 7, 10]], D7: [50, [0, 4, 7, 10]], G7: [43, [0, 4, 7, 10]],
  };

  const SONGS = {
    krakowiak: {
      bpm: 126, bar: 8, beat: 4, key: 7, scale: [0, 2, 4, 5, 7, 9, 11], drone: [43, 50], drums: 'krakowiak', acc: 'polka',
      A: { chords: 'G D G D G C D G', mel: `
        D5:1 G5:2 D5:1 B4:2 G4:2   F#4:1 A4:2 D5:1 C5:2 A4:2   B4:1 D5:2 G5:1 F#5:1 E5:1 D5:2   C5:2 A4:2 F#4:2 D4:2
        G4:1 B4:2 D5:1 G5:2 B5:2   A5:1 G5:2 E5:1 C5:2 E5:2    D5:1 F#5:2 A5:1 G5:1 F#5:1 E5:1 F#5:1   G5:2 G4:2 G5:2 -:2` },
      B: { chords: 'C G C D G A7 D G', mel: `
        E5:1 G5:2 E5:1 C5:2 E5:2   D5:1 G5:2 D5:1 B4:2 D5:2    E5:1 G5:2 A5:1 G5:1 F#5:1 E5:2   F#5:2 A5:2 F#5:2 D5:2
        B4:1 C#5:1 D5:2 B4:1 C#5:1 D5:2   E5:1 C#5:2 E5:1 A5:2 G5:2   F#5:1 E5:1 D5:1 C#5:1 D5:2 A4:2   G5:2 D5:2 G4:2 -:2` },
      forms: ['AABA', 'ABAB', 'AABB'],
    },
    mazurka: {
      bpm: 138, bar: 12, beat: 4, key: 0, scale: [0, 2, 4, 5, 7, 9, 11], drone: null, drums: 'mazurka', acc: 'mazurka',
      A: { chords: 'C G C G F C G C', mel: `
        E5:3 D5:1 C5:4 G5:4   F5:3 E5:1 D5:4 B4:4   C5:3 D5:1 E5:2 F5:2 G5:4   A5:4 G5:4 -:4
        A5:3 G5:1 F5:4 A5:4   G5:3 F5:1 E5:4 C5:4   D5:3 E5:1 F5:2 E5:2 D5:2 B4:2   C5:4 G4:4 C5:4` },
      B: { chords: 'Am Em F C Dm G C G7', mel: `
        A4:3 B4:1 C5:4 E5:4   B4:3 C5:1 D5:4 G5:4   A5:3 G5:1 F5:2 E5:2 F5:4   E5:3 D5:1 C5:4 G4:4
        F5:3 E5:1 D5:4 A5:4   G5:3 F5:1 D5:4 B4:4   E5:3 D5:1 C5:2 D5:2 E5:4   D5:4 G5:4 -:4` },
      forms: ['AABA', 'ABAB'],
    },
    oberek: {
      bpm: 188, bar: 12, beat: 4, key: 2, scale: [0, 2, 4, 5, 7, 9, 11], drone: [50, 57], drums: 'oberek', acc: 'oberek',
      A: { chords: 'D A A D D G A D', mel: `
        A4 D5 F#5 A5 F#5 D5   E5 C#5 A4 C#5 E5 A5   G5 F#5 E5 D5 C#5 E5   F#5:4 D5:2 A4:4 -:2
        A4:1 B4:1 A4:2 F#4:2 A4:2 D5:2 F#5:2   G5 B5 G5 D5 B4 G5   F#5 E5 A5 G5 E5 C#5   D5:4 D5:2 D6:4 -:2` },
      B: { chords: 'G D A D G D A D', mel: `
        B5 A5 G5 A5 B5 G5   A5 F#5 D5 F#5 A5 F#5   G5 E5 C#5 E5 A4 C#5   D5:4 F#5:2 A5:4 -:2
        B4 D5 G5 B4 D5 G5   A4 D5 F#5 A4 D5 F#5   E5 G5 E5 C#5 A4 C#5   D5:4 A4:2 D5:4 -:2` },
      forms: ['AABB', 'ABAB', 'AAB'],
    },
    pastoralka: {
      bpm: 74, bar: 12, beat: 4, key: 5, scale: [0, 2, 4, 5, 7, 9, 10], drone: null, drums: null, acc: 'pad',
      A: { chords: 'F C Bb F Bb F C F', mel: `
        C5:6 A4:2 F4:4   E4:4 G4:4 C5:4   D5:6 C5:2 Bb4:4   A4:8 C5:4
        Bb4:6 D5:2 F5:4   C5:6 A4:2 F4:4   G4:4 A4:2 G4:2 E4:4   F4:12` },
      B: { chords: 'Dm A7 Dm C F Bb C F', mel: `
        F5:6 E5:2 D5:4   E5:4 C#5:4 A4:4   D5:6 E5:2 F5:4   E5:8 C5:4
        A4:6 C5:2 F5:4   D5:6 C5:2 Bb4:4   A4:4 G4:4 E4:4   F4:12` },
      forms: ['AB', 'AAB', 'ABA'],
    },
  };
  CHORD.Am = [45, [0, 3, 7]];
  for (const s of Object.values(SONGS)) for (const p of ['A', 'B']) { s[p].notes = parse(s[p].mel); s[p].chords = s[p].chords.split(' '); }

  /* ------------------------------------------------------------------ arrangement (one pass of a song -> events) */
  const rnd = a => a[Math.floor(Math.random() * a.length)];
  // diatonic step inside the song's scale (used for the second fiddle in thirds and grace notes)
  function diatonic(song, m, steps) {
    const sc = song.scale.map(v => (v + song.key) % 12);
    let pc = ((m % 12) + 12) % 12, idx = sc.indexOf(pc);
    if (idx < 0) return m + (steps < 0 ? -3 : 3);   // chromatic note: plain minor third
    let out = m, i = idx;
    for (let k = 0; k < Math.abs(steps); k++) {
      const ni = (i + Math.sign(steps) + sc.length) % sc.length;
      let d = (sc[ni] - sc[i] + 12) % 12; if (steps < 0) d = d - 12; out += d; i = ni;
    }
    return out;
  }
  function arrange(song, pass) {
    const ev = [], form = rnd(song.forms), barLen = song.bar;
    let t = 0;
    const second = pass > 0 && Math.random() < .6, octaveB = Math.random() < .3, graces = pass > 0 ? .25 : .1;
    for (const [si, part] of [...form].entries()) {
      const sec = song[part], repeat = form.slice(0, si).includes(part);
      // lead + optional second fiddle a diatonic third below (only on repeats, like a village band joining in)
      let st = t;
      for (const n of sec.notes) {
        if (n.m != null) {
          let m = n.m + (part === 'B' && octaveB && n.m < 72 ? 12 : 0);
          if (n.len >= 2 && Math.random() < graces && song !== SONGS.pastoralka) {   // fiddle grace note from above
            ev.push({ t: st, d: .5, ch: 'lead', m: diatonic(song, m, 1), v: .7 }); ev.push({ t: st + .5, d: n.len - .5, ch: 'lead', m, v: 1 });
          } else ev.push({ t: st, d: n.len, ch: 'lead', m, v: 1 });
          if (second && repeat) ev.push({ t: st, d: n.len, ch: 'second', m: diatonic(song, m, -2), v: 1 });
        }
        st += n.len;
      }
      // accompaniment per bar
      sec.chords.forEach((c, b) => {
        const [root, iv] = CHORD[c] || CHORD.C, bt = t + b * barLen;
        const tones = iv.map(i => root + 12 + i);
        if (song.acc === 'polka') {           // bass on the beat, short chord stab off the beat
          ev.push({ t: bt, d: 3, ch: 'bass', m: root }); ev.push({ t: bt + 4, d: 3, ch: 'bass', m: root + 7 });
          for (const o of [2, 6]) ev.push({ t: bt + o, d: 1.5, ch: 'chord', ms: tones });
        } else if (song.acc === 'mazurka') {  // bass on 1, chords on 2 and 3 (3 accented)
          ev.push({ t: bt, d: 4, ch: 'bass', m: root });
          ev.push({ t: bt + 4, d: 2, ch: 'chord', ms: tones, v: .8 }); ev.push({ t: bt + 8, d: 3, ch: 'chord', ms: tones, v: 1 });
        } else if (song.acc === 'oberek') {   // um-pa-PA
          ev.push({ t: bt, d: 3, ch: 'bass', m: root }); ev.push({ t: bt + 6, d: 2, ch: 'bass', m: root + 7 });
          ev.push({ t: bt + 4, d: 2, ch: 'chord', ms: tones, v: .7 }); ev.push({ t: bt + 8, d: 3, ch: 'chord', ms: tones, v: 1.1 });
        } else {                              // pad: held bass, slow rolled chord
          ev.push({ t: bt, d: barLen, ch: 'bass', m: root });
          tones.forEach((m, k) => ev.push({ t: bt + k * 2, d: barLen - k * 2, ch: 'pad', m, v: .9 }));
        }
        if (song.drone && (part === 'A' || Math.random() < .5) && b % 4 === 0) for (const m of song.drone) ev.push({ t: bt, d: barLen * 4, ch: 'drone', m });
        // drums
        const last = b === sec.chords.length - 1, fill = last && Math.random() < .5;
        if (song.drums === 'krakowiak') {
          ev.push({ t: bt, ch: 'kick' }); ev.push({ t: bt + 4, ch: 'kick' });
          for (const o of fill ? [2, 5, 6, 7] : [2, 6]) ev.push({ t: bt + o, ch: 'snare', v: o === 2 || o === 6 ? 1 : .6 });
          for (let o = 1; o < 8; o += 2) ev.push({ t: bt + o, ch: 'hat', v: .5 });
        } else if (song.drums === 'mazurka') {
          ev.push({ t: bt, ch: 'kick' }); ev.push({ t: bt + 4, ch: 'hat', v: .8 }); ev.push({ t: bt + 8, ch: 'snare', v: 1 });
          if (fill) { ev.push({ t: bt + 10, ch: 'snare', v: .6 }); ev.push({ t: bt + 11, ch: 'snare', v: .8 }); }
        } else if (song.drums === 'oberek') {
          ev.push({ t: bt, ch: 'kick' }); ev.push({ t: bt + 4, ch: 'hat', v: .7 }); ev.push({ t: bt + 8, ch: 'snare', v: 1.1 });
          for (const o of [2, 6, 10]) ev.push({ t: bt + o, ch: 'hat', v: .35 });
          if (fill) for (const o of [9, 10, 11]) ev.push({ t: bt + o, ch: 'snare', v: .7 });
        }
      });
      t += sec.chords.length * barLen;
    }
    return { ev: ev.sort((a, b) => a.t - b.t), len: t };
  }

  /* ------------------------------------------------------------------ synth */
  let ac = null, master, bus, noiseBuf, waves = {};
  function pulse(duty) {
    const n = 40, re = new Float32Array(n), im = new Float32Array(n);
    for (let k = 1; k < n; k++) re[k] = 2 / (k * Math.PI) * Math.sin(k * Math.PI * duty);
    return ac.createPeriodicWave(re, im);
  }
  function initAudio() {
    if (ac) return true;
    const Ctx = window.AudioContext || window.webkitAudioContext; if (!Ctx) return false;
    try { ac = new Ctx(); } catch (e) { return false; }
    master = ac.createGain(); master.gain.value = muted ? 0 : .45; master.connect(ac.destination);
    bus = ac.createGain(); bus.gain.value = 1; bus.connect(master);   // the song bus (fades on song change, ducks for jingles)
    noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
    const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    waves = { p12: pulse(.125), p25: pulse(.25), p50: pulse(.5) };
    return true;
  }
  function env(g, t, a, peak, hold, rel) {
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(peak, t + a);
    g.gain.setValueAtTime(peak, t + a + hold); g.gain.linearRampToValueAtTime(0, t + a + hold + rel);
    return t + a + hold + rel;
  }
  function tone(out, wave, m, t, dur, vol, o = {}) {
    const osc = ac.createOscillator(), g = ac.createGain();
    if (wave === 'tri' || wave === 'sine') osc.type = wave === 'tri' ? 'triangle' : 'sine'; else osc.setPeriodicWave(waves[wave]);
    osc.frequency.value = freq(m);
    if (o.vib && dur > .22) {   // fiddle vibrato that fades in
      const l = ac.createOscillator(), lg = ac.createGain(); l.frequency.value = 5.6;
      lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(o.vib, t + Math.min(.35, dur * .6));
      l.connect(lg); lg.connect(osc.detune); l.start(t); l.stop(t + dur + .2);
    }
    if (o.slide) { osc.frequency.setValueAtTime(freq(m) * .94, t); osc.frequency.exponentialRampToValueAtTime(freq(m), t + .04); }
    const end = env(g, t, o.a ?? .005, vol, Math.max(0, dur - (o.a ?? .005) - (o.r ?? .04)), o.r ?? .04);
    osc.connect(g); g.connect(out); osc.start(t); osc.stop(end + .02);
  }
  function noise(out, t, dur, vol, type, f) {
    const s = ac.createBufferSource(), fl = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; fl.type = type; fl.frequency.value = f; fl.Q.value = type === 'bandpass' ? 1.2 : .7;
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + dur);
    s.connect(fl); fl.connect(g); g.connect(out); s.start(t, Math.random() * .5); s.stop(t + dur + .02);
  }
  function kick(out, t, vol) {
    const o = ac.createOscillator(), g = ac.createGain(); o.type = 'triangle';
    o.frequency.setValueAtTime(160, t); o.frequency.exponentialRampToValueAtTime(42, t + .12);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + .16);
    o.connect(g); g.connect(out); o.start(t); o.stop(t + .18);
  }
  const VOICE = {   // per song-type timbre tweaks
    lead: (e, t, d, s) => tone(e.out, s === SONGS.pastoralka ? 'p50' : 'p25', e.m, t, d * .92, .15 * (e.v ?? 1), { vib: 14, slide: s !== SONGS.pastoralka && Math.random() < .15, a: s === SONGS.pastoralka ? .04 : .004, r: s === SONGS.pastoralka ? .18 : .05 }),
    second: (e, t, d, s) => tone(e.out, 'p12', e.m, t, d * .9, .07, { vib: 10 }),
    bass: (e, t, d, s) => tone(e.out, 'tri', e.m - 12 + (s === SONGS.pastoralka ? 12 : 0), t, d * .85, s === SONGS.pastoralka ? .2 : .45, { r: .03 }),
    chord: (e, t, d) => { e.ms.forEach((m, k) => tone(e.out, 'p50', m, t + k * .012, d, .035 * (e.v ?? 1), { r: .03 })); },
    pad: (e, t, d) => tone(e.out, 'p50', e.m, t, d, .04 * (e.v ?? 1), { a: .25, r: .5, vib: 6 }),
    drone: (e, t, d) => tone(e.out, 'p12', e.m, t, d, .025, { a: .3, r: .4 }),
    kick: (e, t) => kick(e.out, t, .5),
    snare: (e, t) => noise(e.out, t, .09, .13 * (e.v ?? 1), 'bandpass', 2200),
    hat: (e, t) => noise(e.out, t, .03, .06 * (e.v ?? 1), 'highpass', 7500),
  };

  /* ------------------------------------------------------------------ scheduler */
  const P = { name: null, song: null, arr: null, pass: 0, startT: 0, idx: 0, out: null, want: null };
  let VILLAGE = 'krakowiak', PICK = null;
  const LOOKAHEAD = .25;
  function startSong(name) {
    if (!ac) return;
    const now = ac.currentTime;
    if (P.out) { const old = P.out; old.gain.cancelScheduledValues(now); old.gain.setValueAtTime(old.gain.value, now); old.gain.linearRampToValueAtTime(0, now + .5); setTimeout(() => { try { old.disconnect(); } catch (e) { } }, 900); }
    P.name = name; P.song = SONGS[name]; P.pass = 0; P.idx = 0;
    P.out = ac.createGain(); P.out.gain.value = 1; P.out.connect(bus);
    P.arr = arrange(P.song, 0); P.startT = now + .15;
  }
  function tick() {
    if (!ac || rendering || ac.state !== 'running') return;
    if (PICK) P.want = PICK();
    if (P.want && P.want !== P.name) startSong(P.want);
    if (!P.song) return;
    const step = 60 / P.song.bpm / 4, horizon = ac.currentTime + LOOKAHEAD;
    for (; ;) {
      if (P.idx >= P.arr.ev.length) {
        const next = P.startT + P.arr.len * step; if (next > horizon) break;
        // the village alternates between the krakowiak and the mazurka every couple of passes
        if ((P.name === 'krakowiak' || P.name === 'mazurka') && P.want === P.name && P.pass % 2 === 1) {
          const other = P.name === 'krakowiak' ? 'mazurka' : 'krakowiak';
          P.want = other; P.name = other; P.song = SONGS[other]; P.pass = 0; VILLAGE = other;
        } else P.pass++;
        P.startT = next; P.idx = 0; P.arr = arrange(P.song, P.pass); continue;
      }
      const e = P.arr.ev[P.idx], t = P.startT + e.t * step;
      if (t > horizon) break;
      if (t >= ac.currentTime - .02) { e.out = P.out; try { VOICE[e.ch](e, t, (e.d || 1) * step, P.song); } catch (err) { } }
      P.idx++;
    }
  }
  setInterval(tick, 50);

  /* ------------------------------------------------------------------ jingles & sfx (on their own bus, music ducks) */
  function duck(sec) {
    if (!ac) return; const now = ac.currentTime; bus.gain.cancelScheduledValues(now);
    bus.gain.setValueAtTime(bus.gain.value, now); bus.gain.linearRampToValueAtTime(.25, now + .05);
    bus.gain.setValueAtTime(.25, now + sec); bus.gain.linearRampToValueAtTime(1, now + sec + .6);
  }
  function jingle() {   // "hej!" fanfare: rising G-major arpeggio and a stamp
    if (!ac || muted || rendering) return; duck(1.3); const t = ac.currentTime + .05, s = .09;
    ['G4', 'B4', 'D5', 'G5', 'B5', 'D6'].forEach((n, i) => tone(master, 'p25', midi(n), t + i * s, s * .95, .13, { r: .02 }));
    tone(master, 'p25', midi('G6'), t + 6 * s, s * 4, .13, { vib: 18, r: .2 }); tone(master, 'p12', midi('D6'), t + 6 * s, s * 4, .07, { r: .2 });
    kick(master, t + 6 * s, .5); noise(master, t + 6 * s, .15, .15, 'bandpass', 2000);
  }
  function ding() {     // pickup blip
    if (!ac || muted || rendering) return; const t = ac.currentTime + .01;
    tone(master, 'p25', midi('E6'), t, .06, .09, { r: .01 }); tone(master, 'p25', midi('B6'), t + .06, .12, .09, { r: .06 });
  }

  /* ------------------------------------------------------------------ control */
  function setMuted(v) {
    muted = v; try { localStorage.setItem(MUTE_KEY, v ? '1' : '0'); } catch (e) { }
    if (ac) { const now = ac.currentTime; master.gain.cancelScheduledValues(now); master.gain.setValueAtTime(master.gain.value, now); master.gain.linearRampToValueAtTime(v ? 0 : .45, now + .25); }
  }
  function unlock() {
    if (!initAudio()) return;
    if (ac.state === 'suspended' && !document.hidden) ac.resume().catch(() => { });
  }
  addEventListener('keydown', unlock, true); addEventListener('pointerdown', unlock, true); addEventListener('touchend', unlock, true);
  document.addEventListener('visibilitychange', () => { if (!ac) return; if (document.hidden) ac.suspend().catch(() => { }); else ac.resume().catch(() => { }); });

  /* ------------------------------------------------------------------ offline render to WAV (previews, videos) */
  let rendering = false;
  async function renderWav(name, passes = 2, rate = 32000) {
    const song = SONGS[name], step = 60 / song.bpm / 4, arrs = [];
    for (let i = 0; i < passes; i++) arrs.push(arrange(song, i));
    const dur = arrs.reduce((a, r) => a + r.len, 0) * step + 1.5;
    const saved = { ac, master, bus, noiseBuf, waves };
    rendering = true;
    ac = new OfflineAudioContext(1, Math.ceil(dur * rate), rate);
    master = ac.createGain(); master.gain.value = .45; master.connect(ac.destination);
    noiseBuf = ac.createBuffer(1, rate, rate); const nd = noiseBuf.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    waves = { p12: pulse(.125), p25: pulse(.25), p50: pulse(.5) };
    let t0 = .05;
    for (const r of arrs) { for (const e of r.ev) { e.out = master; VOICE[e.ch](e, t0 + e.t * step, (e.d || 1) * step, song); } t0 += r.len * step; }
    const job = ac.startRendering();
    ({ ac, master, bus, noiseBuf, waves } = saved); rendering = false;
    const buf = await job, d = buf.getChannelData(0), out = new DataView(new ArrayBuffer(44 + d.length * 2));
    const str = (o, t) => [...t].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
    str(0, 'RIFF'); out.setUint32(4, 36 + d.length * 2, true); str(8, 'WAVEfmt '); out.setUint32(16, 16, true); out.setUint16(20, 1, true);
    out.setUint16(22, 1, true); out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true);
    str(36, 'data'); out.setUint32(40, d.length * 2, true);
    for (let i = 0; i < d.length; i++) out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, d[i])) * 32767, true);
    return new Blob([out], { type: 'audio/wav' });
  }

  window.MUSIC = { renderWav, SONGS: Object.keys(SONGS), play(n) { unlock(); P.want = n; }, get current() { return P.name; }, get muted() { return muted; }, setMuted, jingle, ding, get state() { return ac ? ac.state : 'none'; } };

  /* ------------------------------------------------------------------ game glue */
  window.addEventListener('ark-ready', () => {
    const A = window.ARK, { HOOKS } = A;
    const pick = () => {
      const sc = A.scene;
      if (sc === 'title') return 'mazurka';
      if (sc === 'end' || A.room) return 'pastoralka';
      if (A.minigame && A.minigame()) return 'oberek';
      return VILLAGE;
    };
    PICK = pick;   // polled by tick(): HOOKS.update does not run on the title, end screen or during dialogue
    const pt = A.popToast;   // game.js itself calls MUSIC.jingle() in celebrate() and MUSIC.ding() in popToast()
    addEventListener('keydown', e => {   // a plain listener, so K also works on the title and during dialogue
      if (e.code === 'KeyK' && !e.repeat) { setMuted(!muted); pt(muted ? A.T.musicOff : A.T.musicOn); }
    });
    // tap the note icon (bottom-left) on touch screens
    let ICON = null;
    const icon = (U, H) => (ICON = { x: U * 1.5, y: H - U * 5.5, s: U * 4 });
    HOOKS.pointer.push((px, py) => { const b = ICON; if (b && px < b.x + b.s + b.s / 2 && py > b.y - b.s / 2) { setMuted(!muted); pt(muted ? A.T.musicOff : A.T.musicOn); return true; } return false; });
    HOOKS.hud.push((U, W, H) => {
      const c = A.ctx, b = icon(U, H), u = b.s / 10, x = b.x, y = b.y;
      c.globalAlpha = .75; c.fillStyle = 'rgba(8,12,40,.78)'; c.fillRect(x, y, b.s, b.s);
      c.fillStyle = muted ? '#9aa0c0' : '#ffd21f';
      c.fillRect(x + u * 3, y + u * 6, u * 2.2, u * 2); c.fillRect(x + u * 4.4, y + u * 2, u * .8, u * 5);   // eighth note
      c.fillRect(x + u * 5.2, y + u * 2, u * 1.6, u * .8); c.fillRect(x + u * 6.4, y + u * 2.6, u * .8, u * 1.4);
      if (muted) { c.fillStyle = '#ff3b30'; for (let k = 0; k < 8; k++) c.fillRect(x + u * (1 + k), y + u * (1 + k), u, u); }
      c.globalAlpha = 1;
    });
  });
})();
