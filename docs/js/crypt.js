/* THE CRYPT under the church (Krypta pod kościołem): a secret cellar reached through the confessional.
   Discovery, not a free door:
     1. The confessional whispers a riddle (church POI 'confession'). The four things it names are counted in the church:
        what burns (4 gold candles), what sits (7 rows of pews), what shines in colour (2 stained-glass windows),
        what one climbs (3 altar steps). Reading them after the whisper puts a note in the notebook.
     2. A four-ring cryptex overlay at the confessional takes the code 4-7-2-3 (CRYPT.CODE).
     3. Inside, a second riddle: four wall signs must be touched in the order of the tablet (CRYPT.ORDER);
        that rolls the round stone door aside and reveals the hidden final chamber.
   Rooms use the same shape as church.js: { w, h, top, ground, obj, objects, solid, pois, candles, spawn, exit }.
   Extras used by game.js: lights (flickering additive pools), vignette, kind:'crypt'.
   The hidden chamber also hides a loose brick (POI 'cryptBrick', slightly redder than the gold ones) in its east wall: touching it slides
   a wall block up into the lintel and reveals a short passage whose dark mouth leads into the tunnel to the cemetery. The tunnel itself is
   NOT here: passages.js lazy-loads it (docs/data/passages.json, 'church-cemetery'). This file only draws the crypt side of the door and
   publishes room.openPassages['church-cemetery'] so the passage engine knows the mouth is live.
   Save state (all additive, no SAVE_VERSION bump): Q.cryptHint, Q.cryptNotes[], Q.cryptOpen, Q.cryptSeen, Q.cryptDoor, Q.cryptReward,
   Q.tunnelOpen (the loose brick was pressed: the tunnel exists), Q.tunnelSeen (the tunnel was entered once). */
'use strict';
(() => {
  const NUM = { candles: 4, pew: 7, glass: 2, altar: 3 };                       // what each church clue says
  const RIDDLE = ['candles', 'pew', 'glass', 'altar'];                            // order of the whisper: burns, sits, shines, climbed
  const CODE = RIDDLE.map(k => NUM[k]);                                           // 4 7 2 3
  const ORDER = ['symCrux', 'symRosa', 'symCirculus', 'symLux'];                  // tablet: CRUX, ROSA, CIRCULUS, LUX
  const SYM_X = { symLux: 70, symCirculus: 112, symCrux: 208, symRosa: 250 };      // scrambled on the wall on purpose
  window.CRYPT = {
    CODE, ORDER, NUM, RIDDLE,
    CLUE_KEYS: Object.keys(NUM),
    sanitize(Q) {   // old saves lack these fields; bad ones are dropped, nothing else is touched
      for (const k of ['cryptHint', 'cryptOpen', 'cryptSeen', 'cryptDoor', 'cryptReward', 'tunnelOpen', 'tunnelSeen']) Q[k] = !!Q[k];
      Q.cryptNotes = Array.isArray(Q.cryptNotes) ? Q.cryptNotes.filter((k, i, a) => k in NUM && a.indexOf(k) === i) : [];
      if (Q.tunnelOpen) Q.cryptDoor = true;   // the brick sits in the hidden chamber, so the stone door must be open
      if (Q.cryptDoor) Q.cryptOpen = true;
      return Q;
    },
  };

  /* ================================================================== room */
  window.buildCrypt = function buildCrypt(opts = {}) {
    const W = 320, H = 512;
    const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
    const ground = mk(), obj = mk();
    const g = ground.getContext('2d'), o = obj.getContext('2d');
    const solid = new Uint8Array(W * H).fill(2);                    // everything is rock until carved open
    const objects = [], candles = [], lights = [], pois = [];
    const R = (c, x, y, w, h, col) => { c.fillStyle = col; c.fillRect(x, y, w, h); };
    const openRect = (x, y, w, h) => { for (let j = Math.max(0, y); j < Math.min(H, y + h); j++) solid.fill(0, j * W + Math.max(0, x), j * W + Math.min(W, x + w)); };
    const block = (x, y, w, h) => { for (let j = Math.max(0, y); j < Math.min(H, y + h); j++) solid.fill(2, j * W + Math.max(0, x), j * W + Math.min(W, x + w)); };
    const put = (x, y, w, h, base) => objects.push({ x, y, w, h, base });
    let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const dot = (c, x, y, col) => { c.fillStyle = col; c.fillRect(x, y, 1, 1); };
    const line = (c, x0, y0, x1, y1, col) => {
      c.fillStyle = col; let dx = Math.abs(x1 - x0), dy = -Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, e = dx + dy;
      for (;;) { c.fillRect(x0, y0, 1, 1); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 >= dy) { e += dy; x0 += sx; } if (e2 <= dx) { e += dx; y0 += sy; } }
    };
    const circ = (c, cx, cy, r, col) => {
      c.fillStyle = col; let x = r, y = 0, d = 1 - r;
      while (x >= y) {
        for (const [a, b] of [[x, y], [y, x], [-y, x], [-x, y], [-x, -y], [-y, -x], [y, -x], [x, -y]]) c.fillRect(cx + a, cy + b, 1, 1);
        y++; if (d < 0) d += 2 * y + 1; else { x--; d += 2 * (y - x) + 1; }
      }
    };
    const disc = (c, cx, cy, r, col) => { for (let dy = -r; dy <= r; dy++) { const w = Math.floor(Math.sqrt(r * r - dy * dy)); R(c, cx - w, cy + dy, 2 * w + 1, 1, col); } };

    const BR = ['#4b463f', '#544e46', '#443f39', '#5a544b', '#4f4a42'], BRG = ['#5d4f33', '#6a5a38', '#54482e', '#74623c', '#625434'];
    const bricks = (c, x, y, w, h, pal = BR, mortar = '#25211e') => {
      R(c, x, y, w, h, mortar);
      for (let j = 0, row = 0; j < h; j += 6, row++) for (let i = -((row % 2) * 7); i < w; i += 14) {
        const bx = Math.max(0, i), ex = Math.min(w, i + 13), bh = Math.min(5, h - j);
        if (ex - bx < 1 || bh < 1) continue;
        R(c, x + bx, y + j, ex - bx, bh, pal[(rnd() * pal.length) | 0]); R(c, x + bx, y + j, ex - bx, 1, 'rgba(255,240,210,.10)');
      }
    };
    const flags = (x, y, w, h, warm) => {
      for (let j = y; j < y + h; j += 16) for (let i = x; i < x + w; i += 16) {
        const cw = Math.min(16, x + w - i), ch = Math.min(16, y + h - j), k = ((i + j) / 16) & 1;
        R(g, i, j, cw, ch, warm ? (k ? '#41372a' : '#3b3226') : (k ? '#37332e' : '#322e29'));
        R(g, i, j, cw, 1, warm ? '#231c13' : '#1f1c19'); R(g, i, j, 1, ch, warm ? '#231c13' : '#1f1c19');
        if (rnd() < .3) R(g, i + 2 + ((rnd() * 9) | 0), j + 4 + ((rnd() * 8) | 0), 4, 1, warm ? '#4e4231' : '#413c35');
        if (!warm && rnd() < .07) R(g, i + 3 + ((rnd() * 8) | 0), j + 3 + ((rnd() * 8) | 0), 3, 2, '#2f3a24');
        if (rnd() < .05) line(g, i + 4, j + 3, i + 9, j + 9, '#1c1916');
      }
    };

    /* ---------- rock, floors, walls ---------- */
    R(g, 0, 0, W, H, '#0e0c0a');
    for (let i = 0; i < 900; i++) dot(g, (rnd() * W) | 0, (rnd() * H) | 0, rnd() < .5 ? '#16130f' : '#0a0807');
    // main hall + passage (carve the collision at the same time)
    flags(44, 200, 232, 192); openRect(44, 200, 232, 192);
    flags(136, 392, 48, 104); openRect(136, 392, 48, 112);
    // north wall face of the hall, side walls, south strip with the passage gap
    bricks(g, 32, 160, 256, 40); R(g, 32, 156, 256, 4, '#6a6359'); R(g, 32, 196, 256, 4, 'rgba(0,0,0,.35)');
    bricks(g, 32, 160, 12, 244, BR); bricks(g, 276, 160, 12, 244, BR);
    R(g, 32, 160, 1, 244, '#6a6359'); R(g, 287, 160, 1, 244, '#6a6359');
    bricks(g, 44, 392, 92, 12); bricks(g, 184, 392, 92, 12); R(g, 44, 392, 92, 2, '#6a6359'); R(g, 184, 392, 92, 2, '#6a6359');
    bricks(g, 124, 404, 12, 100); bricks(g, 184, 404, 12, 100); R(g, 124, 404, 1, 100, '#6a6359'); R(g, 195, 404, 1, 100, '#6a6359');
    R(g, 136, 392, 48, 12, '#1d1a17');                                  // dark mouth of the passage under the lintel
    // shadows where wall meets floor
    for (const [x, y, w, h] of [[44, 200, 232, 6], [44, 206, 6, 186], [270, 206, 6, 186]]) R(g, x, y, w, h, 'rgba(0,0,0,.28)');
    // cobwebs in the upper corners
    for (const [x0, y0, dx] of [[44, 200, 1], [275, 200, -1]]) for (let k = 0; k < 4; k++) { line(g, x0, y0, x0 + dx * (8 + k * 3), y0 + 2 + k * 5, 'rgba(220,220,210,.22)'); }
    // stairs up to the church (light falls down them)
    for (let i = 0; i < 5; i++) { const y = 482 + i * 5; R(g, 136, y, 48, 4, ['#6e6354', '#7d705e', '#8d7f69', '#9d8e75', '#b0a086'][i]); R(g, 136, y + 4, 48, 1, '#1a1612'); }
    R(g, 124, 480, 12, 32, '#26221f'); R(g, 184, 480, 12, 32, '#26221f');
    lights.push({ x: 160, y: 500, r: 78, a: .30, c: '255,232,185' });

    /* ---------- the inscribed threshold stone (clue: QUI DESCENDIT, ASCENDIT) ---------- */
    R(g, 140, 428, 40, 16, '#4c473f'); R(g, 140, 428, 40, 1, '#7b7468'); R(g, 140, 443, 40, 1, '#1d1a17');
    for (let row = 0; row < 2; row++) for (let i = 0, x = 144; x < 176; i++) {
      const w = 2 + ((rnd() * 4) | 0); R(g, x, 432 + row * 5, w, 2, '#1f1b18'); R(g, x, 433 + row * 5, w, 1, '#6a6256'); x += w + 2 + ((rnd() * 2) | 0);
    }
    pois.push({ key: 'cryptArch', x: 160, y: 437, r: 20 });

    /* ---------- the wall torches ---------- */
    const torch = (x, y, lx, big) => {
      R(g, x - 1, y + 2, 2, 12, '#2b2520'); R(g, x - 3, y, 6, 3, '#3a3029'); R(g, x - 2, y + 3, 4, 1, '#1d1814');
      candles.push({ x, y: y - 1 }); lights.push({ x: lx ?? x, y: y + (big ? 20 : 6), r: big ? 74 : 56, a: big ? .34 : .28, c: '255,168,70' });   // north-wall torches sit lower so no light leaks into the rock behind
    };
    torch(130, 172, 130, true); torch(190, 172, 190, true);
    torch(130, 426, 142); torch(190, 452, 178); torch(130, 474, 142);   // passage sconces (flames sit on top of the wall)

    /* ---------- the Vitruvian circle in the floor, with a cryptex scale around it ---------- */
    {
      const cx = 160, cy = 296, ink = '#8a7f69', dk = '#1d1a17';
      circ(g, cx, cy + 1, 33, dk); circ(g, cx, cy, 33, ink); circ(g, cx, cy, 30, '#5e5647');
      for (let a = 0; a < 24; a++) { const t = a / 24 * Math.PI * 2; line(g, Math.round(cx + Math.cos(t) * 34), Math.round(cy + Math.sin(t) * 34), Math.round(cx + Math.cos(t) * 38), Math.round(cy + Math.sin(t) * 38), a % 6 === 0 ? ink : '#5e5647'); }
      for (const [x, y, w, h] of [[134, 270, 52, 1], [134, 322, 52, 1], [134, 270, 1, 53], [185, 270, 1, 53]]) R(g, x, y, w, h, ink);   // the square
      disc(g, cx, cy - 18, 3, ink); R(g, cx, cy - 15, 1, 1, dk);                                            // head
      line(g, cx, cy - 14, cx, cy + 6, ink); line(g, cx - 1, cy - 14, cx - 1, cy + 6, '#5e5647');            // body
      line(g, cx, cy - 11, cx - 26, cy - 5, ink); line(g, cx, cy - 11, cx + 26, cy - 5, ink);                // arms, spread low
      line(g, cx, cy - 11, cx - 25, cy - 18, '#5e5647'); line(g, cx, cy - 11, cx + 25, cy - 18, '#5e5647'); // arms, raised
      line(g, cx, cy + 6, cx - 9, cy + 26, ink); line(g, cx, cy + 6, cx + 9, cy + 26, ink);                  // legs together
      line(g, cx, cy + 6, cx - 18, cy + 22, '#5e5647'); line(g, cx, cy + 6, cx + 18, cy + 22, '#5e5647');   // legs apart
    }
    pois.push({ key: 'cryptFloor', x: 160, y: 296, r: 26 });
    lights.push({ x: 160, y: 300, r: 100, a: .10, c: '255,205,130' });

    /* ---------- the four wall signs (state: lit or not) ---------- */
    const symLight = {};
    const glyph = (key, cx, cy, col, c = g) => {
      if (key === 'symCrux') { R(c, cx - 1, cy - 9, 3, 19, col); R(c, cx - 6, cy - 4, 13, 3, col); }
      else if (key === 'symRosa') { for (let k = 0; k < 5; k++) { const t = k / 5 * Math.PI * 2 - Math.PI / 2; R(c, Math.round(cx + Math.cos(t) * 5) - 1, Math.round(cy - 3 + Math.sin(t) * 5) - 1, 3, 3, col); } R(c, cx - 1, cy - 4, 3, 3, col); R(c, cx, cy + 4, 1, 8, col); R(c, cx + 1, cy + 8, 3, 1, col); }
      else if (key === 'symCirculus') { circ(c, cx, cy, 8, col); circ(c, cx, cy, 7, col); R(c, cx - 1, cy - 1, 3, 3, col); }
      else if (key === 'symLux') { [[0, 1], [1, 3], [2, 5], [3, 5], [4, 7], [5, 7], [6, 5], [7, 3]].forEach(([r, w]) => R(c, cx - (w >> 1), cy - 10 + r * 2, w, 2, col)); R(c, cx - 5, cy + 6, 11, 3, col); }
    };
    const drawSym = (key, lit) => {
      const x = SYM_X[key], cy = 177;
      R(g, x - 12, 163, 24, 30, '#2d2926'); R(g, x - 11, 164, 22, 28, lit ? '#6b5a30' : '#4d4741'); R(g, x - 10, 165, 20, 26, lit ? '#4f4224' : '#3f3a35');
      if (lit) { g.globalAlpha = .5; R(g, x - 9, 166, 18, 24, '#ffd86a'); g.globalAlpha = 1; glyph(key, x, cy, '#fff2b8'); }
      else { glyph(key, x + 1, cy + 1, '#6f675c'); glyph(key, x, cy, '#201c19'); }
      symLight[key].a = lit ? .30 : 0;
    };
    for (const k of ORDER) { symLight[k] = { x: SYM_X[k], y: 190, r: 32, a: 0, c: '255,205,100' }; lights.push(symLight[k]); pois.push({ key: k, x: SYM_X[k], y: 213, r: 19 }); }

    /* ---------- the round stone door, and the chamber behind it ---------- */
    let doorOpen = false;
    const drawDoorClosed = () => {
      R(g, 136, 158, 48, 42, '#2b2724'); R(g, 138, 160, 44, 40, '#37322d');
      disc(g, 160, 181, 20, '#27231f'); disc(g, 160, 181, 19, '#5a544c');
      for (const [r, col] of [[19, '#2a2622'], [14, '#2a2622'], [9, '#2a2622'], [4, '#2a2622']]) circ(g, 160, 181, r, col);
      for (const r of [16, 11, 6]) for (let a = 0; a < 12; a++) { const t = a / 12 * Math.PI * 2; dot(g, Math.round(160 + Math.cos(t) * r), Math.round(181 + Math.sin(t) * r), '#7b7367'); }
      for (const [dx, dy] of [[0, -16], [16, 0], [0, 16], [-16, 0]]) R(g, 160 + dx - 1, 181 + dy - 1, 3, 3, '#1f1b18');
      disc(g, 160, 181, 2, '#8a7a55'); dot(g, 160, 181, '#d8c07a');
    };
    drawDoorClosed();
    pois.push({ key: 'cryptDoor', x: 160, y: 214, r: 20 });

    const chamberDone = { v: false };
    const drawChamber = () => {
      if (chamberDone.v) return; chamberDone.v = true;
      // walls of the chamber, warm gold-tinted stone
      bricks(g, 92, 36, 136, 40, BRG); R(g, 92, 32, 136, 4, '#8a7447'); R(g, 92, 72, 136, 4, 'rgba(0,0,0,.35)');
      bricks(g, 92, 76, 8, 84, BRG); bricks(g, 220, 76, 8, 84, BRG);
      flags(100, 76, 120, 84, true); R(g, 100, 76, 120, 6, 'rgba(0,0,0,.3)');
      bricks(g, 92, 160, 52, 4, BRG); bricks(g, 176, 160, 52, 4, BRG);
      // the doorway: corridor floor, rings carved into the frame, the stone disc parked in the wall
      R(g, 136, 158, 48, 42, '#2b2724'); R(g, 144, 160, 32, 40, '#2a231a');
      for (let j = 162; j < 200; j += 8) R(g, 144, j, 32, 1, '#1b150e');
      R(g, 138, 160, 6, 40, '#4a443d'); R(g, 176, 160, 6, 40, '#4a443d');
      for (let j = 164; j < 200; j += 9) { R(g, 139, j, 4, 1, '#8a7a55'); R(g, 177, j, 4, 1, '#8a7a55'); }
      // floor mosaic: a rose in a circle, the four signs at the compass points
      circ(g, 160, 120, 28, '#8a7447'); circ(g, 160, 120, 26, '#5e4f2f'); circ(g, 160, 120, 12, '#8a7447');
      for (let k = 0; k < 8; k++) { const t = k / 8 * Math.PI * 2; line(g, Math.round(160 + Math.cos(t) * 12), Math.round(120 + Math.sin(t) * 12), Math.round(160 + Math.cos(t) * 25), Math.round(120 + Math.sin(t) * 25), '#6e5c37'); }
      // the village carved in the north wall: river, church, windmill, and a small X
      R(g, 122, 40, 76, 30, '#5a4e36'); R(g, 123, 41, 74, 28, '#6b5d40');
      line(g, 124, 66, 134, 58, '#2f3a40'); line(g, 134, 58, 142, 62, '#2f3a40'); line(g, 142, 62, 154, 52, '#2f3a40'); line(g, 154, 52, 160, 44, '#2f3a40'); line(g, 124, 67, 134, 59, '#82929a'); line(g, 134, 59, 142, 63, '#82929a');
      R(g, 170, 56, 7, 6, '#2b2217'); R(g, 172, 52, 3, 4, '#2b2217'); R(g, 173, 49, 1, 3, '#2b2217'); R(g, 172, 50, 3, 1, '#2b2217');     // church with a cross
      line(g, 186, 64, 190, 52, '#2b2217'); line(g, 192, 64, 188, 52, '#2b2217'); line(g, 183, 55, 195, 61, '#2b2217'); line(g, 183, 61, 195, 55, '#2b2217');  // windmill sails
      line(g, 160, 60, 164, 64, '#a02a22'); line(g, 164, 60, 160, 64, '#a02a22');     // the X
      // the pulpit with the sealed book
      R(o, 146, 104, 28, 20, '#5d5448'); R(o, 146, 104, 28, 2, '#8d826f'); R(o, 148, 106, 24, 14, '#4a4238'); R(o, 146, 122, 28, 3, '#2b261f');
      R(o, 148, 96, 24, 9, '#6b3f2a'); R(o, 148, 96, 24, 1, '#9a6a44'); R(o, 158, 98, 4, 5, '#d8b25a'); R(o, 156, 100, 8, 1, '#d8b25a'); R(o, 150, 98, 3, 3, '#d8b25a'); R(o, 167, 98, 3, 3, '#d8b25a');
      put(144, 92, 32, 34, 124); block(146, 112, 28, 12);
      // gold candles around the book
      for (const [x, y] of [[112, 92], [208, 92], [112, 146], [208, 146]]) {
        R(o, x - 2, y + 10, 5, 3, '#6b5c3a'); R(o, x - 1, y, 3, 11, '#e8d9a8'); R(o, x - 1, y, 3, 1, '#fff6d0');
        put(x - 3, y - 2, 7, 16, y + 13); block(x - 3, y + 8, 7, 5); candles.push({ x, y: y - 1 }); lights.push({ x, y: y + 4, r: 46, a: .28, c: '255,190,90' });
      }
      lights.push({ x: 160, y: 114, r: 104, a: .26, c: '255,205,120' });
      openRect(100, 76, 120, 84); openRect(144, 156, 32, 46);
      pois.push({ key: 'cryptMap', x: 126, y: 94, r: 24 }, { key: 'cryptBook', x: 160, y: 138, r: 24 });
      // the loose brick in the east wall: redder than its gold neighbours, with a few crumbs under it
      R(g, 221, 118, 6, 5, '#8c5f3e'); R(g, 221, 118, 6, 1, '#bd8d5f'); R(g, 221, 122, 6, 1, '#4a301c'); R(g, 222, 124, 3, 1, '#3d3020'); dot(g, 225, 126, '#5a4a2c');
      pois.push({ key: 'cryptBrick', x: 213, y: 121, r: 20 });
      if (opts.tunnel) openTunnel(false);
    };

    /* ---------- the secret passage behind the east wall (opens from the loose brick; the tunnel itself is lazy-loaded) ---------- */
    const MOUTH = { x0: 276, x1: 296, y0: 108, y1: 136 };   // keep in sync with ends.a.outer.mouth in docs/data/passages.json
    const openPassages = {};
    let tunnelOpened = false, slide = null, piece = null, floorCache = null;
    const drawCorridor = () => {
      bricks(g, 228, 88, 68, 20, BRG); R(g, 228, 84, 68, 4, '#8a7447'); R(g, 228, 104, 68, 4, 'rgba(0,0,0,.4)');    // north wall face
      bricks(g, 228, 136, 68, 8, BR); R(g, 228, 136, 68, 2, '#6a6359');                                               // low south wall
      bricks(g, 296, 84, 8, 60, BR);                                                                                   // the end of the passage
      flags(220, 108, 76, 28, false); R(g, 220, 108, 76, 5, 'rgba(0,0,0,.3)');
      for (let k = 0; k < 6; k++) R(g, 290 + k, 108, 1, 28, `rgba(5,4,3,${.12 + k * .13})`);                         // the floor falls into the dark
      R(g, 286, 104, 10, 4, '#2a2622'); R(g, 288, 108, 8, 28, 'rgba(8,7,5,.72)'); R(g, 284, 104, 2, 36, '#4a443d');   // arch stones and the black mouth
      for (const x of [244, 262]) R(g, x, 90, 4, 14, '#2b2520');                                                       // soot above the sconces
      torch(252, 112, 252, false); lights.push({ x: 262, y: 122, r: 46, a: .16, c: '255,168,70' });
    };
    function openTunnel(animate, done) {
      if (tunnelOpened) return; tunnelOpened = true;
      piece = document.createElement('canvas'); piece.width = 8; piece.height = 28; piece.getContext('2d').drawImage(ground, 220, 108, 8, 28, 0, 0, 8, 28);
      drawCorridor();
      floorCache = document.createElement('canvas'); floorCache.width = 8; floorCache.height = 28; floorCache.getContext('2d').drawImage(ground, 220, 108, 8, 28, 0, 0, 8, 28);
      const finish = () => { slide = null; R(g, 220, 108, 8, 28, 'rgba(0,0,0,0)'); g.clearRect(220, 108, 8, 28); g.drawImage(floorCache, 220, 108); openRect(220, 108, 76, 28); openPassages['church-cemetery'] = true; if (done) done(); };
      if (animate) { slide = { t: 0, finish }; g.drawImage(piece, 220, 108); } else finish();
    }
    const tick = dt => {   // the wall block slides up into the lintel (0.6 s), then the walkable floor appears
      if (!slide) return;
      slide.t += dt; const k = Math.min(1, slide.t / .6), e = k * k * (3 - 2 * k), vis = Math.round(28 * (1 - e));
      g.clearRect(220, 108, 8, 28); g.drawImage(floorCache, 220, 108); if (vis > 0) g.drawImage(piece, 0, 28 - vis, 8, vis, 220, 108, 8, vis);
      if (k >= 1) slide.finish();
    };
    const openDoor = () => {
      if (doorOpen) return; doorOpen = true;
      drawChamber(); for (const k of ORDER) drawSym(k, true);
    };

    /* ---------- standing objects (depth-sorted against Arek) ---------- */
    const pillar = (cx, base) => {
      R(o, cx - 7, base - 52, 15, 52, '#4a453e'); R(o, cx - 7, base - 52, 5, 52, '#6a645b'); R(o, cx + 4, base - 52, 4, 52, '#35312c'); R(o, cx - 2, base - 52, 6, 52, '#58524a');
      for (let y = base - 48; y < base - 6; y += 9) R(o, cx - 7, y, 15, 1, 'rgba(0,0,0,.22)');
      R(o, cx - 9, base - 58, 19, 6, '#6a645b'); R(o, cx - 9, base - 53, 19, 1, '#25211e'); R(o, cx - 9, base - 5, 19, 5, '#5a544b'); R(o, cx - 9, base - 1, 19, 1, '#25211e');
      put(cx - 10, base - 60, 21, 62, base); block(cx - 9, base - 6, 19, 6);
    };
    for (const cx of [108, 212]) for (const by of [246, 336]) pillar(cx, by);
    const sarc = (x, y, kind) => {
      R(o, x, y + 6, 30, 34, '#6d675d'); R(o, x, y + 6, 30, 2, '#8a8377'); R(o, x + 2, y + 9, 26, 28, '#5e584f'); R(o, x + 28, y + 6, 2, 34, '#4d4841');
      if (kind === 'cross') { R(o, x + 14, y + 13, 2, 20, '#38342e'); R(o, x + 9, y + 18, 12, 2, '#38342e'); R(o, x + 15, y + 13, 1, 20, '#7a7468'); }
      else { line(o, x + 8, y + 13, x + 22, y + 34, '#38342e'); line(o, x + 22, y + 13, x + 8, y + 34, '#38342e'); line(o, x + 9, y + 13, x + 23, y + 34, '#7a7468'); }
      R(o, x - 1, y + 40, 32, 8, '#47423b'); R(o, x - 1, y + 40, 32, 1, '#837c70'); R(o, x - 1, y + 47, 32, 1, '#25211e');
      put(x - 2, y + 4, 34, 46, y + 48); block(x - 1, y + 14, 32, 34);
    };
    sarc(48, 212, 'cross'); sarc(48, 292, 'cross'); sarc(242, 212, 'scythes'); sarc(242, 292, 'scythes');
    candles.push({ x: 63, y: 214 }, { x: 257, y: 214 });
    lights.push({ x: 63, y: 220, r: 50, a: .22, c: '255,170,80' }, { x: 257, y: 220, r: 50, a: .22, c: '255,170,80' });
    for (const [x, y] of [[63, 215], [257, 215]]) { R(o, x - 1, y, 3, 8, '#d9c99a'); put(x - 3, y - 2, 7, 12, y + 8); }
    for (const [x, y] of [[88, 252], [232, 252], [88, 322], [232, 322]]) pois.push({ key: 'cryptTomb', x, y, r: 24 });
    // the tablet on a stone lectern (the order: CRUX, ROSA, CIRCULUS, LUX)
    R(o, 208, 360, 14, 16, '#4b463f'); R(o, 202, 346, 26, 16, '#6a645a'); R(o, 202, 346, 26, 2, '#8d867a'); R(o, 202, 360, 26, 2, '#2d2926');
    for (let r = 0; r < 4; r++) for (let i = 0, x = 205; x < 224; i++) { const w = 2 + (((r * 3 + i) * 7) % 4); R(o, x, 350 + r * 2 + (r > 2 ? 1 : 0), w, 1, '#2a2622'); x += w + 2; }
    put(200, 344, 30, 34, 376); block(204, 366, 22, 10);
    pois.push({ key: 'cryptPlaque', x: 214, y: 385, r: 18 });
    // a heap of old bones against the passage wall
    R(o, 137, 446, 16, 8, '#8a8068'); for (const [x, y] of [[138, 441], [146, 443], [142, 437]]) { R(o, x, y, 6, 5, '#d4cab0'); R(o, x + 1, y + 2, 1, 2, '#1d1a17'); R(o, x + 4, y + 2, 1, 2, '#1d1a17'); R(o, x + 1, y + 5, 4, 1, '#b3a98e'); }
    line(o, 138, 452, 150, 449, '#e3dcc6'); line(o, 140, 454, 152, 453, '#cfc6ac');
    put(136, 434, 20, 22, 455); block(137, 448, 16, 6);

    if (opts.door) openDoor(); else for (const k of ORDER) drawSym(k, false);
    return {
      w: W, h: H, top: 0, ground, obj, objects, solid, pois, candles, lights, vignette: true, kind: 'crypt',
      spawn: { x: 160, y: 466 }, exit: { x0: 140, x1: 180, y: 497 }, rid: 'crypt',
      seq: 0, get doorOpen() { return doorOpen; }, get tunnelOpened() { return tunnelOpened; }, openPassages, mouth: MOUTH, openTunnel, tick,
      setLit: (key, on) => drawSym(key, on), openDoor,
      resetSymbols() { this.seq = 0; for (const k of ORDER) drawSym(k, false); },
    };
  };

  /* ================================================================== interaction logic (called from game.js) */
  // Church side: the confessional riddle and the counting clues. Returns true when it handled the POI.
  window.CRYPT.churchInteract = function (poi, api) {
    const { Q, say, popToast, save, T } = api;
    if (poi === 'confession') {
      if (Q.cryptOpen) { api.enter(); return true; }
      if (!Q.cryptHint) { Q.cryptHint = true; save(); say('szept', T.confessionHint); return true; }
      window.CRYPT.openPuzzle && window.CRYPT.openPuzzle(); return true;
    }
    if (Q.cryptHint && poi in NUM) {
      say('arek', T[poi].concat(T.clue[poi]));
      if (!Q.cryptNotes.includes(poi)) { Q.cryptNotes.push(poi); save(); popToast(`${T.cryptNote}: ${T.cryptNoteNames[poi]} ${NUM[poi]}`); }
      return true;
    }
    if (Q.cryptHint && poi === 'flowers') { say('arek', T.flowers.concat(T.clue.flowers)); return true; }
    return false;
  };
  // Crypt side: signs, door, book and the plain inscriptions. Returns true when handled.
  window.CRYPT.cryptInteract = function (poi, api) {
    const { Q, say, popToast, save, T, room } = api;
    if (ORDER.includes(poi)) {
      if (Q.cryptDoor) { say('arek', T.symDone); return true; }
      if (poi === ORDER[room.seq]) {
        room.seq++; room.setLit(poi, true); popToast(`${T.symOk} ${room.seq}/4`);
        if (room.seq === 4) {
          Q.cryptDoor = true; save(); room.openDoor();
          say('arek', T.cryptDoorOpen, () => popToast(T.cryptDoorToast));
        }
      } else { room.resetSymbols(); popToast(T.symWrong); }
      return true;
    }
    if (poi === 'cryptDoor') { say('arek', Q.cryptDoor ? T.cryptDoorOpened : T.cryptDoorShut); return true; }
    if (poi === 'cryptBrick') {   // the loose brick: slides the wall open and starts the lazy-load of the tunnel
      if (room.tunnelOpened) { say('arek', T.tunnelBrickAgain); return true; }
      say('arek', T.tunnelBrick, () => {
        Q.tunnelOpen = true; save(); popToast(T.tunnelClick);
        if (window.PASSAGES) window.PASSAGES.preload('church-cemetery');
        if (window.ARK && window.ARK.burst) window.ARK.burst(224, 122, ['#8a7447', '#5d4f33', '#3d3020'], 14);
        room.openTunnel(true, () => say('arek', T.tunnelWallOpen, () => popToast(T.tunnelToast)));
      });
      return true;
    }
    if (poi === 'cryptBook') {
      if (Q.cryptReward) { say('arek', T.cryptBookAgain); return true; }
      say('arek', T.cryptBook, () => { Q.cryptReward = true; save(); popToast(T.cryptFound); if (api.celebrate) api.celebrate(); });
      return true;
    }
    return false;
  };

  /* ================================================================== cryptex overlay (canvas, plugs into HOOKS) */
  window.addEventListener('ark-ready', () => {
    const A = window.ARK, { HOOKS, ctx } = A;
    const Q = () => A.Q;
    let PZ = null;   // { d:[4 digits], sel, t, bad, panel, rings:[{x,y,w,h}], ok, close }
    window.CRYPT.openPuzzle = () => { PZ = { d: [0, 0, 0, 0], sel: 0, t: 0, bad: 0, panel: null, rings: [], ok: null, close: null }; };
    window.CRYPT.puzzle = () => PZ ? { d: PZ.d.slice(), sel: PZ.sel } : null;   // for tests
    const check = () => {
      if (PZ.d.every((v, i) => v === CODE[i])) {
        PZ = null; const Qs = Q(); Qs.cryptOpen = true; A.save();
        const r = A.room; if (r && r.openConfessional) r.openConfessional();
        A.popToast(A.T.cryptUnlocked); A.say('arek', A.T.cryptSolved, () => A.enterCrypt());
      } else { PZ.bad = 1.1; A.popToast(A.T.cryptWrong); }
    };
    const turn = (i, by) => { PZ.sel = i; PZ.d[i] = (PZ.d[i] + by + 10) % 10; };
    HOOKS.key.push(e => {
      if (!PZ) return false;
      const c = e.code;
      if (c === 'Escape') PZ = null;
      else if (c === 'ArrowLeft' || c === 'KeyA') PZ.sel = (PZ.sel + 3) % 4;
      else if (c === 'ArrowRight' || c === 'KeyD') PZ.sel = (PZ.sel + 1) % 4;
      else if (c === 'ArrowUp' || c === 'KeyW') turn(PZ.sel, 1);
      else if (c === 'ArrowDown' || c === 'KeyS') turn(PZ.sel, -1);
      else if (/^(Digit|Numpad)\d$/.test(c)) { PZ.d[PZ.sel] = +c.slice(-1); PZ.sel = Math.min(3, PZ.sel + 1); }
      else if (c === 'Enter' || c === 'Space') check();
      return true;
    });
    const inRect = (px, py, r) => r && px >= r[0] && px <= r[0] + r[2] && py >= r[1] && py <= r[1] + r[3];
    HOOKS.pointer.push((px, py) => {
      if (!PZ) return false;
      if (inRect(px, py, PZ.close)) { PZ = null; return true; }
      if (inRect(px, py, PZ.ok)) { check(); return true; }
      PZ.rings.forEach((r, i) => { if (inRect(px, py, [r.x, r.y - r.h * .5, r.w, r.h * 2])) turn(i, py < r.y + r.h / 2 ? 1 : -1); });
      if (!inRect(px, py, PZ.panel)) PZ = null;
      return true;
    });
    HOOKS.blocksPlayer.push(() => !!PZ);
    HOOKS.busy.push(() => !!PZ);
    HOOKS.update.push(dt => { if (PZ) { PZ.t += dt; PZ.bad = Math.max(0, PZ.bad - dt); } });
    HOOKS.questLog.push(lines => { if (Q().cryptHint) lines.push([A.T.cryptQuest, !!Q().cryptReward]); });
    HOOKS.hud.push((U, W, H) => {
      if (!PZ) return;
      const T = A.T, pw = Math.min(W - U * 4, U * 72), ph = U * 50, px = (W - pw) / 2, py = (H - ph) / 2;
      PZ.panel = [px, py, pw, ph];
      ctx.save(); ctx.globalAlpha = 1; ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(0,0,0,.66)'; ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#1d1713'; ctx.fillRect(px, py, pw, ph);
      ctx.strokeStyle = '#8a6a2a'; ctx.lineWidth = Math.max(2, U * .45); ctx.strokeRect(px + U * .4, py + U * .4, pw - U * .8, ph - U * .8);
      ctx.strokeStyle = '#4a3a1a'; ctx.lineWidth = Math.max(1, U * .2); ctx.strokeRect(px + U * 1.2, py + U * 1.2, pw - U * 2.4, ph - U * 2.4);
      ctx.textAlign = 'center'; ctx.font = `${U * 2.5}px PixelifySans`; ctx.fillStyle = '#ffd21f'; ctx.fillText(T.cryptPuzzleTitle, W / 2, py + U * 4);
      ctx.font = `${U * 1.45}px PixelifySans`; ctx.fillStyle = '#c9b27a';
      A.wrapText(T.cryptRiddle.toUpperCase(), pw - U * 8).slice(0, 3).forEach((l, i) => ctx.fillText(l, W / 2, py + U * 8 + i * U * 2.1));
      // the four rings
      const cw = U * 8.4, gap = U * 3.2, rh = U * 11, total = cw * 4 + gap * 3, rx0 = (W - total) / 2, ry = py + U * 16.5;
      PZ.rings = [];
      for (let i = 0; i < 4; i++) {
        const x = rx0 + i * (cw + gap), sel = i === PZ.sel, shake = PZ.bad > 0 ? Math.sin(PZ.t * 60) * U * .35 : 0;
        PZ.rings.push({ x, y: ry, w: cw, h: rh });
        const xs = x + shake;
        ctx.fillStyle = '#3d2c0f'; ctx.fillRect(xs, ry - U * 3.2, cw, rh + U * 6.4);          // the cylinder, with the neighbours showing
        ctx.fillStyle = '#6b5120'; ctx.fillRect(xs, ry - U * 3.2, cw, U * 3.2); ctx.fillRect(xs, ry + rh, cw, U * 3.2);
        ctx.fillStyle = PZ.bad > 0 ? '#9a4a3a' : '#a98234'; ctx.fillRect(xs, ry, cw, rh);
        ctx.fillStyle = PZ.bad > 0 ? '#c86a58' : '#d8b04a'; ctx.fillRect(xs, ry + U * .6, cw, U * .9);
        ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.fillRect(xs, ry + rh - U * 1.4, cw, U * 1.4);
        ctx.textAlign = 'center'; ctx.font = `${U * 2.6}px PixelifySans`; ctx.fillStyle = '#8a6a2a';
        ctx.fillText(String((PZ.d[i] + 1) % 10), xs + cw / 2, ry - U * 1.7); ctx.fillText(String((PZ.d[i] + 9) % 10), xs + cw / 2, ry + rh + U * 1.7);
        ctx.font = `${U * 6}px PixelifySans`; ctx.fillStyle = '#2b1d0a'; ctx.fillText(String(PZ.d[i]), xs + cw / 2 + U * .3, ry + rh / 2 + U * .3);
        ctx.fillStyle = '#fff1c0'; ctx.fillText(String(PZ.d[i]), xs + cw / 2, ry + rh / 2);
        if (sel) {
          ctx.strokeStyle = Math.floor(PZ.t * 3) % 2 ? '#ffd21f' : '#fff1c0'; ctx.lineWidth = Math.max(2, U * .4); ctx.strokeRect(xs - U * .3, ry - U * 3.5, cw + U * .6, rh + U * 7);
          ctx.fillStyle = '#ffd21f';
          ctx.beginPath(); ctx.moveTo(xs + cw / 2, ry - U * 5.8); ctx.lineTo(xs + cw / 2 - U * 1.3, ry - U * 4); ctx.lineTo(xs + cw / 2 + U * 1.3, ry - U * 4); ctx.fill();
          ctx.beginPath(); ctx.moveTo(xs + cw / 2, ry + rh + U * 5.8); ctx.lineTo(xs + cw / 2 - U * 1.3, ry + rh + U * 4); ctx.lineTo(xs + cw / 2 + U * 1.3, ry + rh + U * 4); ctx.fill();
        }
      }
      // notebook
      const ny = ry + rh + U * 9.5, notes = Q().cryptNotes || [];
      ctx.textAlign = 'left'; ctx.font = `${U * 1.45}px PixelifySans`; ctx.fillStyle = '#ffd21f'; ctx.fillText(T.cryptNotesTitle, px + U * 4, ny);
      ctx.fillStyle = '#f5f0e0';
      const txt = notes.length ? notes.map(k => `${T.cryptNoteNames[k]} ${NUM[k]}`).join('  ·  ') : T.cryptNotesEmpty;
      A.wrapText(txt, pw - U * 8).slice(0, 2).forEach((l, i) => ctx.fillText(l, px + U * 4, ny + U * 2.4 + i * U * 2.1));
      // buttons + help
      const bw = U * 15, bh = U * 4.2, bx = px + pw - bw - U * 4, by = py + ph - bh - U * 3.4;
      PZ.ok = [bx, by, bw, bh]; ctx.fillStyle = '#6b5120'; ctx.fillRect(bx, by, bw, bh); ctx.fillStyle = '#a98234'; ctx.fillRect(bx, by, bw, U * .6);
      ctx.textAlign = 'center'; ctx.font = `${U * 1.8}px PixelifySans`; ctx.fillStyle = '#fff1c0'; ctx.fillText(T.cryptTry, bx + bw / 2, by + bh / 2 + U * .1);
      const xs = U * 3.6; PZ.close = [px + pw - xs - U * 1.6, py + U * 1.6, xs, xs];
      ctx.fillStyle = '#4a3a1a'; ctx.fillRect(...PZ.close); ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2}px PixelifySans`; ctx.fillText('X', PZ.close[0] + xs / 2, PZ.close[1] + xs / 2);
      ctx.textAlign = 'left'; ctx.font = `${U * 1.2}px PixelifySans`; ctx.fillStyle = '#8f8468'; ctx.fillText(T.cryptHelp, px + U * 4, py + ph - U * 2.4);
      if (PZ.bad > 0) { ctx.textAlign = 'center'; ctx.font = `${U * 2}px PixelifySans`; ctx.fillStyle = '#ff6a58'; ctx.fillText(T.cryptWrong, W / 2, ry + rh + U * 7.2 - U * 0); }
      ctx.restore();
    });
  });
})();
