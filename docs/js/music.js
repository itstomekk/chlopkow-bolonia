/* MUZYKA - procedural 8-bit Polish folk chiptune for Arek w Chłopkowie, plus a rotating Ogg/Opus recording playlist.
   Procedural tracks are synthesised live with WebAudio (NES-style pulse leads, triangle bass, noise drums, a bagpipe drone).
   The entrance screen plays the printed Polka Dziadek alone; village and field share one "default" zone that
   plays the recorded playlist at random. Church, cemetery, forest, shop, barn and minigames keep the procedural tracks.
   Tracks (all original tunes written in folk-dance idioms):
     krakowiak — 2/4, syncopated 16th-8th-16th "hop" rhythm, G major with a Góral raised-4th (C#) in part B  (village)
     mazurka   — 3/4, dotted first beat, accents on 2 and 3, C major                                         (title, village alt.)
     oberek    — fast 3/4 whirling eighths, um-pa-PA accompaniment, D major                                   (minigames)
     pastoralka— slow 3/4 lullaby, soft pads, F major                                    (available as a quiet piece)
     choral    — sacred organ hymn in D Dorian, 4/4 half notes, a church bell on each section           (church interior)
     nokturn   — Chopin-style nocturne in A minor, rolling left-hand arpeggios, ornamented melody  (cemetery, memory archive)
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
      bpm: 74, bar: 12, beat: 4, key: 5, scale: [0, 2, 4, 5, 7, 9, 10], drone: null, drums: null, acc: 'pad', style: 'soft', range: [.75, 1],
      A: { chords: 'F C Bb F Bb F C F', mel: `
        C5:6 A4:2 F4:4   E4:4 G4:4 C5:4   D5:6 C5:2 Bb4:4   A4:8 C5:4
        Bb4:6 D5:2 F5:4   C5:6 A4:2 F4:4   G4:4 A4:2 G4:2 E4:4   F4:12` },
      B: { chords: 'Dm A7 Dm C F Bb C F', mel: `
        F5:6 E5:2 D5:4   E5:4 C#5:4 A4:4   D5:6 E5:2 F5:4   E5:8 C5:4
        A4:6 C5:2 F5:4   D5:6 C5:2 Bb4:4   A4:4 G4:4 E4:4   F4:12` },
      forms: ['AB', 'AAB', 'ABA'],
    },
    choral: {   // Polish church-song feel: modal (Dorian), plain half notes, organ with pedal bass
      bpm: 60, bar: 16, beat: 4, key: 2, scale: [0, 2, 3, 5, 7, 9, 10], drone: null, drums: null, acc: 'organ', style: 'organ', range: [.8, 1], bell: true,
      A: { chords: 'Dm Dm C Dm F C A Dm', mel: `
        D5:8 E5:4 F5:4   E5:8 D5:8   C5:4 D5:4 E5:4 C5:4   D5:16
        F5:8 G5:4 A5:4   G5:8 E5:8   F5:4 E5:4 D5:4 C#5:4   D5:16` },
      B: { chords: 'F C Dm A Bb F Gm A', mel: `
        A5:8 A5:4 G5:4   E5:4 F5:4 G5:8   F5:8 E5:4 D5:4   E5:16
        D5:8 F5:4 D5:4   C5:8 A4:8   Bb4:8 A4:4 G4:4   A4:16` },
      forms: ['AB', 'AAB', 'ABA'],
    },
    nokturn: {  // night piece for the cemetery: rolling arpeggios under a singing, ornamented line
      bpm: 66, bar: 12, beat: 4, key: 9, scale: [0, 2, 3, 5, 7, 8, 11], drone: null, drums: null, acc: 'nocturne', style: 'piano', range: [.8, 1], second: false,
      A: { chords: 'Am Am Dm E Am F E7 Am', mel: `
        E5:8 D5:2 C5:2   B4:4 C5:4 A4:4   F5:6 E5:2 D5:2 F5:2   E5:6 D5:1 C5:1 B4:4
        A5:8 G#5:2 A5:2   C6:6 B5:2 A5:2 F5:2   E5:4 G#4:4 B4:2 D5:2   C5:4 B4:2 A4:6` },
      B: { chords: 'C G Am Em F C Dm E', mel: `
        G5:8 E5:2 G5:2   D5:8 B4:2 D5:2   C5:6 B4:2 C5:2 E5:2   B4:12
        A5:6 G5:2 F5:2 A5:2   G5:6 F5:2 E5:2 C5:2   F5:4 E5:2 D5:2 C5:2 D5:2   B4:8 G#4:4` },
      forms: ['AB', 'AAB', 'ABAB'],
    },
    jazz: {     // JAZZ W STODOLE: swing in F. bar = 12 triplet-eighth steps (4/4 swung), ii-V-I changes, walking bass, ride & brushes
      bpm: 150, bar: 12, beat: 3, key: 5, scale: [0, 2, 4, 5, 7, 9, 11], drone: null, drums: 'swing', acc: 'walking', style: 'jazz', range: [.9, 1.05], second: false,
      A: { chords: 'Fmaj7 D7 Gm7 C7 Am7 D7 Gm7 C7', mel: `
        A4:2 C5:1 E5:2 F5:1 A5:4 G5:2   F#5:2 A5:1 C6:2 A5:1 F#5:3 D5:3   G5:2 Bb5:1 D6:2 C6:1 Bb5:2 A5:1 G5:3   E5:2 G5:1 Bb5:3 A5:2 G5:1 E5:3
        C6:3 A5:2 G5:1 E5:3 C5:3   D5:2 F#5:1 A5:2 C6:1 B5:2 A5:1 F#5:3   Bb5:2 A5:1 G5:2 F5:1 E5:2 D5:1 C5:3   E5:2 G5:1 F5:6 -:3` },
      B: { chords: 'Bb7 Bb7 Fmaj7 D7 Gm7 C7 Fmaj7 C7', mel: `
        D5:2 F5:1 Ab5:3 G5:2 F5:1 D5:3   F5:2 D5:1 Bb4:3 -:3 Ab4:2 A4:1   C5:2 F5:1 A5:2 C6:1 E6:6   D6:2 C6:1 A5:2 F#5:1 D5:3 -:3
        Bb4:2 D5:1 F5:2 A5:1 G5:6   G5:2 E5:1 C5:2 Bb4:1 Db5:2 D5:1 E5:3   F5:3 A5:2 C6:1 A5:6   G5:2 F5:1 E5:2 C5:1 Bb4:3 G4:3` },
      forms: ['AABA', 'ABAB', 'AAB'],
    },
  };
  CHORD.Gm = [43, [0, 3, 7]]; CHORD.E7 = [52, [0, 4, 7, 10]];
  CHORD.Am = [45, [0, 3, 7]];
  Object.assign(CHORD, { Fmaj7: [53, [0, 4, 7, 11]], Gm7: [43, [0, 3, 7, 10]], C7: [48, [0, 4, 7, 10]], Am7: [45, [0, 3, 7, 10]], Bb7: [46, [0, 4, 7, 10]] });
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
    const second = song.second !== false && pass > 0 && Math.random() < .6, octaveB = Math.random() < .3, graces = pass > 0 ? .25 : .1;
    for (const [si, part] of [...form].entries()) {
      const sec = song[part], repeat = form.slice(0, si).includes(part);
      // lead + optional second fiddle a diatonic third below (only on repeats, like a village band joining in)
      let st = t;
      for (const n of sec.notes) {
        if (n.m != null) {
          let m = n.m + (part === 'B' && octaveB && n.m < 72 ? 12 : 0);
          if (n.len >= 2 && Math.random() < graces && (song.style || 'folk') !== 'soft' && song.style !== 'organ') {   // grace note from above (fiddle / Chopin turn)
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
        } else if (song.acc === 'organ') {    // pedal note + full held chord, a bell at the top of each section
          ev.push({ t: bt, d: barLen, ch: 'bass', m: root });
          ev.push({ t: bt, d: barLen, ch: 'organ', ms: tones });
          if (song.bell && b === 0) ev.push({ t: bt, ch: 'bell', m: root + 24 });
        } else if (song.acc === 'nocturne') { // left hand: low root, fifth, tenth... rolling in eighths, pedal held
          const third = iv[1], pat = [0, 7, 12 + third, 19, 12 + third, 7];
          pat.forEach((o, k) => ev.push({ t: bt + k * 2, d: 6, ch: 'harp', m: root - 12 + o + 12, v: k === 0 ? 1 : .75 }));
        } else if (song.acc === 'walking') {  // walking bass in quarters (root, chord tone, fifth, chromatic approach) + Charleston comping
          const next = CHORD[sec.chords[(b + 1) % sec.chords.length]] || CHORD.C, nr = next[0];
          const walk = [root, root + (Math.random() < .5 ? iv[1] : 2), root + 7, nr + (nr > root + 6 ? -1 : 1) * (Math.random() < .5 ? 1 : -1)];
          walk.forEach((m, k) => ev.push({ t: bt + k * 3, d: 2.6, ch: 'bass', m, v: k ? .85 : 1 }));
          ev.push({ t: bt, d: 1.5, ch: 'chord', ms: tones, v: .8 });
          ev.push({ t: bt + (Math.random() < .5 ? 5 : 8), d: 1.2, ch: 'chord', ms: tones, v: .65 });
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
        } else if (song.drums === 'swing') {  // ride "ding, ding-a ding, ding-a", hi-hat foot on 2 and 4, brush swishes
          for (const o of [0, 3, 5, 6, 9, 11]) ev.push({ t: bt + o, ch: 'ride', v: o % 3 ? .55 : 1 });
          for (const o of [3, 9]) { ev.push({ t: bt + o, ch: 'hat', v: .6 }); ev.push({ t: bt + o, ch: 'brush', v: 1 }); }
          if (fill) for (const o of [7, 8, 10, 11]) ev.push({ t: bt + o, ch: 'brush', v: .7 });
          if (b % 2 === 0) ev.push({ t: bt, ch: 'kick', v: .4 });
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
  function env(g, t, a, peak, hold, rel, decay = 1) {   // decay < 1: the note fades while held (piano/harp)
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(peak, t + a);
    if (decay < 1) g.gain.linearRampToValueAtTime(peak * decay, t + a + hold); else g.gain.setValueAtTime(peak, t + a + hold);
    g.gain.linearRampToValueAtTime(0, t + a + hold + rel);
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
    const end = env(g, t, o.a ?? .005, vol, Math.max(0, dur - (o.a ?? .005) - (o.r ?? .04)), o.r ?? .04, o.decay);
    osc.connect(g); g.connect(out); osc.start(t); osc.stop(end + .02);
  }
  function noise(out, t, dur, vol, type, f) {
    const s = ac.createBufferSource(), fl = ac.createBiquadFilter(), g = ac.createGain();
    s.buffer = noiseBuf; fl.type = type; fl.frequency.value = f; fl.Q.value = type === 'bandpass' ? 1.2 : .7;
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + dur);
    s.connect(fl); fl.connect(g); g.connect(out); s.start(t, Math.random() * .5); s.stop(t + dur + .02);
  }
  function partial(out, f, t, vol, len) {   // one sine partial of a bell
    const o = ac.createOscillator(), g = ac.createGain(); o.type = 'sine'; o.frequency.value = f;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + .005); g.gain.exponentialRampToValueAtTime(.0005, t + len);
    o.connect(g); g.connect(out); o.start(t); o.stop(t + len + .05);
  }
  function kick(out, t, vol) {
    const o = ac.createOscillator(), g = ac.createGain(); o.type = 'triangle';
    o.frequency.setValueAtTime(160, t); o.frequency.exponentialRampToValueAtTime(42, t + .12);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + .16);
    o.connect(g); g.connect(out); o.start(t); o.stop(t + .18);
  }
  const VOICE = {   // per song-type timbre tweaks
    lead: (e, t, d, s) => {
      const v = e.v ?? 1;
      if (s.style === 'organ') { tone(e.out, 'p50', e.m, t, d * .97, .11 * v, { a: .06, r: .25 }); tone(e.out, 'p25', e.m - 12, t, d * .97, .05 * v, { a: .08, r: .25 }); return; }
      if (s.style === 'piano') { tone(e.out, 'p25', e.m, t, d * 1.05, .24 * v, { a: .004, r: .35, decay: .4, vib: 6 }); return; }
      if (s.style === 'jazz') {   // tenor-sax-ish: soft attack, scoop into the note, late vibrato, a breath of air
        tone(e.out, 'p50', e.m, t, d * .9, .12 * v, { a: .03, r: .08, vib: 16, slide: Math.random() < .35 });
        tone(e.out, 'p12', e.m, t, d * .9, .04 * v, { a: .04, r: .08 });
        noise(e.out, t, Math.min(.12, d * .5), .015, 'bandpass', 1800); return;
      }
      const soft = s.style === 'soft';
      tone(e.out, soft ? 'p50' : 'p25', e.m, t, d * .92, .15 * v, { vib: 14, slide: !soft && Math.random() < .15, a: soft ? .04 : .004, r: soft ? .18 : .05 });
    },
    organ: (e, t, d) => { e.ms.forEach(m => { tone(e.out, 'p50', m, t, d * .98, .03, { a: .12, r: .3 }); tone(e.out, 'p12', m + 12, t, d * .98, .012, { a: .15, r: .3 }); }); },
    harp: (e, t, d) => tone(e.out, 'p50', e.m, t, d, .085 * (e.v ?? 1), { a: .004, r: .4, decay: .2 }),
    bell: (e, t) => { for (const [r, v, len] of [[1, .12, 3], [2.76, .05, 1.6], [5.4, .03, .9], [.5, .06, 3.5]]) partial(e.out, freq(e.m) * r, t, v, len); },
    second: (e, t, d, s) => tone(e.out, 'p12', e.m, t, d * .9, .07, { vib: 10 }),
    bass: (e, t, d, s) => { const soft = s.style === 'soft' || s.style === 'organ'; tone(e.out, 'tri', e.m - 12 + (s.style === 'soft' ? 12 : 0), t, d * (soft ? .98 : .85), soft ? .22 : .45, { r: soft ? .2 : .03, a: soft ? .05 : .005 }); },
    chord: (e, t, d) => { e.ms.forEach((m, k) => tone(e.out, 'p50', m, t + k * .012, d, .035 * (e.v ?? 1), { r: .03 })); },
    pad: (e, t, d) => tone(e.out, 'p50', e.m, t, d, .04 * (e.v ?? 1), { a: .25, r: .5, vib: 6 }),
    drone: (e, t, d) => tone(e.out, 'p12', e.m, t, d, .025, { a: .3, r: .4 }),
    kick: (e, t) => kick(e.out, t, .5 * (e.v ?? 1)),
    snare: (e, t) => noise(e.out, t, .09, .13 * (e.v ?? 1), 'bandpass', 2200),
    hat: (e, t) => noise(e.out, t, .03, .06 * (e.v ?? 1), 'highpass', 7500),
    ride: (e, t) => { noise(e.out, t, .35, .035 * (e.v ?? 1), 'highpass', 6000); partial(e.out, 3150, t, .012 * (e.v ?? 1), .4); },
    brush: (e, t) => noise(e.out, t, .16, .05 * (e.v ?? 1), 'bandpass', 3200),
  };

  /* ------------------------------------------------------------------ scheduler
     Tempo follows the player: standing still -> 0.2x the written BPM, moving -> the "energy" builds up and the band
     slowly speeds up to 1.3x (slower build-up while walking or running), stopping -> it relaxes linearly.
     Because the tempo changes while playing, the scheduler keeps a frontier (audio time fT <-> song step fS) and
     advances it at the current tempo, so a tempo change never makes the music jump. */
  const P = { name: null, song: null, arr: null, pass: 0, idx: 0, fT: 0, fS: 0, out: null, want: null };
  let VILLAGE = 'krakowiak', PICK = null, ACTIVITY = null;
  // Ogg/Opus is supported by modern browsers and keeps the recorded 8-bit tracks small enough for Pages.
  // The printed Polka Dziadek belongs to the entrance screen alone; the village/field "default" zone plays
  // the recorded list below in random order.
  const TITLE_TRACKS = ['audio/Polka_Dziadek_true_chiptune_NES.ogg'];
  const DEFAULT_TRACKS = [
    'audio/track-number-4.ogg',
    'audio/track-number-5.ogg',
    'audio/track-poland-anthem.ogg',
    'audio/track-ucieczka.ogg',
    'audio/track-polska-przydrozna.ogg',
    'audio/track-ona-tanczy.ogg',
  ];
  let mainTrack = null, mainTrackSrc = null, mainTrackZone = null, mainTrackOn = false;
  const LOOKAHEAD = .25;
  const TEMPO = { idle: .2, max: 1.3, still: .8,   // x written BPM; `still` is used on the title screen
    rampUp: 30, rampRun: 20, rampDown: 20 };        // linear energy seconds to max (walking / running / stopping)
  // quiet pieces (church hymn, nocturne, lullaby) set song.range, e.g. [.8, 1], so they stay slow and dignified
  let energy = 0, tempo = TEMPO.still, lastTick = performance.now();
  function updateTempo() {
    const now = performance.now(), dt = Math.min(.25, (now - lastTick) / 1000); lastTick = now;
    const a = ACTIVITY ? ACTIVITY() : null;   // null = not playing (title/end), else { moving, running }
    let target;
    if (!a) target = TEMPO.still;
    else {
      if (a.moving) energy = Math.min(1, energy + dt / (a.running ? TEMPO.rampRun : TEMPO.rampUp));
      else energy = Math.max(0, energy - dt / TEMPO.rampDown);
      const [lo, hi] = (P.song && P.song.range) || [TEMPO.idle, TEMPO.max];
      target = lo + energy * (hi - lo);
    }
    tempo = target;                                  // keep the audible tempo linear with energy; no exponential catch-up
  }
  function startSong(name) {
    if (!ac) return;
    const now = ac.currentTime;
    if (P.out) { const old = P.out; old.gain.cancelScheduledValues(now); old.gain.setValueAtTime(old.gain.value, now); old.gain.linearRampToValueAtTime(0, now + .5); setTimeout(() => { try { old.disconnect(); } catch (e) { } }, 900); }
    const prev = P.name;
    P.name = name; P.song = SONGS[name]; P.pass = 0; P.idx = 0;
    sting(prev, name, now);
    P.out = ac.createGain(); P.out.gain.value = 1; P.out.connect(bus);
    P.arr = arrange(P.song, 0); P.fT = now + .15; P.fS = 0;
  }
  function pickMainTrack(zone) {
    if (zone === 'title') return TITLE_TRACKS[0];   // the entrance screen repeats its one printed track
    if (DEFAULT_TRACKS.length === 1) return DEFAULT_TRACKS[0];
    let src = mainTrackSrc, n = 0;
    while (src === mainTrackSrc && n++ < 24) src = DEFAULT_TRACKS[(Math.random() * DEFAULT_TRACKS.length) | 0];
    return src;                                     // random, never the same track twice in a row
  }
  function loadMainTrack(src) {
    const track = new Audio(src);
    track.loop = false;
    track.preload = 'metadata';
    track.volume = .62;
    track.muted = muted;
    track.addEventListener('ended', () => {
      if (mainTrack !== track || !mainTrackOn) return;
      loadMainTrack(pickMainTrack(mainTrackZone));
      mainTrack.play().catch(() => { });
    });
    mainTrack = track; mainTrackSrc = src;
  }
  function setMainTrack(zone) {      // zone: 'title', 'main', or null when a procedural track owns the moment
    if (!zone) {
      if (mainTrack) { mainTrack.pause(); mainTrack.currentTime = 0; }
      mainTrackOn = false; mainTrackZone = null;
      return;
    }
    if (mainTrackZone !== zone) {    // entered a recorded zone: start a fresh pick for it
      mainTrackZone = zone;
      loadMainTrack(pickMainTrack(zone));
      mainTrackOn = true;
      mainTrack.play().catch(() => { });
      return;
    }
    if (!mainTrackOn) { mainTrackOn = true; mainTrack.play().catch(() => { }); }
  }
  function setSynthEnabled(enabled) {
    if (!bus || !ac) return;
    const now = ac.currentTime;
    bus.gain.cancelScheduledValues(now);
    bus.gain.setValueAtTime(bus.gain.value, now);
    bus.gain.linearRampToValueAtTime(enabled ? 1 : 0, now + .25);
  }
  function nextPass() {
    // the village alternates between the krakowiak and the mazurka every couple of passes
    if ((P.name === 'krakowiak' || P.name === 'mazurka') && P.want === P.name && P.pass % 2 === 1) {
      const other = P.name === 'krakowiak' ? 'mazurka' : 'krakowiak';
      P.want = other; P.name = other; P.song = SONGS[other]; P.pass = 0; VILLAGE = other;
    } else P.pass++;
    P.idx = 0; P.arr = arrange(P.song, P.pass);
  }
  // The recorded tracks follow the player's activity. The village/field playlist runs linearly from 0.4x
  // (standing still) to 1.3x (full energy); the entrance screen keeps its own gentle 0.8x.
  const MAIN_RATE_MIN = .4;
  function mainTrackRate() {
    if (mainTrackZone === 'title') return TEMPO.still;
    return MAIN_RATE_MIN + energy * (TEMPO.max - MAIN_RATE_MIN);
  }
  function syncMainTrackRate() {
    if (!mainTrack) return;
    const rate = Math.max(MAIN_RATE_MIN, Math.min(TEMPO.max, mainTrackRate()));
    if (Math.abs(mainTrack.playbackRate - rate) > .01) { mainTrack.preservesPitch = true; mainTrack.playbackRate = rate; }
  }
  function tick() {
    updateTempo();
    syncMainTrackRate();
    if (!ac || rendering || ac.state !== 'running') return;
    if (PICK) {
      const zone = PICK();                                   // 'title' | 'main' | a procedural song name
      const recorded = zone === 'title' || zone === 'main';
      setMainTrack(recorded ? zone : null);
      setSynthEnabled(!recorded);
      P.want = recorded ? 'krakowiak' : zone;
    }
    if (P.want && P.want !== P.name) startSong(P.want);
    if (!P.song) startSong('krakowiak');
    const step = 60 / (P.song.bpm * tempo) / 4, horizon = ac.currentTime + LOOKAHEAD;
    if (P.fT < ac.currentTime - .5) P.fT = ac.currentTime;   // after a suspend: resume from now instead of catching up
    while (P.fT < horizon) {
      const endS = P.fS + (horizon - P.fT) / step;
      for (; P.idx < P.arr.ev.length && P.arr.ev[P.idx].t < Math.min(endS, P.arr.len); P.idx++) {
        const e = P.arr.ev[P.idx], t = P.fT + (e.t - P.fS) * step;
        if (t >= ac.currentTime - .02) { e.out = P.out; try { VOICE[e.ch](e, t, (e.d || 1) * step, P.song); } catch (err) { } }
      }
      if (endS < P.arr.len) { P.fS = endS; P.fT = horizon; break; }
      P.fT += (P.arr.len - P.fS) * step; P.fS = 0; nextPass();   // pass ends before the horizon: continue into the next one
    }
  }
  setInterval(tick, 50);

  /* ------------------------------------------------------------------ jingles & sfx (on their own bus, music ducks) */
  function duck(sec) {
    if (!ac) return; const now = ac.currentTime; bus.gain.cancelScheduledValues(now);
    bus.gain.setValueAtTime(bus.gain.value, now); bus.gain.linearRampToValueAtTime(.25, now + .05);
    bus.gain.setValueAtTime(.25, now + sec); bus.gain.linearRampToValueAtTime(1, now + sec + .6);
  }
  // a short cue whenever the scene changes the song, so the change is clearly heard
  function sting(from, to, now) {
    if (muted) return; const t = now + .05;
    if (SCENE_START && to === 'krakowiak') { SCENE_START = false; jingle(); return; }   // game start: "hej!" fanfare
    if (!from) return;
    if (to === 'choral') { VOICE.bell({ out: master, m: midi('D5') }, t); VOICE.bell({ out: master, m: midi('A4') }, t + 1.1); }
    else if (to === 'nokturn') VOICE.bell({ out: master, m: midi('A4') }, t);
    else if (from === 'choral' || from === 'nokturn') ['G4', 'D5', 'G5'].forEach((n, i) => tone(master, 'p25', midi(n), t + i * .08, .08, .1, { r: .02 }));   // back outside
  }
  let SCENE_START = true;
  function bark() {   // "hau!": a falling nasal square yelp through a mouth-like band-pass, plus breath noise
    if (!ac || muted || rendering) return; const t = ac.currentTime + .01;
    const o = ac.createOscillator(), f = ac.createBiquadFilter(), g = ac.createGain();
    o.setPeriodicWave(waves.p25); o.frequency.setValueAtTime(420, t); o.frequency.linearRampToValueAtTime(620, t + .03); o.frequency.exponentialRampToValueAtTime(260, t + .16);
    f.type = 'bandpass'; f.Q.value = 3; f.frequency.setValueAtTime(900, t); f.frequency.linearRampToValueAtTime(1500, t + .04); f.frequency.exponentialRampToValueAtTime(600, t + .16);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.5, t + .015); g.gain.exponentialRampToValueAtTime(.001, t + .19);
    o.connect(f); f.connect(g); g.connect(master); o.start(t); o.stop(t + .22);
    noise(master, t, .06, .1, 'bandpass', 1400);
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
  function hop() {      // jump "boing": a quick upward pulse sweep with a springy wobble
    if (!ac || muted || rendering) return; const t = ac.currentTime + .005;
    const o = ac.createOscillator(), g = ac.createGain(), l = ac.createOscillator(), lg = ac.createGain();
    o.setPeriodicWave(waves.p25); o.frequency.setValueAtTime(190, t); o.frequency.exponentialRampToValueAtTime(620, t + .11); o.frequency.exponentialRampToValueAtTime(430, t + .2);
    l.frequency.value = 28; lg.gain.value = 45; l.connect(lg); lg.connect(o.frequency);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.09, t + .01); g.gain.exponentialRampToValueAtTime(.001, t + .22);
    o.connect(g); g.connect(master); o.start(t); o.stop(t + .24); l.start(t); l.stop(t + .24);
    window.MUSIC.hops = (window.MUSIC.hops || 0) + 1;
  }

  /* ------------------------------------------------------------------ control */
  function setMuted(v) {
    muted = v; try { localStorage.setItem(MUTE_KEY, v ? '1' : '0'); } catch (e) { }
    if (mainTrack) mainTrack.muted = v;
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
    const song = SONGS[name], step = 60 / (song.bpm * TEMPO.still) / 4, arrs = [];
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

  window.MUSIC = { renderWav, SONGS: Object.keys(SONGS), TITLE_TRACKS: [...TITLE_TRACKS], DEFAULT_TRACKS: [...DEFAULT_TRACKS], play(n) { unlock(); P.want = n; }, get current() { return P.name; }, get muted() { return muted; }, setMuted, jingle, ding, bark, hop, get state() { return ac ? ac.state : 'none'; }, get tempo() { return tempo; }, get mainTrackRate() { return mainTrack ? mainTrack.playbackRate : null; }, get mainTrackSource() { return mainTrack ? mainTrack.src : null; }, get mainTrackEl() { return mainTrack; }, get mainTrackZone() { return mainTrackZone; }, MAIN_RATE_MIN, TEMPO };

  /* ------------------------------------------------------------------ game glue */
  window.addEventListener('ark-ready', () => {
    const A = window.ARK, { HOOKS } = A;
    // cemetery zone: the OSM landuse rectangle around the cemetery POI (about 110 x 100 m), with hysteresis at the edge
    const CEM = A.MAP.pois.find(q => q.key === 'cemetery'), CEM_HALF = [112, 97];
    let inCem = false;
    const nearCemetery = () => {
      if (!CEM || A.room) return false;
      const m = inCem ? 70 : 25, dx = Math.abs(A.P.x - CEM.x), dy = Math.abs(A.P.y - CEM.y);
      return (inCem = dx < CEM_HALF[0] + m && dy < CEM_HALF[1] + m);
    };
    // JAZZ W STODOLE: the barn yard plays swing (map.json jazz {x, y, r}), with hysteresis at the edge
    let inJazz = false;
    const nearJazz = () => {
      const J = A.MAP.jazz; if (!J || A.room) return (inJazz = false);
      return (inJazz = Math.hypot(A.P.x - J.x, A.P.y - J.y) < J.r + (inJazz ? 40 : 0));
    };
    const pick = () => {
      const sc = A.scene;
      if (sc === 'title') return 'title';   // the printed Polka Dziadek is the entrance screen only
      if (A.room && A.room.soltys) return 'choral';
      if (A.room && A.room.shop) return 'mazurka';
      if (sc === 'end' || nearCemetery()) return 'nokturn';
      if (A.minigame && A.minigame()) return 'oberek';
      if (sc === 'play' && A.terrainAt && A.terrainAt(A.P.x, A.P.y) === 'forest') return 'pastoralka';
      if (sc === 'play' && nearJazz()) return 'jazz';
      if (sc === 'play') return 'main';
      return VILLAGE;
    };
    ACTIVITY = () => A.scene === 'play' ? { moving: !!A.P.moving, running: A.keys.has('ShiftLeft') || A.keys.has('ShiftRight') } : A.scene === 'end' ? { moving: false } : null;
    // Frodo answers Arek with short, slightly overconfident dog thoughts.
    let dogLine = null, touching = false;
    const DOG_LINES = ['WĘSZĘ KŁOPOTY.', 'AREK, ZA MNĄ. MAM PLAN.', 'DOBRY CZŁOWIEK. SŁABY NOS.', 'KTO MA KIEŁBASĘ?', 'SZYBCIEJ. ŁAPA ZA ŁAPĄ.'];
    setInterval(() => {
      const F = A.FRODO; if (A.scene !== 'play' || !F) { touching = false; return; }
      const d = Math.hypot(A.P.x - F.x, A.P.y - F.y);
      if (!touching && d < 18 && (!dogLine || performance.now() - dogLine.t > 1800)) { touching = true; bark(); const raw = DOG_LINES[(Math.random() * DOG_LINES.length) | 0]; dogLine = { t: performance.now(), text: A.heroText ? A.heroText(raw) : raw }; window.MUSIC.barks = (window.MUSIC.barks || 0) + 1; }
      else if (touching && d > 28) touching = false;
    }, 50);
    HOOKS.hud.push(U => {
      if (!dogLine) return; const age = (performance.now() - dogLine.t) / 1000; if (age > 1.8) return;
      const cam = A.camera, F = A.FRODO; if (!cam) return;
      const [x, y0] = cam.S(F.x, F.y), y = y0 - 18 * cam.zoom, c = A.ctx;
      c.globalAlpha = Math.min(1, (1.8 - age) * 2); c.font = `${U * 1.65}px Silkscreen`; c.textAlign = 'center';
      const yy = y - U * 4 - age * U * 3, w = c.measureText(dogLine.text).width + U * 1.6;
      c.fillStyle = '#fff'; c.fillRect(x - w / 2, yy - U * 2.2, w, U * 3); c.fillStyle = '#10163a'; c.fillText(dogLine.text, x, yy);
      c.globalAlpha = 1;
    });
    if (!OFF_PARAM) { initAudio(); if (ac && ac.state === 'suspended') ac.resume().catch(() => { }); }
    PICK = pick;   // polled by tick(): HOOKS.update does not run on the title, end screen or during dialogue
    const pt = A.popToast;   // game.js itself calls MUSIC.jingle() in celebrate() and MUSIC.ding() in popToast()
    addEventListener('keydown', e => {   // a plain listener, so K also works on the title and during dialogue
      if (e.code === 'KeyK' && !e.repeat) { setMuted(!muted); pt(muted ? A.T.musicOff : A.T.musicOn); }
    });
    // tap the note icon (bottom-left) on touch screens
    let ICON = null;
    const icon = (U, H) => (ICON = { x: U * 1.5, y: H - U * 7.2, s: U * 4 });
    HOOKS.pointer.push((px, py) => { const b = ICON; if (b && px < b.x + b.s + b.s / 2 && py > b.y - b.s / 2 && py < b.y + b.s * 1.2) { setMuted(!muted); pt(muted ? A.T.musicOff : A.T.musicOn); return true; } return false; });
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
