/* KS "Sokół" Chłopków crest mown faintly into the grass, like a watermark.
   Standalone hook plugin: decoration only, no collision or interaction.
   Position is given in lat/lon and converted with map.json's bbox, so it
   stays on the same spot if the map is re-rendered. */
'use strict';
(() => {
  const SPOT = { lat: 52.27140, lon: 22.87699 };
  const SIZE = 280;   // map px across (2 px per metre -> ~140 m)
  const READY = () => {
    const A = window.ARK;
    if (!A || A.__sokolWatermarkInstalled) return;
    A.__sokolWatermarkInstalled = true;

    const { HOOKS, MAP, ctx } = A;
    const b = MAP.bbox, s = MAP.scale || 2;
    const x = (SPOT.lon - b[1]) * 111320 * Math.cos((b[0] + b[2]) / 2 * Math.PI / 180) * s;
    const y = (b[2] - SPOT.lat) * 110574 * s;
    let img = null;
    A.load('img/sokol_watermark.png').then(i => { img = i; }, () => {});

    HOOKS.world.push((push, S, inView) => {
      if (!img || !(inView(x - SIZE / 2, y) || inView(x + SIZE / 2, y) || inView(x, y - SIZE / 2) || inView(x, y + SIZE / 2))) return;
      // Lowest baseline: painted right after the ground, under everything else.
      push(-1e9, () => {
        const z = A.zoom, [sx, sy] = S(x - SIZE / 2, y - SIZE / 2);
        const smooth = ctx.imageSmoothingEnabled;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(img, sx, sy, SIZE * z, SIZE * z);
        ctx.imageSmoothingEnabled = smooth;
      });
    });

    window.__sokolWatermark = { x, y, size: SIZE };
  };

  window.addEventListener('ark-ready', READY);
  if (window.ARK) READY();
})();
