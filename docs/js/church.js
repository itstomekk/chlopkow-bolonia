/* CHURCH INTERIOR — Kościół pw. Narodzenia NMP, drawn in code from Tomek's reference photos (2026-09-27):
   cream walls, marble presbytery with three steps, altar with white lace cloth, four gold candles, marble ambo,
   Sacred Heart painting between marble columns, stained glass, murals, Lourdes Mary in a marble niche,
   light-pine pews, big leaded side windows, Stations of the Cross, flags, confessional, the "100" jubilee flowers.
   Returns a room in the same shape game.js uses for the village: ground canvas, object canvas + sorted object
   rects, collision bytes (0 floor, 2 solid), pois, spawn and exit. 1 unit = 1 art pixel, like map_ground.png.
   A GPT-generated interior can replace ground/objects later; keep the layout constants in sync. */
'use strict';
/* Optional AI art: a PNG in docs/img/church/ named after a key of CHURCH_PIECES (and listed in manifest.json,
   which gen/prep_church_sprite.py maintains) replaces the hand-drawn piece.
   Sprites are transparent PNGs cropped to the object, any resolution; they are fitted into the box (keeping
   aspect, centred, standing on the bottom edge). 'backwall' is stretched to fill its box. Missing files = hand-drawn. */
window.CHURCH_PIECES = {
  backwall: [0, 0, 320, 104], altar: [126, 104, 68, 45], candles: [103, 98, 24, 48], cross: [194, 86, 12, 63],
  ambo: [228, 106, 34, 45], banner: [266, 92, 28, 44], mary: [14, 98, 48, 53], flags: [288, 92, 20, 70],
  flowers100: [134, 146, 52, 32], pew: null, confessional: [15, 388, 36, 39], font: [195, 405, 14, 17], soltys: null,
};
window.CHURCH_ART = {};
window.fitSprite = function (ctx, img, x, y, w, h, stretch) {
  ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  if (stretch) { ctx.drawImage(img, x, y, w, h); return; }
  const k = Math.min(w / img.width, h / img.height), dw = img.width * k, dh = img.height * k;
  ctx.drawImage(img, x + (w - dw) / 2, y + h - dh, dw, dh);
};
window.buildChurch = function buildChurch() {
  const W = 320, H = 440;
  const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const ground = mk(), obj = mk();
  const g = ground.getContext('2d'), o = obj.getContext('2d');
  const solid = new Uint8Array(W * H);
  const objects = [];
  const R = (c, x, y, w, h, col) => { c.fillStyle = col; c.fillRect(x, y, w, h); };
  const block = (x, y, w, h) => { for (let j = Math.max(0, y); j < Math.min(H, y + h); j++) solid.fill(2, j * W + Math.max(0, x), j * W + Math.min(W, x + w)); };
  const put = (x, y, w, h, base) => objects.push({ x, y, w, h, base });
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;

  /* ---------- floor ---------- */
  for (let y = 112; y < H; y += 16) for (let x = 0; x < W; x += 16) {
    const pres = y < 160, k = ((x + y) / 16) % 2;
    R(g, x, y, 16, 16, pres ? (k ? '#ece6da' : '#e2dccf') : (k ? '#eadfc8' : '#e3d6bb'));
    R(g, x, y, 16, 1, pres ? '#d3cbbb' : '#d4c4a3'); R(g, x, y, 1, 16, pres ? '#d3cbbb' : '#d4c4a3');
    if (rnd() < .35) R(g, x + 3 + (rnd() * 9 | 0), y + 3 + (rnd() * 9 | 0), 3, 1, '#f6efe0');   // marble glint
  }
  // light falling from the big side windows
  g.globalAlpha = .22;
  for (const wy of [200, 290]) for (const [x0, dir] of [[12, 1], [308, -1]]) {
    g.fillStyle = '#fff6c8'; g.beginPath(); g.moveTo(x0, wy); g.lineTo(x0, wy + 44); g.lineTo(x0 + dir * 70, wy + 64); g.lineTo(x0 + dir * 70, wy + 20); g.fill();
  }
  g.globalAlpha = 1;
  // presbytery steps
  for (let i = 0; i < 3; i++) { R(g, 12, 160 + i * 5, W - 24, 5, ['#f1ece2', '#e4ddd0', '#d8d0c1'][i]); R(g, 12, 164 + i * 5, W - 24, 1, '#bdb3a2'); }
  // aisle carpet
  R(g, 146, 175, 28, 252, '#8e2b25'); R(g, 148, 175, 24, 252, '#a8382e');
  for (let y = 180; y < 425; y += 8) { R(g, 152, y, 16, 1, '#6d1f1b'); R(g, 158, y + 3, 4, 2, '#d8a441'); }
  R(g, 148, 175, 1, 252, '#d8a441'); R(g, 171, 175, 1, 252, '#d8a441');
  R(g, 132, 110, 56, 50, '#c2a15c'); R(g, 134, 112, 52, 46, '#a5462f');   // rug under the altar

  /* ---------- walls ---------- */
  R(g, 0, 0, W, 112, '#efe8d8');
  for (let y = 0; y < 112; y += 4) R(g, 0, y, W, 1, 'rgba(160,140,110,.08)');
  R(g, 0, 0, W, 8, '#d9ceb6'); R(g, 0, 8, W, 2, '#bfb196'); R(g, 0, 104, W, 8, '#ddd2ba'); R(g, 0, 104, W, 1, '#b8a98c');
  // apse arch + Sacred Heart painting between marble columns
  R(g, 112, 12, 96, 92, '#e6dcc4'); g.fillStyle = '#e6dcc4'; g.beginPath(); g.arc(160, 26, 48, Math.PI, 0); g.fill();
  R(g, 132, 16, 56, 80, '#c29b3e'); R(g, 134, 18, 52, 76, '#8fb6d8'); R(g, 134, 66, 52, 28, '#6f9a4a');
  R(g, 150, 32, 20, 58, '#fbf6ea'); R(g, 146, 38, 28, 48, '#c9362c'); R(g, 150, 38, 8, 40, '#e05a44');   // robe + mantle
  R(g, 154, 24, 12, 12, '#e8b58c'); R(g, 153, 22, 14, 5, '#6b4424'); R(g, 158, 44, 4, 4, '#ffd24a');     // head, hair, heart
  R(g, 150, 20, 20, 2, '#ffe9a0');
  for (const cx of [104, 206]) { R(g, cx, 18, 10, 86, '#dcd6cc'); R(g, cx + 2, 18, 3, 86, '#f2eee6'); R(g, cx + 7, 18, 1, 86, '#b9b1a4'); R(g, cx - 2, 14, 14, 5, '#cbc3b5'); R(g, cx - 2, 100, 14, 4, '#cbc3b5'); }
  // stained glass
  const glass = (x, y, w, h) => {
    g.fillStyle = '#3a3a44'; g.beginPath(); g.arc(x + w / 2, y + w / 2, w / 2 + 1, Math.PI, 0); g.fill(); R(g, x - 1, y + w / 2, w + 2, h - w / 2 + 1, '#3a3a44');
    const cols = ['#2f63b8', '#4a86d8', '#c8322e', '#e8c248', '#3d9a55', '#7a4ab0', '#86c3e8'];
    for (let j = y + 2; j < y + h; j += 4) for (let i = x + 1; i < x + w - 1; i += 4) {
      const dx = i + 2 - (x + w / 2), dy = j + 2 - (y + w / 2);
      if (j < y + w / 2 && dx * dx + dy * dy > (w / 2 - 1) ** 2) continue;
      R(g, i, j, 3, 3, cols[(rnd() * cols.length) | 0]);
    }
    R(g, x + w / 2 - 4, y + h / 2 - 6, 8, 18, '#f1e8d8'); R(g, x + w / 2 - 2, y + h / 2 - 10, 4, 4, '#e8b58c');   // saint
  };
  glass(74, 16, 22, 76); glass(224, 16, 22, 76);
  // murals (Last Supper on the left, the parish's patrons on the right)
  const mural = (x) => {
    R(g, x, 20, 46, 72, '#c7a15e'); R(g, x + 2, 22, 42, 68, '#e4c88e'); R(g, x + 2, 22, 42, 20, '#d9b774');
    const robe = ['#b0452f', '#6f8a4a', '#3f6aa6', '#c4803a', '#8a4f7d'];
    for (let i = 0; i < 5; i++) { const fx = x + 5 + i * 8, fy = 44 + (i % 2) * 6; R(g, fx, fy, 6, 22, robe[i]); R(g, fx + 1, fy - 5, 4, 5, '#dcaa80'); }
    R(g, x + 4, 72, 38, 5, '#f4efe2');
  };
  mural(16); mural(258);
  // side walls with Stations of the Cross and window slits
  R(g, 0, 112, 12, H - 112, '#ddd3bd'); R(g, 11, 112, 1, H - 112, '#b8a98c');
  R(g, W - 12, 112, 12, H - 112, '#ddd3bd'); R(g, W - 12, 112, 1, H - 112, '#b8a98c');
  for (const wy of [200, 290]) { R(g, 2, wy, 8, 44, '#8fb8d8'); R(g, 5, wy, 1, 44, '#3a3a44'); R(g, W - 10, wy, 8, 44, '#8fb8d8'); R(g, W - 6, wy, 1, 44, '#3a3a44'); }
  for (const sy of [180, 250, 340, 380]) { for (const sx of [2, W - 10]) { R(g, sx, sy, 8, 10, '#c9a24e'); R(g, sx + 1, sy + 1, 6, 8, '#efe3c4'); R(g, sx + 3, sy + 2, 2, 5, '#9a7a3a'); R(g, sx + 2, sy + 3, 4, 1, '#9a7a3a'); } }
  // entrance wall with open doors
  R(g, 0, 428, W, 12, '#ddd3bd'); R(g, 0, 428, W, 1, '#b8a98c');
  R(g, 140, 428, 40, 12, '#4a2c16'); R(g, 142, 430, 36, 10, '#2b190c'); R(g, 136, 428, 4, 12, '#6b4424'); R(g, 180, 428, 4, 12, '#6b4424');
  block(0, 0, W, 112); block(0, 0, 12, H); block(W - 12, 0, 12, H); block(0, 428, 140, 12); block(180, 428, W - 180, 12);

  /* ---------- standing objects (depth-sorted against Arek) ---------- */
  // altar
  R(o, 128, 116, 64, 8, '#fbfaf5'); R(o, 128, 124, 64, 18, '#f1efe6'); R(o, 128, 124, 64, 1, '#d6d2c6');
  for (let x = 128; x < 192; x += 4) { R(o, x, 136, 3, 3, '#ffffff'); R(o, x + 1, 139, 1, 2, '#e3ded0'); }
  R(o, 132, 142, 56, 6, '#cfcac0'); R(o, 132, 147, 56, 1, '#a9a397'); R(o, 150, 112, 20, 4, '#e0b23a'); R(o, 158, 106, 4, 6, '#e0b23a');
  put(126, 104, 68, 45, 148); block(128, 130, 64, 18);
  // four gold candles on a stand
  for (let i = 0; i < 4; i++) { R(o, 106 + i * 5, 104, 3, 20, '#e0b23a'); R(o, 107 + i * 5, 104, 1, 20, '#f6dc86'); R(o, 106 + i * 5, 113, 3, 1, '#a07a22'); }
  R(o, 104, 124, 22, 2, '#b98f2c'); R(o, 114, 126, 2, 18, '#b98f2c'); R(o, 109, 143, 12, 2, '#b98f2c');
  put(103, 98, 24, 48, 145); block(108, 138, 14, 7);
  // processional cross
  R(o, 199, 90, 2, 58, '#d8a93a'); R(o, 195, 94, 10, 2, '#e8c050'); R(o, 197, 146, 6, 2, '#b98f2c'); put(194, 86, 12, 63, 148); block(197, 144, 6, 4);
  // marble ambo with a cross
  R(o, 232, 118, 26, 32, '#d6d3cc'); R(o, 232, 118, 26, 4, '#eeebe5'); R(o, 256, 118, 2, 32, '#b3aea4'); R(o, 229, 115, 32, 4, '#e3e0d9');
  R(o, 243, 128, 4, 12, '#bdb8ae'); R(o, 240, 131, 10, 3, '#bdb8ae'); R(o, 236, 108, 18, 7, '#7a3a2a');
  put(228, 106, 34, 45, 150); block(232, 136, 26, 14);
  // red banner with the bishop's coat of arms
  R(o, 268, 94, 2, 40, '#6b4424'); R(o, 270, 96, 22, 30, '#c8231f'); R(o, 275, 101, 12, 14, '#f4efe2'); R(o, 278, 104, 6, 8, '#2e7a4a'); R(o, 280, 103, 2, 3, '#e0b23a');
  put(266, 92, 28, 44, 134); block(267, 130, 4, 4);
  // Lourdes Mary in a marble niche, with flowers and a harvest wreath
  R(o, 16, 100, 44, 50, '#dcd8cf'); R(o, 20, 100, 36, 34, '#c9c3b8'); R(o, 22, 104, 32, 28, '#8fa6c2');
  R(o, 32, 106, 12, 26, '#fbfaf5'); R(o, 34, 106, 8, 6, '#fbfaf5'); R(o, 35, 109, 6, 4, '#e8c0a0'); R(o, 36, 116, 4, 12, '#6fb6e8');
  R(o, 16, 134, 44, 16, '#e7e3db'); R(o, 16, 134, 44, 2, '#f5f2ec'); R(o, 16, 149, 44, 1, '#a9a397');
  for (let i = 0; i < 12; i++) R(o, 20 + (rnd() * 34 | 0), 128 + (rnd() * 8 | 0), 3, 3, ['#d8262c', '#f08aa8', '#ffffff', '#e8c248'][i % 4]);
  put(14, 98, 48, 53, 150); block(16, 134, 44, 16);
  // flags by the right wall
  for (let i = 0; i < 3; i++) { const fx = 290 + i * 5; R(o, fx, 96, 1, 64, '#8a6a3a'); R(o, fx - 1, 94, 3, 3, '#e0b23a'); R(o, fx + 1, 100, 4, 22, ['#c8231f', '#f4efe2', '#2f5fa8'][i]); }
  put(288, 92, 20, 70, 160); block(289, 154, 16, 6);
  // jubilee flowers with the gold "100"
  for (let i = 0; i < 70; i++) { const a = rnd() * Math.PI, r = rnd() * 22; R(o, 160 + Math.cos(a) * r * 1.1, 172 - Math.sin(a) * r * .8, 2, 2, ['#3d7a3a', '#56a04a', '#2d5f2c'][i % 3]); }
  for (let i = 0; i < 46; i++) { const a = rnd() * Math.PI, r = rnd() * 20; R(o, 160 + Math.cos(a) * r * 1.1, 171 - Math.sin(a) * r * .8, 3, 3, ['#d8262c', '#f08aa8', '#ffffff', '#e84a3a', '#f7c8d8'][i % 5]); }
  // outlined gold digits: dark edge first, then the gold stroke on top
  const one = (x, c, d) => { R(o, x + d, 156 + d, 3 - 2 * d, 14 - 2 * d, c); R(o, x - 2 + d, 157 + d, 3 - d, 2 - d, c); };
  const zero = (x, c, d) => { R(o, x + d, 156 + d, 9 - 2 * d, 3 - d, c); R(o, x + d, 167, 9 - 2 * d, 3 - d, c); R(o, x + d, 156 + d, 3 - d, 14 - 2 * d, c); R(o, x + 6, 156 + d, 3 - d, 14 - 2 * d, c); };
  for (const [c, d] of [['#8a6a10', 0], ['#f7d534', 1]]) { one(146, c, d); zero(151, c, d); zero(162, c, d); }
  R(o, 148, 157, 1, 11, '#fff3a0'); R(o, 152, 158, 1, 10, '#fff3a0'); R(o, 163, 158, 1, 10, '#fff3a0');
  put(134, 146, 52, 32, 176); block(142, 168, 36, 8);
  // pews: two blocks of light-pine benches seen from behind
  const pew = (x, y, w) => {
    R(o, x, y, w, 4, '#e8b060'); R(o, x, y + 4, w, 10, '#c98a3c'); R(o, x, y + 4, w, 1, '#f0c27a'); R(o, x, y + 13, w, 1, '#8a531c');
    for (const ex of [x - 2, x + w - 2]) { R(o, ex, y - 3, 4, 18, '#b0712a'); R(o, ex + 1, y - 3, 2, 2, '#e8b060'); }
    put(x - 3, y - 4, w + 6, 20, y + 14); block(x - 2, y + 4, w + 4, 11);
  };
  const pewRects = [];
  for (let i = 0; i < 7; i++) { const y = 190 + i * 28; pew(24, y, 114); pew(182, y, 114); pewRects.push([21, y - 4, 120, 20], [179, y - 4, 120, 20]); }
  // confessional by the entrance
  R(o, 16, 390, 34, 36, '#9a5f28'); R(o, 18, 392, 30, 4, '#c98a3c'); R(o, 22, 398, 10, 26, '#6b3b16'); R(o, 34, 398, 10, 26, '#7a4a1c');
  R(o, 38, 402, 2, 8, '#e0b23a'); R(o, 36, 404, 6, 2, '#e0b23a'); put(15, 388, 36, 39, 426); block(16, 410, 34, 16);
  // holy water font
  R(o, 196, 406, 12, 5, '#e7e3db'); R(o, 198, 407, 8, 2, '#8fb6d8'); R(o, 200, 411, 4, 10, '#cfcac0'); put(195, 405, 14, 17, 421); block(198, 414, 8, 7);

  // swap in AI sprites where they exist: clear every replaced box first, then draw, so neighbours stay intact
  const art = window.CHURCH_ART, boxes = [];
  for (const [k, r] of Object.entries(window.CHURCH_PIECES)) if (r && k !== 'backwall' && art[k]) boxes.push([art[k], r]);
  if (art.pew) for (const r of pewRects) boxes.push([art.pew, r]);
  for (const [, r] of boxes) o.clearRect(...r);
  for (const [img, r] of boxes) window.fitSprite(o, img, ...r);
  if (art.backwall) window.fitSprite(g, art.backwall, ...window.CHURCH_PIECES.backwall, true);
  const candles = art.candles ? [] : [0, 1, 2, 3].map(i => ({ x: 107.5 + i * 5, y: 103 }));
  const pois = [
    { key: 'altar', x: 160, y: 158, r: 30 }, { key: 'mary', x: 38, y: 160, r: 26 }, { key: 'glass', x: 86, y: 118, r: 22 },
    { key: 'flowers', x: 160, y: 186, r: 16 }, { key: 'confession', x: 60, y: 418, r: 20 }, { key: 'pew', x: 160, y: 300, r: 16 },
  ];
  return { w: W, h: H, top: 0, ground, obj, objects, solid, pois, candles, spawn: { x: 160, y: 418 }, exit: { x0: 140, x1: 180, y: 433 }, soltys: { x: 216, y: 158 } };
};

/* Sołtys (village head) sprite, drawn at 1 unit = 1 px, feet at (0,0). From Tomek's photo: grey hair, glasses,
   brown pinstripe suit, white shirt, grey tie, holding a harvest loaf on a lace cloth. */
window.drawSoltys = function drawSoltys(ctx, sx, sy, s, t) {
  const P = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
  const b = Math.round(Math.sin(t * 2) * .5);
  P(-5, -9, 4, 9, '#2b2420'); P(1, -9, 4, 9, '#2b2420'); P(-6, -1, 5, 2, '#111'); P(1, -1, 5, 2, '#111');   // legs, shoes
  P(-8, -26 + b, 16, 18, '#4a3326');                                                                              // jacket
  for (let x = -7; x < 8; x += 3) P(x, -26 + b, 1, 18, '#5e4535');                                                // pinstripes
  P(-3, -26 + b, 6, 9, '#f2f0ea'); P(-1, -25 + b, 2, 9, '#7d7f84'); P(-4, -26 + b, 1, 12, '#35251b'); P(3, -26 + b, 1, 12, '#35251b');
  P(-10, -24 + b, 3, 13, '#4a3326'); P(7, -24 + b, 3, 13, '#4a3326');                                             // arms
  P(-11, -15 + b, 22, 3, '#ffffff'); P(-10, -12 + b, 20, 1, '#e3e0d6');                                           // lace cloth
  P(-8, -19 + b, 16, 5, '#d9a45a'); P(-7, -20 + b, 14, 2, '#eac38a'); P(-5, -19 + b, 2, 2, '#f2d9a8'); P(2, -19 + b, 2, 2, '#f2d9a8');
  P(-6, -16 + b, 2, 2, '#3d9a55'); P(4, -16 + b, 2, 2, '#3d9a55');                                                // loaf + leaves
  P(-9, -14 + b, 3, 2, '#e8b58c'); P(6, -14 + b, 3, 2, '#e8b58c');                                                // hands
  P(-4, -36 + b, 8, 10, '#e2a988'); P(-5, -34 + b, 1, 4, '#d69478'); P(4, -34 + b, 1, 4, '#d69478');              // face, ears
  P(-4, -38 + b, 8, 3, '#8d8a86'); P(-5, -37 + b, 2, 3, '#8d8a86'); P(3, -37 + b, 2, 2, '#6f6c68');               // grey hair
  P(-4, -33 + b, 3, 2, '#2a2a2a'); P(1, -33 + b, 3, 2, '#2a2a2a'); P(-1, -33 + b, 2, 1, '#2a2a2a');               // glasses
  P(-3, -32 + b, 1, 1, '#9fc3e0'); P(2, -32 + b, 1, 1, '#9fc3e0'); P(-2, -29 + b, 4, 1, '#a9644e');
};
