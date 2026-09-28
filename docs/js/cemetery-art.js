/* Small, non-interactive cemetery dressing for "Arek w Chłopkowie".
   The map already supplies the clearing, graves and approach path. This plugin
   adds only sparse muted details and leaves the map collision/path untouched. */
'use strict';
(() => {
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__cemeteryArtInstalled) return;
    A.__cemeteryArtInstalled = true;

    const { HOOKS, MAP, ctx } = A;
    const poi = (MAP.pois || []).find(p => p.key === 'cemetery')
      || (MAP.pois || []).find(p => p.key === 'cemetery_real');
    if (!poi || !Number.isFinite(poi.x) || !Number.isFinite(poi.y)) return;

    // The OSM cemetery clearing is roughly 224 x 194 map pixels. Keep the
    // overlay inside that footprint, with a wide opening on the south path.
    const C = { x: poi.x, y: poi.y, halfW: 112, halfH: 97 };
    const stone = ['#59615f', '#6d7670', '#818a80'];
    const edge = '#3f4847';
    const moss = '#697866';
    const grass = ['#71816b', '#7e8b72', '#64755f'];

    const graves = [
      { x: -76, y: -56, w: 11, h: 13, kind: 0, tone: 1 },
      { x: -45, y: -67, w: 13, h: 16, kind: 1, tone: 0 },
      { x:  48, y: -65, w: 12, h: 15, kind: 0, tone: 2 },
      { x:  79, y: -48, w: 11, h: 13, kind: 2, tone: 1 },
      { x: -83, y: -16, w: 13, h: 16, kind: 1, tone: 1 },
      { x:  67, y: -18, w: 12, h: 14, kind: 0, tone: 0 },
      { x: -69, y:  25, w: 11, h: 13, kind: 2, tone: 2 },
      { x:  54, y:  24, w: 13, h: 16, kind: 1, tone: 0 },
      { x: -42, y:  48, w: 12, h: 14, kind: 0, tone: 1 },
      { x:  42, y:  49, w: 11, h: 13, kind: 2, tone: 2 },
    ];
    const tufts = [
      [-101, -74, 0], [-26, -83, 1], [28, -80, 2], [99, -65, 1],
      [-101,  10, 2], [-27,  10, 0], [28,   8, 1], [99,  16, 2],
      [-98,  65, 1], [92,  66, 0], [-18,  75, 2], [18,  72, 1],
    ];

    const px = (sx, sy, s, x, y, w, h, colour) => {
      ctx.fillStyle = colour;
      ctx.fillRect(Math.round(sx + x * s), Math.round(sy + y * s), Math.max(1, Math.round(w * s)), Math.max(1, Math.round(h * s)));
    };
    const bar = (sx, sy, s, x, y, w, h, colour) => px(sx, sy, s, x, y, w, h, colour);

    function drawTuft(sx, sy, s, colour) {
      px(sx, sy, s, -1, 0, 2, 2, colour);
      px(sx, sy, s, -3, -3, 2, 3, colour);
      px(sx, sy, s, 1, -4, 2, 4, colour);
    }

    function drawGrave(grave, sx, sy, s) {
      // A tiny ground shadow makes the stones sit in the existing grassy map.
      px(sx, sy, s, -grave.w / 2 - 2, 1, grave.w + 4, 2, 'rgba(49,61,48,.32)');
      const x = -grave.w / 2, y = -grave.h, w = grave.w;
      px(sx, sy, s, x - 2, y + 2, w + 4, grave.h - 1, edge);
      if (grave.kind === 1) {
        // Plain cross marker: no plaque, lettering or invented epitaph.
        px(sx, sy, s, x + w * .42, y - 3, Math.max(2, w * .18), grave.h + 3, stone[grave.tone]);
        px(sx, sy, s, x + w * .12, y + 3, w * .76, Math.max(2, w * .18), stone[grave.tone]);
      } else {
        px(sx, sy, s, x, y + 3, w, grave.h - 3, stone[grave.tone]);
        if (grave.kind === 0) px(sx, sy, s, x + 2, y, w - 4, 4, stone[grave.tone]);
        else px(sx, sy, s, x + 2, y + 1, w - 4, 2, stone[grave.tone]);
        // A single weathered highlight keeps the shape readable at game zoom.
        px(sx, sy, s, x + 2, y + 5, 2, 2, '#9aa095');
      }
      px(sx, sy, s, x, y + grave.h - 2, w, 2, moss);
    }

    function drawBackFence(sx, sy, s) {
      const left = -C.halfW + 7, right = C.halfW - 7, top = -C.halfH + 8;
      // Low, broken rails follow the clearing edge without painting over it.
      bar(sx, sy, s, left, top, right - left, 2, edge);
      bar(sx, sy, s, left, top + 5, right - left, 2, '#69716d');
      bar(sx, sy, s, left, top, 3, C.halfH * .7, edge);
      bar(sx, sy, s, right - 3, top, 3, C.halfH * .7, edge);
      for (const x of [left + 2, left + 47, left + 94, right - 2]) {
        bar(sx, sy, s, x - 2, top - 4, 4, 10, '#69716d');
        bar(sx, sy, s, x - 1, top - 5, 2, 2, '#8a9288');
      }
    }

    function drawFrontFence(sx, sy, s) {
      const left = -C.halfW + 7, right = C.halfW - 7, y = C.halfH - 18;
      const opening = 45;
      bar(sx, sy, s, left, y, -opening / 2 - left, 2, edge);
      bar(sx, sy, s, opening / 2, y, right - opening / 2, 2, edge);
      bar(sx, sy, s, left, y + 5, -opening / 2 - left, 2, '#69716d');
      bar(sx, sy, s, opening / 2, y + 5, right - opening / 2, 2, '#69716d');
    }

    function drawGate(sx, sy, s) {
      // The gate is visibly open: its leaves sit outside a broad central path.
      px(sx, sy, s, -27, -30, 7, 34, edge);
      px(sx, sy, s,  20, -30, 7, 34, edge);
      px(sx, sy, s, -25, -28, 3, 29, stone[1]);
      px(sx, sy, s,  22, -28, 3, 29, stone[1]);
      px(sx, sy, s, -26, -32, 5, 3, '#8a9288');
      px(sx, sy, s,  21, -32, 5, 3, '#8a9288');

      // Open leaf panels, stepped like small pixel-art iron/wood gates.
      for (const y of [-23, -12]) {
        bar(sx, sy, s, -55, y, 27, 3, edge);
        bar(sx, sy, s,  28, y, 27, 3, edge);
      }
      for (const x of [-48, -36, 36, 48]) bar(sx, sy, s, x, -24, 3, 15, '#68716c');
      bar(sx, sy, s, -55, -24, 3, 3, '#899188');
      bar(sx, sy, s,  52, -24, 3, 3, '#899188');
      px(sx, sy, s, -31, 2, 15, 2, 'rgba(48,58,48,.35)');
      px(sx, sy, s,  16, 2, 15, 2, 'rgba(48,58,48,.35)');
    }

    HOOKS.world.push((push, S, inView) => {
      const [cx, cy] = S(C.x, C.y);
      if (inView(C.x, C.y)) push(C.y - C.halfH + 12, () => drawBackFence(cx, cy, A.zoom));
      for (const [x, y, tone] of tufts) {
        const wx = C.x + x, wy = C.y + y;
        if (inView(wx, wy)) push(wy, () => drawTuft(...S(wx, wy), A.zoom, grass[tone]));
      }
      for (const grave of graves) {
        const wx = C.x + grave.x, wy = C.y + grave.y;
        if (inView(wx, wy)) push(wy, () => drawGrave(grave, ...S(wx, wy), A.zoom));
      }
      if (inView(C.x, C.y + C.halfH - 18)) {
        push(C.y + C.halfH - 18, () => drawFrontFence(cx, cy, A.zoom));
        push(C.y + C.halfH + 3, () => drawGate(...S(C.x, C.y + C.halfH), A.zoom));
      }
    });

    // A small diagnostic surface keeps browser smoke tests independent of
    // private hook-array ordering; it has no gameplay or interaction effect.
    window.__cemeteryArt = { center: { x: C.x, y: C.y }, halfWidth: C.halfW, halfHeight: C.halfH };
  };

  window.addEventListener('ark-ready', READY);
  if (window.ARK) READY();
})();
