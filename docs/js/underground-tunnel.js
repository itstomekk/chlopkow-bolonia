/* UNDERGROUND TUNNEL (lazy module, kind 'tunnel'): a long north-south corridor drawn in code, muted stone, wooden supports, wall torches.
   NOT in index.html: passages.js fetches this file and docs/data/tunnel-church-cemetery.json the first time the passage is needed
   (the loose brick in the hidden chamber preloads it; the cemetery slab does too).
   build(def, data, ctx) returns a room in the same shape as crypt.js: { w, h, top, ground, obj, objects, solid, pois, candles, lights,
   vignette, kind:'tunnel', labelKey, spawns{crypt,cemetery}, portals[], interact(poi, api), tick(dt) } and NO plain `exit`: the ends are
   portals handled by passages.js (south = back to the crypt, north = stairs up to the hidden slab in the cemetery).
   Engine hooks for later: room.sealed lists walled-up side doors ({id, x, y, gate}); a future underground village / secret-society cellar
   only needs a new passage entry plus a gate on that door. The layout is drawn per segment (SEG px) so nothing is rendered twice. */
'use strict';
(() => {
  const SEG = 256;
  window.PASSAGES.defineKind('tunnel', { build(def, data, ctx) {
    const A = ctx.ARK, W = data.w, H = data.h, C = data.corridor;
    const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
    const ground = mk(), obj = mk(), g = ground.getContext('2d'), o = obj.getContext('2d');
    const solid = new Uint8Array(W * H).fill(2);
    const objects = [], candles = [], lights = [], pois = [];
    const R = (c, x, y, w, h, col) => { c.fillStyle = col; c.fillRect(x, y, w, h); };
    const dot = (c, x, y, col) => { c.fillStyle = col; c.fillRect(x, y, 1, 1); };
    const open = (x, y, w, h) => { for (let j = Math.max(0, y); j < Math.min(H, y + h); j++) solid.fill(0, j * W + Math.max(0, x), j * W + Math.min(W, x + w)); };
    const block = (x, y, w, h) => { for (let j = Math.max(0, y); j < Math.min(H, y + h); j++) solid.fill(2, j * W + Math.max(0, x), j * W + Math.min(W, x + w)); };
    const put = (x, y, w, h, base) => objects.push({ x, y, w, h, base });
    let seed = 29; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const line = (c, x0, y0, x1, y1, col) => {
      c.fillStyle = col; let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy;
      for (;;) { c.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
    };
    const BR = ['#4b463f', '#544e46', '#443f39', '#5a544b', '#4f4a42'], NEW = ['#6b5a48', '#74634f', '#665646'];
    const bricks = (x, y, w, h, pal = BR, mortar = '#25211e') => {
      R(g, x, y, w, h, mortar);
      for (let j = 0, row = 0; j < h; j += 6, row++) for (let i = -((row % 2) * 7); i < w; i += 14) {
        const bx = Math.max(0, i), ex = Math.min(w, i + 13), bh = Math.min(5, h - j);
        if (ex - bx < 1 || bh < 1) continue;
        R(g, x + bx, y + j, ex - bx, bh, pal[(rnd() * pal.length) | 0]); R(g, x + bx, y + j, ex - bx, 1, 'rgba(255,240,210,.09)');
      }
    };
    const WL = C.x0 - 12, WR = C.x1;   // wall strips: [WL, C.x0) and [C.x1, C.x1 + 12)

    /* ---------- rock, then the corridor drawn segment by segment ---------- */
    R(g, 0, 0, W, H, '#0e0c0a');
    for (let i = 0; i < 2400; i++) dot(g, (rnd() * W) | 0, (rnd() * H) | 0, rnd() < .5 ? '#16130f' : '#0a0807');
    const floorTile = (x, y, w, h, kind) => {
      const k = ((x + y) / 16) & 1;
      if (kind === 'flag') { R(g, x, y, w, h, k ? '#37332e' : '#322e29'); R(g, x, y, w, 1, '#1f1c19'); R(g, x, y, 1, h, '#1f1c19'); if (rnd() < .3) R(g, x + 2 + ((rnd() * 9) | 0), y + 4 + ((rnd() * 8) | 0), 4, 1, '#413c35'); if (rnd() < .06) R(g, x + 3 + ((rnd() * 8) | 0), y + 3 + ((rnd() * 8) | 0), 3, 2, '#2f3a24'); }
      else { R(g, x, y, w, h, k ? '#2e2922' : '#2a251f'); for (let n = 0; n < 5; n++) dot(g, x + ((rnd() * w) | 0), y + ((rnd() * h) | 0), rnd() < .5 ? '#3a342b' : '#221e19'); if (rnd() < .12) R(g, x + ((rnd() * 10) | 0), y + ((rnd() * 12) | 0), 3, 2, '#463f34'); }
    };
    for (let y0 = C.y0 - 8; y0 < C.y1 + 36; y0 += SEG) {
      const y1 = Math.min(H, y0 + SEG);
      for (let y = y0; y < y1; y += 16) for (let x = C.x0; x < C.x1; x += 16) {
        const flag = y < 330 || y > 1260 || Math.abs(x - 128) < 8 && rnd() < .8;   // flagstones near both ends and a worn line down the middle; packed earth elsewhere
        floorTile(x, y, Math.min(16, C.x1 - x), Math.min(16, y1 - y), flag ? 'flag' : 'earth');
      }
      bricks(WL, y0, 12, y1 - y0); bricks(WR, y0, 12, y1 - y0);
      R(g, WL, y0, 1, y1 - y0, '#6a6359'); R(g, WR + 11, y0, 1, y1 - y0, '#6a6359');
      R(g, C.x0, y0, 5, y1 - y0, 'rgba(0,0,0,.30)'); R(g, C.x1 - 5, y0, 5, y1 - y0, 'rgba(0,0,0,.30)');   // shadow where wall meets floor
    }
    open(C.x0, C.y0, C.x1 - C.x0, C.y1 - C.y0 + 36);

    /* ---------- north end: stone steps up to the hidden slab (light falls down them) ---------- */
    {
      const st = data.stairs, n = 6, step = Math.round((st.y1 - st.y0) / n);
      R(g, C.x0 - 12, st.y0 - 30, C.x1 - C.x0 + 24, 32, '#1d1a17');
      bricks(C.x0 - 12, st.y0 - 26, C.x1 - C.x0 + 24, 26); R(g, C.x0 - 12, st.y0 - 28, C.x1 - C.x0 + 24, 2, '#6a6359');
      for (let i = 0; i < n; i++) {
        const y = st.y0 + i * step, t = i / (n - 1);
        R(g, C.x0, y, C.x1 - C.x0, step - 1, ['#b6a98c', '#a4977c', '#92856c', '#7e725d', '#6b6050', '#584f43'][i]); R(g, C.x0, y, C.x1 - C.x0, 1, `rgba(255,248,220,${.35 - t * .2})`); R(g, C.x0, y + step - 1, C.x1 - C.x0, 1, '#1a1612');
      }
      // the slab seen from below: a lighter square with a glowing seam and an iron ring
      R(g, C.x0 + 6, st.y0 - 24, C.x1 - C.x0 - 12, 22, '#6f776f'); R(g, C.x0 + 6, st.y0 - 24, C.x1 - C.x0 - 12, 2, '#9aa196'); R(g, C.x0 + 6, st.y0 - 3, C.x1 - C.x0 - 12, 1, '#fff6d0');
      R(g, C.x0 + 6, st.y0 - 24, 1, 22, '#fff6d0'); R(g, C.x1 - 7, st.y0 - 24, 1, 22, '#fff6d0'); R(g, 126, st.y0 - 16, 4, 4, '#2b2520'); R(g, 127, st.y0 - 15, 2, 2, '#6a655c');
      lights.push({ x: 128, y: st.y0 + 12, r: 96, a: .40, c: '190,220,255' });
    }
    pois.push({ key: 'tunnelStairs', x: 128, y: 86, r: 26 });

    /* ---------- south end: the arch back into the crypt ---------- */
    {
      const y = C.y1;
      R(g, WL, y, 12, 40, '#1d1a17'); R(g, WR, y, 12, 40, '#1d1a17'); bricks(WL, y, 12 + (C.x1 - C.x0) + 12, 10, ['#5a544b', '#4f4a42']); R(g, WL, y, 80, 2, '#6a6359');
      for (let i = 0; i < 4; i++) R(g, C.x0, y + 10 + i * 6, C.x1 - C.x0, 5, `rgba(5,4,3,${.35 + i * .17})`);   // the floor falls into the dark
      lights.push({ x: 128, y: C.y1 - 30, r: 64, a: .24, c: '255,200,120' });
    }

    /* ---------- wooden supports (posts in the wall strips, a crossbeam overhead) ---------- */
    const wood = ['#5b4126', '#6b4d2e', '#4a331d'];
    for (const base of data.beams) {
      for (const px of [WL + 1, WR + 5]) { R(g, px, base - 2, 6, 4, '#2b2216'); R(o, px, base - 44, 6, 44, wood[0]); R(o, px, base - 44, 2, 44, wood[1]); R(o, px + 5, base - 44, 1, 44, wood[2]); }
      R(o, C.x0 - 12, base - 48, C.x1 - C.x0 + 24, 6, wood[0]); R(o, C.x0 - 12, base - 48, C.x1 - C.x0 + 24, 2, wood[1]); R(o, C.x0 - 12, base - 43, C.x1 - C.x0 + 24, 1, wood[2]);
      for (let i = 0; i < 3; i++) dot(o, C.x0 + 4 + ((rnd() * 40) | 0), base - 46 + ((rnd() * 3) | 0), '#3a2a18');
      R(g, C.x0, base, C.x1 - C.x0, 3, 'rgba(0,0,0,.22)');       // the beam's shadow on the floor
      put(C.x0 - 12, base - 50, C.x1 - C.x0 + 24, 52, base + 2);
    }

    /* ---------- wall torches ---------- */
    for (const [x, y] of data.torches) {
      R(g, x - 1, y + 2, 2, 12, '#2b2520'); R(g, x - 3, y, 6, 3, '#3a3029'); R(g, x - 2, y + 3, 4, 1, '#1d1814');
      candles.push({ x, y: y - 1 }); lights.push({ x: x < 128 ? x + 14 : x - 14, y: y + 6, r: 66, a: .30, c: '255,168,70' });
    }

    /* ---------- puddles, bones, rats, drips ---------- */
    for (const [x, y, w, h] of data.puddles) {
      R(g, x + 2, y, w - 4, h, '#1c2a30'); R(g, x, y + 2, w, h - 4, '#1c2a30'); R(g, x + 3, y + 1, w - 6, 2, '#41606a'); R(g, x + 6, y + h - 3, w - 14, 1, '#2d4650');
      R(g, x + 1, y + 2, 1, h - 4, '#322d26');   // muddy rim
    }
    for (const [x, y] of data.bones) {
      R(o, x - 2, y + 8, 18, 7, '#8a8068'); for (const [bx, by] of [[x, y + 3], [x + 8, y + 5], [x + 4, y]]) { R(o, bx, by, 6, 5, '#d4cab0'); R(o, bx + 1, by + 2, 1, 2, '#1d1a17'); R(o, bx + 4, by + 2, 1, 2, '#1d1a17'); R(o, bx + 1, by + 5, 4, 1, '#b3a98e'); }
      line(o, x - 2, y + 14, x + 12, y + 12, '#e3dcc6'); R(o, x + 14, y + 4, 2, 12, '#5a4a38'); R(o, x + 12, y + 2, 6, 3, '#7a7468');   // a rusty shovel
      put(x - 4, y - 2, 24, 20, y + 15); block(x - 2, y + 8, 18, 7);
      pois.push({ key: 'tunnelBones', x: x + 6, y: y + 20, r: 24 });
    }
    for (const [x, y] of data.rats) { R(o, x, y + 2, 7, 3, '#4a423a'); R(o, x + 6, y + 1, 3, 3, '#5a5046'); dot(o, x + 8, y + 2, '#c33'); line(o, x - 1, y + 3, x - 5, y + 5, '#6a5a50'); put(x - 5, y, 15, 7, y + 5); }

    /* ---------- the side niche (east) with a tiny lore tablet, and the walled-up door (west) ---------- */
    {
      const n = data.niche, h = n.y1 - n.y0, x0 = C.x1, x1 = C.x1 + n.depth;
      bricks(x0, n.y0 - 8, n.depth + 12, 8); bricks(x0, n.y1, n.depth + 12, 8); bricks(x1, n.y0, 12, h);
      for (let y = n.y0; y < n.y1; y += 16) for (let x = x0; x < x1; x += 16) floorTile(x, y, Math.min(16, x1 - x), Math.min(16, n.y1 - y), 'flag');
      open(x0, n.y0, n.depth, h);
      // tablet on a stone plinth, candle stub, bowl
      R(o, x0 + 10, n.y0 + 16, 16, 14, '#4b463f'); R(o, x0 + 8, n.y0 + 8, 20, 10, '#6a645a'); R(o, x0 + 8, n.y0 + 8, 20, 2, '#8d867a'); R(o, x0 + 8, n.y0 + 16, 20, 2, '#2d2926');
      for (const [i, k] of [[0, 'rose'], [1, 'cross'], [2, 'circle']]) {
        const cx = x0 + 12 + i * 6, cy = n.y0 + 13;
        if (k === 'cross') { R(o, cx, cy - 2, 1, 5, '#2a2622'); R(o, cx - 1, cy, 3, 1, '#2a2622'); } else if (k === 'circle') { R(o, cx - 1, cy - 1, 3, 3, '#2a2622'); dot(o, cx, cy, '#6a645a'); } else { R(o, cx - 1, cy - 1, 3, 3, '#2a2622'); dot(o, cx, cy + 2, '#2a2622'); }
      }
      R(o, x0 + 22, n.y0 + 28, 4, 6, '#e8d9a8'); dot(o, x0 + 23, n.y0 + 27, '#ffb02e'); R(o, x0 + 4, n.y0 + 32, 8, 3, '#6b5c3a');
      put(x0 + 4, n.y0 + 6, 26, 30, n.y0 + 34); block(x0 + 6, n.y0 + 18, 22, 16);
      candles.push({ x: x0 + 24, y: n.y0 + 27 }); lights.push({ x: x0 + 18, y: n.y0 + 26, r: 44, a: .24, c: '255,190,90' });
      pois.push({ key: 'tunnelNiche', x: x0 + 18, y: n.y0 + 40, r: 24 });
    }
    const sealed = [];
    {
      const s = data.sealed, h = s.y1 - s.y0, x1 = C.x0, x0 = C.x0 - s.depth;
      bricks(x0 - 12, s.y0 - 8, s.depth + 12, 8); bricks(x0 - 12, s.y1, s.depth + 12, 8); bricks(x0 - 12, s.y0, 12, h);
      for (let y = s.y0; y < s.y1; y += 16) for (let x = x0; x < x1; x += 16) floorTile(x, y, Math.min(16, x1 - x), Math.min(16, s.y1 - y), 'earth');
      open(x0, s.y0, s.depth, h);
      // the arch is bricked up with newer, redder bricks; chalk marks on them
      R(g, x0 + 2, s.y0 + 2, 6, h - 4, '#1d1a17'); bricks(x0 + 2, s.y0 + 4, 10, h - 8, NEW, '#3a2f26'); R(g, x0 + 2, s.y0 + 2, 12, 3, '#6a6359');
      R(g, x0 + 3, s.y0 + 14, 1, 7, '#d8d2c0'); R(g, x0 + 1, s.y0 + 17, 5, 1, '#d8d2c0'); R(g, x0 + 5, s.y0 + 22, 3, 3, '#d8d2c0'); dot(g, x0 + 6, s.y0 + 23, '#6b5a48'); R(g, x0 + 4, s.y0 + 8, 3, 3, '#d8d2c0'); dot(g, x0 + 5, s.y0 + 9, '#6b5a48');
      R(g, x1 - 6, s.y0 + 6, 6, h - 12, 'rgba(0,0,0,.3)');
      const cy = Math.round((s.y0 + s.y1) / 2);
      pois.push({ key: 'tunnelSealed', x: x0 + 20, y: cy, r: 26 });
      sealed.push({ id: 'sealed-west', x: x0 + 20, y: cy, gate: { type: 'quiz', quiz: 'TODO-underground-village' } });   // engine hook: today the gate is a locked stub
      lights.push({ x: x0 + 20, y: cy, r: 40, a: .12, c: '255,170,90' });
    }

    /* ---------- the room object ---------- */
    let announced = false;
    const portals = [
      { rect: data.portals.crypt, go: () => ctx.PASSAGES.leave(def.id, 'crypt') },
      { rect: data.portals.cemetery, go: () => ctx.PASSAGES.leave(def.id, 'cemetery') },
    ];
    const room = {
      w: W, h: H, top: 0, ground, obj, objects, solid, pois, candles, lights, vignette: true, kind: 'tunnel', labelKey: 'tunnelLabel',
      spawns: data.spawns, portals, sealed, passageId: def.id, seenBefore: !!A.Q.tunnelSeen,
      tick() {   // the first time the tunnel is entered, Arek says a line once the fade is over
        if (announced || A.rooms.busy || A.room !== room) return; announced = true;
        if (!room.seenBefore && A.T.tunnelFirst) A.say('arek', A.T.tunnelFirst);
      },
      interact(poi, api) {
        const T = api.T;
        if (poi === 'tunnelStairs') { api.say('arek', T.tunnelStairs, () => ctx.PASSAGES.leave(def.id, 'cemetery')); return true; }
        if (T[poi]) { api.say('arek', T[poi]); return true; }
        return false;
      },
    };
    return room;
  } });
})();
